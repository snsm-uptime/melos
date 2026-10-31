"use client";

import { useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { closeShoppingList } from "@/lib/shoppingListClient";

type DoneButtonProps = {
  kitchenId: string;
  locale: Locale;
  listId: string;
  /** The list has no items (FR-007). */
  empty: boolean;
  /** I am editing the cart, so what I see is not the saved list. */
  editing: boolean;
  onClosed: () => void;
};

/** Done (Listo): asks, then closes the active list for good (spec 025 FR-007). */
export function DoneButton({ kitchenId, locale, listId, empty, editing, onClosed }: DoneButtonProps) {
  const t = shoppingListMessages[locale];
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const hint = editing ? t.doneEditing : empty ? t.doneEmpty : null;

  async function close() {
    setPending(true);
    setError(false);
    const result = await closeShoppingList(kitchenId, listId);
    setPending(false);
    setOpen(false);
    // Someone else closed it first: the fresh read shows that.
    if (result.ok || result.code === "list_not_active") onClosed();
    else setError(true);
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={hint !== null}
        className="min-h-11 rounded-[var(--radius-md)] bg-accent px-5 text-[0.95rem] font-[600] text-background focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50"
        onClick={() => setOpen(true)}
      >
        {t.done}
      </button>
      {hint ? <p className="m-0 text-[0.85rem] text-muted">{hint}</p> : null}
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.changeError}
        </p>
      ) : null}
      <ActionDialog
        open={open}
        title={t.doneConfirmTitle}
        confirmLabel={t.done}
        cancelLabel={t.doneCancel}
        pending={pending}
        onOpenChange={setOpen}
        onConfirm={() => void close()}
      >
        {t.doneConfirmBody}
      </ActionDialog>
    </div>
  );
}
