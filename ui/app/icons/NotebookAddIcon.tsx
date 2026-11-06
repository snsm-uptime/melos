import { useId, type SVGProps } from "react";

import { NotebookShape } from "./NotebookShape";

/** Add a notebook: the notebook with a solid circle over its lower-right corner and a plus cut through it. */
export function NotebookAddIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  // Each icon on a page needs its own mask id.
  const mask = useId();
  const plus = useId();
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <mask id={mask}>
        <rect width="24" height="24" fill="white" />
        {/* The notebook stops a gap short of the circle. */}
        <circle cx="18" cy="18" r="6.25" fill="black" />
      </mask>
      <mask id={plus}>
        <rect width="24" height="24" fill="white" />
        {/* The plus is cut out, so the background shows through it. */}
        <path d="M18 15.5v5M15.5 18h5" stroke="black" strokeWidth="1.6" strokeLinecap="round" />
      </mask>
      <NotebookShape mask={`url(#${mask})`} />
      <circle cx="18" cy="18" r="5.5" fill="currentColor" mask={`url(#${plus})`} />
    </svg>
  );
}
