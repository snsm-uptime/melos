import type { SVGProps } from "react";

import { NotebookShape } from "./NotebookShape";

/** The notebook base alone: the shape the notebook actions add a badge to, with no badge. */
export function NotebookBaseIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <NotebookShape />
    </svg>
  );
}
