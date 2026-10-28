"use client";

import { useState } from "react";

import { usePreferences } from "@/components/PreferencesProvider";
import { accountCopy } from "@/lib/i18n/account";
import type { Locale } from "@/lib/i18n/locale";

/**
 * The language choice on the account screen (spec 063 FR-003 to FR-005): English or Spanish, the
 * current one checked. A choice is saved to the account and applies at once; if it cannot be
 * saved the member is told and the language that is saved stays shown.
 */
export function LanguageChoice() {
  const { locale, setLanguage } = usePreferences();
  const t = accountCopy(locale);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function choose(next: Locale) {
    if (next === locale || pending) return;
    setPending(true);
    setFailed(false);
    try {
      await setLanguage(next);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  const options: { value: Locale; label: string }[] = [
    { value: "en", label: t.en },
    { value: "es", label: t.es },
  ];

  return (
    <div className="flex flex-col gap-2">
      <div
        role="radiogroup"
        aria-label={t.language}
        className="inline-flex self-start overflow-hidden rounded-[var(--radius-md)] border border-border"
      >
        {options.map((option) => {
          const checked = option.value === locale;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={checked}
              disabled={pending}
              tabIndex={checked ? 0 : -1}
              onClick={() => void choose(option.value)}
              onKeyDown={(event) => {
                if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) {
                  event.preventDefault();
                  void choose(option.value === "en" ? "es" : "en");
                }
              }}
              className={`px-4 py-2 text-[0.95rem] disabled:opacity-60 ${
                checked ? "bg-accent font-semibold text-on-accent" : "bg-transparent text-foreground"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      {failed ? (
        <p role="alert" className="m-0 text-[0.85rem] text-owe">
          {t.saveLanguageFailed}
        </p>
      ) : null}
    </div>
  );
}
