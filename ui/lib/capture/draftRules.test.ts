import { describe, expect, it } from "vitest";

import {
  ALLOWED_UNITS,
  checkDraft,
  hasErrors,
  lineErrors,
  pendingUnitQuestions,
  type DraftInput,
  type LineInput,
} from "./draftRules";

const TEN = [...ALLOWED_UNITS];

const measured: LineInput = { vague: false, quantity: 2, unit: "unit", size: "large" };

function draft(overrides: Partial<DraftInput> = {}): DraftInput {
  return {
    title: "Onion soup",
    baseServings: 4,
    lines: [measured],
    steps: [{ text: "Simmer." }],
    // MVP-OUT: mainIngredientCount: 0,
    // MVP-OUT: cuisineCount: 1,
    ...overrides,
  };
}

describe("lineErrors (FR-013)", () => {
  it("accepts a measured line with a positive quantity and an allowed unit", () => {
    expect(lineErrors({ vague: false, quantity: 1, unit: "cup", size: null }, TEN)).toEqual([]);
  });

  it("needs a positive quantity and an allowed unit on a measured line", () => {
    expect(lineErrors({ vague: false, quantity: null, unit: "cup", size: null }, TEN)).toEqual([
      "amountAndUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 0, unit: "cup", size: null }, TEN)).toEqual([
      "amountAndUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 1, unit: "pinch", size: null }, TEN)).toEqual([
      "amountAndUnit",
    ]);
  });

  it("keeps a vague line free of quantity and unit", () => {
    expect(lineErrors({ vague: true, quantity: null, unit: null, size: null }, TEN)).toEqual([]);
    expect(lineErrors({ vague: true, quantity: 2, unit: null, size: null }, TEN)).toEqual([
      "vagueHasAmount",
    ]);
  });

  it("allows a size only with the unit 'unit', and only small, medium or large", () => {
    expect(lineErrors({ vague: false, quantity: 1, unit: "cup", size: "large" }, TEN)).toEqual([
      "sizeOnlyForUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 1, unit: "unit", size: "huge" }, TEN)).toEqual([
      "sizeInvalid",
    ]);
  });
});

describe("checkDraft (FR-013)", () => {
  it("passes a valid draft", () => {
    expect(hasErrors(checkDraft(draft(), TEN))).toBe(false);
  });

  it("requires a title of 1 to 200 characters after trimming", () => {
    expect(checkDraft(draft({ title: "   " }), TEN).title).toBe("titleRequired");
    expect(checkDraft(draft({ title: "x".repeat(201) }), TEN).title).toBe("titleTooLong");
    expect(checkDraft(draft({ title: "x".repeat(200) }), TEN).title).toBeUndefined();
  });

  it("requires base servings to be a whole number of at least 1", () => {
    expect(checkDraft(draft({ baseServings: 0 }), TEN).servings).toBe("servingsInvalid");
    expect(checkDraft(draft({ baseServings: 2.5 }), TEN).servings).toBe("servingsInvalid");
  });

  it("requires at least one non-empty step", () => {
    expect(checkDraft(draft({ steps: [{ text: " " }] }), TEN).steps).toBe("stepsRequired");
  });

  it("reports the broken line by its index", () => {
    const errors = checkDraft(draft({ lines: [measured, { ...measured, quantity: null }] }), TEN);
    expect(Object.keys(errors.lines)).toEqual(["1"]);
  });
});

describe("custom units (spec 055)", () => {
  const lata: LineInput = { vague: false, quantity: 1, unit: "lata", size: null };

  it("flags a line outside the allowed units, and accepts one inside them", () => {
    expect(lineErrors(lata, TEN)).toEqual(["amountAndUnit"]);
    expect(lineErrors(lata, [...TEN, "lata"])).toEqual([]);
    expect(checkDraft(draft({ lines: [lata] }), TEN).lines[0]).toEqual(["amountAndUnit"]);
    expect(hasErrors(checkDraft(draft({ lines: [lata] }), [...TEN, "lata"]))).toBe(false);
  });

  it("lists a word asked about once, in line order", () => {
    const bote = { ...lata, unit: "bote" };
    expect(pendingUnitQuestions([lata, bote, lata], TEN, [], [])).toEqual(["lata", "bote"]);
  });

  it("does not ask about an allowed, kept or declined word", () => {
    expect(pendingUnitQuestions([lata], [...TEN, "lata"], [], [])).toEqual([]);
    expect(pendingUnitQuestions([lata], TEN, ["lata"], [])).toEqual([]);
    expect(pendingUnitQuestions([lata], TEN, [], ["lata"])).toEqual([]);
  });

  it("does not ask once no line uses the word, or about a vague line", () => {
    expect(pendingUnitQuestions([], TEN, [], [])).toEqual([]);
    const vague: LineInput = { vague: true, quantity: null, unit: null, size: null };
    expect(pendingUnitQuestions([vague], TEN, [], [])).toEqual([]);
  });
});
