"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { GhostInput } from "@/components/soft-ledger/GhostInput";
import { AddItemCard } from "@/components/Card";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { createNotebook } from "@/lib/notebooksClient";

import styles from "./notebooks.module.scss";

/** The plus tile of the Notebook tab: name a notebook, then open it, empty (S-059). */
export function NewNotebookCard({ locale }: { locale: Locale }) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    if (pending) return;
    if (!name.trim()) {
      setError(t.newNotebookNameRequired);
      return;
    }
    setPending(true);
    setError(null);
    const result = await createNotebook(name.trim());
    setPending(false);
    if (result.ok) {
      router.push(`/notebooks/${encodeURIComponent(result.value.id)}`);
      return;
    }
    setError(result.code === "invalid_notebook_name" ? t.newNotebookNameRequired : t.newNotebookFailed);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void create();
  }

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setName("");
      setError(null);
    }
  }

  return (
    <>
      <AddItemCard label={t.newNotebook} onClick={() => setOpen(true)} className="h-full" />
      <ActionDialog
        open={open}
        title={t.newNotebook}
        confirmLabel={t.newNotebookCreate}
        cancelLabel={t.snapshotCancel}
        onOpenChange={onOpenChange}
        onConfirm={() => void create()}
        pending={pending}
      >
        <form onSubmit={onSubmit}>
          <GhostInput
            aria-label={t.newNotebookName}
            placeholder={t.newNotebookName}
            type="text"
            value={name}
            maxLength={200}
            autoComplete="off"
            autoFocus
            disabled={pending}
            onChange={(event) => setName(event.target.value)}
          />
        </form>
        {error ? (
          <p className={`${styles.alert} mt-2`} role="alert">
            {error}
          </p>
        ) : null}
      </ActionDialog>
    </>
  );
}
