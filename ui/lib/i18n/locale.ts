/**
 * Shared locale helpers: English and Spanish only, Spanish by default (spec 063). The language
 * of the interface comes from one place on the server (`lib/serverLocale.ts`) and from the
 * preferences provider in the browser; nothing here guesses it from the browser or a header.
 */
export type Locale = "en" | "es";

/** What everyone sees until they choose otherwise (spec 063 FR-001). */
export const DEFAULT_LOCALE: Locale = "es";

/** The signed-out pick: a session cookie holding "en" or "es" (spec 063 FR-013, data-model). */
export const LANGUAGE_COOKIE = "melos_lang";

export function isLocale(raw: unknown): raw is Locale {
  return raw === "en" || raw === "es";
}

/** The value if it is English or Spanish; anything else, including none, is the default (FR-016). */
export function resolveLocale(raw: string | null | undefined): Locale {
  return isLocale(raw) ? raw : DEFAULT_LOCALE;
}

export type ThemePreference = "light" | "dark" | "system";
