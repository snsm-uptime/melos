"use client";

import type { NameChange } from "@/lib/capture/nameChanges";
import { captureMessages } from "@/lib/i18n/capture";

type NameChangeNoticeProps = {
  change: NameChange;
  onUndo: (line: number) => void;
};

/**
 * The name change of one ingredient line (spec 018 FR-003, FR-004), shown as a row right above
 * that line's card so the member sees what changed where it changed. Undo applies to this line only.
 */
export function NameChangeNotice({ change, onUndo }: NameChangeNoticeProps) {
  return (
    <div
      role="status"
      data-name-change={change.line}
      className="flex items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-accent px-[var(--space-4)] py-[var(--space-2)] text-[0.85rem] text-accent"
    >
      <span>{captureMessages.changeItem(change.from, change.to)}</span>
      <button
        type="button"
        onClick={() => onUndo(change.line)}
        className="text-[0.85rem] text-accent underline underline-offset-2"
      >
        {captureMessages.undoChange}
      </button>
    </div>
  );
}
