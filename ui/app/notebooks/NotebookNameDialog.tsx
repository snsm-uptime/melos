"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { GhostInput } from "@/components/soft-ledger/GhostInput";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import type { NotebookResponse, NotebookResult } from "@/lib/notebooksClient";

import styles from "./notebooks.module.scss";

type NotebookNameDialogProps = {
  title: string;
  confirmLabel: string;
  initialName?: string;
  /** Shown for a failure with no message of its own. */
  failedMessage: string;
  locale: Locale;
  /** Gets the trimmed name. Never called with an empty one. */
  submit: (name: string) => Promise<NotebookResult<NotebookResponse>>;
  onSaved: (notebook: NotebookResponse) => void;
  onClose: () => void;
  /** Where closing leads once the notebook is gone. */
  goneHref?: string;
  /** Where a person sent to choose an alias comes back to. */
  returnTo: string;
};

/**
 * The one place a notebook gets a name: creating one and renaming one (spec 059 research R9). Mount
 * it to open it. What the person typed stays through every failure (FR-018).
 */
export function NotebookNameDialog({
  title,
  confirmLabel,
  initialName = "",
  failedMessage,
  locale,
  submit,
  onSaved,
  onClose,
  goneHref = "/notebooks",
  returnTo,
}: NotebookNameDialogProps) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Set once what the dialog acts on is gone: there is nothing left to do but leave.
  const [gone, setGone] = useState<{ message: string; href: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // After the dialog's focus trap, which gives focus to Cancel when it opens.
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function save() {
    if (pending) return;
    const trimmed = name.trim();
    if (!trimmed) {
      setError(t.newNotebookNameRequired);
      return;
    }
    setPending(true);
    setError(null);
    const result = await submit(trimmed);
    setPending(false);
    if (result.ok) {
      onSaved(result.value);
      return;
    }
    switch (result.code) {
      case "invalid_notebook_name":
        setError(t.newNotebookNameRequired);
        break;
      case "notebook_not_found":
        setGone({ message: t.notebookGone, href: goneHref });
        break;
      case "kitchen_not_found":
        setGone({ message: t.kitchenGone, href: "/kitchens" });
        break;
      case "kitchen_archived":
        setError(t.notebookArchived);
        break;
      case "alias_required":
        router.replace(`/alias?returnTo=${encodeURIComponent(returnTo)}`);
        break;
      default:
        setError(failedMessage);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void save();
  }

  if (gone) {
    return (
      <ActionDialog
        open
        title={title}
        cancelLabel={t.snapshotClose}
        onOpenChange={() => router.replace(gone.href)}
      >
        <p className={styles.alert} role="alert">
          {gone.message}
        </p>
      </ActionDialog>
    );
  }

  return (
    <ActionDialog
      open
      title={title}
      confirmLabel={confirmLabel}
      cancelLabel={t.snapshotCancel}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      onConfirm={() => void save()}
      pending={pending}
    >
      <form onSubmit={onSubmit}>
        <GhostInput
          ref={inputRef}
          aria-label={t.newNotebookName}
          placeholder={t.newNotebookName}
          type="text"
          value={name}
          maxLength={200}
          autoComplete="off"
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
  );
}
