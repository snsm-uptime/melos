import { describe, expect, it } from "vitest";

import { checkDraft, hasErrors, lineErrors, type DraftInput, type LineInput } from "./draftRules";

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
    expect(lineErrors({ vague: false, quantity: 1, unit: "cup", size: null })).toEqual([]);
  });

  it("needs a positive quantity and an allowed unit on a measured line", () => {
    expect(lineErrors({ vague: false, quantity: null, unit: "cup", size: null })).toEqual([
      "amountAndUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 0, unit: "cup", size: null })).toEqual([
      "amountAndUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 1, unit: "pinch", size: null })).toEqual([
      "amountAndUnit",
    ]);
  });

  it("keeps a vague line free of quantity and unit", () => {
    expect(lineErrors({ vague: true, quantity: null, unit: null, size: null })).toEqual([]);
    expect(lineErrors({ vague: true, quantity: 2, unit: null, size: null })).toEqual([
      "vagueHasAmount",
    ]);
  });

  it("allows a size only with the unit 'unit', and only small, medium or large", () => {
    expect(lineErrors({ vague: false, quantity: 1, unit: "cup", size: "large" })).toEqual([
      "sizeOnlyForUnit",
    ]);
    expect(lineErrors({ vague: false, quantity: 1, unit: "unit", size: "huge" })).toEqual([
      "sizeInvalid",
    ]);
  });
});

describe("checkDraft (FR-013)", () => {
  it("passes a valid draft", () => {
    expect(hasErrors(checkDraft(draft()))).toBe(false);
  });

  it("requires a title of 1 to 200 characters after trimming", () => {
    expect(checkDraft(draft({ title: "   " })).title).toBe("titleRequired");
    expect(checkDraft(draft({ title: "x".repeat(201) })).title).toBe("titleTooLong");
    expect(checkDraft(draft({ title: "x".repeat(200) })).title).toBeUndefined();
  });

  it("requires base servings to be a whole number of at least 1", () => {
    expect(checkDraft(draft({ baseServings: 0 })).servings).toBe("servingsInvalid");
    expect(checkDraft(draft({ baseServings: 2.5 })).servings).toBe("servingsInvalid");
  });

  it("requires at least one non-empty step", () => {
    expect(checkDraft(draft({ steps: [{ text: " " }] })).steps).toBe("stepsRequired");
  });

  it("reports the broken line by its index", () => {
    const errors = checkDraft(draft({ lines: [measured, { ...measured, quantity: null }] }));
    expect(Object.keys(errors.lines)).toEqual(["1"]);
  });
});
