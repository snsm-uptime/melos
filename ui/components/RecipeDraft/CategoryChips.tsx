"use client";

import type { CategoryRef } from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";

export type CategoryOption = { id: string; label: string; tag: string | null };

type CategoryChipsProps = {
  title: string;
  addLabel: string;
  selected: CategoryRef[];
  options: CategoryOption[];
  max: number;
  /** The label of a variant's tag, for "Variant · Tag". */
  tagLabel: (tag: string) => string;
  onChange: (next: CategoryRef[]) => void;
};

const chipClassName =
  "inline-flex items-center gap-2 rounded-[8px] border border-accent px-2 py-[0.18rem] text-[0.75rem] text-accent";

/**
 * One group of controlled categories (spec 016 FR-011, FR-012). Chips come only from the
 * controlled lists. The add control hides once the group holds `max` values.
 */
export function CategoryChips({
  title,
  addLabel,
  selected,
  options,
  max,
  tagLabel,
  onChange,
}: CategoryChipsProps) {
  const available = options.filter((option) => !selected.some((item) => item.id === option.id));

  return (
    <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
      <legend className="mb-1 text-[0.85rem] text-muted">{title}</legend>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {selected.map((item) => (
          <li key={item.id} className={chipClassName}>
            <span>{item.tag ? captureMessages.variant(tagLabel(item.tag)) : item.label}</span>
            <span className="sr-only">{item.label}</span>
            <button
              type="button"
              aria-label={`${captureMessages.remove} ${item.label}`}
              onClick={() => onChange(selected.filter((value) => value.id !== item.id))}
              className="border-0 bg-transparent p-0 text-muted"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      {selected.length < max && available.length > 0 ? (
        <select
          aria-label={addLabel}
          className="w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[0.95rem] text-foreground"
          value=""
          onChange={(event) => {
            const picked = options.find((option) => option.id === event.target.value);
            if (!picked) return;
            onChange([...selected, { id: picked.id, label: picked.label, tag: picked.tag }]);
          }}
        >
          <option value="">{addLabel}</option>
          {available.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      ) : null}
    </fieldset>
  );
}
