/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotebookRecipesScreen } from "./NotebookRecipesScreen";

const replace = vi.fn();
const router = { replace };
let search = "";

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/notebooks/nb-1",
  useSearchParams: () => new URLSearchParams(search),
}));

vi.mock("@/components/AddRecipeCallToAction", () => ({
  AddRecipeCallToAction: () => <button type="button">Add a recipe</button>,
}));

const notebook = {
  id: "nb-1",
  name: "ana's Notebook",
  kind: "personal",
  owner_alias: "ana",
  access: "owner",
  is_default: true,
  kitchen_id: null,
  kitchen_is_archived: null,
};

function stub(handlers: { notebook: { status: number; body: unknown }; recipes?: unknown }) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      const reply = url.includes("/recipes")
        ? { status: 200, body: handlers.recipes }
        : handlers.notebook;
      return {
        ok: reply.status >= 200 && reply.status < 300,
        status: reply.status,
        json: async () => reply.body,
      };
    }),
  );
  return calls;
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("NotebookRecipesScreen", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    replace.mockReset();
    search = "";
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function render() {
    await act(async () => {
      root.render(<NotebookRecipesScreen notebookId="nb-1" locale="en" />);
    });
    await flush();
  }

  it("shows the notebook name and its recipes from the address page and filter", async () => {
    search = "page=2&q=soup";
    const calls = stub({
      notebook: { status: 200, body: notebook },
      recipes: {
        items: [
          {
            id: "r1",
            title: "Lentil soup",
            author_alias: "ana",
            ingredient_count: 3,
            notebook_id: "nb-1",
            notebook_name: "ana's Notebook",
            created_at: "2026-10-27T12:00:00Z",
          },
        ],
        page: 2,
        page_size: 12,
        total: 13,
        total_pages: 2,
      },
    });

    await render();

    expect(container.querySelector("h1")?.textContent).toBe("ana's Notebook");
    expect(container.querySelector("h3")?.textContent).toBe("Lentil soup");
    expect(calls).toContain("/api/notebooks/nb-1/recipes?page=2&q=soup");
  });

  it("shows an empty notebook message with the add-recipe action", async () => {
    stub({
      notebook: { status: 200, body: notebook },
      recipes: { items: [], page: 1, page_size: 12, total: 0, total_pages: 1 },
    });

    await render();

    expect(container.textContent).toContain("No recipes in this notebook yet.");
    expect(container.textContent).toContain("Add a recipe");
  });

  it("shows no add-recipe action for an archived kitchen's notebook", async () => {
    stub({
      notebook: {
        status: 200,
        body: { ...notebook, kind: "kitchen", kitchen_id: "k1", kitchen_is_archived: true },
      },
      recipes: { items: [], page: 1, page_size: 12, total: 0, total_pages: 1 },
    });

    await render();

    expect(container.textContent).not.toContain("Add a recipe");
  });

  it("shows the not found message for a notebook the member cannot see", async () => {
    stub({ notebook: { status: 404, body: { code: "notebook_not_found" } } });

    await render();

    expect(container.textContent).toContain("This notebook is unavailable.");
    expect(container.querySelector("input")).toBeNull();
  });

  it("redirects to the alias step when an alias is required", async () => {
    stub({ notebook: { status: 403, body: { code: "alias_required" } } });

    await render();

    expect(replace).toHaveBeenCalledWith("/alias?returnTo=%2Fnotebooks%2Fnb-1");
  });
});
