/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/AppShell";
import { SHOW_DELAY_MS } from "@/components/Tooltip/Tooltip";

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
  recipe_count: 0,
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

  const emptyPage = { items: [], page: 1, total_pages: 1, total: 0 };

  it("labels a snapshot with the original's name, as text with no link", async () => {
    stub({
      notebook: {
        status: 200,
        body: { ...notebook, kind: "kitchen", origin_notebook_name: "ana's Notebook" },
      },
      recipes: emptyPage,
    });
    await render();

    const label = Array.from(container.querySelectorAll("p")).find(
      (el) => el.textContent === "Copied from ana's Notebook",
    );
    expect(label).toBeDefined();
    expect(label?.querySelector("a")).toBeNull();
    expect(label?.closest("a")).toBeNull();
  });

  it("shows no label without an origin name", async () => {
    stub({
      notebook: { status: 200, body: { ...notebook, origin_notebook_name: null } },
      recipes: emptyPage,
    });
    await render();

    expect(container.textContent).not.toContain("Copied from");
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

  it("goes to the notebooks when the member cannot see this one", async () => {
    stub({ notebook: { status: 404, body: { code: "notebook_not_found" } } });

    await render();

    expect(replace).toHaveBeenCalledWith("/notebooks");
    expect(container.querySelector("main input")).toBeNull();
  });

  it("goes to the notebooks when access ends while the list is open", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const gone = url.includes("/recipes");
        return {
          ok: !gone,
          status: gone ? 404 : 200,
          json: async () => (gone ? { code: "notebook_not_found" } : notebook),
        };
      }),
    );

    await render();

    expect(replace).toHaveBeenCalledWith("/notebooks");
  });

  it("on a first load that answers 404, goes back to the list it came from", async () => {
    search = `from=${encodeURIComponent("/kitchens/k1/notebooks")}`;
    stub({ notebook: { status: 404, body: { code: "notebook_not_found" } } });

    await render();

    expect(replace).toHaveBeenCalledWith("/kitchens/k1/notebooks");
  });

  it("goes to the kitchen's notebooks when a loaded kitchen notebook goes", async () => {
    const inKitchen = {
      ...notebook,
      kind: "kitchen",
      access: "kitchen_member",
      kitchen_id: "k1",
      kitchen_is_archived: false,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const gone = url.includes("/recipes");
        return {
          ok: !gone,
          status: gone ? 404 : 200,
          json: async () => (gone ? { code: "notebook_not_found" } : inKitchen),
        };
      }),
    );

    await render();

    expect(replace).toHaveBeenCalledWith("/kitchens/k1/notebooks");
  });

  const empty = { items: [], page: 1, page_size: 12, total: 0, total_pages: 0 };
  const shareButton = () => container.querySelector('button[aria-label="Share this notebook"]');
  const optionsButton = () =>
    container.querySelector('button[aria-label="Notebook options"]') as HTMLButtonElement | null;
  const item = (name: string) =>
    Array.from(container.querySelectorAll<HTMLElement>('[role="menuitem"]')).find(
      (el) => el.textContent === name,
    ) as HTMLElement;
  const dialogButton = (name: string) =>
    Array.from(container.querySelectorAll('[role="dialog"] button, main button')).find(
      (el) => el.textContent === name,
    ) as HTMLButtonElement;
  const inKitchen = {
    ...notebook,
    kind: "kitchen",
    access: "kitchen_member",
    is_default: false,
    kitchen_id: "k1",
    kitchen_is_archived: false,
  };

  async function choose(name: string) {
    act(() => optionsButton()?.click());
    await act(async () => {
      item(name).click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  function stubWrites(body: unknown, write: { status: number; body: unknown }) {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const reply =
        init?.method === "PATCH" || init?.method === "DELETE"
          ? write
          : url.includes("/recipes")
            ? { status: 200, body: empty }
            : url.endsWith("/members")
              ? { status: 200, body: { members: [] } }
              : { status: 200, body };
      return {
        ok: reply.status < 300,
        status: reply.status,
        json: async () => reply.body,
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it.each([
    ["the owner", notebook],
    ["a member of an active kitchen", inKitchen],
  ])("shows the options to %s", async (_who, body) => {
    stub({ notebook: { status: 200, body }, recipes: empty });

    await render();

    expect(optionsButton()).not.toBeNull();
  });

  it.each([
    ["a notebook member", { ...notebook, access: "member" }],
    ["an archived kitchen", { ...inKitchen, kitchen_is_archived: true }],
  ])("shows no options to %s", async (_who, body) => {
    stub({ notebook: { status: 200, body }, recipes: empty });

    await render();

    expect(optionsButton()).toBeNull();
  });

  it("keeps Share with the options on a personal notebook, after it", async () => {
    stub({ notebook: { status: 200, body: notebook }, recipes: empty });

    await render();

    const position = shareButton()?.compareDocumentPosition(optionsButton() as Node) ?? 0;
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renames, closes the dialog and updates the title", async () => {
    const fetchMock = stubWrites(notebook, {
      status: 200,
      body: { ...notebook, name: "Winter soups" },
    });
    await render();
    await choose("Rename");
    const input = container.querySelector('[role="dialog"] input') as HTMLInputElement;
    expect(input.value).toBe("ana's Notebook");

    await act(async () => {
      dialogButton("Save").click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(true);
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(container.querySelector("header h1")?.textContent).toBe("Winter soups");
  });

  it("on a rename that finds it gone, closing goes to the kitchen's notebooks", async () => {
    stubWrites(inKitchen, { status: 404, body: { code: "notebook_not_found" } });
    await render();
    await choose("Rename");

    await act(async () => {
      dialogButton("Save").click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(container.querySelector('[role="dialog"] [role="alert"]')?.textContent).toBe(
      "This notebook no longer exists.",
    );
    await act(async () => dialogButton("Close").click());
    expect(replace).toHaveBeenCalledWith("/kitchens/k1/notebooks");
  });

  it("deletes after confirming and goes to the person's notebooks", async () => {
    const fetchMock = stubWrites(notebook, { status: 204, body: null });
    await render();
    await choose("Delete");
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(false);

    await act(async () => {
      dialogButton("Delete").click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(true);
    expect(replace).toHaveBeenCalledWith("/notebooks");
  });

  it("puts the share button in the chrome on a personal notebook and opens the dialog", async () => {
    stub({ notebook: { status: 200, body: notebook }, recipes: empty });

    await render();

    expect(container.querySelector("main")?.contains(shareButton())).toBe(false);
    expect(shareButton()).not.toBeNull();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    act(() => shareButton()?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
  });

  it("shows the share button disabled on a kitchen notebook, with the kitchen-invite tooltip", async () => {
    stub({
      notebook: { status: 200, body: { ...notebook, kind: "kitchen", access: "kitchen_member" } },
      recipes: empty,
    });

    await render();

    const button = shareButton() as HTMLButtonElement | null;
    expect(button).not.toBeNull();
    expect(button?.disabled).toBe(true);
    await act(async () => {
      button?.parentElement?.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, SHOW_DELAY_MS + 50));
    });
    expect(document.querySelector('[data-testid="tooltip-bubble"]')?.textContent).toBe(
      "Requires invite to kitchen",
    );
    act(() => button?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(document.querySelector('[role="dialog"]')).toBeNull();
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
