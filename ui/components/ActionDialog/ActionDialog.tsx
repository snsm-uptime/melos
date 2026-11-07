"use client";

import { useId, useRef, type ReactNode } from "react";

import { CloseIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";

import { useFocusTrap } from "@/hooks/useFocusTrap";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";

export type ActionDialogProps = {
  /** Whether the dialog is open */
  open: boolean;
  /** Dialog title/heading */
  title: string;
  /** Main content of the dialog (accepts any ReactNode — text, chips, forms, etc.) */
  children: ReactNode;
  /** Label for the confirm action button. Omit both labels and onConfirm for a dialog without footer buttons. */
  confirmLabel?: string;
  /** Label for the cancel button. Alone (no confirmLabel), the footer is just this close button. */
  cancelLabel?: string;
  /** Callback when dialog should close */
  onOpenChange: (open: boolean) => void;
  /** Callback when user confirms */
  onConfirm?: () => void;
  /** Whether an async operation is pending (disables buttons, shows loading state) */
  pending?: boolean;
  /** Adds a ✕ at the end of the title row with this accessible name. */
  closeLabel?: string;
};

/**
 * Generic modal dialog for confirmations and actions with custom content.
 * Reusable for chip selection, confirmations, or any action-triggered dialog.
 *
 * Features:
 * - Controlled open state
 * - Backdrop click or Escape to cancel
 * - Focus trap and keyboard accessibility
 * - Pending/loading state support
 * - Flexible content area (accepts any ReactNode)
 */
export function ActionDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel,
  onOpenChange,
  onConfirm,
  pending = false,
  closeLabel,
}: ActionDialogProps) {
  // Unique, so a confirmation opened over another dialog names itself.
  const titleId = useId();
  // A dialog with neither label renders no footer (spec 016 contracts/capture-ui.md).
  const hasFooter = confirmLabel !== undefined || cancelLabel !== undefined;
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useFocusTrap({
    isActive: open,
    containerRef: panelRef,
    defaultFocusRef: cancelRef,
    onEscapePress: () => onOpenChange(false),
  });

  if (!open) return null;

  return (
    <div
      className="modal-scrim fixed inset-0 z-50 flex items-center justify-center bg-background/70 px-6"
      role="presentation"
      onClick={() => onOpenChange(false)}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-[28rem] rounded-md border border-border bg-surface p-5 shadow-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2">
          <h2 id={titleId} className="m-0 text-[1.05rem] font-[550] text-foreground">
            {title}
          </h2>
          {closeLabel ? (
            <IconButton
              variant="ghost"
              className="size-8"
              label={closeLabel}
              icon={<CloseIcon className="size-5" />}
              onClick={() => onOpenChange(false)}
            />
          ) : null}
        </div>
        <div className="mt-4">{children}</div>
        {hasFooter ? (
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <GhostButton
              ref={cancelRef}
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              {cancelLabel}
            </GhostButton>
            {confirmLabel !== undefined ? (
              <PrimaryButton onClick={onConfirm} disabled={pending} loading={pending}>
                {confirmLabel}
              </PrimaryButton>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
