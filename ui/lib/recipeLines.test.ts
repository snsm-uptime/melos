import { describe, expect, it } from "vitest";

import { formatQuantity } from "./recipeLines";

describe("formatQuantity", () => {
  it("trims fractions to two places and never leaves a trailing zero", () => {
    expect(formatQuantity(0.5)).toBe("0.5");
    expect(formatQuantity(1.25)).toBe("1.25");
    expect(formatQuantity(2)).toBe("2");
    expect(formatQuantity(0.3333)).toBe("0.33");
  });
});
