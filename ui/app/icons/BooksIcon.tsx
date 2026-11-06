import type { SVGProps } from "react";

/**
 * Three book spines on a shelf: a banded one, a plain one, and a banded one leaning on it.
 * The Notebooks entry.
 */
export function BooksIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
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
      <g transform="translate(0.9 1.4)">
        <rect x="2.5" y="2.5" width="3.8" height="2.4" />
        <rect x="2.5" y="6.2" width="3.8" height="8.4" />
        <rect x="2.5" y="15.9" width="3.8" height="2.4" />
        <rect x="8" y="5.3" width="3.6" height="13" />
        <g transform="rotate(-16 15.8 10.4)">
          <rect x="13.9" y="2.5" width="3.8" height="2.4" />
          <rect x="13.9" y="6.2" width="3.8" height="8.4" />
          <rect x="13.9" y="15.9" width="3.8" height="2.4" />
        </g>
      </g>
    </svg>
  );
}
