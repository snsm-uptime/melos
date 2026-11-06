"use client";

import { useId } from "react";

import { SoftLedgerRadio } from "@/components/soft-ledger/Radio";

export type ContentLanguage = "en" | "es";

export type LanguageFieldLabels = {
  en: string;
  es: string;
  /** Offered as a third choice ("Not set") when given. */
  none?: string;
};

/**
 * English or Spanish as a radio group, for a recipe's or an ingredient name's language
 * (spec 043). The group is a fieldset, so a screen reader names the choice and the arrow keys
 * move between the options.
 */
export function LanguageField({
  legend,
  value,
  onChange,
  labels,
  disabled = false,
}: {
  legend: string;
  value: ContentLanguage | null;
  onChange: (value: ContentLanguage | null) => void;
  labels: LanguageFieldLabels;
  disabled?: boolean;
}) {
  const name = useId();
  const options: { value: ContentLanguage | null; label: string }[] = [
    { value: "en", label: labels.en },
    { value: "es", label: labels.es },
    ...(labels.none ? [{ value: null, label: labels.none }] : []),
  ];
  return (
    <fieldset className="m-0 flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 border-0 p-0">
      <legend className="mb-1 p-0 text-[0.9rem] text-muted">{legend}</legend>
      {options.map((option) => (
        <SoftLedgerRadio
          key={option.value ?? "none"}
          name={name}
          value={option.value ?? ""}
          checked={value === option.value}
          disabled={disabled}
          onChange={() => onChange(option.value)}
        >
          {option.label}
        </SoftLedgerRadio>
      ))}
    </fieldset>
  );
}
