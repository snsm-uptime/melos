"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AddItemCard } from "@/components/Card";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { createKitchenNotebook, createNotebook } from "@/lib/notebooksClient";

import { NotebookNameDialog } from "./NotebookNameDialog";

/**
 * Name a notebook, then open it, empty (S-059). A personal notebook on the Notebook tab; with a
 * `kitchenId`, a notebook of that kitchen on its notebooks list. Mounting it opens it.
 */
export function NewNotebookDialog({
  locale,
  kitchenId,
  onClose,
}: {
  locale: Locale;
  kitchenId?: string;
  onClose: () => void;
}) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const listPath = kitchenId
    ? `/kitchens/${encodeURIComponent(kitchenId)}/notebooks`
    : "/notebooks";
  return (
    <NotebookNameDialog
      title={t.newNotebook}
      confirmLabel={t.newNotebookCreate}
      failedMessage={t.newNotebookFailed}
      locale={locale}
      submit={(name) =>
        kitchenId
          ? createKitchenNotebook(kitchenId, name)
          : createNotebook(name)
      }
      onSaved={(notebook) => {
        const path = `/notebooks/${encodeURIComponent(notebook.id)}`;
        router.push(
          kitchenId ? `${path}?from=${encodeURIComponent(listPath)}` : path,
        );
      }}
      onClose={onClose}
      returnTo={listPath}
    />
  );
}

/** The plus tile on the notebooks grid: opens `NewNotebookDialog`. */
export function NewNotebookCard({
  locale,
  kitchenId,
}: {
  locale: Locale;
  kitchenId?: string;
}) {
  const t = notebooksMessages[locale];
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* As tall as a notebook card, so the plus tile keeps its shape on a one-column phone grid. */}
      <AddItemCard
        label={t.newNotebook}
        onClick={() => setOpen(true)}
        className="h-full min-h-[5.8rem]"
      />
      {open ? (
        <NewNotebookDialog
          locale={locale}
          kitchenId={kitchenId}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}
