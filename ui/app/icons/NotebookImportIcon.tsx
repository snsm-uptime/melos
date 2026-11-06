import { useId, type SVGProps } from "react";

import { NotebookShape } from "./NotebookShape";

/** Add a notebook from another one: the notebook with a solid circle over its lower-right corner and a download arrow cut through it. */
export function NotebookImportIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  // Each icon on a page needs its own mask id.
  const mask = useId();
  const arrow = useId();
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
      <mask id={arrow}>
        <rect width="24" height="24" fill="white" />
        {/* The arrow is cut out, so the background shows through it. */}
        <path
          d="M18 15.2v5M15.6 18.4l2.4 2.4 2.4-2.4"
          stroke="black"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </mask>
      <NotebookShape mask={`url(#${mask})`} />
      <circle cx="18" cy="18" r="5.5" fill="currentColor" mask={`url(#${arrow})`} />
    </svg>
  );
}
