import type { SVGProps } from "react";

/** A solid map pin with a round hole (even-odd, so the background shows). The Location button. */
export function LocationIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
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
        d="M12 2.5a7.5 7.5 0 0 0-7.5 7.5c0 2.6 1.4 5.3 3.4 7.6L12 22l4.1-4.4c2-2.3 3.4-5 3.4-7.6A7.5 7.5 0 0 0 12 2.5Zm0 4.9a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2Z"
      />
    </svg>
  );
}
