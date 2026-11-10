import { Chip } from "@/components/Chip";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { FakeButton, inAt, MiniCard, outAt, popAt, Scene } from "./parts";

/**
 * Ingredients (FR-006.5): two spellings merged into one name, which then shows its name in the
 * other language. Each page draws the names in its own language: "onions" into "onion", shown as
 * "cebolla" in English; "cebollas" into "cebolla", shown as "onion" in Spanish.
 */
export function IngredientsScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.ingredients;
  return (
    <Scene>
      <MiniCard title={t.catalog}>
        <div className="flex min-w-0 flex-wrap items-center gap-2 rounded-[var(--radius-sm)] border border-border px-2 py-1.5">
          <strong className="font-semibold">{t.kept}</strong>
          <span className={`flex items-center gap-1.5 ${inAt(4)}`}>
            <Chip>{t.variantLabel}</Chip>
            <span>{t.variant}</span>
          </span>
        </div>

        {/* The merged spelling's row, then the note that replaces it. */}
        <div className="grid">
          <div
            className={`flex min-w-0 items-center justify-between gap-2 rounded-[var(--radius-sm)] border border-border px-2 py-1.5 [grid-area:1/1] ${outAt(3)}`}
          >
            <strong className="font-semibold">{t.merged}</strong>
            <FakeButton className={`${inAt(1)} ${popAt(2)}`}>{t.merge}</FakeButton>
          </div>
          <p className={`m-0 self-center px-2 text-muted [grid-area:1/1] ${inAt(3)}`}>{t.mergedNote}</p>
        </div>
      </MiniCard>
    </Scene>
  );
}
