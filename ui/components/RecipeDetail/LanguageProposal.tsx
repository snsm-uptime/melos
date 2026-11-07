"use client";

import { useState } from "react";

import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { setRecipeLanguage } from "@/lib/catalogClient";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import type { RecipeDetail } from "@/lib/recipesClient";

/**
 * "Detected: Spanish. Apply? / Dismiss" (spec 043 FR-005a). The model only proposed the language;
 * nothing changes until a person who can edit the recipe applies it. Dismiss drops the proposal.
 */
export function LanguageProposal({
  recipe,
  proposed,
  locale,
  onRecipeChange,
}: {
  recipe: RecipeDetail;
  proposed: "en" | "es";
  locale: Locale;
  onRecipeChange?: (recipe: RecipeDetail) => void;
}) {
  const t = recipeDetailMessages[locale];
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const language = t.languages[proposed];

  async function answer(apply: boolean) {
    if (pending) return;
    setPending(true);
    setError(null);
    const result = await setRecipeLanguage(recipe.id, apply ? proposed : null);
    setPending(false);
    if (result.ok) onRecipeChange?.(result.value as RecipeDetail);
    else setError(t.languageError);
  }

  return (
    <div
      className="mx-1 mt-2 flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2"
      role="region"
      aria-label={t.languageLabel}
    >
      <span className="text-[0.9rem] text-foreground">{t.detected(language)}</span>
      <GhostButton type="button" disabled={pending} onClick={() => void answer(true)}>
        {t.applyLanguage}
      </GhostButton>
      <GhostButton type="button" disabled={pending} onClick={() => void answer(false)}>
        {t.dismissLanguage}
      </GhostButton>
      {error ? (
        <p className="m-0 w-full text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
