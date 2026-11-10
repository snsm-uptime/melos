"use client";

import { AddRecipeOptionsDialog } from "@/components/AddRecipeCallToAction/AddRecipeOptionsDialog";
import { IngredientLineRow } from "@/components/RecipeDraft/IngredientLineRow";
import type { Locale } from "@/lib/i18n/locale";

import { draftLines, SIZES, UNITS } from "./data";
import { ignore, inAt, Rows, Scene, Swap } from "./parts";

/**
 * Capture (FR-006.1): the app's add-recipe choices (a link, a picture, text), then the draft the
 * pasted text became, in the draft page's own rows: salt with the vague amount "a pinch", and
 * onion as 2 unit large.
 */
export function CaptureScene({ locale }: { locale: Locale }) {
  const lines = draftLines(locale);
  return (
    <Scene>
      <Swap
        slot={3}
        before={
          <div className={inAt(1)}>
            <AddRecipeOptionsDialog
              open
              locale={locale}
              onClose={ignore}
              onChooseUrl={ignore}
              onChoosePicture={ignore}
              onChooseText={ignore}
              onChooseManual={ignore}
            />
          </div>
        }
        after={
          <div className="flex flex-col gap-2">
            {lines.map((line, index) => (
              <Rows key={line.key} className={inAt(index === 0 ? 3 : 4)}>
                <IngredientLineRow
                  line={line}
                  index={index}
                  count={lines.length}
                  errors={[]}
                  units={UNITS}
                  sizes={SIZES}
                  catalog={[]}
                  onUndoChange={ignore}
                  onChange={ignore}
                  onRemove={ignore}
                  onMove={ignore}
                  locale={locale}
                />
              </Rows>
            ))}
          </div>
        }
      />
    </Scene>
  );
}
