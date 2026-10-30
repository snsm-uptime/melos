import type { Locale } from "@/lib/i18n/locale";
import type { ShoppingLine } from "@/lib/shoppingListClient";
import { formatLine } from "@/lib/shoppingListText";

import { RecipeChips } from "./RecipeChips";

type ShoppingLineRowProps = { line: ShoppingLine; kitchenId: string; locale: Locale };

/** One measured line of the shopping list with its recipe chips (spec 023). React escapes the text, so a name never becomes markup. */
export function ShoppingLineRow({ line, kitchenId, locale }: ShoppingLineRowProps) {
  return (
    <li className="flex flex-col gap-2 rounded-[var(--radius-md)] border border-border bg-surface p-3">
      <span className="text-[1rem] font-[550] text-foreground">{formatLine(line)}</span>
      <RecipeChips kitchenId={kitchenId} recipes={line.recipes} locale={locale} />
    </li>
  );
}
