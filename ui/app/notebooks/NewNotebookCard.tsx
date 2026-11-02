"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AddItemCard } from "@/components/Card";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { createKitchenNotebook, createNotebook } from "@/lib/notebooksClient";

import { NotebookNameDialog } from "./NotebookNameDialog";

/**
 * The plus tile: name a notebook, then open it, empty (S-059). A personal notebook on the Notebook
 * tab; with a `kitchenId`, a notebook of that kitchen on its notebooks list.
 */
export function NewNotebookCard({ locale, kitchenId }: { locale: Locale; kitchenId?: string }) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const listPath = kitchenId ? `/kitchens/${encodeURIComponent(kitchenId)}/notebooks` : "/notebooks";

  return (
    <>
      <AddItemCard label={t.newNotebook} onClick={() => setOpen(true)} className="h-full" />
      {open ? (
        <NotebookNameDialog
          title={t.newNotebook}
          confirmLabel={t.newNotebookCreate}
          failedMessage={t.newNotebookFailed}
          locale={locale}
          submit={(name) =>
            kitchenId ? createKitchenNotebook(kitchenId, name) : createNotebook(name)
          }
          onSaved={(notebook) => {
            const path = `/notebooks/${encodeURIComponent(notebook.id)}`;
            router.push(kitchenId ? `${path}?from=${encodeURIComponent(listPath)}` : path);
          }}
          onClose={() => setOpen(false)}
          returnTo={listPath}
        />
      ) : null}
    </>
  );
}
