"use client";

import { useId, useState } from "react";

import { parseCount } from "@/lib/cartFactor";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

type CountFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  locale: Locale;
  disabled?: boolean;
};

/**
 * A whole number from 1 to 99 (spec 022 FR-004). Invalid or blank input keeps the last valid
 * value and says what is allowed; leaving the field shows the valid value again.
 */
export function CountField({ label, value, onChange, locale, disabled }: CountFieldProps) {
  const t = cartMessages[locale];
  const id = useId();
  const [text, setText] = useState(String(value));
  const [invalid, setInvalid] = useState(false);
  // A new value from outside (e.g. a reload) replaces the text, unless it is what was typed.
  const [shown, setShown] = useState(value);
  if (shown !== value) {
    setShown(value);
    if (parseCount(text) !== value) setText(String(value));
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-[0.85rem] text-muted">
        {label}
      </label>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        value={text}
        disabled={disabled}
        aria-invalid={invalid}
        aria-describedby={invalid ? `${id}-error` : undefined}
        className="w-16 rounded-[var(--radius-sm,6px)] border border-border bg-background px-2 py-1 text-foreground"
        onChange={(event) => {
          // Digits only: anything else never reaches the field.
          if (/\D/.test(event.target.value)) return;
          setText(event.target.value);
          const parsed = parseCount(event.target.value);
          setInvalid(parsed === null);
          if (parsed !== null && parsed !== value) onChange(parsed);
        }}
        onBlur={() => {
          setText(String(value));
          setInvalid(false);
        }}
      />
      {/* Space kept for one line, and the text out of the flow, so showing it moves nothing. */}
      <div className="relative h-[1.2rem]">
        {invalid ? (
          <span
            id={`${id}-error`}
            role="alert"
            className="absolute left-0 top-0 whitespace-nowrap text-[0.8rem] text-owe"
          >
            {t.countError}
          </span>
        ) : null}
      </div>
    </div>
  );
}
