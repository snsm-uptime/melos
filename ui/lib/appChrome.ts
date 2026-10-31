const APP_CHROME_PREFIXES = ["/home", "/kitchens", "/notebooks", "/recipes"] as const;

/** Authenticated product surfaces that show the side panel. */
export function showsAppChrome(pathname: string): boolean {
  return APP_CHROME_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

/** "notebooks" or `kitchen:{id}`. */
export type PanelEntry = string;

/** The side panel entry for a page. */
export function panelEntryFromPath(pathname: string): PanelEntry | undefined {
  const kitchenId = /^\/kitchens\/([^/]+)/.exec(pathname)?.[1];
  if (kitchenId) return `kitchen:${kitchenId}`;
  // A recipe lives in a notebook, so its detail and edit pages keep Notebooks marked.
  if (
    pathname === "/notebooks" ||
    pathname.startsWith("/notebooks/") ||
    pathname.startsWith("/recipes/")
  ) {
    return "notebooks";
  }
  return undefined;
}

const LANGUAGE_SWITCH_PREFIXES = [
  "/sign-in",
  "/signup",
  "/sign-up",
  "/forgot-password",
  "/reset-password",
  "/verify",
  "/invites/accept",
] as const;

/** Signed-out screens that place the switch themselves, inside their own column. */
const INLINE_LANGUAGE_SWITCH_PREFIXES = ["/sign-in"] as const;

/** Signed-out screens that carry the small English/Spanish switch (spec 063 FR-017). */
export function showsLanguageSwitch(pathname: string): boolean {
  // The landing page is the first signed-out screen a visitor sees.
  if (pathname === "/") return true;
  return LANGUAGE_SWITCH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

/** The screens whose switch floats at the top right; the others render it in their own column. */
export function showsFloatingLanguageSwitch(pathname: string): boolean {
  if (!showsLanguageSwitch(pathname)) return false;
  return !INLINE_LANGUAGE_SWITCH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
