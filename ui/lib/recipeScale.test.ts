import { describe, expect, it } from "vitest";

import { parseServings, scaleFactor, scaleLine, stepServings } from "./recipeScale";

const line = {
  name: "onion",
  quantity: 2 as number | null,
  unit: "unit",
  size: "large",
  preparation: "chopped",
  note: null as string | null,
};

describe("parseServings", () => {
  it.each(["6", " 6 ", "1", "100", "06"])("accepts %s", (text) => {
    expect(parseServings(text)).toBe(Number.parseInt(text, 10));
  });

  it.each(["", "  ", "abc", "0", "101", "2.5", "-3", "1e2", "٣", "6 7", "+5"])(
    "rejects %j",
    (text) => {
      expect(parseServings(text)).toBeNull();
    },
  );
});

describe("scaleLine", () => {
  it("scales a measured line in proportion", () => {
    const rice = { ...line, name: "rice", quantity: 1, unit: "cup", size: null };
    expect(scaleLine(rice, 6, 4).quantity).toBe(1.5);
    expect(scaleLine(rice, 2, 4).quantity).toBe(0.5);
    expect(scaleLine(rice, 8, 4).quantity).toBe(2);
  });

  it("scales a counted line exactly, without rounding up", () => {
    expect(scaleLine(line, 6, 4).quantity).toBe(3);
    expect(scaleLine(line, 5, 4).quantity).toBe(2.5);
  });

  it("returns a vague line as the same object", () => {
    const salt = { ...line, name: "salt", quantity: null, unit: null, note: "to taste" };
    expect(scaleLine(salt, 6, 4)).toBe(salt);
  });

  it("changes only the quantity", () => {
    const scaled = scaleLine(line, 6, 4);
    expect({ ...scaled, quantity: 0 }).toEqual({ ...line, quantity: 0 });
  });

  it("does not mutate its input", () => {
    const frozen = Object.freeze({ ...line });
    expect(() => scaleLine(frozen, 6, 4)).not.toThrow();
    expect(frozen.quantity).toBe(2);
  });

  it("returns to the saved amount after going away and back", () => {
    const third = { ...line, quantity: 1 / 3 };
    const there = scaleLine(third, 7, 4);
    expect(there.quantity).not.toBe(third.quantity);
    expect(scaleLine(third, 4, 4).quantity).toBe(third.quantity);
  });
});

describe("scaleFactor and stepServings", () => {
  it("is chosen over saved", () => {
    expect(scaleFactor(6, 4)).toBe(1.5);
  });

  it("steps by one and stays within 1 to 100", () => {
    expect(stepServings(4, 1)).toBe(5);
    expect(stepServings(4, -1)).toBe(3);
    expect(stepServings(1, -1)).toBe(1);
    expect(stepServings(100, 1)).toBe(100);
    expect(stepServings(120, -1)).toBe(100);
  });
});
