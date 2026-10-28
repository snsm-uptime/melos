/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "./fixtures";
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
});
