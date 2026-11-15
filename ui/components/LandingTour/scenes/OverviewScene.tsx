"use client";

import { RecipeCard } from "@/components/RecipeCard/RecipeCard";
import { ShoppingLineRow } from "@/components/ShoppingList/ShoppingLine";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { recipeCard, shoppingLines } from "./data";
import { ignore, inAt, popAt, Rows, Scene, Swap } from "./parts";

/**
 * The hero demo (FR-002a), with the app's recipe cards and shopping rows: two recipes of Ana's
 * Notebook go into the cart, and the list adds up their flour on one line with both recipes.
 */
export function OverviewScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.overview;
  const lines = shoppingLines(locale);
  const card = (id: string, title: string, inCart: boolean) => (
    <RecipeCard
      recipe={recipeCard(id, title, t.notebook, 6)}
      locale={locale}
      showNotebook
      cart={{ inCart, onToggle: ignore }}
    />
  );
  return (
    <Scene long>
      <div className="grid grid-cols-1 gap-2 min-[30rem]:grid-cols-2">
        <div className={inAt(1)}>
          <Swap before={card("demo-a", t.recipeA, false)} after={card("demo-a", t.recipeA, true)} slot={2} />
        </div>
        <div className={inAt(2)}>
          <Swap before={card("demo-b", t.recipeB, false)} after={card("demo-b", t.recipeB, true)} slot={3} />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <div className={inAt(4)}>
          <Rows className={`origin-left ${popAt(6)}`}>
            <ShoppingLineRow line={lines.flour} locale={locale} />
          </Rows>
        </div>
        <Rows className={inAt(5)}>
          <ShoppingLineRow line={lines.eggs} locale={locale} />
        </Rows>
      </div>
    </Scene>
  );
}
