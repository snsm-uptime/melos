import Link from "next/link";

import type { CartEntry } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

import { CloseIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";

import { CountField } from "./CountField";

type CartEntryRowProps = {
  entry: CartEntry;
  /** Shown instead of the entry's saved factor while editing. */
  factor: string;
  locale: Locale;
  /** The address the recipe page's Back returns to. */
  from: string;
  /** Set in the editing view. */
  onServingsChange?: (servings: number) => void;
  onRemove?: () => void;
};

/** One cart recipe: title link, notebook, "Serves n", servings and the factor (spec 022). */
export function CartEntryRow({
  entry,
  factor,
  locale,
  from,
  onServingsChange,
  onRemove,
}: CartEntryRowProps) {
  const t = cartMessages[locale];
  const editing = Boolean(onServingsChange);
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
      {editing && onServingsChange ? (
        <CountField
          label={t.servings}
          value={entry.servings}
          onChange={onServingsChange}
          locale={locale}
        />
      ) : (
        <span className="text-[0.85rem] text-muted">
          {t.servings} {entry.servings}
        </span>
      )}
      <span className="min-w-12 text-right text-[1rem] font-[550] text-foreground" data-testid="factor">
        {t.factor(factor)}
      </span>
      {onRemove ? (
        <IconButton
          label={t.removeRecipe(entry.title)}
          tone="danger"
          icon={<CloseIcon />}
          onClick={onRemove}
        />
      ) : null}
    </li>
  );
}
