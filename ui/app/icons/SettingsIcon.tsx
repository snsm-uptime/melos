import type { SVGProps } from "react";

export function SettingsIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        d="M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
