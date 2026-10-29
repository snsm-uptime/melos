import { describe, expect, it } from "vitest";

import { formatFactor, parseCount } from "./cartFactor";

describe("formatFactor", () => {
  it.each([
    [2, 1, 4, "0.5"],
    [3, 2, 4, "1.5"],
    [2, 1, 3, "0.67"],
    [1, 1, 3, "0.33"],
    [2, 1, 1, "2"],
    [3, 1, 4, "0.75"],
    [1, 1, 200, "0.01"],
    [1, 1, 400, "0"],
    [10, 1, 1, "10"],
    [3, 3, 9, "1"],
  ])("people %i meals %i base %i → %s", (people, meals, base, text) => {
    expect(formatFactor(people, meals, base)).toBe(text);
  });
});

describe("parseCount", () => {
  it("accepts whole numbers from 1 to 99", () => {
    expect(parseCount("1")).toBe(1);
    expect(parseCount(" 99 ")).toBe(99);
  });

  it.each(["0", "100", "-1", "1.5", "", "a", "3e1"])("rejects %s", (text) => {
    expect(parseCount(text)).toBeNull();
  });
});
