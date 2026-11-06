"use client";

import { useEffect, useState } from "react";

import { ArrowIcon, CloseIcon, PencilIcon, TrashIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import { DataTable, type TableSchema } from "@/components/DataTable";
import { IconButton } from "@/components/IconButton";
import {
  fetchCatalog,
  splitName,
  type CatalogIngredient,
  type MergeResult,
  type NotebookCatalog,
} from "@/lib/catalogClient";
import { catalogMessages, type CatalogMessages } from "@/lib/i18n/catalog";
import type { Locale } from "@/lib/i18n/locale";
import { tableMessages } from "@/lib/i18n/table";

import { DeleteNameDialog } from "./DeleteNameDialog";
import { MergeDialog } from "./MergeDialog";
import { PairSuggestions } from "./PairSuggestions";
import { RenameDialog } from "./RenameDialog";

const BUTTON =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-4 text-[0.9rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";
const CHIP =
  "inline-flex max-w-full items-center gap-1 rounded-[var(--radius-md)] border border-border bg-surface py-[0.1rem] pr-[0.1rem] pl-2 text-[0.9rem] text-foreground";

type State =
  | { status: "loading" }
  | { status: "ready"; catalog: NotebookCatalog }
  | { status: "error" };

type Open =
  | { kind: "none" }
  | { kind: "rename"; ingredient: CatalogIngredient }
  | { kind: "merge"; merged: string; kept?: string }
  | { kind: "delete"; ingredient: CatalogIngredient }
  | { kind: "split"; ingredient: CatalogIngredient; otherName: string };

function otherNames(item: CatalogIngredient, t: CatalogMessages): string[] {
  return [
    ...item.variants.map((v) => `${v.name} (${t.languageShort[v.language]})`),
    ...item.spellings.map((s) => `${s} (${t.spelling})`),
  ];
}

function catalogTable(
  t: CatalogMessages,
  canWrite: boolean,
  open: (next: Open) => void,
): TableSchema<CatalogIngredient> {
  const c = t.columns;
  return {
    search: true,
    rowKey: (row) => row.name,
    columns: [
      { key: "name", label: c.name, sort: "text", searchable: true },
      {
        key: "language",
        label: c.language,
        sort: "text",
        value: (row) => (row.language ? t.languages[row.language] : ""),
        cell: (row) => (row.language ? t.languages[row.language] : t.noLanguage),
      },
      {
        key: "other_names",
        label: c.otherNames,
        sort: false,
        searchable: true,
        wrap: true,
        searchValue: (row) => [...row.variants.map((v) => v.name), ...row.spellings],
        value: (row) => otherNames(row, t).join(", "),
        cell: (row) => (
          <ul className="m-0 flex list-none flex-wrap gap-1 p-0">
            {[...row.variants.map((v) => v.name), ...row.spellings].map((name, index) => (
              <li key={name} className={CHIP}>
                <span className="min-w-0 truncate">{otherNames(row, t)[index]}</span>
                {canWrite ? (
                  <IconButton
                    variant="ghost"
                    className="size-7"
                    label={t.split(name)}
                    icon={<CloseIcon className="size-4" />}
                    onClick={() => open({ kind: "split", ingredient: row, otherName: name })}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        ),
      },
      { key: "recipe_count", label: c.recipes, sort: "number" },
      ...(canWrite
        ? [
            {
              key: "actions",
              label: c.actions,
              sort: false as const,
              cell: (row: CatalogIngredient) => (
                <span className="flex gap-1">
                  <IconButton
                    variant="ghost"
                    className="size-9"
                    label={t.rename(row.name)}
                    icon={<PencilIcon className="size-5" />}
                    onClick={() => open({ kind: "rename", ingredient: row })}
                  />
                  <IconButton
                    variant="ghost"
                    className="size-9"
                    label={t.merge(row.name)}
                    icon={<ArrowIcon className="size-5" />}
                    onClick={() => open({ kind: "merge", merged: row.name })}
                  />
                  <IconButton
                    variant="ghost"
                    className="size-9"
                    label={t.remove(row.name)}
                    icon={<TrashIcon className="size-5" />}
                    onClick={() => open({ kind: "delete", ingredient: row })}
                  />
                </span>
              ),
            },
          ]
        : []),
    ],
  };
}

/**
 * One notebook's catalog on the Ingredients page (spec 043): each kept name with its language,
 * its other names and how many recipes use it. A person who can write to the notebook renames,
 * merges, deletes and splits names, and asks for suggested pairs; one who can only read sees
 * the names. Every result is announced in a polite live region (FR-017).
 */
export function CatalogManager({ locale, notebookId }: { locale: Locale; notebookId: string }) {
  const t = catalogMessages[locale];
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [dialog, setDialog] = useState<Open>({ kind: "none" });
  const [announcement, setAnnouncement] = useState("");
  const [splitting, setSplitting] = useState(false);

  useEffect(() => {
    let current = true;
    void fetchCatalog(notebookId).then((result) => {
      if (!current) return;
      setState(result.ok ? { status: "ready", catalog: result.value } : { status: "error" });
    });
    return () => {
      current = false;
    };
  }, [notebookId, attempt]);

  const reload = () => setAttempt((n) => n + 1);

  function finish(message: string) {
    setDialog({ kind: "none" });
    setAnnouncement(message);
    reload();
  }

  function changedElsewhere() {
    finish(t.reload);
  }

  function merged(result: MergeResult, mergedName: string, keptName: string) {
    const parts = [t.merged(mergedName, keptName, result.merged.length)];
    if (result.skipped.length > 0) parts.push(t.skipped(result.skipped.length));
    finish(parts.join(" "));
  }

  async function split() {
    if (dialog.kind !== "split" || splitting) return;
    setSplitting(true);
    const result = await splitName(notebookId, dialog.ingredient.name, dialog.otherName);
    setSplitting(false);
    if (result.ok) finish(t.splitDone(dialog.otherName));
    else if (result.code === "name_changed") changedElsewhere();
    else setAnnouncement(t.saveError);
  }

  const status = (
    <p className="sr-only" role="status" aria-live="polite">
      {announcement}
    </p>
  );

  if (state.status === "loading") {
    return (
      <>
        {status}
        <CauldronLoader label={t.loading} />
      </>
    );
  }
  if (state.status === "error") {
    return (
      <div className="flex flex-col items-start gap-2">
        {status}
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.loadError}
        </p>
        <button
          type="button"
          className={BUTTON}
          onClick={() => {
            setState({ status: "loading" });
            reload();
          }}
        >
          {t.retry}
        </button>
      </div>
    );
  }

  const { catalog } = state;
  const names = catalog.ingredients.map((i) => i.name);

  return (
    <section className="flex min-w-0 flex-col gap-4">
      {status}
      {announcement ? (
        <p className="m-0 text-[0.9rem] text-foreground" aria-hidden="true">
          {announcement}
        </p>
      ) : null}
      {catalog.can_write ? (
        <PairSuggestions
          t={t}
          notebookId={notebookId}
          onAccept={(pair) => setDialog({ kind: "merge", merged: pair.es, kept: pair.en })}
          onAnnounce={setAnnouncement}
        />
      ) : (
        <p className="m-0 text-[0.9rem] text-muted">{t.readOnly}</p>
      )}
      <DataTable
        schema={catalogTable(t, catalog.can_write, setDialog)}
        rows={catalog.ingredients}
        locale={locale}
        labels={tableMessages[locale]}
        empty={t.empty}
      />

      {dialog.kind === "merge" ? (
        <MergeDialog
          t={t}
          notebookId={notebookId}
          merged={dialog.merged}
          kept={dialog.kept}
          names={names}
          onClose={() => setDialog({ kind: "none" })}
          onDone={merged}
        />
      ) : null}
      {dialog.kind === "rename" ? (
        <RenameDialog
          t={t}
          notebookId={notebookId}
          ingredient={dialog.ingredient}
          onClose={() => setDialog({ kind: "none" })}
          onDone={finish}
          onChanged={changedElsewhere}
          onMergeInto={(existing) =>
            setDialog({ kind: "merge", merged: dialog.ingredient.name, kept: existing })
          }
        />
      ) : null}
      {dialog.kind === "delete" ? (
        <DeleteNameDialog
          t={t}
          notebookId={notebookId}
          ingredient={dialog.ingredient}
          onClose={() => setDialog({ kind: "none" })}
          onDone={finish}
          onChanged={changedElsewhere}
          onMergeInstead={() => setDialog({ kind: "merge", merged: dialog.ingredient.name })}
        />
      ) : null}
      <ActionDialog
        open={dialog.kind === "split"}
        title={dialog.kind === "split" ? t.splitTitle(dialog.otherName) : ""}
        confirmLabel={t.splitConfirm}
        cancelLabel={t.cancel}
        pending={splitting}
        onOpenChange={(next) => {
          if (!next) setDialog({ kind: "none" });
        }}
        onConfirm={() => void split()}
      >
        {dialog.kind === "split" ? t.splitBody(dialog.otherName, dialog.ingredient.name) : null}
      </ActionDialog>
    </section>
  );
}
