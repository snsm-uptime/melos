import type { SVGProps } from "react";

/**
 * A filled "paste" icon: one rounded board with a tab on its top edge and a handle slot cut out
 * of it. The slot is drawn in the opposite direction, so the non-zero fill leaves it empty.
 */
export function ClipboardIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path d="M4 7.5Q4 4.5 7 4.5H17Q20 4.5 20 7.5V19Q20 22 17 22H7Q4 22 4 19Z" />
      <path d="M8 4.8Q8 2 10.8 2H13.2Q16 2 16 4.8Z" />
      <path d="M9 6.5A1 1 0 0 0 9 8.5H15A1 1 0 0 0 15 6.5H9Z" />
    </svg>
  );
}
