import type { SVGProps } from "react";

import { ICON_STROKE } from "./stroke";

/** A page with a folded corner in front of the edge of the page it was copied from. */
export function CopyIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <g
        stroke="currentColor"
        strokeWidth={ICON_STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M11.5 2.5H16l3.5 3.5v9.5a1.5 1.5 0 0 1-1.5 1.5h-6.5a1.5 1.5 0 0 1-1.5-1.5v-11.5a1.5 1.5 0 0 1 1.5-1.5Z" />
        <path d="M6.5 7H6a1.5 1.5 0 0 0-1.5 1.5v11A1.5 1.5 0 0 0 6 21h7" />
      </g>
    </svg>
  );
}
