"use client";

import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import { RecipeCard } from "@/components/RecipeCard/RecipeCard";
import { ServingsControl } from "@/components/RecipeDetail/ServingsControl";
import { IngredientLineRow } from "@/components/RecipeDraft/IngredientLineRow";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { scaleLine } from "@/lib/recipeScale";

import { ANA, recipeCard, soupLines } from "./data";
import { ignore, inAt, Rows, Scene, Swap } from "./parts";

const SAVED_SERVINGS = 4;
const CHOSEN_SERVINGS = 2;

/**
 * Notebooks (FR-006.2): Ana's Notebook and its recipe cards; the lentil soup opens on the recipe
 * page's ingredients, where the servings go from 4 to 2 and every amount is halved, with the same
 * servings control, ingredient cards and scaling as the recipe page.
 */
export function NotebooksScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.notebooks;
  const d = recipeDetailMessages[locale];
  const saved = soupLines(locale);
  const ingredients = (servings: number) => (
    <Rows>
      {saved.map((line) => (
        <IngredientLineRow
          key={line.name}
          line={scaleLine(line, servings, SAVED_SERVINGS)}
          readOnly
          locale={locale}
        />
      ))}
    </Rows>
  );
  const header = (servings: number) => (
    <div className="flex items-center justify-between gap-2">
      <h2 className="m-0 text-[1rem] font-[550] text-foreground">{d.ingredientsTitle}</h2>
      <ServingsControl value={servings} onChange={ignore} locale={locale} />
    </div>
  );
  return (
    <Scene>
      <Swap
        slot={3}
        before={
          <div className="flex flex-col gap-2">
            <div className={inAt(1)}>
              <NotebookCard
                name={t.notebook}
                ownerAlias={ANA}
                viewerAlias={ANA}
                recipeCount={t.recipes.length}
                access="owner"
                isDefault
                locale={locale}
              />
            </div>
            <div className={`grid grid-cols-1 gap-2 min-[36rem]:grid-cols-3 ${inAt(2)}`}>
              {t.recipes.map((title, index) => (
                <RecipeCard key={title} recipe={recipeCard(`demo-${index}`, title, t.notebook, 3)} locale={locale} />
              ))}
            </div>
          </div>
        }
        after={
          <div className="flex flex-col gap-2">
            <p className="m-0 text-[1.5rem] font-[550] leading-normal text-foreground">{t.recipes[0]}</p>
            <Swap slot={5} before={header(SAVED_SERVINGS)} after={header(CHOSEN_SERVINGS)} />
            <Swap slot={5} before={ingredients(SAVED_SERVINGS)} after={ingredients(CHOSEN_SERVINGS)} />
          </div>
        }
      />
    </Scene>
  );
}
