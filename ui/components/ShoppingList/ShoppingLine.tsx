import type { ReactNode } from "react";

import type { Locale } from "@/lib/i18n/locale";
import type { ShoppingLine, ShoppingRecipeRef } from "@/lib/shoppingListClient";

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

/** One compact list row: name and detail, then recipe chips, then the bought checkbox. React escapes the text, so a name never becomes markup. */
export function ShoppingRow({
  name,
  detail,
  recipes,
  bought,
  kitchenId,
  locale,
  onToggle,
  showToggle,
  trailing,
}: {
  name: string;
  detail: string;
  recipes: ShoppingRecipeRef[];
  bought: boolean | undefined;
  kitchenId: string;
  locale: Locale;
  onToggle?: (bought: boolean) => void;
  showToggle: boolean;
  /** Extra control after the checkbox (Remove on a hand item). */
  trailing?: ReactNode;
}) {
  return (
    <li
      data-bought={bought ? "true" : undefined}
      className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-1.5"
    >
      <div className="min-w-0 flex-1">
        <span
          className={`flex min-w-0 items-baseline gap-2 ${boughtText(bought)}`}
        >
          <span className="truncate text-[1rem] font-[550]">{name}</span>
          <span className="sr-only"> — </span>
          <span className="shrink-0 text-[0.9rem] tabular-nums text-muted">
            {detail}
          </span>
        </span>
      </div>
      {recipes.length > 0 ? (
        <RecipeChips kitchenId={kitchenId} recipes={recipes} locale={locale} />
      ) : null}
      {showToggle ? (
        <BoughtToggle
          name={name}
          bought={bought === true}
          locale={locale}
          onToggle={onToggle}
        />
      ) : null}
      {trailing}
    </li>
  );
}

/** One measured line of the shopping list with its recipe chips (spec 023). */
export function ShoppingLineRow({
  line,
  kitchenId,
  locale,
  onToggle,
  frozen = false,
}: ShoppingLineRowProps) {
  const amounts = line.amounts
    .map((amount) =>
      line.kind === "count"
        ? amount.quantity
        : `${amount.quantity} ${amount.unit}`,
    )
    .join(" + ");
  return (
    <ShoppingRow
      name={line.size ? `${line.name}, ${line.size}` : line.name}
      detail={amounts}
      recipes={line.recipes}
      bought={line.bought}
      kitchenId={kitchenId}
      locale={locale}
      onToggle={onToggle}
      showToggle={Boolean(onToggle) || frozen}
    />
  );
}
