/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({
  client: { fetchShoppingList: vi.fn(), setItemBought: vi.fn() },
}));
vi.mock("@/lib/shoppingListClient", () => client);

import { cart, mount } from "@/components/Cart/testRoot";
import type { ShoppingList } from "@/lib/shoppingListClient";

import { ShoppingListSection } from "./ShoppingListSection";

function list(over: Partial<ShoppingList> = {}): ShoppingList {
  return {
    is_empty: false,
    status: "active",
    list_id: "l1",
    kitchen_is_archived: false,
    lines: [
      {
        id: "i1",
        bought: false,
        place: { kind: "default", key: "farmers_market" },
        name: "tomato",
        kind: "count",
        size: null,
        amounts: [{ quantity: "2", unit: "unit" }],
        recipes: [],
      },
      {
        id: "i2",
        bought: false,
        place: { kind: "default", key: "supermarket" },
        name: "flour",
        kind: "mass",
        size: null,
        amounts: [{ quantity: "500", unit: "g" }],
        recipes: [],
      },
    ],
    your_call: [],
    hand_items: [],
    custom_places: [],
    ...over,
  };
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("bought and store tabs (spec 070)", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
    client.fetchShoppingList.mockReset();
    client.setItemBought.mockReset();
  });
  afterEach(() => view.unmount());

  async function render(value: ShoppingList, locale: "en" | "es" = "en") {
    client.fetchShoppingList.mockResolvedValue({ ok: true, value });
    view.render(
      <ShoppingListSection kitchenId="k1" locale={locale} cart={cart()} onClosed={() => {}} />,
    );
    await settle();
  }

  function boxes() {
    return Array.from(view.container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]'));
  }

  function names() {
    return Array.from(view.container.querySelectorAll("ul > li > div > span")).map(
      (s) => s.textContent,
    );
  }

  it("marks an item at once, saves it, and moves it last", async () => {
    let answer!: (v: unknown) => void;
    client.setItemBought.mockReturnValue(new Promise((r) => (answer = r)));
    await render(list());
    expect(boxes().map((b) => b.getAttribute("aria-label"))).toEqual([
      "Bought: tomato",
      "Bought: flour",
    ]);
    act(() => boxes()[0].click());
    expect(client.setItemBought).toHaveBeenCalledWith("k1", "i1", true);
    expect(names()).toEqual(["flour — 500 g", "tomato — 2"]);
    expect(view.container.querySelector('[data-bought="true"]')?.textContent).toContain("tomato");
    const saved = list();
    saved.lines[0] = { ...saved.lines[0], bought: true };
    await act(async () => answer({ ok: true, value: saved }));
    expect(boxes()[1].checked).toBe(true);
  });

  it("puts the item back and says so when saving fails", async () => {
    client.setItemBought.mockResolvedValue({ ok: false, status: 500, code: null });
    await render(list());
    act(() => boxes()[0].click());
    await settle();
    expect(boxes().every((b) => !b.checked)).toBe(true);
    expect(view.container.querySelector('[role="alert"]')?.textContent).toBe(
      "Could not save that. Try again.",
    );
  });

  it("offers no checkbox on a live or draft list, or in an archived kitchen", async () => {
    await render(list({ status: "live", list_id: null }));
    expect(boxes()).toEqual([]);
    view.unmount();
    view = mount();
    await render(list({ kitchen_is_archived: true }));
    expect(boxes()).toEqual([]);
  });

  it("says everything is bought", async () => {
    const all = list();
    all.lines = all.lines.map((l) => ({ ...l, bought: true }));
    await render(all);
    expect(view.container.querySelector('p[role="status"]')?.textContent).toBe(
      "Everything is bought. Press Done to close the list.",
    );
  });

  it("filters by store tab with counts of what is left", async () => {
    await render(list());
    const tabs = () =>
      Array.from(view.container.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    expect(tabs().map((t) => t.textContent)).toEqual([
      "All",
      "Supermarket 1",
      "Farmers market 1",
    ]);
    act(() => tabs()[2].click());
    expect(names()).toEqual(["tomato — 2"]);
    expect(tabs()[2].getAttribute("aria-selected")).toBe("true");
  });

  it("shows no tabs when every item is at one place, and names tabs in Spanish", async () => {
    const one = list();
    one.lines = [one.lines[1]];
    await render(one);
    expect(view.container.querySelector('[role="tablist"]')).toBeNull();
    view.unmount();
    view = mount();
    await render(list(), "es");
    const labels = Array.from(view.container.querySelectorAll('[role="tab"]')).map(
      (t) => t.textContent,
    );
    expect(labels).toEqual(["Todo", "Supermercado 1", "Mercado de agricultores 1"]);
  });
});
