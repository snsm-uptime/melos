import type { Locale } from "@/lib/i18n/locale";
import type { ShoppingLine } from "@/lib/shoppingListClient";
import { formatLine } from "@/lib/shoppingListText";

import { BoughtToggle, boughtText } from "./BoughtToggle";
import { RecipeChips } from "./RecipeChips";

type ShoppingLineRowProps = {
  line: ShoppingLine;
  kitchenId: string;
  locale: Locale;
  /** Shown only for a stored, writable list (spec 070 R3). */
  onToggle?: (bought: boolean) => void;
  /** A closed list: the saved bought state, read only (spec 070 FR-004). */
  frozen?: boolean;
};

/** One measured line of the shopping list with its recipe chips (spec 023). React escapes the text, so a name never becomes markup. */
export function ShoppingLineRow({
  line,
  kitchenId,
  locale,
  onToggle,
  frozen = false,
}: ShoppingLineRowProps) {
  return (
    <li
      data-bought={line.bought ? "true" : undefined}
      className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-surface p-3"
    >
      {onToggle || frozen ? (
        <BoughtToggle
          name={line.name}
          bought={line.bought === true}
          locale={locale}
          onToggle={onToggle}
        />
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <span className={`text-[1rem] font-[550] ${boughtText(line.bought)}`}>
          {formatLine(line)}
        </span>
        <RecipeChips kitchenId={kitchenId} recipes={line.recipes} locale={locale} />
      </div>
    </li>
  );
}
