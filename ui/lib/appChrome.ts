import type { TabKey } from "@/components/soft-ledger/TabBar";

const APP_CHROME_PREFIXES = ["/home", "/kitchens", "/account", "/notebooks", "/recipes"] as const;

/** Authenticated product surfaces that keep the bottom tab bar mounted. */
export function showsAppChrome(pathname: string): boolean {
  return APP_CHROME_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function tabKeyFromPath(pathname: string): TabKey | undefined {
  if (
    pathname === "/home" ||
    pathname.startsWith("/home/") ||
    pathname === "/kitchens" ||
    pathname.startsWith("/kitchens/")
  ) {
    return "home";
  }
  // A recipe lives in a notebook, so its detail and edit pages keep the Notebook tab active.
  if (
    pathname === "/notebooks" ||
    pathname.startsWith("/notebooks/") ||
    pathname.startsWith("/recipes/")
  ) {
    return "notebook";
  }
  if (pathname === "/account" || pathname.startsWith("/account/")) return "account";
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

/** Signed-out screens that carry the small English/Spanish switch (spec 063 FR-017). */
export function showsLanguageSwitch(pathname: string): boolean {
  // The landing page is the first signed-out screen a visitor sees.
  if (pathname === "/") return true;
  return LANGUAGE_SWITCH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
