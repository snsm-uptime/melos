"use client";

import { SendIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { Avatar } from "@/components/Avatar";
import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import { RecipeCard } from "@/components/RecipeCard/RecipeCard";
import { SearchableSelect } from "@/components/SearchableSelect";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import { messagesFor } from "@/lib/i18n/messages";
import { recipeShareMessages } from "@/lib/i18n/recipeShare";

import { ANA, ANA_SEED, LEO, LEO_SEED, recipeCard } from "./data";
import { ignore, inAt, Scene, Swap } from "./parts";

/**
 * Cook together (FR-006.3): a kitchen with Ana and Leo and their notebooks; Ana sends the tomato
 * rice to Leo from the recipe's Share dialog, which then says it was sent. The dialog is the
 * app's, drawn in place, with the person picker the Share dialog uses (ShareRecipeDialog reads its
 * people from the api, which a scene never calls).
 */
export function TogetherScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.together;
  const s = messagesFor(recipeShareMessages, locale);
  return (
    <Scene>
      <div className={`flex items-center justify-between gap-2 ${inAt(1)}`}>
        <p className="m-0 min-w-0 truncate text-[1.25rem] font-[550] text-foreground">{t.kitchen}</p>
        <span className="flex shrink-0 gap-1">
          <Avatar alias={ANA} seed={ANA_SEED} size="sm" />
          <Avatar alias={LEO} seed={LEO_SEED} size="sm" />
        </span>
      </div>
      <div className={`grid grid-cols-1 gap-2 min-[30rem]:grid-cols-2 ${inAt(2)}`}>
        <NotebookCard name={t.notebookAna} ownerAlias={ANA} viewerAlias={ANA} recipeCount={3} access="owner" locale={locale} />
        <NotebookCard name={t.notebookLeo} ownerAlias={LEO} viewerAlias={ANA} recipeCount={2} access="kitchen_member" locale={locale} />
      </div>
      <div className={inAt(3)}>
        <RecipeCard recipe={recipeCard("demo-rice", t.recipe, t.notebookAna, 5)} locale={locale} showNotebook />
      </div>
      <div className={inAt(4)}>
        <ActionDialog open title={s.shareTitle} closeLabel={s.shareClose} onOpenChange={ignore}>
          <Swap
            slot={5}
            before={
              <div className="flex w-full max-w-full items-center gap-1 rounded-[var(--radius-md)] border border-border bg-surface py-1 pr-1 pl-2 [&>span]:min-w-0 [&>span]:flex-1">
                <SearchableSelect
                  className="min-w-0 flex-1 justify-between text-[0.95rem] text-foreground"
                  aria-label={s.shareSearchLabel}
                  placeholder={s.sharePlaceholder}
                  searchLabel={s.shareSearchLabel}
                  noResults={s.shareNoResults}
                  value={LEO_SEED}
                  options={[{ value: LEO_SEED, label: LEO }]}
                  onChange={ignore}
                  action={{ icon: <SendIcon className="size-4" />, label: s.shareSend, onClick: ignore }}
                />
              </div>
            }
            after={<p className="m-0 text-foreground">{s.shareSent(LEO)}</p>}
          />
        </ActionDialog>
      </div>
    </Scene>
  );
}
