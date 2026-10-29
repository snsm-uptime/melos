"use client";

import { useToastState } from "./ToastProvider";

type ToastViewportProps = {
  className?: string;
  /** Localized label of a toast's close control. */
  dismissLabel?: string;
};

/**
 * Where toasts show: the host places it at the bottom of the screen body, above the tab bar
 * (spec 022 FR-017b, research R13). Bottom-up: the dock (the Cart page's editing bar), then the
 * toasts above it.
 */
export function ToastViewport({ className = "", dismissLabel = "Dismiss" }: ToastViewportProps) {
  const state = useToastState();
  if (!state) return null;
  const { toasts, dock, dismiss } = state;
  if (toasts.length === 0 && !dock) return null;
  return (
    <div
      data-toast-viewport=""
      aria-live="polite"
      className={`pointer-events-none flex flex-col gap-2 px-[var(--page-gutter,1rem)] pb-2 ${className}`}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`${BOX} pointer-events-auto`}
          title={toast.persistent ? undefined : dismissLabel}
          onClick={toast.persistent ? undefined : () => dismiss(toast.id)}
        >
          <span className="min-w-0 flex-1">{toast.text}</span>
          {toast.action ? (
            <button
              type="button"
              className={ACTION}
              onClick={(event) => {
                event.stopPropagation();
                toast.action?.onClick();
              }}
            >
              {toast.action.label}
            </button>
          ) : null}
        </div>
      ))}
      {dock ? <div className="pointer-events-auto mx-auto w-full max-w-[640px]">{dock}</div> : null}
    </div>
  );
}

const BOX =
  "mx-auto flex w-full max-w-[640px] flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-accent bg-surface px-3 py-2 text-[0.9rem] text-foreground shadow-sm";
const ACTION =
  "rounded-[var(--radius-md)] border border-border bg-background px-3 py-1 text-[0.85rem] text-foreground hover:border-accent";
