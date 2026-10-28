"use client";

import { useOptionalPreferences } from "@/components/PreferencesProvider";

import type { Locale } from "./locale";

/**
 * The interface language in a client component: the preferences provider's locale. Without a
 * provider it is "en"; that only happens in component tests, because the root layout always
 * mounts the provider (spec 063 research R9).
 */
export function useLocale(): Locale {
  return useOptionalPreferences()?.locale ?? "en";
}
