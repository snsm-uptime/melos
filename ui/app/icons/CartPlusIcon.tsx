import type { SVGProps } from "react";

type CartPlusIconProps = SVGProps<SVGSVGElement> & {
  /** The recipe is in the cart: the "+" turns 45° into an "×" (spec 022 FR-017c). */
  inCart?: boolean;
};

/** A shopping cart with a "+" in its basket, for adding a recipe to the cart. */
export function CartPlusIcon({ className, inCart = false, ...props }: CartPlusIconProps) {
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
        {/* Handle, then the basket: wide top, narrower bottom. */}
        <path d="M2 2.5h2.2l1.4 2.5L8 16" />
        <path d="M5.6 5h15.6l-2.5 9.6a1.8 1.8 0 0 1-1.7 1.4H8" />
        <circle cx="9" cy="20" r="1.6" />
        <circle cx="17" cy="20" r="1.6" />
        <g
          data-testid="cart-plus-mark"
          className="motion-reduce:transition-none"
          style={{
            transform: inCart ? "rotate(45deg)" : "none",
            transformBox: "fill-box",
            transformOrigin: "center",
            transition: "transform 150ms",
          }}
        >
          <path d="M13.2 7.6v5.4M10.5 10.3h5.4" />
        </g>
      </g>
    </svg>
  );
}
