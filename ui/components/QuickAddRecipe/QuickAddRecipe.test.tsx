/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  replaceMembershipKitchens,
  resetMembershipKitchensStore,
} from "@/app/kitchens/membershipKitchensStore";
import { clearCapture, getCaptureState } from "@/lib/capture/captureStore";

import { QuickAddRecipe, kitchenFromPath } from "./QuickAddRecipe";

const nav = vi.hoisted(() => ({ pathname: "/kitchens/k1/shopping-lists" }));
vi.mock("next/navigation", () => ({
  usePathname: () => nav.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function notebook(id: string, name: string, extra: Record<string, unknown> = {}) {
  return {
    id,
    name,
    kind: "personal",
    owner_alias: "ana",
    access: "owner",
    is_default: false,
    recipe_count: 1,
    kitchen_id: null,
    kitchen_is_archived: null,
    origin_notebook_name: null,
    is_snapshot: false,
    is_own_capture_notebook: false,
    ...extra,
  };
}

const kitchen = (id: string, name: string, archived = false) => ({
  id,
  name,
  owner_id: "u1",
  role: "owner",
  is_archived: archived,
});

let container: HTMLDivElement;
let root: Root;

function fetchMock(input: RequestInfo | URL): Promise<Response> {
  const url = String(input);
  if (url === "/api/notebooks") {
    return Promise.resolve(
      json(200, {
        notebooks: [
          notebook("p-other", "Weekend"),
          notebook("p-default", "ana's Notebook", { is_default: true }),
        ],
      }),
    );
  }
  if (url === "/api/notebooks/kitchens/k1") {
    return Promise.resolve(
      json(200, {
        notebooks: [
          notebook("kn-ben", "ben's (Home) Notebook", { kind: "kitchen", kitchen_id: "k1" }),
          notebook("kn-ana", "ana's (Home) Notebook", {
            kind: "kitchen",
            kitchen_id: "k1",
            is_own_capture_notebook: true,
          }),
        ],
      }),
    );
  }
  return Promise.resolve(json(200, { max_text_chars: 5000 }));
}

async function render() {
  await act(async () => root.render(<QuickAddRecipe />));
  await act(async () => {
    for (let i = 0; i < 6; i += 1) await Promise.resolve();
  });
}

function button(label: string): HTMLButtonElement | null {
  return (
    (Array.from(document.querySelectorAll("button")).find(
      (el) => el.getAttribute("aria-label") === label || el.querySelector("span")?.textContent === label,
    ) as HTMLButtonElement | undefined) ?? null
  );
}

async function open() {
  await act(async () => button("Add recipe")!.click());
}

function options(): string[] {
  return Array.from(document.querySelectorAll("[role='list'] button")).map(
    (el) => el.querySelector("span")?.textContent ?? "",
  );
}

beforeEach(() => {
  prefs.value = null;
  nav.pathname = "/kitchens/k1/shopping-lists";
  clearCapture();
  replaceMembershipKitchens([kitchen("k1", "Home"), kitchen("k2", "Cabin")]);
  vi.stubGlobal("fetch", vi.fn(fetchMock));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  resetMembershipKitchensStore();
  vi.unstubAllGlobals();
});

describe("kitchenFromPath", () => {
  it("reads the kitchen of a kitchen address only", () => {
    expect(kitchenFromPath("/kitchens/k1")).toBe("k1");
    expect(kitchenFromPath("/kitchens/k1/cart")).toBe("k1");
    expect(kitchenFromPath("/notebooks")).toBeNull();
  });
});

describe("QuickAddRecipe (spec 069 US2)", () => {
  it("opens URL, Picture, Text and Recipe from another notebook", async () => {
    await render();
    await open();
    expect(options()).toEqual(["URL", "Picture", "Text", "Recipe from another notebook"]);
  });

  it("inside a kitchen, Text captures into my own kitchen notebook and returns to this page", async () => {
    await render();
    await open();
    await act(async () => button("Text")!.click());

    const notebook = getCaptureState().notebook;
    expect(notebook?.id).toBe("kn-ana");
    expect(notebook?.returnPath).toBe("/kitchens/k1/shopping-lists");
    expect(notebook?.opener).toBe("quick-add");
  });

  it("outside a kitchen, Text captures into the default personal notebook", async () => {
    nav.pathname = "/notebooks";
    await render();
    await open();
    await act(async () => button("Text")!.click());

    expect(getCaptureState().notebook?.id).toBe("p-default");
    expect(getCaptureState().notebook?.returnPath).toBe("/notebooks");
  });

  it("outside a kitchen with two kitchens, the copy asks which kitchen", async () => {
    nav.pathname = "/notebooks";
    await render();
    await open();
    await act(async () => button("Recipe from another notebook")!.click());
    await act(async () => {
      for (let i = 0; i < 6; i += 1) await Promise.resolve();
    });

    const select = Array.from(document.querySelectorAll("select")).find((el) =>
      Array.from(el.options).some((o) => o.textContent === "Cabin"),
    );
    expect(select).toBeTruthy();
  });

  it("with no active kitchen, the option is disabled with a reason", async () => {
    nav.pathname = "/notebooks";
    replaceMembershipKitchens([kitchen("k1", "Home", true)]);
    await render();
    await open();

    const option = Array.from(document.querySelectorAll("[role='list'] button")).at(-1)!;
    expect(option.getAttribute("aria-disabled")).toBe("true");
    expect(option.textContent).toContain("Join or create a kitchen first.");
  });

  it("inside an archived kitchen, the option is not shown", async () => {
    replaceMembershipKitchens([kitchen("k1", "Home", true)]);
    await render();
    await open();
    expect(options()).toEqual(["URL", "Picture", "Text"]);
  });

  it("is labelled in Spanish", async () => {
    prefs.value = { locale: "es" };
    await render();
    expect(button("Agregar receta")).not.toBeNull();
  });
});
