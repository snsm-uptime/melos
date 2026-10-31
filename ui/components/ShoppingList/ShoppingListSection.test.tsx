/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({ client: { fetchShoppingList: vi.fn() } }));
vi.mock("@/lib/shoppingListClient", () => client);

import type { ShoppingList } from "@/lib/shoppingListClient";
import { cart, mount } from "@/components/Cart/testRoot";

import { ShoppingListSection } from "./ShoppingListSection";

function list(over: Partial<ShoppingList> = {}): ShoppingList {
  return {
    is_empty: false,
    status: "active",
    list_id: "l1",
    kitchen_is_archived: false,
    hand_items: [],
    lines: [
      {
        name: "flour",
        kind: "volume",
        size: null,
        amounts: [
          { quantity: "1", unit: "cup" },
          { quantity: "3", unit: "tbsp" },
        ],
        recipes: [],
      },
      {
        name: "onion",
        kind: "count",
        size: "large",
        amounts: [{ quantity: "2", unit: "unit" }],
        recipes: [],
      },
    ],
    your_call: [],
    ...over,
  };
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("ShoppingListSection", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
    client.fetchShoppingList.mockReset();
  });
  afterEach(() => view.unmount());

  function render() {
    view.render(
      <ShoppingListSection kitchenId="k1" locale="en" cart={cart()} onClosed={() => {}} />,
    );
  }

  it("shows a loading status first, then the lines under the heading", async () => {
    let resolve: (value: unknown) => void = () => {};
    client.fetchShoppingList.mockReturnValue(new Promise((r) => (resolve = r)));
    render();
    expect(view.container.querySelector('[role="status"]')?.textContent).toBe(
      "Loading the shopping list",
    );

    resolve({ ok: true, value: list() });
    await settle();

    expect(view.container.querySelector('[role="status"]')).toBeNull();
    expect(view.container.querySelector("h2")?.textContent).toBe("Shopping list");
    const items = Array.from(view.container.querySelectorAll("ul > li > span")).map(
      (span) => span.textContent,
    );
    expect(items).toEqual(["flour — 1 cup + 3 tbsp", "onion, large — 2"]);
    expect(client.fetchShoppingList).toHaveBeenCalledWith("k1");
  });

  it("offers the item form for an empty cart, with no Done", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({ is_empty: true, lines: [], status: "live", list_id: null }),
    });
    render();
    await settle();

    expect(view.container.querySelector("form")).not.toBeNull();
    expect(view.container.textContent).not.toContain("Done");
  });

  it("renders nothing for an empty archived kitchen", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({
        is_empty: true,
        lines: [],
        status: "live",
        list_id: null,
        kitchen_is_archived: true,
      }),
    });
    render();
    await settle();

    expect(view.container.innerHTML).toBe("");
  });

  it("shows the status and hides Done and the form when archived", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({ kitchen_is_archived: true }),
    });
    render();
    await settle();

    expect(view.container.textContent).toContain("Saved");
    expect(view.container.querySelector("form")).toBeNull();
    expect(view.container.textContent).not.toContain("Done");
  });

  it("disables Done while I edit the cart", async () => {
    client.fetchShoppingList.mockResolvedValue({ ok: true, value: list({ status: "draft" }) });
    render();
    await settle();

    const done = Array.from(view.container.querySelectorAll("button")).find(
      (b) => b.textContent === "Done",
    );
    expect(done?.disabled).toBe(true);
    expect(view.container.textContent).toContain("Showing your unsaved cart");
  });

  it("shows an error with Retry that fetches again", async () => {
    client.fetchShoppingList.mockResolvedValueOnce({ ok: false, status: 0, code: null });
    render();
    await settle();

    expect(view.container.querySelector('[role="alert"]')?.textContent).toContain(
      "Could not load the shopping list",
    );

    client.fetchShoppingList.mockResolvedValueOnce({ ok: true, value: list() });
    const retry = Array.from(view.container.querySelectorAll("button")).find(
      (b) => b.textContent === "Try again",
    );
    act(() => retry?.click());
    await settle();

    expect(client.fetchShoppingList).toHaveBeenCalledTimes(2);
    expect(view.container.querySelector('[role="alert"]')).toBeNull();
    expect(view.container.textContent).toContain("flour — 1 cup + 3 tbsp");
  });

  it("renders an ingredient name as text, never as markup", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({
        lines: [
          {
            name: "<b>x</b>",
            kind: "count",
            size: null,
            amounts: [{ quantity: "1", unit: "unit" }],
            recipes: [],
          },
        ],
      }),
    });
    render();
    await settle();

    expect(view.container.querySelector("b")).toBeNull();
    expect(view.container.textContent).toContain("<b>x</b> — 1");
  });

  it("shows a chip for each recipe of a line, linking back to the Cart page", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({
        lines: [
          {
            name: "flour",
            kind: "volume",
            size: null,
            amounts: [{ quantity: "1", unit: "cup" }],
            recipes: [
              { recipe_id: "r1", title: "Bread" },
              { recipe_id: "r2", title: "Pancakes" },
            ],
          },
        ],
      }),
    });
    render();
    await settle();

    const links = Array.from(view.container.querySelectorAll("li li a"));
    expect(links.map((a) => a.textContent)).toEqual(["Bread", "Pancakes"]);
    expect(links[0].getAttribute("href")).toBe(
      `/recipes/r1?from=${encodeURIComponent("/kitchens/k1/cart")}`,
    );
  });

  it("shows Your call after the measured lines, with chips, only when there are entries", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({
        your_call: [
          {
            name: "salt",
            notes: ["a pinch", "to taste"],
            recipes: [
              { recipe_id: "r1", title: "Bread" },
              { recipe_id: "r2", title: "Stew" },
            ],
          },
        ],
      }),
    });
    render();
    await settle();

    const headings = Array.from(view.container.querySelectorAll("h2, h3")).map(
      (h) => h.textContent,
    );
    expect(headings).toEqual(["Shopping list", "Your call"]);
    const text = view.container.textContent ?? "";
    expect(text.indexOf("flour — 1 cup")).toBeLessThan(text.indexOf("Your call"));
    expect(text).toContain("salt — a pinch, to taste");
    const chips = Array.from(view.container.querySelectorAll("[data-your-call] a")).map(
      (a) => a.textContent,
    );
    expect(chips).toEqual(["Bread", "Stew"]);
  });

  it("does not show the Your call heading when there are no entries", async () => {
    client.fetchShoppingList.mockResolvedValue({ ok: true, value: list() });
    render();
    await settle();

    expect(view.container.textContent).not.toContain("Your call");
  });

  it("shows Your call alone when every ingredient is vague", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({
        lines: [],
        your_call: [{ name: "salt", notes: ["to taste"], recipes: [{ recipe_id: "r1", title: "A" }] }],
      }),
    });
    render();
    await settle();

    expect(view.container.textContent).toContain("salt — to taste");
    expect(view.container.textContent).not.toContain("These recipes have no ingredients");
  });

  it("says the recipes have no ingredients when both lists are empty but the cart is not", async () => {
    client.fetchShoppingList.mockResolvedValue({
      ok: true,
      value: list({ lines: [], your_call: [] }),
    });
    render();
    await settle();

    expect(view.container.textContent).toContain("These recipes have no ingredients");
  });

  it("shows the heading in Spanish", async () => {
    client.fetchShoppingList.mockResolvedValue({ ok: true, value: list() });
    view.render(<ShoppingListSection kitchenId="k1" locale="es" cart={cart()} onClosed={() => {}} />);
    await settle();

    expect(view.container.querySelector("h2")?.textContent).toBe("Lista de compras");
  });

  describe("following the cart (spec 023 US4)", () => {
    function renderFor(current: ReturnType<typeof cart>) {
      view.render(
        <ShoppingListSection kitchenId="k1" locale="en" cart={current} onClosed={() => {}} />,
      );
    }

    it("fetches again whenever the cart state is replaced", async () => {
      client.fetchShoppingList.mockResolvedValue({ ok: true, value: list() });
      renderFor(cart());
      await settle();
      expect(client.fetchShoppingList).toHaveBeenCalledTimes(1);

      renderFor(cart());
      await settle();
      expect(client.fetchShoppingList).toHaveBeenCalledTimes(2);
    });

    it("does not fetch again when the same cart state renders again", async () => {
      client.fetchShoppingList.mockResolvedValue({ ok: true, value: list() });
      const same = cart();
      renderFor(same);
      await settle();
      renderFor(same);
      await settle();
      expect(client.fetchShoppingList).toHaveBeenCalledTimes(1);
    });

    it("keeps the previous list on screen while the next one loads", async () => {
      client.fetchShoppingList.mockResolvedValueOnce({ ok: true, value: list() });
      renderFor(cart());
      await settle();

      let resolve: (value: unknown) => void = () => {};
      client.fetchShoppingList.mockReturnValueOnce(new Promise((r) => (resolve = r)));
      renderFor(cart());
      await settle();

      expect(view.container.querySelector('[role="status"]')).toBeNull();
      expect(view.container.textContent).toContain("flour — 1 cup + 3 tbsp");

      resolve({ ok: true, value: list({ lines: [] , your_call: [] }) });
      await settle();
      expect(view.container.textContent).toContain("These recipes have no ingredients");
    });

    it("ignores an answer that arrives after a newer request", async () => {
      let resolveOld: (value: unknown) => void = () => {};
      client.fetchShoppingList.mockReturnValueOnce(new Promise((r) => (resolveOld = r)));
      renderFor(cart());
      await settle();

      client.fetchShoppingList.mockResolvedValueOnce({
        ok: true,
        value: list({
          lines: [
            {
              name: "newer",
              kind: "count",
              size: null,
              amounts: [{ quantity: "1", unit: "unit" }],
              recipes: [],
            },
          ],
        }),
      });
      renderFor(cart());
      await settle();
      expect(view.container.textContent).toContain("newer — 1");

      resolveOld({ ok: true, value: list() });
      await settle();

      expect(view.container.textContent).toContain("newer — 1");
      expect(view.container.textContent).not.toContain("flour");
    });

    it("drops the lines when the cart becomes empty", async () => {
      client.fetchShoppingList.mockResolvedValueOnce({ ok: true, value: list() });
      renderFor(cart());
      await settle();
      expect(view.container.textContent).toContain("flour");

      client.fetchShoppingList.mockResolvedValueOnce({
        ok: true,
        value: list({ is_empty: true, lines: [] }),
      });
      renderFor(cart());
      await settle();

      expect(view.container.textContent).not.toContain("flour");
    });
  });
});
