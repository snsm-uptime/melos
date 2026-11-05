import { describe, expect, it } from "vitest";

import type { PlaceRef } from "@/lib/places";

import { ALL_TAB, everythingBought, inTab, placeTabs, withBought } from "./shoppingByPlace";

const FARMERS: PlaceRef = { kind: "default", key: "farmers_market" };
const ASIAN: PlaceRef = { kind: "custom", id: "p1", name: "Asian market" };
const ZOO: PlaceRef = { kind: "custom", id: "p2", name: "Zoo shop" };
const SUPER: PlaceRef = { kind: "default", key: "supermarket" };

function item(name: string, place: PlaceRef, bought = false) {
  return { id: name, name, place, bought };
}

const list = {
  lines: [item("rice", ASIAN), item("tomato", FARMERS, true), item("flour", SUPER)],
  your_call: [item("salt", SUPER, true)],
  hand_items: [item("soap", ZOO)],
  custom_places: [
    { id: "p2", name: "Zoo shop" },
    { id: "p1", name: "Asian market" },
  ],
};

describe("placeTabs", () => {
  it("orders defaults first, then own places by name, and counts what is left", () => {
    expect(placeTabs(list, "en")).toEqual([
      { key: "default:supermarket", label: "Supermarket", left: 1 },
      { key: "default:farmers_market", label: "Farmers market", left: 0 },
      { key: "custom:p1", label: "Asian market", left: 1 },
      { key: "custom:p2", label: "Zoo shop", left: 1 },
    ]);
  });

  it("hides places with no items and names defaults in Spanish", () => {
    const tabs = placeTabs({ ...list, lines: [], hand_items: [] }, "es");
    expect(tabs).toEqual([{ key: "default:supermarket", label: "Supermercado", left: 0 }]);
  });

  it("treats a missing place as Supermarket", () => {
    const tabs = placeTabs(
      { lines: [{ bought: false }], your_call: [], hand_items: [], custom_places: [] },
      "en",
    );
    expect(tabs.map((t) => t.key)).toEqual(["default:supermarket"]);
  });
});

describe("inTab", () => {
  it("filters by place and puts bought items last", () => {
    const items = [item("a", SUPER, true), item("b", FARMERS), item("c", SUPER)];
    expect(inTab(items, ALL_TAB).map((i) => i.name)).toEqual(["b", "c", "a"]);
    expect(inTab(items, "default:supermarket").map((i) => i.name)).toEqual(["c", "a"]);
  });
});

describe("everythingBought and withBought", () => {
  it("is true only when every item is bought", () => {
    expect(everythingBought(list)).toBe(false);
    const empty = { lines: [], your_call: [], hand_items: [] };
    expect(everythingBought(empty)).toBe(false);
    let all = list;
    for (const name of ["rice", "flour", "soap"]) all = withBought(all, name, true);
    expect(everythingBought(all)).toBe(true);
    expect(withBought(all, "soap", false).hand_items[0].bought).toBe(false);
  });
});
