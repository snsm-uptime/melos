"use client";

import type { NameChange } from "@/lib/capture/nameChanges";
import type { Locale } from "@/lib/i18n/locale";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

type NameChangeNoticeProps = {
  change: NameChange;
  onUndo: (line: number) => void;
  locale?: Locale;
};

/**
 * The name change of one ingredient line (spec 018 FR-003, FR-004), shown as a row right above
 * that line's card so the member sees what changed where it changed. Undo applies to this line only.
 */
export function NameChangeNotice({ change, onUndo, locale }: NameChangeNoticeProps) {
  const t = useCaptureMessages(locale);
  return (
    <div
      role="status"
      data-name-change={change.line}
      className="flex items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-accent px-[var(--space-4)] py-[var(--space-2)] text-[0.85rem] text-accent"
    >
      <span>{t.changeItem(change.from, change.to)}</span>
      <button
        type="button"
        onClick={() => onUndo(change.line)}
        className="text-[0.85rem] text-accent underline underline-offset-2"
      >
        {t.undoChange}
      </button>
    </div>
  );
}
