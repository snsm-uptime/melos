"use client";

import type { NameChange } from "@/lib/capture/nameChanges";
import { captureMessages } from "@/lib/i18n/capture";

type NameChangeListProps = {
  changes: NameChange[];
  onUndo: (line: number) => void;
};

/**
 * The name changes the member sees before saving (spec 018 FR-003, FR-004). Renders nothing
 * when there are none. Each item can be undone on its own.
 */
export function NameChangeList({ changes, onUndo }: NameChangeListProps) {
  if (changes.length === 0) return null;

  return (
    <section aria-labelledby="name-changes-title" className="mb-4 flex flex-col gap-2">
      <h3 id="name-changes-title" className="m-0 text-[0.85rem] font-medium text-muted">
        {captureMessages.namesChanged}
      </h3>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {changes.map((change) => (
          <li
            key={change.line}
            className="flex items-center justify-between gap-3 rounded-[0.6rem] border border-border px-3 py-2 text-[0.9rem]"
          >
            <span>{captureMessages.changeItem(change.from, change.to)}</span>
            <button
              type="button"
              onClick={() => onUndo(change.line)}
              className="text-[0.85rem] text-accent underline-offset-2 hover:underline"
            >
              {captureMessages.undoChange}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
