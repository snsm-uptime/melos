import type { ReactNode } from "react";

/** The band's curved top and bottom, in a 1440 × 48 view box stretched to the page width. */
const TOP_CURVE = "M0,30 C240,6 480,2 720,18 C960,34 1200,40 1440,14";
const BOTTOM_CURVE = "M0,22 C300,46 600,44 860,26 C1100,10 1300,8 1440,30";

/**
 * A full-width surface-coloured band behind a run of landing sections, for depth (spec 075
 * FR-018). Its top and bottom edges are gentle curves rather than straight lines: each edge is an
 * SVG filled with `--surface` that reaches into the neighbouring section's padding, with a
 * `--border` line along the curve. Decorative only: hidden from screen readers, no pointer events,
 * still, and as wide as the page, so nothing scrolls sideways.
 */
export function SurfaceBand({ children }: { children: ReactNode }) {
  return (
    <div data-landing-band className="relative bg-surface">
      <Edge side="top" />
      {children}
      <Edge side="bottom" />
    </div>
  );
}

function Edge({ side }: { side: "top" | "bottom" }) {
  const curve = side === "top" ? TOP_CURVE : BOTTOM_CURVE;
  // The filled side: below the curve on top (it joins the band), above it at the bottom.
  const fill = side === "top" ? `${curve} L1440,48 L0,48 Z` : `${curve} L1440,0 L0,0 Z`;
  return (
    <svg
      data-landing-band-edge={side}
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 1440 48"
      preserveAspectRatio="none"
      // One pixel over the band, so no hairline shows at the seam.
      className={`pointer-events-none absolute inset-x-0 h-8 w-full md:h-12 ${
        side === "top" ? "bottom-[calc(100%-1px)]" : "top-[calc(100%-1px)]"
      }`}
    >
      <path d={fill} className="fill-surface" />
      <path d={curve} className="fill-none stroke-border" strokeWidth="1" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
