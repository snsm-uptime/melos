import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import type { YourCallEntry } from "@/lib/shoppingListClient";
import { formatYourCall } from "@/lib/shoppingListText";

import { BoughtToggle, boughtText } from "./BoughtToggle";
import { RecipeChips } from "./RecipeChips";

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
      <h3 className="m-0 text-[1rem] font-[600] text-foreground">{t.yourCall}</h3>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {entries.map((entry) => (
          <li
            key={entry.name}
            data-bought={entry.bought ? "true" : undefined}
            className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-surface p-3"
          >
            {(onToggle && entry.id) || frozen ? (
              <BoughtToggle
                name={entry.name}
                bought={entry.bought === true}
                locale={locale}
                onToggle={
                  onToggle && entry.id
                    ? (bought) => onToggle(entry.id as string, bought)
                    : undefined
                }
              />
            ) : null}
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <span className={`text-[1rem] font-[550] ${boughtText(entry.bought)}`}>
                {formatYourCall(entry)}
              </span>
              <RecipeChips kitchenId={kitchenId} recipes={entry.recipes} locale={locale} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
