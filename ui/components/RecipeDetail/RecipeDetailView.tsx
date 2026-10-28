import Link from "next/link";

import { BackIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import { IngredientLineRow } from "@/components/RecipeDraft/IngredientLineRow";
import { StepCard } from "@/components/RecipeDraft/StepCard";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import type { RecipeDetail } from "@/lib/recipesClient";

type RecipeDetailViewProps = {
  recipe: RecipeDetail;
  locale: Locale;
  /** The list the member came from (spec 027 FR-004). */
  backHref: string;
  editHref: string;
  onDelete: () => void;
};

/**
 * One saved recipe in the layout of the draft review page, display only: the title, the
 * ingredient cards and the step cards are text, with no fields, dropdowns, or move and remove
 * controls. Edit and Delete show only to those who can write (spec 027 FR-005).
 */
export function RecipeDetailView({
  recipe,
  locale,
  backHref,
  editHref,
  onDelete,
}: RecipeDetailViewProps) {
  const t = recipeDetailMessages[locale];
  const source = recipe.source?.url ?? null;
  return (
    <main className="mx-auto flex w-full flex-col gap-4 md:min-h-0 md:flex-1">
      <div className="flex flex-col gap-6 md:min-h-0 md:flex-1">
        {/* Same insets and Back slot as the draft page and AppShell's chrome header. */}
        <header className="flex items-center gap-2 pt-[max(0.5rem,env(safe-area-inset-top))] pr-[max(1rem,env(safe-area-inset-right))] pb-1 pl-[max(0.5rem,env(safe-area-inset-left))]">
          <div className="flex w-10 shrink-0 items-center justify-start self-center">
            <Link
              href={backHref}
              aria-label={t.back}
              title={t.back}
              className="m-0 inline-flex flex-shrink-0 items-center justify-center rounded-[8px] border-0 bg-transparent p-1 leading-none text-muted transition-all duration-150 hover:text-foreground"
            >
              <BackIcon className="size-6" />
            </Link>
          </div>
          <div className="flex min-w-0 flex-1 flex-col">
            <h1 className="m-0 min-w-0 px-1 py-[0.15rem] text-[1.5rem] font-[550] leading-normal text-foreground">
              {recipe.title}
            </h1>
            <h4 className="m-0 px-1 text-[0.9rem] font-normal text-muted">
              {recipe.notebook.name}
            </h4>
            <div className="flex flex-wrap items-center gap-2 px-1 pt-1 text-[0.85rem] text-muted">
              <span>{t.authorLabel}</span>
              <Chip tone="accent">{recipe.author_alias ?? t.authorUnknown}</Chip>
            </div>
          </div>
        </header>

        <div className="flex flex-col gap-6 px-4 md:min-h-0 md:flex-1 md:flex-row">
          <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:max-w-[450px] md:flex-1 md:overflow-hidden">
            <div className="flex shrink-0 items-center justify-between gap-2">
              <h2 className="m-0 text-[1rem] font-[550] text-foreground">{t.ingredientsTitle}</h2>
              <div className="flex items-center gap-2 text-[0.85rem] text-muted">
                <span>{t.servings(recipe.base_servings)}</span>
                {recipe.servings_estimated ? <Chip tone="warning">{t.estimated}</Chip> : null}
              </div>
            </div>
            <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {recipe.ingredient_lines.map((line, index) => (
                  <IngredientLineRow key={`${index}-${line.name}`} line={line} readOnly />
                ))}
              </ul>
            </div>
          </section>

          <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-hidden">
            <h2 className="m-0 shrink-0 text-[1rem] font-[550] text-foreground">{t.stepsTitle}</h2>
            <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
              <ol className="m-0 flex list-none flex-col gap-2 p-0">
                {recipe.steps.map((step, index) => (
                  <StepCard key={`${index}-${step.slice(0, 12)}`} index={index} text={step} readOnly />
                ))}
              </ol>
            </div>
          </section>
        </div>

        {source ? (
          <a
            href={source}
            rel="noopener noreferrer"
            target="_blank"
            className="px-4 text-[0.9rem] text-accent"
          >
            {t.sourceLink}
          </a>
        ) : null}

        {recipe.can_write ? (
          <div className="flex items-center justify-end gap-4 px-4">
            <button type="button" onClick={onDelete} className="text-[0.95rem] text-owe">
              {t.delete}
            </button>
            <Link
              href={editHref}
              className="rounded-[0.75rem] bg-accent px-4 py-2 text-[0.95rem] font-semibold text-on-accent no-underline"
            >
              {t.edit}
            </Link>
          </div>
        ) : null}
      </div>
    </main>
  );
}
