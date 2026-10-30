import { describe, expect, it } from "vitest";

import type { ShoppingLine, YourCallEntry } from "./shoppingListClient";
import { formatLine, formatYourCall } from "./shoppingListText";

function line(over: Partial<ShoppingLine>): ShoppingLine {
  return {
    name: "flour",
    kind: "volume",
    size: null,
    amounts: [{ quantity: "1", unit: "cup" }],
    recipes: [],
    ...over,
  };
}

describe("formatLine", () => {
  it("joins the units of one kind with +, largest first as the api sends them", () => {
    expect(
      formatLine(
        line({
          amounts: [
            { quantity: "1", unit: "cup" },
            { quantity: "3", unit: "tbsp" },
          ],
        }),
      ),
    ).toBe("flour — 1 cup + 3 tbsp");
  });

  it("shows only the number for a count, with the size after the name", () => {
    expect(
      formatLine(
        line({
          name: "onion",
          kind: "count",
          size: "large",
          amounts: [{ quantity: "2", unit: "unit" }],
        }),
      ),
    ).toBe("onion, large — 2");
  });

  it("shows a count with no size as the name and the number", () => {
    expect(
      formatLine(
        line({ name: "onion", kind: "count", amounts: [{ quantity: "1", unit: "unit" }] }),
      ),
    ).toBe("onion — 1");
  });

  it("keeps decimals as the api sends them", () => {
    expect(formatLine(line({ amounts: [{ quantity: "0.33", unit: "cup" }] }))).toBe(
      "flour — 0.33 cup",
    );
  });

  it("returns names as stored, untranslated", () => {
    expect(formatLine(line({ name: "ñame", amounts: [{ quantity: "200", unit: "g" }] }))).toBe(
      "ñame — 200 g",
    );
  });
});

describe("formatYourCall", () => {
  const entry = (over: Partial<YourCallEntry>): YourCallEntry => ({
    name: "salt",
    notes: ["a pinch", "to taste"],
    recipes: [],
    ...over,
  });

  it("shows the name, then its notes joined with a comma", () => {
    expect(formatYourCall(entry({}))).toBe("salt — a pinch, to taste");
  });

  it("shows a single note as is", () => {
    expect(formatYourCall(entry({ notes: ["to taste"] }))).toBe("salt — to taste");
  });
});
