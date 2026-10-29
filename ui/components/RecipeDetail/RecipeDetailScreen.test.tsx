/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "./fixtures";
import { ToastProvider, ToastViewport } from "@/components/Toast";

import { RecipeDetailScreen } from "./RecipeDetailScreen";

const replace = vi.fn();
const router = { replace };
let search = "";

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(search),
}));

function stub(replies: { status: number; body?: unknown }[]) {
  const queue = [...replies];
  const mock = vi.fn(async () => {
    const reply = queue.shift() ?? replies[replies.length - 1];
    return new Response(reply.status === 204 ? null : JSON.stringify(reply.body ?? {}), {
      status: reply.status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("RecipeDetailScreen", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    replace.mockReset();
    search = "";
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function render() {
    await act(async () => {
      root.render(<RecipeDetailScreen recipeId="r1" locale="en" />);
    });
    await flush();
  }

  it("shows loading, then the recipe with Back to the list it came from", async () => {
    search = "from=" + encodeURIComponent("/kitchens/k1");
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        await gate;
        return new Response(JSON.stringify(recipeFixture()), { status: 200 });
      }),
    );
    await act(async () => {
      root.render(<RecipeDetailScreen recipeId="r1" locale="en" />);
    });
    expect(container.textContent).toContain("Loading recipe");
    await act(async () => release());
    await flush();
    expect(container.querySelector("h1")?.textContent).toBe("Tomato rice");
    expect(container.querySelector("a[aria-label=Back]")?.getAttribute("href")).toBe("/kitchens/k1");
  });

  it("falls back to the notebook when from is not a list of this app", async () => {
    search = "from=" + encodeURIComponent("https://evil.example");
    stub([{ status: 200, body: recipeFixture() }]);
    await render();
    expect(container.querySelector("a[aria-label=Back]")?.getAttribute("href")).toBe(
      "/notebooks/nb1",
    );
  });

  it("says the recipe isn't available on a 404", async () => {
    stub([{ status: 404, body: { code: "recipe_not_found" } }]);
    await render();
    expect(container.textContent).toContain("That recipe isn't available.");
    expect(container.querySelector("h1")).toBeNull();
  });

  it("offers a retry after a failure", async () => {
    const mock = stub([{ status: 500 }, { status: 200, body: recipeFixture() }]);
    await render();
    expect(container.textContent).toContain("Could not load the recipe.");
    const retry = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Try again",
    );
    await act(async () => retry?.click());
    await flush();
    expect(mock).toHaveBeenCalledTimes(2);
    expect(container.querySelector("h1")?.textContent).toBe("Tomato rice");
  });

  it("asks before deleting and returns to the list afterwards", async () => {
    search = "from=" + encodeURIComponent("/notebooks/nb1?page=2");
    const mock = stub([{ status: 200, body: recipeFixture() }, { status: 204 }]);
    await render();
    const open = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Delete",
    );
    act(() => open?.click());
    expect(document.body.textContent).toContain("Delete “Tomato rice”?");
    expect(mock).toHaveBeenCalledTimes(1);
    const confirm = Array.from(document.querySelectorAll("button")).filter(
      (b) => b.textContent === "Delete",
    );
    await act(async () => confirm[confirm.length - 1].click());
    await flush();
    expect(mock).toHaveBeenCalledTimes(2);
    expect(replace).toHaveBeenCalledWith("/notebooks/nb1?page=2");
  });

  it("links Edit with the same list to return to", async () => {
    search = "from=" + encodeURIComponent("/notebooks/nb1?page=2");
    stub([{ status: 200, body: recipeFixture() }]);
    await render();
    const edit = Array.from(container.querySelectorAll("a")).find((a) => a.textContent === "Edit");
    expect(edit?.getAttribute("href")).toBe(
      `/recipes/r1/edit?from=${encodeURIComponent("/notebooks/nb1?page=2")}`,
    );
  });

  it("keeps the servings out of the Edit link and out of where Delete returns to", async () => {
    search = "from=" + encodeURIComponent("/notebooks/nb1?page=2");
    stub([{ status: 200, body: recipeFixture() }, { status: 204 }]);
    await render();
    const edit = () =>
      Array.from(container.querySelectorAll("a")).find((a) => a.textContent === "Edit");
    const before = edit()?.getAttribute("href");

    const input = container.querySelector("input") as HTMLInputElement;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, "6");
    act(() => {
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(container.textContent).toContain("1.5");
    expect(edit()?.getAttribute("href")).toBe(before);

    act(() =>
      Array.from(container.querySelectorAll("button"))
        .find((b) => b.textContent === "Delete")
        ?.click(),
    );
    const confirm = Array.from(document.querySelectorAll("button")).filter(
      (b) => b.textContent === "Delete",
    );
    await act(async () => confirm[confirm.length - 1].click());
    await flush();
    expect(replace).toHaveBeenCalledWith("/notebooks/nb1?page=2");
  });

  it("adds a kitchen recipe to my cart draft and shows the editing bar (spec 022)", async () => {
    const kitchenRecipe = recipeFixture({
      notebook: { id: "nb1", name: "Home", kind: "kitchen", kitchen_id: "k1" },
      in_cart: false,
      cart_editor: null,
      editor: null,
    });
    const editingCart = {
      kitchen_id: "k1",
      people: 2,
      people_is_default: true,
      entries: [],
      editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" },
      draft: {
        people: 2,
        people_is_default: true,
        entries: [
          {
            recipe_id: "r1",
            title: "Tomato rice",
            notebook_id: "nb1",
            notebook_name: "Home",
            base_servings: 4,
            meals: 1,
            factor: "0.5",
          },
        ],
        dropped_recipe_ids: [],
      },
      can_edit: true,
    };
    const mock = stub([
      { status: 200, body: kitchenRecipe },
      { status: 200, body: editingCart },
    ]);
    await render();
    const add = container.querySelector<HTMLButtonElement>('button[aria-label="Add to cart"]');
    await act(async () => add?.click());
    await flush();
    const [url, init] = mock.mock.calls[1] as unknown as [string, RequestInit];
    expect(url).toBe("/api/kitchens/k1/cart/draft/items");
    expect(init.method).toBe("POST");
    expect(container.querySelector('button[aria-label="Remove from cart"]')).not.toBeNull();
    // No message on success and no editing bar on the recipe page (FR-017a).
    expect(container.textContent).not.toContain("You're editing the cart.");
  });

  it("toasts the refusal when someone else edits the cart", async () => {
    const kitchenRecipe = recipeFixture({
      notebook: { id: "nb1", name: "Home", kind: "kitchen", kitchen_id: "k1" },
      in_cart: false,
      cart_editor: { alias: "ben", is_me: false, idle_expires_at: null },
      editor: null,
    });
    stub([
      { status: 200, body: kitchenRecipe },
      { status: 409, body: { code: "cart_locked", editor_alias: "ben" } },
      { status: 200, body: kitchenRecipe },
    ]);
    await act(async () => {
      root.render(
        <ToastProvider>
          <RecipeDetailScreen recipeId="r1" locale="en" />
          <ToastViewport />
        </ToastProvider>,
      );
    });
    await flush();
    const add = container.querySelector<HTMLButtonElement>('button[aria-label="Add to cart"]');
    expect(add?.disabled).toBe(false);
    await act(async () => add?.click());
    await flush();
    expect(container.querySelector("[data-toast-viewport]")?.textContent).toBe(
      "ben is editing the cart",
    );
  });

  it("shows no cart button for a personal recipe", async () => {
    stub([{ status: 200, body: recipeFixture({ in_cart: null, cart_editor: null }) }]);
    await render();
    expect(container.querySelector('button[aria-label="Add to cart"]')).toBeNull();
  });
});
