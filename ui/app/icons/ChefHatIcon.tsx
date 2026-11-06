import { useId, type SVGProps } from "react";

/**
 * A chef's hat: a three-lobed puff over a band with three upright slots cut through it (masked,
 * so the background shows), and a separate brim bar below. The Kitchens mark in the side panel.
 */
export function ChefHatIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  const maskId = `chef-hat-slots-${useId().replace(/:/g, "")}`;
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
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="24" height="24">
          <rect width="24" height="24" fill="white" />
          <rect x="8.6" y="11.5" width="1.6" height="6" fill="black" />
          <rect x="11.2" y="11.5" width="1.6" height="6" fill="black" />
          <rect x="13.8" y="11.5" width="1.6" height="6" fill="black" />
        </mask>
      </defs>
      <g mask={`url(#${maskId})`}>
        <circle cx="7" cy="9" r="3.5" />
        <circle cx="12" cy="7" r="4.5" />
        <circle cx="17" cy="9" r="3.5" />
        <rect x="5.5" y="9" width="13" height="8" />
      </g>
      <rect x="5.5" y="18.5" width="13" height="2.5" />
    </svg>
  );
}
