import type { SVGProps } from "react";

import { ICON_STROKE } from "./stroke";

/** A clock circled by a counterclockwise arrow: opens the kitchen's past lists (spec 025). */
export function HistoryIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <g
        stroke="currentColor"
        strokeWidth={ICON_STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 4v5h5" />
        <path d="M4 9a9.5 9.5 0 1 1 2.28 9.72" />
        <path d="M13 7v5.5l3.5 3.5" />
      </g>
    </svg>
  );
}
