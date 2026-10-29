import Link from "next/link";

import type { CartEntry } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

import { CountField } from "./CountField";

type CartEntryRowProps = {
  entry: CartEntry;
  /** Shown instead of the entry's saved factor while editing. */
  factor: string;
  locale: Locale;
  /** The address the recipe page's Back returns to. */
  from: string;
  /** Set in the editing view. */
  onMealsChange?: (meals: number) => void;
  onRemove?: () => void;
};

/** One cart recipe: title link, notebook, "Serves n", meals and the factor (spec 022). */
export function CartEntryRow({
  entry,
  factor,
  locale,
  from,
  onMealsChange,
  onRemove,
}: CartEntryRowProps) {
  const t = cartMessages[locale];
  const editing = Boolean(onMealsChange);
  return (
    <li className="flex flex-wrap items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface p-3">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <Link
          href={`/recipes/${encodeURIComponent(entry.recipe_id)}?from=${encodeURIComponent(from)}`}
          className="truncate text-[1rem] font-[550] text-foreground no-underline hover:text-accent"
        >
          {entry.title}
        </Link>
        <span className="truncate text-[0.85rem] text-muted">{entry.notebook_name}</span>
        <span className="text-[0.85rem] text-muted">{t.serves(entry.base_servings)}</span>
      </div>
      {editing && onMealsChange ? (
        <CountField label={t.meals} value={entry.meals} onChange={onMealsChange} locale={locale} />
      ) : (
        <span className="text-[0.85rem] text-muted">
          {t.meals} {entry.meals}
        </span>
      )}
      <span className="min-w-12 text-right text-[1rem] font-[550] text-foreground" data-testid="factor">
        {t.factor(factor)}
      </span>
      {onRemove ? (
        <button
          type="button"
          className="rounded-[var(--radius-md)] border border-border bg-background px-3 py-1 text-[0.85rem] text-foreground hover:border-owe"
          onClick={onRemove}
        >
          {t.remove}
        </button>
      ) : null}
    </li>
  );
}
