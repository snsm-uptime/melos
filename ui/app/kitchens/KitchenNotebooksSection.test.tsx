/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider, ToastViewport } from "@/components/Toast";

import { KitchenCartCountProvider, useKitchenCartCount } from "./cartCount";
import { KitchenNotebooksSection } from "./KitchenNotebooksSection";

const replace = vi.fn();
const router = { replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => `/kitchens/5e7b0c1a-0000-4000-8000-000000000001`,
  useSearchParams: () => new URLSearchParams(),
}));

// The combined recipe list has its own tests; here it stays loading.
const { fetchKitchenRecipes } = vi.hoisted(() => ({
  fetchKitchenRecipes: vi.fn(() => new Promise(() => {})),
}));
vi.mock("@/lib/recipesClient", () => ({ fetchKitchenRecipes }));

// The cart (spec 022) is read once; by default nobody edits it and it is empty.
const { cartMocks } = vi.hoisted(() => ({
  cartMocks: {
    fetchCart: vi.fn(),
    addDraftItem: vi.fn(),
    removeDraftItem: vi.fn(),
    startCartEdit: vi.fn(),
    discardCart: vi.fn(),
  },
}));
vi.mock("@/lib/cartClient", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/cartClient")>()),
  ...cartMocks,
}));

function cartWith(over: Record<string, unknown> = {}) {
  return {
    kitchen_id: "5e7b0c1a-0000-4000-8000-000000000001",
    entries: [],
    editor: null,
    draft: null,
    can_edit: true,
    ...over,
  };
}

const kitchenId = "5e7b0c1a-0000-4000-8000-000000000001";

const homeNotebook = {
  id: "c3d0-1",
  name: "ana's (Home) Notebook",
  kind: "kitchen",
  owner_alias: "ana",
  access: "kitchen_member",
  is_default: false,
  recipe_count: 0,
  kitchen_id: kitchenId,
  kitchen_is_archived: false,
};

const secondNotebook = {
  id: "c3d0-2",
  name: "Weekend list",
  kind: "kitchen",
  owner_alias: null,
  access: "kitchen_member",
  is_default: false,
  recipe_count: 0,
  kitchen_id: kitchenId,
  kitchen_is_archived: false,
};

type Reply = { status: number; body: unknown };

function stubBff(queue: Reply[]) {
  const fetchMock = vi.fn(async () => {
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("KitchenNotebooksSection", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    replace.mockReset();
    for (const mock of Object.values(cartMocks)) mock.mockReset();
    cartMocks.fetchCart.mockResolvedValue({ ok: true, value: cartWith() });
    fetchKitchenRecipes.mockImplementation(() => new Promise(() => {}));
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.unstubAllGlobals();
  });

  function render(isArchived = false) {
    act(() => {
      root.render(
        <KitchenNotebooksSection
          kitchenId={kitchenId}
          isArchived={isArchived}
          locale="en"
        />,
      );
    });
  }

  it("calls the kitchen notebooks path for the kitchen", async () => {
    const fetchMock = stubBff([{ status: 200, body: { notebooks: [homeNotebook] } }]);

    render();
    await flush();

    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe(`/api/notebooks/kitchens/${kitchenId}`);
  });

  it("shows the kitchen not-found message and no cards on 404 kitchen_not_found", async () => {
    stubBff([{ status: 404, body: { code: "kitchen_not_found" } }]);

    render();
    await flush();

    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "This kitchen is unavailable.",
    );
    expect(container.querySelector("h3")).toBeNull();
  });

  it("shows the empty state when the kitchen has no notebooks", async () => {
    stubBff([{ status: 200, body: { notebooks: [] } }]);

    render();
    await flush();

    expect(container.textContent).toContain("This kitchen has no notebooks yet.");
    expect(container.querySelector("h3")).toBeNull();
  });

  it("shows no notebook cards, and one Add recipe button beside the filter", async () => {
    stubBff([{ status: 200, body: { notebooks: [homeNotebook, secondNotebook] } }]);

    render();
    await flush();

    expect(container.querySelector("h3")).toBeNull();
    expect(container.textContent).not.toContain("Owned by");
    expect(container.querySelector("a")).toBeNull();
    const buttons = Array.from(container.querySelectorAll("button"));
    expect(buttons.map((el) => el.textContent)).toEqual(["Add recipe"]);
    const filter = container.querySelector("input[type=search]") as HTMLInputElement;
    expect(filter.parentElement?.parentElement).toBe(buttons[0].parentElement);
  });

  it("lists the kitchen's recipes, read from the address", async () => {
    stubBff([{ status: 200, body: { notebooks: [homeNotebook] } }]);

    render();
    await flush();

    expect(fetchKitchenRecipes).toHaveBeenCalledWith(kitchenId, 1, "");
    expect(container.querySelector("input[type=search]")).not.toBeNull();
  });

  it("renders no add-recipe action in an archived kitchen, and still lists its recipes", async () => {
    stubBff([{ status: 200, body: { notebooks: [{ ...homeNotebook, kitchen_is_archived: true }] } }]);

    render(true);
    await flush();

    expect(container.querySelector("input[type=search]")).not.toBeNull();
    expect(container.querySelectorAll("button").length).toBe(0);
  });

  it("redirects to the alias step on 403 alias_required and shows no cards", async () => {
    stubBff([{ status: 403, body: { code: "alias_required" } }]);

    render();
    await flush();

    expect(replace).toHaveBeenCalledWith(`/alias?returnTo=${encodeURIComponent(`/kitchens/${kitchenId}`)}`);
    expect(container.querySelector("h3")).toBeNull();
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("shows the loading error with retry on other failures, and retry reloads", async () => {
    const fetchMock = stubBff([
      { status: 500, body: { detail: "boom" } },
      { status: 200, body: { notebooks: [homeNotebook] } },
    ]);

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "Could not load notebooks. Try again.",
    );

    await act(async () => {
      (container.querySelector("button") as HTMLButtonElement).click();
    });
    await flush();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("input[type=search]")).not.toBeNull();
  });

  it("drops the error while a retry is loading", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        calls += 1;
        if (calls === 1) {
          return Promise.resolve({ ok: false, status: 500, json: async () => ({}) });
        }
        return new Promise(() => {});
      }),
    );

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();

    await act(async () => {
      (container.querySelector("button") as HTMLButtonElement).click();
    });

    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("h3")).toBeNull();
  });

  describe("cart (spec 022)", () => {
    const card = {
      id: "r1",
      title: "Lentil soup",
      author_alias: "ana",
      ingredient_count: 3,
      notebook_id: "c3d0-1",
      notebook_name: "ana's (Home) Notebook",
      created_at: "2026-10-27T12:00:00Z",
    };

    function withRecipes() {
      fetchKitchenRecipes.mockImplementation(() =>
        Promise.resolve({
          ok: true,
          value: { items: [card], page: 1, page_size: 20, total: 1, total_pages: 1 },
        }),
      );
      stubBff([{ status: 200, body: { notebooks: [homeNotebook] } }]);
    }

    function renderWithToasts() {
      act(() => {
        root.render(
          <ToastProvider>
            <KitchenNotebooksSection kitchenId={kitchenId} isArchived={false} locale="en" />
            <ToastViewport />
          </ToastProvider>,
        );
      });
    }

    const cartButton = () =>
      container.querySelector<HTMLButtonElement>('button[aria-pressed]');

    it("adds with the cart-icon button and shows no message or bar", async () => {
      withRecipes();
      const editing = cartWith({
        editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" },
        draft: {
          entries: [
            {
              recipe_id: "r1",
              title: "Lentil soup",
              notebook_id: "c3d0-1",
              notebook_name: "x",
              base_servings: 4,
              servings: 1,
              factor: "0.5",
            },
          ],
          dropped_recipe_ids: [],
        },
      });
      cartMocks.addDraftItem.mockResolvedValue({ ok: true, value: editing });
      renderWithToasts();
      await flush();
      expect(cartButton()?.getAttribute("aria-label")).toBe("Add to cart");
      act(() => cartButton()?.click());
      await flush();
      expect(cartMocks.addDraftItem).toHaveBeenCalledWith(kitchenId, "r1");
      expect(cartButton()?.getAttribute("aria-label")).toBe("Remove from cart");
      expect(container.querySelector("[data-toast-viewport]")).toBeNull();
      expect(container.textContent).not.toContain("You're editing the cart.");
    });

    describe("cart count for the header badge", () => {
      function Probe() {
        return <span data-testid="count">{String(useKitchenCartCount())}</span>;
      }
      const countText = () => container.querySelector('[data-testid="count"]')?.textContent;
      const entry = (id: string) => ({
        recipe_id: id,
        title: id,
        notebook_id: "c3d0-1",
        notebook_name: "x",
        base_servings: 4,
        servings: 1,
        factor: "0.5",
      });

      function renderWithProbe() {
        act(() => {
          root.render(
            <ToastProvider>
              <KitchenCartCountProvider>
                <Probe />
                <KitchenNotebooksSection kitchenId={kitchenId} isArchived={false} locale="en" />
              </KitchenCartCountProvider>
            </ToastProvider>,
          );
        });
      }

      it("publishes the saved cart's recipe count, and the draft's count after a quick add", async () => {
        withRecipes();
        cartMocks.fetchCart.mockResolvedValue({
          ok: true,
          value: cartWith({ entries: [entry("a"), entry("b")] }),
        });
        cartMocks.addDraftItem.mockResolvedValue({
          ok: true,
          value: cartWith({
            entries: [entry("a"), entry("b")],
            editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" },
            draft: {
              entries: [entry("a"), entry("b"), entry("r1")],
              dropped_recipe_ids: [],
            },
          }),
        });
        renderWithProbe();
        expect(countText()).toBe("null");
        await flush();
        expect(countText()).toBe("2");

        act(() => cartButton()?.click());
        await flush();

        expect(countText()).toBe("3");
      });

      it("publishes 0 for an empty cart and null when the cart cannot be read", async () => {
        withRecipes();
        renderWithProbe();
        await flush();
        expect(countText()).toBe("0");

        act(() => root.unmount());
        root = createRoot(container);
        cartMocks.fetchCart.mockResolvedValue({ ok: false, status: 500, code: null });
        renderWithProbe();
        await flush();
        expect(countText()).toBe("null");
      });
    });

    it("keeps the button enabled while someone else edits and toasts the refusal", async () => {
      withRecipes();
      cartMocks.fetchCart.mockResolvedValue({
        ok: true,
        value: cartWith({
          editor: { alias: "ben", is_me: false, idle_expires_at: null },
          can_edit: false,
        }),
      });
      cartMocks.addDraftItem.mockResolvedValue({
        ok: false,
        status: 409,
        code: "cart_locked",
        editorAlias: "ben",
      });
      renderWithToasts();
      await flush();
      expect(cartButton()?.disabled).toBe(false);
      expect(container.textContent).not.toContain("ben is editing the cart");
      act(() => cartButton()?.click());
      await flush();
      expect(container.querySelector("[data-toast-viewport]")?.textContent).toBe(
        "ben is editing the cart",
      );
      expect(cartButton()?.getAttribute("aria-label")).toBe("Add to cart");
    });
  });
});
