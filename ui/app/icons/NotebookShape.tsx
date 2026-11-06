import { useId, type SVGProps } from "react";

/**
 * The notebook base for the notebook actions: rings on the left edge, a spine gap, a rounded
 * body. Coordinates follow the reference drawing scaled into the 24 grid. `mask` cuts the
 * corner where the action badge sits, as `RecipeShape` does for the recipe icons.
 */
export function NotebookShape({
  mask,
  ...props
}: SVGProps<SVGGElement> & { mask?: string }) {
  // Each icon on a page needs its own mask id.
  const spine = useId();
  return (
    <g fill="currentColor" mask={mask} {...props}>
      <mask id={spine}>
        <rect width="24" height="24" fill="white" />
        <rect x="10" y="0" width="1.2" height="24" fill="black" />
      </mask>
      <g mask={`url(#${spine})`}>
        <rect x="6" y="4.3" width="14.2" height="14.9" rx="2.2" />
      </g>
      <rect x="3.8" y="7.05" width="2.6" height="1.3" rx="0.65" />
      <rect x="3.8" y="11.35" width="2.6" height="1.3" rx="0.65" />
      <rect x="3.8" y="15.15" width="2.6" height="1.3" rx="0.65" />
    </g>
  );
}
