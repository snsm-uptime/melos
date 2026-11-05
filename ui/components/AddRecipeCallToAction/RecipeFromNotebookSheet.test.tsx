/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeFromNotebookSheet } from "./RecipeFromNotebookSheet";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function notebook(id: string, name: string, kind: "personal" | "kitchen", count: number, isDefault = false) {
  return {
    id,
    name,
    kind,
    owner_alias: "ana",
    access: kind === "personal" ? "owner" : "kitchen_member",
    is_default: isDefault,
    recipe_count: count,
    kitchen_id: kind === "kitchen" ? "k1" : null,
    kitchen_is_archived: kind === "kitchen" ? false : null,
    origin_notebook_name: null,
    is_snapshot: false,
    is_own_capture_notebook: false,
  };
}

function page(titles: string[]) {
  return {
    items: titles.map((title, index) => ({
      id: `r${index + 1}`,
      title,
      author_alias: "ana",
      ingredient_count: 3,
      notebook_id: "p1",
      notebook_name: "ana's Notebook",
      created_at: "2026-11-04T00:00:00Z",
    })),
    page: 1,
    page_size: 20,
    total: titles.length,
    total_pages: 1,
  };
}

type Copy = { status: number; body: unknown };

let container: HTMLDivElement;
let root: Root;
let notebooks: unknown[];
let copies: Copy[];
let posted: { url: string; body: { source_recipe_id: string; on_repeat: string } }[];
let recipeQueries: string[];

function fetchMock(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = String(input);
  if (url === "/api/notebooks") return Promise.resolve(json(200, { notebooks }));
  if (url.startsWith("/api/notebooks/p1/recipes")) {
    recipeQueries.push(url);
    const q = new URL(url, "http://x").searchParams.get("q") ?? "";
    const titles = ["Lentil soup", "Pea soup"].filter((title) =>
      title.toLowerCase().includes(q.toLowerCase()),
    );
    return Promise.resolve(json(200, page(titles)));
  }
  if (url.endsWith("/recipe-copies")) {
    posted.push({ url, body: JSON.parse(String(init?.body)) });
    const next = copies.shift() ?? { status: 500, body: {} };
    return Promise.resolve(json(next.status, next.body));
  }
  return Promise.resolve(json(404, {}));
}

async function flush() {
  await act(async () => {
    for (let i = 0; i < 5; i += 1) await Promise.resolve();
  });
}

async function render(props: Partial<Parameters<typeof RecipeFromNotebookSheet>[0]> = {}) {
  const onDone = props.onDone ?? vi.fn();
  await act(async () => {
    root.render(
      <RecipeFromNotebookSheet open onClose={vi.fn()} kitchenId="k1" {...props} onDone={onDone} />,
    );
  });
  await flush();
  return onDone;
}

function byText(text: string): HTMLButtonElement | null {
  return (
    (Array.from(document.querySelectorAll("button")).find(
      (el) => el.textContent?.trim() === text,
    ) as HTMLButtonElement | undefined) ?? null
  );
}

function radios(): HTMLInputElement[] {
  return Array.from(document.querySelectorAll("input[type='radio']"));
}

async function pick(index: number) {
  await act(async () => radios()[index].click());
}

async function click(text: string) {
  await act(async () => byText(text)!.click());
  await flush();
}

const copied = {
  recipe_id: "c1",
  notebook_id: "kn1",
  notebook_name: "ana's (Home) Notebook",
  overwritten: false,
};

beforeEach(() => {
  prefs.value = null;
  notebooks = [
    notebook("p1", "ana's Notebook", "personal", 2, true),
    notebook("kn", "Home notebook", "kitchen", 4),
  ];
  copies = [];
  posted = [];
  recipeQueries = [];
  vi.stubGlobal("fetch", vi.fn(fetchMock));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("RecipeFromNotebookSheet (spec 069)", () => {
  it("lists only personal notebooks and their recipes", async () => {
    await render();
    expect(document.querySelector("select")).toBeNull(); // one personal notebook: no picker
    expect(radios().map((el) => el.parentElement?.textContent)).toEqual(["Lentil soup", "Pea soup"]);
    expect(recipeQueries[0]).toContain("/api/notebooks/p1/recipes");
  });

  it("searches by recipe name", async () => {
    await render();
    const search = document.querySelector("input[type='search']") as HTMLInputElement;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      setter.call(search, "pea");
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await flush();
    expect(radios().map((el) => el.parentElement?.textContent)).toEqual(["Pea soup"]);
    expect(recipeQueries.at(-1)).toContain("q=pea");
  });

  it("says so and offers no confirm when the personal notebooks have no recipes", async () => {
    notebooks = [notebook("p1", "ana's Notebook", "personal", 0, true)];
    await render();
    expect(document.body.textContent).toContain("Your personal notebooks have no recipes yet.");
    expect(byText("Add to kitchen")).toBeNull();
  });

  it("copies the picked recipe into the open kitchen", async () => {
    copies = [{ status: 201, body: copied }];
    const onDone = await render();
    expect(byText("Add to kitchen")!.disabled).toBe(true);

    await pick(0);
    await click("Add to kitchen");

    expect(posted).toEqual([
      {
        url: "/api/notebooks/kitchens/k1/recipe-copies",
        body: { source_recipe_id: "r1", on_repeat: "ask" },
      },
    ]);
    expect(onDone).toHaveBeenCalledWith(copied, "k1");
  });

  it.each([
    ["Add another copy", "add"],
    ["Overwrite", "overwrite"],
  ])("on a repeat, %s posts on_repeat=%s", async (choice, onRepeat) => {
    copies = [
      {
        status: 409,
        body: {
          code: "recipe_already_in_kitchen",
          existing_recipe_id: "c0",
          notebook_name: "ana's (Home) Notebook",
        },
      },
      { status: onRepeat === "add" ? 201 : 200, body: { ...copied, overwritten: onRepeat === "overwrite" } },
    ];
    const onDone = await render();
    await pick(0);
    await click("Add to kitchen");

    expect(document.body.textContent).toContain("Already in this kitchen");
    expect(document.body.textContent).toContain("ana's (Home) Notebook");
    await click(choice);

    expect(posted.map((p) => p.body.on_repeat)).toEqual(["ask", onRepeat]);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("on a repeat, Cancel posts nothing more", async () => {
    copies = [{ status: 409, body: { code: "recipe_already_in_kitchen", notebook_name: "N" } }];
    const onDone = await render();
    await pick(0);
    await click("Add to kitchen");
    await click("Cancel");

    expect(posted).toHaveLength(1);
    expect(onDone).not.toHaveBeenCalled();
    expect(byText("Add to kitchen")).not.toBeNull();
  });

  it("explains a recipe deleted while the picker was open", async () => {
    copies = [{ status: 404, body: { code: "recipe_not_found" } }];
    await render();
    await pick(0);
    await click("Add to kitchen");
    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That recipe is no longer available. Pick another one.",
    );
  });

  it("outside a kitchen asks which kitchen when there are two", async () => {
    copies = [{ status: 201, body: copied }];
    const onDone = await render({
      kitchenId: null,
      kitchens: [
        { id: "k1", name: "Home" },
        { id: "k2", name: "Cabin" },
      ],
    });
    const select = document.querySelector("select") as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual(["Kitchen", "Home", "Cabin"]);
    await pick(0);
    expect(byText("Add to kitchen")!.disabled).toBe(true);

    await act(async () => {
      select.value = "k2";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await click("Add to kitchen");

    expect(posted[0].url).toBe("/api/notebooks/kitchens/k2/recipe-copies");
    expect(onDone).toHaveBeenCalledWith(copied, "k2");
  });

  it("outside a kitchen preselects the only kitchen", async () => {
    await render({ kitchenId: null, kitchens: [{ id: "k1", name: "Home" }] });
    expect(document.querySelector("select")).toBeNull();
    await pick(0);
    expect(byText("Add to kitchen")!.disabled).toBe(false);
  });

  it("reads in Spanish", async () => {
    prefs.value = { locale: "es" };
    await render();
    expect(document.body.textContent).toContain("Receta de otro cuaderno");
    expect(byText("Agregar a la cocina")).not.toBeNull();
  });
});
