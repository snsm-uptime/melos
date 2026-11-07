"use client";

import { useState, type FormEvent } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { renameName, type CatalogIngredient, type CatalogLanguage } from "@/lib/catalogClient";
import type { CatalogMessages } from "@/lib/i18n/catalog";

import { LanguageField } from "@/components/LanguageField";

const FIELD =
  "min-h-11 w-full rounded-[var(--radius-md)] border border-border bg-background px-3 text-[0.95rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";
const LINK =
  "self-start text-[0.9rem] text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";

/**
 * Rename a name, or set the language of the kept name (spec 043 US2, FR-010 to FR-012). A name
 * that already exists is refused with an offer to merge into it instead.
 */
export function RenameDialog({
  t,
  notebookId,
  ingredient,
  onClose,
  onDone,
  onMergeInto,
  onChanged,
}: {
  t: CatalogMessages;
  notebookId: string;
  ingredient: CatalogIngredient;
  onClose: () => void;
  onDone: (message: string) => void;
  onMergeInto: (existing: string) => void;
  /** The name was changed by someone else first: the caller reloads. */
  onChanged: () => void;
}) {
  const [name, setName] = useState(ingredient.name);
  const [language, setLanguage] = useState<CatalogLanguage | null>(ingredient.language);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<string | null>(null);

  async function save(event?: FormEvent) {
    event?.preventDefault();
    if (pending) return;
    if (name.trim() === "") {
      setError(t.nameBlank);
      return;
    }
    setPending(true);
    setError(null);
    setExisting(null);
    const languageChanged = language !== ingredient.language;
    const result = await renameName(
      notebookId,
      ingredient.name,
      name,
      languageChanged ? language : undefined,
    );
    setPending(false);
    if (result.ok) {
      const renamed = result.value.name !== ingredient.name;
      onDone(renamed ? t.renamed(result.value.name) : t.languageSaved(result.value.name));
      return;
    }
    if (result.code === "name_exists" && result.existing) {
      setExisting(result.existing);
      setError(t.nameExists(result.existing));
    } else if (result.code === "name_is_own_other_name") {
      setError(t.ownOtherName(name.trim(), ingredient.name));
    } else if (result.code === "name_blank") {
      setError(t.nameBlank);
    } else if (result.code === "name_changed") {
      onChanged();
    } else {
      setError(t.saveError);
    }
  }

  return (
    <ActionDialog
      open
      title={t.renameTitle(ingredient.name)}
      confirmLabel={t.save}
      cancelLabel={t.cancel}
      pending={pending}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      onConfirm={() => void save()}
    >
      <form className="flex flex-col gap-4" onSubmit={(event) => void save(event)}>
        <label className="flex flex-col gap-1">
          <span className="text-[0.9rem] text-muted">{t.newName}</span>
          <input
            className={FIELD}
            value={name}
            maxLength={200}
            readOnly={pending}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <LanguageField
          legend={t.nameLanguage}
          value={language}
          onChange={setLanguage}
          labels={{ ...t.languages, none: t.noLanguage }}
          disabled={pending}
        />
        {error ? (
          <p className="m-0 text-[0.9rem] text-muted" role="alert">
            {error}
          </p>
        ) : null}
        {existing ? (
          <button type="button" className={LINK} onClick={() => onMergeInto(existing)}>
            {t.mergeInto(existing)}
          </button>
        ) : null}
      </form>
    </ActionDialog>
  );
}
