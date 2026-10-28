"use client";

import { usePreferences } from "@/components/PreferencesProvider";
import { accountCopy } from "@/lib/i18n/account";
import type { Locale } from "@/lib/i18n/locale";

/**
 * The small English/Spanish switch on the signed-out screens (spec 063 FR-017). The default stays
 * Spanish; a pick lasts for the browser session and is dropped at sign-in. Each language is
 * named in its own language, so the switch reads the same in both.
 */
export function SignedOutLanguageSwitch() {
  const { locale, setLanguage } = usePreferences();
  const t = accountCopy(locale);
  const options: { value: Locale; label: string }[] = [
    { value: "en", label: t.en },
    { value: "es", label: t.es },
  ];
  return (
    <div
      role="group"
      aria-label={t.language}
      className="absolute right-4 top-3 z-10 inline-flex overflow-hidden rounded-[var(--radius-md)] border border-border bg-surface text-[0.8rem]"
    >
      {options.map((option) => {
        const current = option.value === locale;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={current}
            onClick={() => {
              if (!current) void setLanguage(option.value);
            }}
            className={`px-3 py-1 ${
              current ? "bg-accent font-semibold text-on-accent" : "bg-transparent text-foreground"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
