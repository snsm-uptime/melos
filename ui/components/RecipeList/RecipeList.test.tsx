/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotebookResult } from "@/lib/notebooksClient";
import type { RecipeCard, RecipePage } from "@/lib/recipesClient";

import { RecipeList } from "./RecipeList";

vi.mock("@/components/AddRecipeCallToAction", () => ({
  AddRecipeCallToAction: () => <button type="button">Add a recipe</button>,
}));

function card(title: string): RecipeCard {
  return {
    id: title,
    title,
    author_alias: "ana",
    ingredient_count: 2,
    notebook_id: "n1",
    notebook_name: "Home notebook",
    created_at: "2026-10-27T12:00:00Z",
  };
}

function page(titles: string[], pageNo = 1, totalPages = 1): NotebookResult<RecipePage> {
  return {
    ok: true,
    value: {
      items: titles.map(card),
      page: pageNo,
      page_size: 12,
      total: titles.length,
      total_pages: totalPages,
    },
  };
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("RecipeList", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onChange = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    onChange.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.useRealTimers();
  });

  async function render(
    load: (p: number, q: string) => Promise<NotebookResult<RecipePage>>,
    props: Partial<Parameters<typeof RecipeList>[0]> = {},
  ) {
    await act(async () => {
      root.render(
        <RecipeList
          scope="notebook"
          locale="en"
          page={1}
          q=""
          onChange={onChange}
          load={load}
          returnPath="/notebooks/n1"
          {...props}
        />,
      );
    });
    await flush();
  }

  it("puts the filter action beside the filter, and wraps the cards in the wrap layout", async () => {
    await render(async () => page(["Lentil soup"]), {
      filterAction: <button type="button">Add recipe</button>,
      layout: "wrap",
    });
    const filter = container.querySelector("input[type=search]") as HTMLInputElement;
    const action = Array.from(container.querySelectorAll("button")).find(
      (el) => el.textContent === "Add recipe",
    );
    expect(action?.parentElement).toBe(filter.parentElement?.parentElement);
    expect(container.querySelector("ul")?.className).toContain("auto-fill");
  });

  it("shows loading, then the cards", async () => {
    let finish: (value: NotebookResult<RecipePage>) => void = () => {};
    await render(() => new Promise((resolve) => (finish = resolve)));
    expect(container.textContent).toContain("Loading recipes");
    await act(async () => finish(page(["Soup", "Tart"])));
    expect(Array.from(container.querySelectorAll("h3")).map((h) => h.textContent)).toEqual([
      "Soup",
      "Tart",
    ]);
  });

  it("links each card to its detail and remembers the page and filter", async () => {
    await render(async () => page(["Soup"], 2, 3), { page: 2, q: "soup" });
    const href = container.querySelector("h3 a")?.getAttribute("href");
    expect(href).toBe(`/recipes/Soup?from=${encodeURIComponent("/notebooks/n1?page=2&q=soup")}`);
  });

  it("shows the notebook name on kitchen lists only", async () => {
    await render(async () => page(["Soup"]), { scope: "kitchen" });
    expect(container.textContent).toContain("Home notebook");
  });

  it("has no pager for one page, and a pager with the current page marked for several", async () => {
    await render(async () => page(["Soup"]));
    expect(container.querySelector("nav")).toBeNull();

    await render(async () => page(["Soup"], 2, 3), { page: 2 });
    expect(container.textContent).toContain("Page 2 of 3");
    const current = container.querySelector("[aria-current=page]");
    expect(current?.textContent).toBe("2");
  });

  it("goes to the next, previous and numbered page keeping the filter", async () => {
    await render(async () => page(["Soup"], 2, 3), { page: 2, q: "soup" });
    const buttons = Array.from(container.querySelectorAll("nav button"));
    const byText = (text: string) => buttons.find((b) => b.textContent === text) as HTMLElement;

    await act(async () => byText("Next").click());
    expect(onChange).toHaveBeenLastCalledWith(3, "soup");
    await act(async () => byText("Previous").click());
    expect(onChange).toHaveBeenLastCalledWith(1, "soup");
    await act(async () => byText("3").click());
    expect(onChange).toHaveBeenLastCalledWith(3, "soup");
  });

  it("disables Previous on the first page and Next on the last", async () => {
    await render(async () => page(["Soup"], 1, 2));
    const [previous, , , next] = Array.from(container.querySelectorAll("nav button")) as HTMLButtonElement[];
    expect(previous.disabled).toBe(true);
    expect(next.disabled).toBe(false);
  });

  it("applies typed text after a pause and returns to page 1", async () => {
    await render(async () => page(["Soup"], 2, 3), { page: 2 });
    const input = container.querySelector("input") as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;

    await act(async () => {
      setter.call(input, "onion");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(onChange).not.toHaveBeenCalled();
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(onChange).toHaveBeenCalledWith(1, "onion");
  });

  it("limits the filter text to 100 characters", async () => {
    await render(async () => page(["Soup"]));
    expect(container.querySelector("input")?.getAttribute("maxlength")).toBe("100");
  });

  it("tells an empty list from a list with no match, and clears the filter", async () => {
    await render(async () => page([]));
    expect(container.textContent).toContain("No recipes in this notebook yet.");

    await render(async () => page([]), { q: "zzz" });
    expect(container.textContent).toContain('No recipes match "zzz".');
    const clear = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Clear filter",
    ) as HTMLElement;
    await act(async () => clear.click());
    expect(onChange).toHaveBeenLastCalledWith(1, "");
  });

  it("offers add-recipe in the empty state only when candidates are given", async () => {
    await render(async () => page([]));
    expect(container.textContent).not.toContain("Add a recipe");

    await render(async () => page([]), {
      addCandidates: [{ id: "n1", name: "Mine", kind: "personal", kitchenId: null }],
    });
    expect(container.textContent).toContain("Add a recipe");
  });

  it("shows not found for a 404", async () => {
    await render(async () => ({ ok: false, status: 404, code: "notebook_not_found" }));
    expect(container.textContent).toContain("This notebook is unavailable.");
  });

  it("shows an error with retry for other failures", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 0, code: null })
      .mockResolvedValue(page(["Soup"]));
    await render(load);
    expect(container.textContent).toContain("Could not load recipes. Try again.");
    const retry = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Try again",
    ) as HTMLElement;
    await act(async () => retry.click());
    await flush();
    expect(container.querySelector("h3")?.textContent).toBe("Soup");
  });
});
