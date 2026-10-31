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
          className={`${panelEntryClass} ${current ? "!text-foreground font-semibold" : ""}`}
          onClick={onClick}
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
