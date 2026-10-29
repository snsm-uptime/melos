"use client";

import { useEffect, useRef } from "react";

import { useLockKeepAlive } from "@/hooks/useLockKeepAlive";
import { discardCart, startCartEdit } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

type CartEditingBarProps = {
  kitchenId: string;
  /** When my cart lock ends without activity. */
  idleExpiresAt: string | null;
  locale: Locale;
  /** Reload the cart after Discard, Keep editing or expiry. */
  onChanged: () => void;
  onSave: () => void;
  /** Discard; defaults to discarding through the api, then `onChanged`. */
  onDiscard?: () => void;
  pending?: boolean;
};

/**
 * Shown on the Cart page while my session edits the cart, docked above the tab bar (spec 022
 * FR-017a): Save and Discard, and one minute before the idle limit a warning with Keep editing.
 */
export function CartEditingBar({
  kitchenId,
  idleExpiresAt,
  locale,
  onChanged,
  onSave,
  onDiscard,
  pending = false,
}: CartEditingBarProps) {
  const t = cartMessages[locale];
  const { keepNow, warning, expired } = useLockKeepAlive({
    keepAlive: () => void startCartEdit(kitchenId).then(onChanged),
    idleExpiresAt,
  });
  const told = useRef(false);

  useEffect(() => {
    if (expired && !told.current) {
      told.current = true;
      onChanged();
    }
  }, [expired, onChanged]);

  if (expired) {
    return (
      <div role="status" className={BAR}>
        <span>{t.cartDiscarded}</span>
      </div>
    );
  }
  return (
    <div role="status" className={BAR}>
      <span className="min-w-0 flex-1">{warning ? t.idleWarning : t.editingBar}</span>
      <div className="flex flex-wrap gap-2">
        {warning ? (
          <button type="button" className={ACTION} onClick={keepNow}>
            {t.keepEditing}
          </button>
        ) : null}
        <button
          type="button"
          className={ACTION}
          disabled={pending}
          onClick={onDiscard ?? (() => void discardCart(kitchenId).then(onChanged))}
        >
          {t.discard}
        </button>
        <button type="button" className={PRIMARY} disabled={pending} onClick={onSave}>
          {t.save}
        </button>
      </div>
    </div>
  );
}

const BAR =
  "flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-accent bg-surface px-3 py-2 text-[0.9rem] text-foreground";
const PRIMARY =
  "rounded-[var(--radius-md)] border border-accent bg-accent px-3 py-1 text-[0.85rem] font-[550] text-background disabled:opacity-50";
const ACTION =
  "rounded-[var(--radius-md)] border border-border bg-background px-3 py-1 text-[0.85rem] text-foreground no-underline hover:border-accent";
