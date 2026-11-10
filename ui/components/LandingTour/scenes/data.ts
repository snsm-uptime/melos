/**
 * The invented data the landing scenes give to the app's components (spec 075 FR-010), in the
 * app's own types, so a scene draws exactly what the app would draw for it. Names and recipes come
 * from lib/i18n/landing.ts in the page's language; amounts and units are the same in both, as the
 * app keeps unit codes ("cup", "unit") in every language. No id here is a real record.
 */
import type { LineView } from "@/lib/capture/captureStore";
import type { CartEntry } from "@/lib/cartClient";
import type { CatalogIngredient } from "@/lib/catalogClient";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import type { RecipeCard, RecipeLine } from "@/lib/recipesClient";
import type { ShoppingLine } from "@/lib/shoppingListClient";

export const ANA = "Ana";
export const LEO = "Leo";
/** Seeds of the avatars' colours; not user ids. */
export const ANA_SEED = "demo-ana";
export const LEO_SEED = "demo-leo";

const CREATED = "2026-01-01T00:00:00Z";

export function recipeCard(id: string, title: string, notebook: string, ingredients: number): RecipeCard {
  return {
    id,
    title,
    author_alias: ANA,
    ingredient_count: ingredients,
    notebook_id: "demo-notebook-ana",
    notebook_name: notebook,
    created_at: CREATED,
    preview_image: null,
  };
}

/** The cart rows of the overview and shop scenes: two recipes for 4, at ×1. */
export function cartEntries(locale: Locale): CartEntry[] {
  const t = landingMessages[locale].demo.shop;
  return [
    { recipe_id: "demo-a", title: t.recipeA, notebook_id: "demo-notebook-ana", notebook_name: t.notebook, base_servings: 4, servings: 4, factor: "1" },
    { recipe_id: "demo-b", title: t.recipeB, notebook_id: "demo-notebook-ana", notebook_name: t.notebook, base_servings: 4, servings: 4, factor: "1" },
  ];
}

/** The list's lines: flour from both recipes, kept as 1 cup + 3 tbsp (no unit is converted). */
export function shoppingLines(locale: Locale): { flour: ShoppingLine; eggs: ShoppingLine; milk: ShoppingLine } {
  const t = landingMessages[locale].demo.shop;
  const a = { recipe_id: "demo-a", title: t.recipeA };
  const b = { recipe_id: "demo-b", title: t.recipeB };
  return {
    flour: {
      name: t.flour,
      kind: "volume",
      size: null,
      amounts: [
        { quantity: "1", unit: "cup" },
        { quantity: "3", unit: "tbsp" },
      ],
      recipes: [a, b],
    },
    eggs: { name: t.eggs, kind: "count", size: null, amounts: [{ quantity: "2", unit: "unit" }], recipes: [a] },
    milk: { name: t.milk, kind: "volume", size: null, amounts: [{ quantity: "2", unit: "cup" }], recipes: [a, b] },
  };
}

/** The pasted recipe's draft lines: a vague salt and 2 large onions. */
export function draftLines(locale: Locale): LineView[] {
  const t = landingMessages[locale].demo.capture;
  const line = (key: string, name: string, rest: Partial<LineView>): LineView => ({
    key,
    name,
    vague: false,
    quantity: null,
    unit: null,
    size: null,
    preparation: null,
    vagueText: null,
    note: null,
    textName: name,
    match: { kind: "new", entry: null },
    ...rest,
  });
  return [
    line("demo-salt", t.salt, { vague: true, vagueText: t.saltAmount }),
    line("demo-onion", t.onion, { quantity: 2, unit: "unit", size: "large" }),
  ];
}

/** The lentil soup's saved lines, for 4. */
export function soupLines(locale: Locale): RecipeLine[] {
  const [lentils, carrots, water] = landingMessages[locale].demo.notebooks.lines;
  const line = (name: string, quantity: number, unit: string, size: string | null = null): RecipeLine => ({
    name,
    vague: false,
    quantity,
    unit,
    size,
    preparation: null,
    vague_text: null,
    note: null,
  });
  return [line(lentils, 2, "cup"), line(carrots, 4, "unit", "medium"), line(water, 6, "cup")];
}

/** The catalog rows before and after "onions" is merged into "onion". */
export function catalogRows(locale: Locale): { before: CatalogIngredient[]; after: CatalogIngredient[] } {
  const t = landingMessages[locale].demo.ingredients;
  const other = locale === "en" ? "es" : "en";
  return {
    before: [
      { name: t.kept, language: locale, recipe_count: 3, variants: [{ name: t.variant, language: other }], spellings: [] },
      { name: t.merged, language: locale, recipe_count: 1, variants: [], spellings: [] },
    ],
    after: [
      {
        name: t.kept,
        language: locale,
        recipe_count: 4,
        variants: [{ name: t.variant, language: other }],
        spellings: [t.merged],
      },
    ],
  };
}

/** The units and sizes the draft's pickers list, as the app's vocabulary sends them. */
export const UNITS = ["g", "kg", "ml", "l", "cup", "tbsp", "tsp", "unit"];
export const SIZES = ["small", "medium", "large"];
