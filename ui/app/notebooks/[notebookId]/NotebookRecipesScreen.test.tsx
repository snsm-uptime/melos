/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/AppShell";

import { NotebookRecipesScreen } from "./NotebookRecipesScreen";

const replace = vi.fn();
const push = vi.fn();
const router = { replace, push };
let search = "";

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/notebooks/nb-1",
  useSearchParams: () => new URLSearchParams(search),
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en" }),
  useOptionalPreferences: () => ({ locale: "en" }),
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
    push.mockReset();
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
      root.render(
        <AppShell>
          <NotebookRecipesScreen notebookId="nb-1" locale="en" />
        </AppShell>,
      );
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

    expect(container.querySelector("header h1")?.textContent).toBe("ana's Notebook");
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

  const oneRecipe = {
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
    page: 1,
    page_size: 12,
    total: 13,
    total_pages: 2,
  };

  async function clickBack() {
    await act(async () => {
      (container.querySelector('header button[aria-label="Back"]') as HTMLButtonElement).click();
    });
  }

  it("has a Back control that returns to the Notebook tab by default", async () => {
    stub({ notebook: { status: 200, body: notebook }, recipes: oneRecipe });
    await render();

    await clickBack();

    expect(push).toHaveBeenCalledWith("/notebooks");
  });

  it("returns to the kitchen list it was opened from", async () => {
    search = `from=${encodeURIComponent("/kitchens/k1?page=2&q=soup")}`;
    stub({ notebook: { status: 200, body: notebook }, recipes: oneRecipe });
    await render();

    await clickBack();

    expect(push).toHaveBeenCalledWith("/kitchens/k1?page=2&q=soup");
  });

  it("ignores a from that points off the app's lists", async () => {
    search = `from=${encodeURIComponent("https://evil.example/kitchens/k1")}`;
    stub({ notebook: { status: 200, body: notebook }, recipes: oneRecipe });
    await render();

    await clickBack();

    expect(push).toHaveBeenCalledWith("/notebooks");
  });

  it("keeps from when the page changes, and passes the list address on to a recipe", async () => {
    search = `from=${encodeURIComponent("/kitchens/k1")}`;
    stub({ notebook: { status: 200, body: notebook }, recipes: oneRecipe });
    await render();

    const link = container.querySelector("h3 a") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe(
      `/recipes/r1?from=${encodeURIComponent("/notebooks/nb-1?from=%2Fkitchens%2Fk1")}`,
    );

    await act(async () => {
      (container.querySelector('button[aria-label="Page 2"]') as HTMLButtonElement).click();
    });
    expect(replace).toHaveBeenCalledWith("/notebooks/nb-1?from=%2Fkitchens%2Fk1&page=2");
  });
});
