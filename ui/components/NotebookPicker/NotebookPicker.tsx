"use client";

import { SearchableSelect } from "@/components/SearchableSelect";
import type { Locale } from "@/lib/i18n/locale";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";

export type NotebookPickerOption = { id: string; name: string };

const FIELD_CLASS =
  "w-full justify-between rounded-[var(--rounded-sm)] border border-border bg-surface px-2 py-1.5 text-left text-[0.95rem] text-foreground outline-none focus-visible:border-accent disabled:opacity-60";
const INLINE_CLASS =
  "max-w-full rounded-[0.4rem] border border-transparent px-1 py-[0.1rem] text-left text-[0.9rem] text-muted outline-none hover:bg-background hover:text-foreground focus-visible:border-accent focus-visible:text-foreground disabled:opacity-60";

/**
 * The standard notebook picker: a searchable dropdown of notebooks (first made for the default
 * notebook in Settings). "field" is a bordered form field; "inline" reads as the text around it.
 */
export function NotebookPicker({
  value,
  notebooks,
  onChange,
  label,
  disabled = false,
  variant = "field",
  locale,
}: {
  value: string;
  notebooks: NotebookPickerOption[];
  onChange: (id: string) => void;
  /** The accessible name. */
  label: string;
  disabled?: boolean;
  variant?: "field" | "inline";
  locale: Locale;
}) {
  const t = sidePanelMessages[locale];
  return (
    <SearchableSelect
      aria-label={label}
      searchLabel={t.searchNotebooks}
      noResults={t.noNotebookMatch}
      className={variant === "inline" ? INLINE_CLASS : FIELD_CLASS}
      panelWidth={240}
      value={value}
      disabled={disabled}
      options={notebooks.map((notebook) => ({
        value: notebook.id,
        label: notebook.name,
      }))}
      onChange={(id) => onChange(id)}
    />
  );
}
