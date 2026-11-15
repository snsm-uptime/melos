"use client";

import type { ReactNode } from "react";

import { ArrowIcon, MoonIcon, SunIcon } from "@/app/icons";
import { RecipeCard } from "@/components/RecipeCard/RecipeCard";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { recipeCard } from "./data";
import { ignore, inAt, Scene, type Slot } from "./parts";

/**
 * Home (FR-006.6): the app's recipe card in Spanish with the light look, then in English with the
 * dark look. Each takes its theme's tokens from `.theme-light-scope` / `.theme-dark-scope`
 * (globals.css), so no colour is copied here. The card is drawn in both languages on purpose; the
 * theme labels follow the page.
 */
export function HomeScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.home;
  return (
    <Scene>
      <div className="grid grid-cols-1 items-center gap-2 min-[26rem]:grid-cols-[1fr_auto_1fr]">
        <ThemedCard cardLocale="es" scope="theme-light-scope" themeLabel={t.light} icon={<SunIcon />} />
        <ArrowIcon className={`mx-auto size-4 -rotate-90 text-muted min-[26rem]:rotate-180 ${inAt(2)}`} />
        <ThemedCard cardLocale="en" scope="theme-dark-scope" themeLabel={t.dark} icon={<MoonIcon />} slot={3} />
      </div>
    </Scene>
  );
}

function ThemedCard({
  cardLocale,
  scope,
  themeLabel,
  icon,
  slot,
}: {
  cardLocale: Locale;
  scope: "theme-light-scope" | "theme-dark-scope";
  themeLabel: string;
  icon: ReactNode;
  slot?: Slot;
}) {
  const card = landingMessages[cardLocale].demo.home.card;
  return (
    <div
      className={`${scope} flex min-w-0 flex-col gap-2 rounded-[var(--radius-md)] border border-border bg-background p-2.5 text-foreground ${
        slot ? inAt(slot) : ""
      }`}
    >
      <span className="flex items-center justify-end gap-1 text-[0.75rem] text-muted [&_svg]:size-3.5">
        {icon}
        {themeLabel}
      </span>
      <RecipeCard
        recipe={recipeCard(`demo-home-${cardLocale}`, card.recipe, card.notebook, 6)}
        locale={cardLocale}
        showNotebook
        upright
        cart={{ inCart: false, onToggle: ignore }}
      />
    </div>
  );
}
