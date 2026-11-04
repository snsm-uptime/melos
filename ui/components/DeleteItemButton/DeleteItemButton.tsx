"use client";

import { useState, type ReactNode } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { IconButton } from "@/components/IconButton";
import { TrashIcon } from "@/app/icons";

export type DeleteItemButtonProps = {
  /** Accessible name and tooltip of the trash button, e.g. "Delete recipe Sopa". */
  label: string;
  /** Heading of the confirmation dialog, e.g. "Delete “Sopa”?". */
  dialogTitle: string;
  /** What is lost, shown in the dialog before the person confirms. */
  message: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  /** Shown in the dialog when the delete fails. */
  errorMessage: string;
  /**
   * Performs the delete. Resolve true when the item is gone, false when it was not. The dialog
   * closes on true; the caller usually removes the row, which unmounts this button.
   */
  onDelete: () => Promise<boolean>;
  disabled?: boolean;
};

/**
 * The standard delete control for a list row: a trash button that opens a confirmation dialog
 * before anything is removed. Every delete in the app uses it, so the confirmation looks and
 * behaves the same everywhere. Pass the text in the reader's language.
 */
export function DeleteItemButton({
  label,
  dialogTitle,
  message,
  confirmLabel,
  cancelLabel,
  errorMessage,
  onDelete,
  disabled = false,
}: DeleteItemButtonProps) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  function close() {
    if (pending) return;
    setOpen(false);
    setFailed(false);
  }

  async function confirm() {
    if (pending) return;
    setPending(true);
    setFailed(false);
    const deleted = await onDelete();
    setPending(false);
    if (deleted) {
      setOpen(false);
    } else {
      setFailed(true);
    }
  }

  return (
    <>
      <IconButton
        icon={<TrashIcon className="size-5" />}
        label={label}
        tone="danger"
        disabled={disabled}
        onClick={() => setOpen(true)}
      />
      <ActionDialog
        open={open}
        title={dialogTitle}
        confirmLabel={confirmLabel}
        cancelLabel={cancelLabel}
        onOpenChange={(next) => {
          if (!next) close();
        }}
        onConfirm={() => void confirm()}
        pending={pending}
      >
        <div className="flex flex-col gap-2">
          <div>{message}</div>
          {failed ? (
            <p role="alert" className="m-0 text-[0.9rem] text-error">
              {errorMessage}
            </p>
          ) : null}
        </div>
      </ActionDialog>
    </>
  );
}
