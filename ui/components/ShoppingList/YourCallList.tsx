import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import type { YourCallEntry } from "@/lib/shoppingListClient";

import { ITEM_GRID } from "./itemGrid";
import { ShoppingRow } from "./ShoppingLine";

type YourCallListProps = {
  entries: YourCallEntry[];
  kitchenId: string;
  locale: Locale;
  /** Shown only for a stored, writable list (spec 070 R3). */
  onToggle?: (itemId: string, bought: boolean) => void;
  /** A closed list: the saved bought state, read only (spec 070 FR-004). */
  frozen?: boolean;
};

/**
 * "Your call" (spec 023 FR-007): ingredients given without an amount, once each with every
 * distinct note. Renders nothing when there are none.
 */
export function YourCallList({
  entries,
  kitchenId,
  locale,
  onToggle,
  frozen = false,
}: YourCallListProps) {
  if (entries.length === 0) return null;
  const t = shoppingListMessages[locale];
  return (
    <div data-your-call className="flex flex-col gap-2">
      <h3 className="m-0 text-[1rem] font-[600] text-foreground">
        {t.yourCall}
      </h3>
      <ul className={ITEM_GRID}>
        {entries.map((entry) => (
          <ShoppingRow
            key={entry.name}
            name={entry.name}
            detail={entry.notes.join(", ")}
            recipes={entry.recipes}
            bought={entry.bought}
            kitchenId={kitchenId}
            locale={locale}
            showToggle={Boolean(onToggle && entry.id) || frozen}
            onToggle={
              onToggle && entry.id
                ? (bought) => onToggle(entry.id as string, bought)
                : undefined
            }
          />
        ))}
      </ul>
    </div>
  );
}
