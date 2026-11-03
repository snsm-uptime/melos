"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  deleteNotebook,
  fetchNotebook,
  fetchNotebookMembers,
  type NotebookResponse,
} from "@/lib/notebooksClient";
import { requestSidePanelRefresh } from "@/lib/sidePanelClient";

import styles from "../notebooks.module.scss";

type ReadState =
  | { status: "loading" }
  | { status: "ready"; notebook: NotebookResponse; members: number }
  | { status: "gone" }
  | { status: "error" };

/** Reads the real numbers, since the page's can be old (spec 059 research R7). */
async function readWhatIsLost(notebookId: string): Promise<ReadState> {
  const notebook = await fetchNotebook(notebookId);
  if (!notebook.ok) return notebook.status === 404 ? { status: "gone" } : { status: "error" };
  if (notebook.value.kind !== "personal") {
    return { status: "ready", notebook: notebook.value, members: 0 };
  }
  const members = await fetchNotebookMembers(notebookId);
  if (!members.ok) return members.status === 404 ? { status: "gone" } : { status: "error" };
  return {
    status: "ready",
    notebook: notebook.value,
    members: members.value.filter((member) => member.role !== "owner").length,
  };
}

/**
 * The one step before a notebook is deleted, stating what will be lost (spec 059 FR-007). Mount it
 * to open it.
 */
export function NotebookDeleteDialog({
  notebookId,
  notebookName,
  goneHref,
  locale,
  onClose,
}: {
  notebookId: string;
  notebookName: string;
  goneHref: string;
  locale: Locale;
  onClose: () => void;
}) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const [read, setRead] = useState<ReadState>({ status: "loading" });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    void readWhatIsLost(notebookId).then((next) => {
      if (current) setRead(next);
    });
    return () => {
      current = false;
    };
  }, [notebookId]);

  async function confirm() {
    if (pending) return;
    setPending(true);
    setError(null);
    const result = await deleteNotebook(notebookId);
    setPending(false);
    if (result.ok) {
      requestSidePanelRefresh();
      router.replace(goneHref);
    } else if (result.status === 404) {
      setRead({ status: "gone" });
    } else {
      setError(result.code === "kitchen_archived" ? t.notebookArchived : t.deleteFailed);
    }
  }

  const title = t.deleteTitle(read.status === "ready" ? read.notebook.name : notebookName);

  if (read.status === "gone") {
    return (
      <ActionDialog
        open
        title={title}
        cancelLabel={t.snapshotClose}
        onOpenChange={() => router.replace(goneHref)}
      >
        <p className={styles.alert} role="alert">
          {t.notebookGone}
        </p>
      </ActionDialog>
    );
  }

  const ready = read.status === "ready" ? read : null;
  return (
    <ActionDialog
      open
      title={title}
      confirmLabel={ready ? t.deleteConfirm : undefined}
      cancelLabel={t.snapshotCancel}
      onOpenChange={(next) => {
        if (!next && !pending) onClose();
      }}
      onConfirm={() => void confirm()}
      pending={pending}
    >
      {read.status === "loading" ? <CauldronLoader label={t.deleteLoading} /> : null}
      {read.status === "error" ? (
        <p className={styles.alert} role="alert">
          {t.deleteLoadError}
        </p>
      ) : null}
      {ready ? (
        <div className="flex flex-col gap-2">
          <p>{t.deleteRecipes(ready.notebook.recipe_count)}</p>
          {ready.members > 0 ? <p>{t.deletePeople(ready.members)}</p> : null}
          {ready.notebook.is_default ? <p>{t.deleteDefault}</p> : null}
        </div>
      ) : null}
      {error ? (
        <p className={`${styles.alert} mt-2`} role="alert">
          {error}
        </p>
      ) : null}
    </ActionDialog>
  );
}
