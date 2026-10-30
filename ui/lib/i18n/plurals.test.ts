import { describe, expect, it } from "vitest";

import { recipeDetailMessages } from "./recipeDetail";
import { recipeListMessages } from "./recipeLists";
import { shoppingListMessages } from "./shoppingList";

/** Counts read correctly in both languages (spec 063 FR-015). */
describe("plurals and counts", () => {
  it.each([
    ["en", 1, "1 ingredient"],
    ["en", 3, "3 ingredients"],
    ["es", 1, "1 ingrediente"],
    ["es", 3, "3 ingredientes"],
    ["es", 0, "0 ingredientes"],
  ] as const)("recipe list %s %i", (locale, count, expected) => {
    expect(recipeListMessages[locale].ingredients(count)).toBe(expected);
  });

  it.each([
    ["en", 1, "1 serving"],
    ["en", 4, "4 servings"],
    ["es", 1, "1 porción"],
    ["es", 4, "4 porciones"],
  ] as const)("recipe detail servings %s %i", (locale, count, expected) => {
    expect(recipeDetailMessages[locale].servings(count)).toBe(expected);
  });

  it.each([
    ["en", 1, "1 recipe"],
    ["en", 3, "3 recipes"],
    ["es", 1, "1 receta"],
    ["es", 3, "3 recetas"],
  ] as const)("shopping list recipe count %s %i", (locale, count, expected) => {
    expect(shoppingListMessages[locale].recipeCount(count)).toBe(expected);
  });
});
