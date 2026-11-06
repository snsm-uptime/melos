import { useId, type SVGProps } from "react";

import { ICON_STROKE } from "./stroke";

/**
 * A shopping basket: peaked handle and rim as lines, a solid body with three upright slots cut
 * through it (masked, so the background shows). The Ingredients entry.
 */
export function BasketIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  const maskId = `basket-slots-${useId().replace(/:/g, "")}`;
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
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="24" height="24">
          <rect width="24" height="24" fill="white" />
          <path
            d="M9 13.3v3.4M12 13.3v3.4M15 13.3v3.4"
            stroke="black"
            strokeWidth={ICON_STROKE}
            strokeLinecap="round"
          />
        </mask>
      </defs>
      <g
        stroke="currentColor"
        strokeWidth={ICON_STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M7.5 9.5 12 4.5l4.5 5" />
        <path d="M3 9.5h18" />
        <path
          d="M4.5 9.5 6.3 19a1.2 1.2 0 0 0 1.2 1h9a1.2 1.2 0 0 0 1.2-1l1.8-9.5Z"
          fill="currentColor"
          mask={`url(#${maskId})`}
        />
      </g>
    </svg>
  );
}
