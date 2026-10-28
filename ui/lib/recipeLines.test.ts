import { describe, expect, it } from "vitest";

import { formatQuantity } from "./recipeLines";

describe("formatQuantity", () => {
  it("trims fractions to two places and never leaves a trailing zero", () => {
    expect(formatQuantity(0.5)).toBe("0.5");
    expect(formatQuantity(1.25)).toBe("1.25");
    expect(formatQuantity(2)).toBe("2");
    expect(formatQuantity(0.3333)).toBe("0.33");
  });

  it("rounds a half up even when floating point would round it down", () => {
    expect(formatQuantity(1.005)).toBe("1.01");
    expect(formatQuantity(0.005)).toBe("0.01");
  });

  it("never shows an amount above zero as 0", () => {
    expect(formatQuantity(0.004)).toBe("<0.01");
    expect(formatQuantity((0.1 * 1) / 100)).toBe("<0.01");
    expect(formatQuantity(0.0025)).toBe("<0.01");
  });
});
