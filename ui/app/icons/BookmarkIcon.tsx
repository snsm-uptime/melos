import type { SVGProps } from "react";

export function BookmarkIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        d="M6 20V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v15l-6-3.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}
