import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import type { YourCallEntry } from "@/lib/shoppingListClient";
import { formatYourCall } from "@/lib/shoppingListText";

import { RecipeChips } from "./RecipeChips";

type YourCallListProps = { entries: YourCallEntry[]; kitchenId: string; locale: Locale };

/**
 * "Your call" (spec 023 FR-007): ingredients given without an amount, once each with every
 * distinct note. Renders nothing when there are none.
 */
export function YourCallList({ entries, kitchenId, locale }: YourCallListProps) {
  if (entries.length === 0) return null;
  const t = shoppingListMessages[locale];
  return (
    <div data-your-call className="flex flex-col gap-2">
      <h3 className="m-0 text-[1rem] font-[600] text-foreground">{t.yourCall}</h3>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {entries.map((entry) => (
          <li
            key={entry.name}
            className="flex flex-col gap-2 rounded-[var(--radius-md)] border border-border bg-surface p-3"
          >
            <span className="text-[1rem] font-[550] text-foreground">{formatYourCall(entry)}</span>
            <RecipeChips kitchenId={kitchenId} recipes={entry.recipes} locale={locale} />
          </li>
        ))}
      </ul>
    </div>
  );
}
