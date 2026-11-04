import type { SVGProps } from "react";

/** A bookmark outline; pass `filled` for the solid version (the notebook's default marker). */
export function BookmarkIcon({
  className,
  filled = false,
  ...props
}: SVGProps<SVGSVGElement> & { filled?: boolean }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        d="M6 20V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v15l-6-3.5z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}
