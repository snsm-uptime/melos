import type { SVGProps } from "react";

/** A wok on its ring with a pair of chopsticks resting in it: the kitchen-notebooks tab. */
export function ChopsticksWokIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M7.5 2.5L11.5 10.5M10.5 2.5L14.5 10.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M3 11h18c0 4.4-3.6 8-9 8s-9-3.6-9-8z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M21 13.5h2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
