import { CartIcon, CheckIcon, ClipboardIcon, NotebookIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { inAt, ListLine, MiniCard, popAt, Scene } from "./parts";

/** The hero demo (FR-002a): a recipe captured, saved, added to the cart, and on the list. */
export function OverviewScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.overview;
  return (
    <Scene long>
      <MiniCard title={t.pasteLabel} icon={<ClipboardIcon />} className={inAt(1)}>
        <p className="m-0 text-muted">{t.pasted}</p>
      </MiniCard>

      <div className="flex flex-col gap-1.5">
        <span className={`flex items-center gap-1.5 ${inAt(2)}`}>
          <CheckIcon className="size-4 shrink-0 text-accent" />
          {t.captured}
        </span>
        <span className={`flex items-center gap-1.5 ${inAt(3)}`}>
          <NotebookIcon className="size-4 shrink-0 text-accent" />
          {t.savedTo}
        </span>
        <span className={`flex flex-wrap items-center gap-1.5 ${inAt(4)}`}>
          <CartIcon className="size-4 shrink-0 text-accent" />
          {t.addedToCart}
          <Chip tone="accent">{t.recipeA}</Chip>
          <Chip tone="accent">{t.recipeB}</Chip>
        </span>
      </div>

      <MiniCard title={t.listTitle} className={inAt(5)}>
        <div className={`origin-left ${popAt(6)}`}>
          <ListLine
            chips={
              <>
                <Chip>{t.recipeA}</Chip>
                <Chip>{t.recipeB}</Chip>
              </>
            }
          >
            <strong className="font-semibold">{t.flourLine}</strong>
          </ListLine>
        </div>
        <ListLine chips={<Chip>{t.recipeA}</Chip>}>{t.eggsLine}</ListLine>
      </MiniCard>
    </Scene>
  );
}
