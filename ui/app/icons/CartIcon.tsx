import type { SVGProps } from "react";

/** An empty shopping cart: opens the kitchen's cart (spec 022). Same cart as CartPlusIcon. */
export function CartIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 2.5h2.2l1.4 2.5L8 16" />
        <path d="M5.6 5h15.6l-2.5 9.6a1.8 1.8 0 0 1-1.7 1.4H8" />
        <circle cx="9" cy="20" r="1.6" />
        <circle cx="17" cy="20" r="1.6" />
      </g>
    </svg>
  );
}
