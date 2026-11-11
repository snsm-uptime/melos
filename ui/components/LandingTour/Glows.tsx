/** Where a glow is drawn (FR-018): the surface band, or behind the closing call to action. */
export type GlowPlace = "band" | "closing";

type Glow = { colour: "accent" | "primary"; cx: number; cy: number; rx: number; ry: number };

const COLOUR = {
  accent: { stop: "var(--accent-fill)", strength: "var(--glow-accent-strength)" },
  primary: { stop: "var(--primary)", strength: "var(--glow-primary-strength)" },
} as const;

/** In the 1440 × 800 view box, stretched to the place's box. */
const GLOWS: Record<GlowPlace, Glow[]> = {
  band: [
    { colour: "accent", cx: 180, cy: 140, rx: 620, ry: 360 },
    { colour: "primary", cx: 1280, cy: 660, rx: 640, ry: 380 },
  ],
  closing: [
    { colour: "accent", cx: 560, cy: 440, rx: 520, ry: 380 },
    { colour: "primary", cx: 900, cy: 380, rx: 520, ry: 380 },
  ],
};

/**
 * Soft orange and purple glows behind a landing place, for depth (spec 075 FR-018). Vectors, like
 * the hero's waves: radial gradients from the token colour at its theme strength to nothing, so the
 * strongest point is known and tested (glowContrast.test.ts, SC-007). Still on purpose: the demos
 * are the page's only motion. The parent must be `relative isolate overflow-hidden`.
 */
export function Glows({ place }: { place: GlowPlace }) {
  return (
    <svg
      data-landing-glows
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 1440 800"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 -z-10 h-full w-full"
    >
      <defs>
        {(["accent", "primary"] as const).map((colour) => (
          <radialGradient key={colour} id={`glow-${place}-${colour}`}>
            <stop offset="0" style={{ stopColor: COLOUR[colour].stop, stopOpacity: COLOUR[colour].strength }} />
            <stop offset="1" style={{ stopColor: COLOUR[colour].stop, stopOpacity: 0 }} />
          </radialGradient>
        ))}
      </defs>
      {GLOWS[place].map((glow) => (
        <ellipse
          key={`${glow.colour}-${glow.cx}`}
          cx={glow.cx}
          cy={glow.cy}
          rx={glow.rx}
          ry={glow.ry}
          fill={`url(#glow-${place}-${glow.colour})`}
        />
      ))}
    </svg>
  );
}
