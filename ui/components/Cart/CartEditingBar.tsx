"use client";

import { useEffect, useRef, useState } from "react";

import { CloseIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import { useLockKeepAlive } from "@/hooks/useLockKeepAlive";
import { startCartEdit } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

/** How long "You're editing the cart" stays up unless dismissed sooner. */
export const EDITING_NOTICE_MS = 30_000;

type CartEditingBarProps = {
  kitchenId: string;
  /** When my cart lock ends without activity. */
  idleExpiresAt: string | null;
  locale: Locale;
  /** Reload the cart after Keep editing or expiry. */
  onChanged: () => void;
};

/**
 * Shown on the Cart page while my session edits the cart, docked above the tab bar (spec 022
 * FR-017a). It says I'm editing for 30 seconds or until dismissed; Save and Discard are in the
 * chrome. It stays mounted after that, because it keeps the lock's timers: one minute before the
 * idle limit the warning with Keep editing comes up even if the notice was dismissed.
 */
export function CartEditingBar({
  kitchenId,
  idleExpiresAt,
  locale,
  onChanged,
}: CartEditingBarProps) {
  const t = cartMessages[locale];
  const { keepNow, warning, expired } = useLockKeepAlive({
    keepAlive: () => void startCartEdit(kitchenId).then(onChanged),
    idleExpiresAt,
  });
  const told = useRef(false);
  const [noticeClosed, setNoticeClosed] = useState(false);
  const [warningClosed, setWarningClosed] = useState(false);
  // Each warning is its own: closing one doesn't hide the next.
  if (!warning && warningClosed) setWarningClosed(false);

  useEffect(() => {
    const timer = setTimeout(() => setNoticeClosed(true), EDITING_NOTICE_MS);
    return () => clearTimeout(timer);
  }, []);

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
  if (warning ? warningClosed : noticeClosed) return null;
  return (
    <div role="status" className={BAR}>
      <span className="min-w-0 flex-1">{warning ? t.idleWarning : t.editingBar}</span>
      {warning ? (
        <button type="button" className={ACTION} onClick={keepNow}>
          {t.keepEditing}
        </button>
      ) : null}
      <IconButton
        label={t.dismiss}
        icon={<CloseIcon />}
        onClick={() => (warning ? setWarningClosed(true) : setNoticeClosed(true))}
      />
    </div>
  );
}

const BAR =
  "flex items-center gap-2 rounded-[var(--radius-md)] border border-accent bg-surface px-3 py-2 text-[0.9rem] text-foreground";
const ACTION =
  "rounded-[var(--radius-md)] border border-border bg-background px-3 py-1 text-[0.85rem] text-foreground no-underline hover:border-accent";
