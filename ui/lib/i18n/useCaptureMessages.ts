"use client";

import { captureMessagesFor } from "./capture";
import type { Locale } from "./locale";
import { useLocale } from "./useLocale";

/**
 * The capture messages in the language of the screen. An explicit `locale` (a screen that was
 * given one) wins over the provider's; the provider's `useLocale()` is always called first, so
 * the hook order never changes (spec 063 research R8).
 */
export function useCaptureMessages(locale?: Locale) {
  const current = useLocale();
  return captureMessagesFor(locale ?? current);
}
