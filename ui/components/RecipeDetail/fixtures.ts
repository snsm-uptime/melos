import type { RecipeDetail } from "@/lib/recipesClient";

/** A saved recipe for the detail and edit tests. */
export function recipeFixture(overrides: Partial<RecipeDetail> = {}): RecipeDetail {
  return {
    id: "r1",
    title: "Tomato rice",
    base_servings: 4,
    servings_estimated: false,
    author_alias: "ana",
    created_at: "2026-10-28T10:00:00Z",
    version: "2026-10-28T10:00:00.123456+00:00",
    notebook: { id: "nb1", name: "ana's Notebook", kind: "personal", kitchen_id: null },
    can_write: true,
    ingredient_lines: [
      { name: "rice", vague: false, quantity: 1, unit: "cup", size: null, preparation: null, note: null },
      { name: "onion", vague: false, quantity: 2, unit: "unit", size: "large", preparation: "chopped", note: null },
      { name: "salt", vague: true, quantity: null, unit: null, size: null, preparation: null, note: "to taste" },
    ],
    steps: ["Fry the garlic.", "Add the rice."],
    source: null,
    ...overrides,
  };
}
