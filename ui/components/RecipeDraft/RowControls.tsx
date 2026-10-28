import { BackIcon, CloseIcon } from "@/app/icons";
import type { Locale } from "@/lib/i18n/locale";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

const iconButtonClassName =
  "flex h-7 w-7 items-center justify-center rounded-[0.5rem] text-muted hover:text-foreground disabled:opacity-40";

type RowControlsProps = {
  index: number;
  count: number;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
  className?: string;
  locale?: Locale;
};

/** The discard, move up and move down column shared by the ingredient and step cards. */
export function RowControls({
  index,
  count,
  onRemove,
  onMove,
  className,
  locale,
}: RowControlsProps) {
  const t = useCaptureMessages(locale);
  return (
    <div
      className={`flex shrink-0 flex-col border-l border-border items-center justify-between gap-2 self-stretch ${className ?? ""}`}
    >
      <button
        type="button"
        onClick={onRemove}
        aria-label={t.remove}
        title={t.remove}
        className={iconButtonClassName}
      >
        <CloseIcon className="h-4 w-4" />
      </button>
      <div className="flex flex-col items-center gap-1">
        <button
          type="button"
          onClick={() => onMove(-1)}
          disabled={index === 0}
          aria-label={t.moveUp}
          title={t.moveUp}
          className={iconButtonClassName}
        >
          <BackIcon className="size-4 rotate-90" />
        </button>
        <button
          type="button"
          onClick={() => onMove(1)}
          disabled={index === count - 1}
          aria-label={t.moveDown}
          title={t.moveDown}
          className={iconButtonClassName}
        >
          <BackIcon className="size-4 -rotate-90" />
        </button>
      </div>
    </div>
  );
}
