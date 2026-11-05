import type { SVGProps } from "react";

/** The recipe's shapes: a solid frame, thick at the top, around a sheet of three lines, the last one shorter. */
export function RecipeShape(props: SVGProps<SVGGElement>) {
  return (
    <g {...props}>
      {/* A solid frame, thicker at the top, around the empty sheet. */}
      <path
        d="M4.5 3h15v18h-15zM6.5 7.5v12h11v-12z"
        fill="currentColor"
        fillRule="evenodd"
      />
      <path d="M9 11h6M9 14h6M9 17h3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </g>
  );
}

/** A recipe. */
export function RecipeIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <RecipeShape />
    </svg>
  );
}
