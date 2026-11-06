import type { SVGProps } from "react";

/**
 * A magnifier whose solid lens has three bars cut through it (even-odd, so the background
 * shows). The admin dashboard entry in the side panel.
 */
export function AnalyticsIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        fillRule="evenodd"
        d="M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM6.6 9.6h1.5v3.9H6.6Zm2.65-3.1h1.5v7H9.25Zm2.65 1.9h1.5v5.1h-1.5Z"
      />
      <path d="M15 15l5.5 5.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
