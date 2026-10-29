"use client";

import { useEffect, useRef } from "react";

import { useToast } from "@/components/Toast";
import { useLockKeepAlive } from "@/hooks/useLockKeepAlive";
import { startCartEdit, type CartEditor } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

const TOAST_ID = "cart-idle";

/**
 * The cart's idle warning on pages without the editing bar, the kitchen list and recipe pages
 * (spec 022 FR-017d): one minute before my lock ends a persistent toast with Keep editing, then
 * "Your cart changes were discarded". Nothing when the lock is not mine.
 */
export function useCartIdleToasts(
  kitchenId: string | null,
  editor: CartEditor | null | undefined,
  locale: Locale,
  onChanged: () => void,
) {
  const t = cartMessages[locale];
  const toast = useToast();
  const mine = Boolean(kitchenId && editor?.is_me);
  const changed = useRef(onChanged);
  useEffect(() => {
    changed.current = onChanged;
  }, [onChanged]);

  const { keepNow, warning, expired } = useLockKeepAlive({
    keepAlive: () => {
      if (kitchenId) void startCartEdit(kitchenId).then(() => changed.current());
    },
    idleExpiresAt: mine ? (editor?.idle_expires_at ?? null) : null,
  });

  const told = useRef(false);
  useEffect(() => {
    if (!mine) {
      told.current = false;
      toast.dismiss(TOAST_ID);
      return;
    }
    if (expired) {
      if (told.current) return;
      told.current = true;
      toast.show({ id: TOAST_ID, text: t.cartDiscarded });
      changed.current();
    } else if (warning) {
      toast.show({
        id: TOAST_ID,
        text: t.idleWarning,
        persistent: true,
        action: { label: t.keepEditing, onClick: keepNow },
      });
    } else {
      told.current = false;
      toast.dismiss(TOAST_ID);
    }
  }, [mine, warning, expired, toast, keepNow, t]);
}
