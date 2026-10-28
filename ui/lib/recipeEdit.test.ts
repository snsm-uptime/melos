import { describe, expect, it } from "vitest";

import { recipeFixture } from "@/components/RecipeDetail/fixtures";

import { nameChanges } from "./capture/nameChanges";
import {
  applyLineChange,
  applyMatches,
  catalogOf,
  isEdited,
  moveItem,
  newLine,
  pendingChecks,
  toEditState,
  toUpdateBody,
} from "./recipeEdit";

const recipe = recipeFixture();

describe("toEditState and toUpdateBody", () => {
  it("round-trips a stored recipe, and carries the version", () => {
    const body = toUpdateBody(toEditState(recipe), recipe.version);
    expect(body.version).toBe(recipe.version);
    expect(body.title).toBe("Tomato rice");
    expect(body.ingredient_lines).toEqual(recipe.ingredient_lines);
    expect(body.steps).toEqual(recipe.steps);
  });

  it("starts with every stored name matched, so no change is listed", () => {
    const state = toEditState(recipe);
    expect(state.lines.every((line) => line.match.kind === "matched")).toBe(true);
    expect(nameChanges(state.lines)).toEqual([]);
  });
});

describe("isEdited", () => {
  it("is false for the loaded recipe and true after any edit", () => {
    const state = toEditState(recipe);
    expect(isEdited(state, recipe)).toBe(false);
    expect(isEdited({ ...state, title: "Other" }, recipe)).toBe(true);
    expect(isEdited({ ...state, steps: state.steps.slice(1) }, recipe)).toBe(true);
    expect(isEdited({ ...state, lines: [...state.lines, newLine()] }, recipe)).toBe(true);
  });
});

describe("applyLineChange", () => {
  it("treats a name-only change as typed text with no match", () => {
    const [line] = toEditState(recipe).lines;
    const typed = applyLineChange(line, { ...line, name: "rices" });
    expect(typed).toMatchObject({ name: "rices", textName: "rices", match: { kind: "new" } });
  });

  it("leaves other field changes alone", () => {
    const [line] = toEditState(recipe).lines;
    const next = { ...line, quantity: 3 };
    expect(applyLineChange(line, next)).toBe(next);
  });
});

describe("name checks", () => {
  function typedLines() {
    const lines = toEditState(recipe).lines;
    return [applyLineChange(lines[0], { ...lines[0], name: "onions" }), ...lines.slice(1)];
  }

  it("lists only unchecked new named lines", () => {
    const lines = [...typedLines(), newLine()];
    const checked = new Map<string, string>();
    expect(pendingChecks(lines, checked).map((line) => line.name)).toEqual(["onions"]);
    checked.set(lines[0].key, "onions");
    expect(pendingChecks(lines, checked)).toEqual([]);
  });

  it("applies a proposal as a listed, undoable change", () => {
    const lines = typedLines();
    const checked = new Map([[lines[0].key, "onions"]]);
    const applied = applyMatches(lines, checked, [{ name: "onions", entry: "onion" }]);
    expect(applied[0]).toMatchObject({ name: "onion", textName: "onions", match: { kind: "matched" } });
    expect(nameChanges(applied)).toEqual([{ line: 0, from: "onions", to: "onion" }]);
  });

  it("changes nothing without a proposal, for case-only proposals, or when the name moved on", () => {
    const lines = typedLines();
    const checked = new Map([[lines[0].key, "onions"]]);
    expect(applyMatches(lines, checked, [{ name: "onions", entry: null }])).toEqual(lines);
    expect(applyMatches(lines, checked, [{ name: "onions", entry: "Onions" }])).toEqual(lines);
    const moved = [{ ...lines[0], name: "onions and more" }, ...lines.slice(1)];
    expect(applyMatches(moved, checked, [{ name: "onions", entry: "onion" }])).toEqual(moved);
  });
});

describe("catalogOf and moveItem", () => {
  it("lists the matched entries once", () => {
    const lines = toEditState(recipe).lines;
    expect(catalogOf([...lines, ...lines])).toEqual(["rice", "onion", "salt"]);
  });

  it("moves an item and keeps order at the edges", () => {
    expect(moveItem([1, 2, 3], 0, 1)).toEqual([2, 1, 3]);
    expect(moveItem([1, 2, 3], 0, -1)).toEqual([1, 2, 3]);
    expect(moveItem([1, 2, 3], 2, 1)).toEqual([1, 2, 3]);
  });
});
