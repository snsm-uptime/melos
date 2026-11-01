"use client";

import { useRef, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { AddItemCard } from "@/components/Card";
import { CauldronLoader } from "@/components/CauldronLoader";
import { useToast } from "@/components/Toast";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  addNotebookSnapshot,
  fetchDefaultNotebook,
  fetchPersonalNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";

type Choice =
  | { status: "loading" }
  | { status: "ready"; notebooks: NotebookResponse[] }
  | { status: "error" };

type AddNotebookSnapshotProps = {
  kitchenId: string;
  locale: Locale;
  onAdded: () => void;
};

/**
 * Adds a personal notebook the person owns to the kitchen (spec 035). Choosing one adds it at
 * once; only a repeat asks first (FR-002a, FR-008a). Each notebook chosen in one opening keeps
 * one key, so a retry or a confirmation can't make a second snapshot (research R3).
 */
export function AddNotebookSnapshot({ kitchenId, locale, onAdded }: AddNotebookSnapshotProps) {
  const t = notebooksMessages[locale];
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<Choice>({ status: "loading" });
  const [pending, setPending] = useState(false);
  const [repeat, setRepeat] = useState<NotebookResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const keys = useRef(new Map<string, string>());
  // State updates after the render; this stops a second press in the same tick.
  const running = useRef(false);
  const opening = useRef(0);

  async function load(current: number) {
    setChoice({ status: "loading" });
    // The default is created on first use, so it must exist before the list (research R10).
    const made = await fetchDefaultNotebook();
    const list = made.ok ? await fetchPersonalNotebooks() : made;
    if (current !== opening.current) return;
    if (!list.ok) {
      setChoice({ status: "error" });
      return;
    }
    setChoice({
      status: "ready",
      notebooks: list.value.filter(
        (notebook) => notebook.kind === "personal" && notebook.access === "owner",
      ),
    });
  }

  function start() {
    opening.current += 1;
    keys.current.clear();
    setMessage(null);
    setRepeat(null);
    setOpen(true);
    void load(opening.current);
  }

  function close() {
    if (running.current) return;
    setOpen(false);
    setRepeat(null);
  }

  function failure(error: NotebookError): string {
    if (error.code === "kitchen_archived") return t.snapshotArchived;
    if (error.code === "notebook_not_found") return t.snapshotGone;
    if (error.code === "kitchen_not_found") return t.detailNotFound;
    return t.snapshotFailed;
  }

  async function add(notebook: NotebookResponse, confirmRepeat: boolean) {
    if (running.current) return;
    running.current = true;
    setPending(true);
    setMessage(null);
    const key = keys.current.get(notebook.id) ?? globalThis.crypto.randomUUID();
    keys.current.set(notebook.id, key);
    const result = await addNotebookSnapshot(kitchenId, {
      sourceNotebookId: notebook.id,
      snapshotKey: key,
      confirmRepeat,
    });
    running.current = false;
    setPending(false);
    if (result.ok) {
      setOpen(false);
      setRepeat(null);
      toast.show({ id: "notebook-snapshot", text: t.snapshotAdded(notebook.name) });
      onAdded();
      return;
    }
    if (result.code === "snapshot_exists") {
      setRepeat(notebook);
      return;
    }
    setRepeat(null);
    setMessage(failure(result));
  }

  return (
    <>
      <AddItemCard label={t.snapshotAction} onClick={start} className="h-full min-h-[2.75rem]" />
      <ActionDialog
        open={open}
        title={repeat ? t.snapshotRepeatTitle : t.snapshotChoose}
        cancelLabel={repeat ? t.snapshotCancel : t.snapshotClose}
        confirmLabel={repeat ? t.snapshotRepeatConfirm : undefined}
        onConfirm={repeat ? () => void add(repeat, true) : undefined}
        onOpenChange={(next) => {
          if (!next) close();
        }}
        pending={pending}
      >
        {repeat ? (
          <p className="m-0">{t.snapshotRepeatWarning(repeat.name)}</p>
        ) : (
          <div className="flex flex-col gap-[var(--space-3)]" aria-busy={pending}>
            <p className="m-0 text-[0.9rem] text-muted">{t.snapshotAudience}</p>
            {choice.status === "loading" ? <CauldronLoader label={t.snapshotLoading} /> : null}
            {choice.status === "error" ? (
              <p className="m-0 text-owe text-[0.9rem]" role="alert">
                {t.loadError}
              </p>
            ) : null}
            {choice.status === "ready" && choice.notebooks.length === 0 ? (
              <p className="m-0">{t.snapshotNoNotebooks}</p>
            ) : null}
            {choice.status === "ready" && choice.notebooks.length > 0 ? (
              <ul className="m-0 flex max-h-[40vh] list-none flex-col gap-[var(--space-2)] overflow-y-auto p-0">
                {choice.notebooks.map((notebook) => (
                  <li key={notebook.id}>
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void add(notebook, false)}
                      className="flex w-full cursor-pointer flex-col items-start gap-[var(--space-1)] rounded-[var(--radius-md)] border border-border bg-surface p-[var(--space-3)] text-left text-foreground enabled:hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-65"
                    >
                      <span className="break-words font-[550]">{notebook.name}</span>
                      <span className="text-[0.85rem] text-muted">
                        {t.recipeCount(notebook.recipe_count)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            {pending ? <p className="m-0 text-[0.9rem] text-muted">{t.snapshotAdding}</p> : null}
            {message ? (
              <p className="m-0 text-owe text-[0.9rem]" role="alert">
                {message}
              </p>
            ) : null}
          </div>
        )}
      </ActionDialog>
    </>
  );
}
