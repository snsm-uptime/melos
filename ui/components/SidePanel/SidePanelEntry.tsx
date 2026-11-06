"use client";

import Link from "next/link";
import type { MouseEvent, ReactNode } from "react";

import { Tooltip } from "@/components/Tooltip";
import { panelEntryClass, usePanelLayout } from "./panelLayout";

/** One panel row: icon and label, as a link with `href` and otherwise a button. */
export function SidePanelEntry({
  label,
  icon,
  href,
  current = false,
  atTarget = false,
  disabled = false,
  expanded,
  id,
  controls,
  reserveTrailing = false,
  onClick,
}: {
  label: string;
  icon: ReactNode;
  href?: string;
  current?: boolean;
  /** Already on the page `href` opens, so the row shows no pointer. */
  atTarget?: boolean;
  disabled?: boolean;
  expanded?: boolean;
  id?: string;
  controls?: string;
  /** Keeps the label clear of a control floating at the end of the row. */
  reserveTrailing?: boolean;
  onClick?: (event: MouseEvent) => void;
}) {
  const { labelClass } = usePanelLayout();
  const content = (
    <>
      {icon}
      <span className={`${labelClass} ${reserveTrailing ? "pr-10" : ""}`}>{label}</span>
    </>
  );
  return (
    <Tooltip label={label}>
      {href ? (
        <Link
          href={href}
          aria-label={label}
          aria-current={current ? "page" : undefined}
          className={`${panelEntryClass} ${current ? "!text-foreground font-semibold" : ""} ${atTarget ? "!cursor-default" : ""}`}
          onClick={(event) => {
            // Already on this page: no navigation, so the page and panel stay as they are.
            if (atTarget) event.preventDefault();
            onClick?.(event);
          }}
        >
          {content}
        </Link>
      ) : (
        <button
          type="button"
          id={id}
          aria-label={label}
          aria-expanded={expanded}
          aria-controls={controls}
          className={panelEntryClass}
          disabled={disabled}
          onClick={onClick}
        >
          {content}
        </button>
      )}
    </Tooltip>
  );
}
