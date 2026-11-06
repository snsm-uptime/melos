import type { SVGProps } from "react";

import { ICON_STROKE } from "./stroke";

/** Two chain links hooked into each other on a diagonal. */
export function LinkIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
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
        <path d="M10 13.5a4 4 0 0 0 6 .4l3-3a4.24 4.24 0 0 0-6-6l-1.7 1.7" />
        <path d="M14 10.5a4 4 0 0 0-6-.4l-3 3a4.24 4.24 0 0 0 6 6l1.7-1.7" />
      </g>
    </svg>
  );
}
