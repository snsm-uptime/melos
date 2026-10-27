import { describe, expect, it } from "vitest";

import type { LineView } from "./captureStore";
import { nameChanges, sameSpelling } from "./nameChanges";

function line(overrides: Partial<LineView>): LineView {
  return {
    key: "k",
    name: "onion",
    vague: false,
    quantity: 2,
    unit: "unit",
    size: "large",
    preparation: null,
    note: null,
    textName: "onion",
    match: { kind: "new", entry: null },
    ...overrides,
  };
}

describe("sameSpelling", () => {
  it("ignores letter case and spaces", () => {
    expect(sameSpelling("Onion", "onion")).toBe(true);
    expect(sameSpelling("red  onion", "red onion")).toBe(true);
  });

  it("does not ignore a plural or an accent", () => {
    expect(sameSpelling("onions", "onion")).toBe(false);
    expect(sameSpelling("limón", "limon")).toBe(false);
  });
});

describe("nameChanges", () => {
  it("lists a matched line whose text name differs from its entry", () => {
    const lines = [
      line({ textName: "onions", name: "onion", match: { kind: "matched", entry: "onion" } }),
    ];

    expect(nameChanges(lines)).toEqual([{ line: 0, from: "onions", to: "onion" }]);
  });

  it("lists nothing for a case-only difference", () => {
    const lines = [line({ textName: "Onion", name: "onion", match: { kind: "matched", entry: "onion" } })];

    expect(nameChanges(lines)).toEqual([]);
  });

  it("lists nothing for a new ingredient", () => {
    expect(nameChanges([line({ textName: "onions" })])).toEqual([]);
  });

  it("lists only the lines still changed, with their own index", () => {
    const lines = [
      line({ textName: "flour", name: "flour", match: { kind: "matched", entry: "flour" } }),
      line({ textName: "onions", name: "onion", match: { kind: "matched", entry: "onion" } }),
    ];

    expect(nameChanges(lines)).toEqual([{ line: 1, from: "onions", to: "onion" }]);
  });
});
