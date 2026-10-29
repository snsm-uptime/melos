import Link from "next/link";
import type { ReactNode } from "react";

/**
 * The icon actions at the end of a recipe page's chrome (detail, edit, draft). Shrinks before the
 * title does: next to a long title on a narrow screen the row is squeezed to one icon wide, so
 * the icons wrap into a column.
 *
 * Laid out in reverse: the first child (the primary action: edit, save) sits rightmost in a row
 * and on top in a column.
 */
export function HeaderActions({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-w-9 shrink-[1000] flex-row-reverse flex-wrap items-center justify-start gap-1 self-start">
      {children}
    </div>
  );
}

type Tone = "default" | "danger" | "accent";

const toneClass: Record<Tone, string> = {
  default: "text-muted hover:text-foreground",
  danger: "text-muted hover:text-owe",
  accent: "text-accent hover:text-foreground",
};

const baseClass =
  "m-0 inline-flex size-9 flex-shrink-0 cursor-pointer items-center justify-center rounded-[8px] border-0 bg-transparent p-1 leading-none no-underline transition-all duration-150 disabled:cursor-not-allowed disabled:text-muted disabled:opacity-50";

type HeaderActionProps = {
  /** The accessible name and tooltip; kept as screen-reader text too. */
  label: string;
  icon: ReactNode;
  tone?: Tone;
} & ({ href: string } | { onClick: () => void; disabled?: boolean });

/** One icon action in `HeaderActions`: a link when given `href`, otherwise a button. */
export function HeaderAction({
  label,
  icon,
  tone = "default",
  ...rest
}: HeaderActionProps) {
  const className = `${baseClass} ${toneClass[tone]}`;
  const content = (
    <>
      {icon}
      <span className="sr-only">{label}</span>
    </>
  );
  if ("href" in rest) {
    return (
      <Link
        href={rest.href}
        aria-label={label}
        title={label}
        className={className}
      >
        {content}
      </Link>
    );
  }
  return (
    <button
      type="button"
      onClick={rest.onClick}
      disabled={rest.disabled}
      aria-label={label}
      title={label}
      className={className}
    >
      {content}
    </button>
  );
}
