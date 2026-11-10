import type { ReactNode } from "react";

import { ArrowIcon, MoonIcon, RecipeIcon, SunIcon } from "@/app/icons";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { FakeButton, inAt, Scene, type Slot } from "./parts";

type Card = (typeof landingMessages)[Locale]["demo"]["home"]["card"];

/**
 * Home (FR-006.6): the same recipe card in Spanish with the light look, then in English with the
 * dark look. Each card takes its theme's tokens from `.theme-light-scope` / `.theme-dark-scope`
 * (globals.css), so no colour is copied here. The card text is drawn in both languages on purpose;
 * the theme labels follow the page.
 */
export function HomeScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.home;
  return (
    <Scene>
      <div className="grid grid-cols-1 items-center gap-2 min-[26rem]:grid-cols-[1fr_auto_1fr]">
        <ThemedCard
          card={landingMessages.es.demo.home.card}
          scope="theme-light-scope"
          themeLabel={t.light}
          icon={<SunIcon />}
        />
        <ArrowIcon className={`mx-auto size-4 rotate-90 text-muted min-[26rem]:rotate-0 ${inAt(2)}`} />
        <ThemedCard
          card={landingMessages.en.demo.home.card}
          scope="theme-dark-scope"
          themeLabel={t.dark}
          icon={<MoonIcon />}
          slot={3}
        />
      </div>
    </Scene>
  );
}

function ThemedCard({
  card,
  scope,
  themeLabel,
  icon,
  slot,
}: {
  card: Card;
  scope: "theme-light-scope" | "theme-dark-scope";
  themeLabel: string;
  icon: ReactNode;
  slot?: Slot;
}) {
  return (
    <div
      className={`${scope} flex min-w-0 flex-col gap-2 rounded-[var(--radius-md)] border border-border bg-background p-2.5 text-foreground ${
        slot ? inAt(slot) : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2 text-[0.7rem] text-muted">
        <span className="font-semibold">{card.language}</span>
        <span className="flex items-center gap-1 [&_svg]:size-3.5">
          {icon}
          {themeLabel}
        </span>
      </div>
      <div className="flex min-w-0 flex-col gap-1.5 rounded-[var(--radius-sm)] border border-border bg-surface p-2.5">
        <span className="flex min-w-0 items-center gap-1.5 font-semibold">
          <RecipeIcon className="size-4 shrink-0 text-accent" />
          <span className="truncate">{card.recipe}</span>
        </span>
        <span className="text-muted">{card.servings}</span>
        <span>{card.line}</span>
        <FakeButton className="text-[0.7rem]">{card.action}</FakeButton>
      </div>
    </div>
  );
}
