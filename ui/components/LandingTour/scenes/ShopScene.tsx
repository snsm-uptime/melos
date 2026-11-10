import { CartIcon, CheckIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { inAt, ListLine, MiniCard, Scene, Struck, type Slot } from "./parts";

/**
 * Plan and shop (FR-006.4): recipe A (1 cup flour) and B (3 tbsp flour) in the cart become the one
 * line "flour — 1 cup + 3 tbsp" with both recipes' chips; on a place tab, two lines are bought.
 */
export function ShopScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.shop;
  const bought: { text: string; slot: Slot }[] = [
    { text: t.eggsLine, slot: 5 },
    { text: t.milkLine, slot: 6 },
  ];
  return (
    <Scene>
      <MiniCard title={t.cart} icon={<CartIcon />}>
        <div className={`flex min-w-0 justify-between gap-2 ${inAt(1)}`}>
          <strong className="truncate font-semibold">{t.recipeA}</strong>
          <span className="shrink-0 text-muted">{t.flourA}</span>
        </div>
        <div className={`flex min-w-0 justify-between gap-2 ${inAt(2)}`}>
          <strong className="truncate font-semibold">{t.recipeB}</strong>
          <span className="shrink-0 text-muted">{t.flourB}</span>
        </div>
      </MiniCard>

      <MiniCard title={t.listTitle} className={inAt(3)}>
        <div className="flex gap-3 border-b border-border text-[0.75rem]">
          <span className="relative pb-1 font-semibold text-accent">
            {t.placeMarket}
            <span className={`absolute inset-x-0 bottom-[-1px] h-0.5 bg-accent ${inAt(4)}`} />
          </span>
          <span className="pb-1 text-muted">{t.placeBakery}</span>
        </div>
        <ListLine
          chips={
            <>
              <Chip tone="accent">{t.recipeA}</Chip>
              <Chip tone="accent">{t.recipeB}</Chip>
            </>
          }
        >
          <strong className="font-semibold">{t.flourLine}</strong>
        </ListLine>
        {bought.map((line) => (
          <div key={line.text} className="flex items-center gap-2">
            <span className="relative flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-field-border">
              <CheckIcon className={`size-3.5 text-accent ${inAt(line.slot)}`} />
            </span>
            <Struck slot={line.slot}>{line.text}</Struck>
            <span className={inAt(line.slot)}>
              <Chip>{t.bought}</Chip>
            </span>
          </div>
        ))}
      </MiniCard>
    </Scene>
  );
}
