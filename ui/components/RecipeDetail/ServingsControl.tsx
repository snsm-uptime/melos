"use client";

import { useId, useState } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { MAX_SERVINGS, MIN_SERVINGS, parseServings, stepServings } from "@/lib/recipeScale";

type ServingsControlProps = {
  /** The servings the page is showing right now. */
  value: number;
  onChange: (servings: number) => void;
  locale: Locale;
};

const stepButtonClassName =
  "flex h-8 w-8 items-center justify-center rounded-[0.5rem] border border-border text-[1.1rem] leading-none text-foreground disabled:opacity-40";

/**
 * Sets the servings the detail page shows (spec 062). A valid whole number from 1 to 100 applies
 * at once; anything else is not applied and a hint says what is accepted. The typed text is kept
 * apart from the applied value, so "1" on the way to "12" is never an error.
 */
export function ServingsControl({ value, onChange, locale }: ServingsControlProps) {
  const t = recipeDetailMessages[locale];
  const id = useId();
  // What the member typed since the applied value last changed; dropped when it changes.
  const [typed, setTyped] = useState<{ from: number; text: string } | null>(null);
  const text = typed && typed.from === value ? typed.text : String(value);
  const invalid = typed !== null && typed.from === value && parseServings(typed.text) === null;

  // The announcement for screen readers: set when the applied value changes after the first render.
  const [lastValue, setLastValue] = useState(value);
  const [announcement, setAnnouncement] = useState("");
  if (lastValue !== value) {
    setLastValue(value);
    setAnnouncement(t.scaledAnnouncement(value));
  }

  function type(next: string) {
    const parsed = parseServings(next);
    // A valid number is applied and the field follows the applied value from then on; only an
    // entry that was not applied is kept as typed text. Keeping an applied entry would bring it
    // back later, for example after Reset returns to the number it was typed over.
    if (parsed !== null) {
      setTyped(null);
      if (parsed !== value) onChange(parsed);
      return;
    }
    setTyped({ from: value, text: next });
  }

  function settle() {
    setTyped(null);
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <label htmlFor={id} className="text-[0.85rem] text-muted">
          {t.servingsControlLabel}
        </label>
        <button
          type="button"
          className={stepButtonClassName}
          aria-label={t.fewerServings}
          disabled={value <= MIN_SERVINGS}
          onClick={() => onChange(stepServings(value, -1))}
        >
          −
        </button>
        <input
          id={id}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          className="w-16 rounded-[0.75rem] border border-border bg-background px-2 py-1 text-center text-[1rem] text-foreground"
          value={text}
          aria-invalid={invalid || undefined}
          onChange={(event) => type(event.target.value)}
          onBlur={settle}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              settle();
            }
          }}
        />
        <button
          type="button"
          className={stepButtonClassName}
          aria-label={t.moreServings}
          disabled={value >= MAX_SERVINGS}
          onClick={() => onChange(stepServings(value, 1))}
        >
          +
        </button>
      </div>
      {invalid ? (
        <span role="alert" className="text-[0.8rem] text-owe">
          {t.servingsHint}
        </span>
      ) : null}
      <span className="sr-only" aria-live="polite">
        {announcement}
      </span>
    </div>
  );
}
