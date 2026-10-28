/**
 * The signed-out language pick (spec 063 FR-013, research R3): a session cookie `melos_lang`
 * that the server can read on the first request, so a visitor who picked English never sees the
 * page in Spanish first. It has no `Max-Age` and no `Expires`, so it ends with the browser
 * session. Browser only; every access is guarded so blocked cookies never throw.
 */

import { isLocale, LANGUAGE_COOKIE, type Locale } from "./locale";

export function readLanguagePick(): Locale | null {
  try {
    for (const part of document.cookie.split(";")) {
      const [name, ...rest] = part.trim().split("=");
      if (name === LANGUAGE_COOKIE) {
        const value = rest.join("=");
        return isLocale(value) ? value : null;
      }
    }
  } catch {
    /* cookies blocked */
  }
  return null;
}

function secure(): string {
  return typeof location !== "undefined" && location.protocol === "https:" ? "; Secure" : "";
}

export function writeLanguagePick(locale: Locale): void {
  try {
    document.cookie = `${LANGUAGE_COOKIE}=${locale}; Path=/; SameSite=Lax${secure()}`;
  } catch {
    /* cookies blocked: the choice still applies until the next load */
  }
}

export function clearLanguagePick(): void {
  try {
    document.cookie = `${LANGUAGE_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0${secure()}`;
  } catch {
    /* cookies blocked */
  }
}
