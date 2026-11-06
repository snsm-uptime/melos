import Link from "next/link";

import { chipClassName } from "@/components/Chip";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import type { ShoppingRecipeRef } from "@/lib/shoppingListClient";

type RecipeChipsProps = {
  kitchenId: string;
  recipes: ShoppingRecipeRef[];
  locale: Locale;
};

/**
 * The recipes a line comes from (spec 023 FR-008). Each chip opens the recipe, and the recipe
 * page's Back returns to the Cart page (`?from=`, trusted by `safeReturnPath`). A saved chip
 * whose recipe is gone stays as plain text (spec 025 R6).
 */
export function RecipeChips({ kitchenId, recipes, locale }: RecipeChipsProps) {
  const t = shoppingListMessages[locale];
  const from = `/kitchens/${encodeURIComponent(kitchenId)}/cart`;
  return (
    <ul
      aria-label={t.recipesLabel}
      className="m-0 flex max-w-[min(14rem,45%)] shrink-0 list-none gap-1 overflow-x-auto p-0 pb-1"
    >
      {recipes.map((recipe) => (
        <li key={recipe.recipe_id} className="shrink-0">
          {recipe.exists === false ? (
            <span
              title={recipe.title}
              className={`${chipClassName.muted} opacity-70`}
            >
              {recipe.title}
            </span>
          ) : (
            <Link
              href={`/recipes/${encodeURIComponent(recipe.recipe_id)}?from=${encodeURIComponent(from)}`}
              title={recipe.title}
              className={`${chipClassName.muted} no-underline hover:border-accent hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent`}
            >
              {recipe.title}
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}
