import type { Locale } from "./locale";

/**
 * The messages for a locale. English is the base and the chosen language goes on top, so a
 * message missing in Spanish shows its English text, never blank text or a key (spec 063 FR-009).
 * The parity test (`parity.test.ts`) fails the build when any message exists in one language only.
 */
export function messagesFor<T extends object>(
  set: { en: T; es: Partial<NoInfer<T>> },
  locale: Locale,
): T {
  return { ...set.en, ...set[locale] };
}
