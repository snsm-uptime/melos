import Link from "next/link";

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
 * page's Back returns to the Cart page (`?from=`, trusted by `safeReturnPath`).
 */
export function RecipeChips({ kitchenId, recipes, locale }: RecipeChipsProps) {
  const t = shoppingListMessages[locale];
  const from = `/kitchens/${encodeURIComponent(kitchenId)}/cart`;
  return (
    <ul aria-label={t.recipesLabel} className="m-0 flex list-none flex-wrap gap-2 p-0">
      {recipes.map((recipe) => (
        <li key={recipe.recipe_id} className="min-w-0 max-w-full">
          <Link
            href={`/recipes/${encodeURIComponent(recipe.recipe_id)}?from=${encodeURIComponent(from)}`}
            title={recipe.title}
            className="inline-flex min-h-11 max-w-full items-center rounded-full border border-border bg-background px-3 text-[0.85rem] text-foreground no-underline hover:border-accent hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <span className="truncate">{recipe.title}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
