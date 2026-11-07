"use client";

import { useEffect, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import { SearchableSelect } from "@/components/SearchableSelect";
import {
  mergeNames,
  previewMerge,
  type CatalogLanguage,
  type MergePreview,
  type MergeResult,
} from "@/lib/catalogClient";
import type { CatalogMessages } from "@/lib/i18n/catalog";

import { LanguageField } from "@/components/LanguageField";

type Preview =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; value: MergePreview }
  | { status: "error"; message: string };

/** A preview answer, for the pair of names it was asked for. */
type Loaded = { key: string; preview: Preview };

function previewError(code: string | null, t: CatalogMessages): string {
  if (code === "same_ingredient") return t.sameIngredient;
  if (code === "unknown_name") return t.unknownName;
  return t.saveError;
}

/**
 * Merge one name into another (spec 043 US1). The person picks the name to keep, the dialog
 * shows every notebook that changes and the language of each name (editable), and nothing
 * changes until they confirm (FR-004). Picking the kept name is the only step before confirm,
 * so a merge takes four taps from the Ingredients page (SC-001).
 */
export function MergeDialog({
  t,
  notebookId,
  merged: initialMerged,
  kept: initialKept = "",
  names,
  onClose,
  onDone,
}: {
  t: CatalogMessages;
  notebookId: string;
  merged: string;
  kept?: string;
  /** The catalog's kept names, the choices for the name to keep. */
  names: string[];
  onClose: () => void;
  onDone: (result: MergeResult, merged: string, kept: string) => void;
}) {
  const [merged, setMerged] = useState(initialMerged);
  const [kept, setKept] = useState(initialKept);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [mergedLanguage, setMergedLanguage] = useState<CatalogLanguage | null>(null);
  const [keptLanguage, setKeptLanguage] = useState<CatalogLanguage | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const key = `${merged}\u0000${kept}`;
  // Loading until the answer for these two names is in; nothing to ask before a name is kept.
  const preview: Preview = !kept
    ? { status: "idle" }
    : loaded?.key === key
      ? loaded.preview
      : { status: "loading" };

  useEffect(() => {
    if (!kept) return;
    let current = true;
    void previewMerge(notebookId, merged, kept).then((result) => {
      if (!current) return;
      if (!result.ok) {
        setLoaded({ key, preview: { status: "error", message: previewError(result.code, t) } });
        return;
      }
      setLoaded({ key, preview: { status: "ready", value: result.value } });
      setMergedLanguage(result.value.merged_language);
      setKeptLanguage(result.value.kept_language);
    });
    return () => {
      current = false;
    };
  }, [notebookId, merged, kept, key, t]);

  const ready = preview.status === "ready" && preview.value.notebooks.length > 0;

  async function confirm() {
    if (preview.status !== "ready" || !ready || pending) return;
    setPending(true);
    setError(null);
    const result = await mergeNames({
      merged: preview.value.merged,
      kept: preview.value.kept,
      merged_language: mergedLanguage,
      kept_language: keptLanguage,
      notebook_ids: preview.value.notebooks.map((n) => n.notebook_id),
    });
    setPending(false);
    if (result.ok) onDone(result.value, preview.value.merged, preview.value.kept);
    else setError(t.saveError);
  }

  function swap() {
    setMerged(kept);
    setKept(merged);
  }

  return (
    <ActionDialog
      open
      title={t.mergeTitle(merged)}
      confirmLabel={ready ? t.confirmMerge : undefined}
      cancelLabel={t.cancel}
      pending={pending}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      onConfirm={() => void confirm()}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-[0.9rem] text-muted">{t.keepLabel}</span>
          <SearchableSelect
            aria-label={t.keepLabel}
            placeholder={t.keepPlaceholder}
            value={kept}
            options={names.filter((n) => n !== merged).map((n) => ({ value: n, label: n }))}
            searchLabel={t.searchNames}
            noResults={t.noNameMatch}
            onChange={(value) => setKept(value)}
            className="min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-left text-[0.95rem] text-foreground"
          />
          {kept ? (
            <button
              type="button"
              className="self-start text-[0.9rem] text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              onClick={swap}
            >
              {t.swap}
            </button>
          ) : null}
        </div>

        {preview.status === "loading" ? <CauldronLoader label={t.previewLoading} /> : null}
        {preview.status === "error" ? (
          <p className="m-0 text-[0.9rem] text-muted" role="alert">
            {preview.message}
          </p>
        ) : null}
        {preview.status === "ready" ? (
          preview.value.notebooks.length === 0 ? (
            <p className="m-0 text-[0.9rem] text-muted">{t.noNotebooks}</p>
          ) : (
            <>
              <LanguageField
                legend={t.languageOf(preview.value.merged)}
                value={mergedLanguage}
                onChange={setMergedLanguage}
                labels={t.languages}
                disabled={pending}
              />
              <LanguageField
                legend={t.languageOf(preview.value.kept)}
                value={keptLanguage}
                onChange={setKeptLanguage}
                labels={t.languages}
                disabled={pending}
              />
              <div className="flex flex-col gap-1">
                <p className="m-0 text-[0.95rem] text-foreground">
                  {t.previewIntro(preview.value.merged, preview.value.kept)}
                </p>
                <ul className="m-0 list-disc pl-5 text-[0.95rem] text-foreground">
                  {preview.value.notebooks.map((n) => (
                    <li key={n.notebook_id}>{t.previewRow(n.name, n.recipe_count)}</li>
                  ))}
                </ul>
              </div>
            </>
          )
        ) : null}
        {error ? (
          <p className="m-0 text-[0.9rem] text-muted" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </ActionDialog>
  );
}
