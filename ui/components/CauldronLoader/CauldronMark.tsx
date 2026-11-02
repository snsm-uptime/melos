import {
  BUBBLES,
  CAULDRON_SHAPES,
  MARK_INK_STRENGTH,
  MARK_POT_STRENGTH,
  MARK_VIEWBOX_ATTR,
} from "./geometry";

/* Part way to the page background: lighter on a light theme, darker on a dark one. */
const POT_FILL = `color-mix(in srgb, var(--foreground) ${MARK_POT_STRENGTH}%, var(--background))`;
const INK_FILL = `color-mix(in srgb, var(--secondary) ${MARK_INK_STRENGTH}%, var(--background))`;

const POT_PARTS = [
  CAULDRON_SHAPES.body,
  CAULDRON_SHAPES.handleLeft,
  CAULDRON_SHAPES.handleRight,
  CAULDRON_SHAPES.footLeft,
  CAULDRON_SHAPES.footRight,
];

/**
 * The cauldron as a logo: still and decorative, cropped square like the browser icon. Colours
 * follow the theme. For a wait, use CauldronLoader, which moves and is announced.
 */
export function CauldronMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox={MARK_VIEWBOX_ATTR} aria-hidden="true" focusable="false">
      <g fill={POT_FILL}>
        {POT_PARTS.map(({ d }) => (
          <path key={d} d={d} />
        ))}
      </g>
      <g fill={INK_FILL}>
        <path d={CAULDRON_SHAPES.rim.d} />
        <path d={CAULDRON_SHAPES.drip.d} />
        {BUBBLES.map(({ cx, cy, r }) => (
          <circle key={cx} cx={cx} cy={cy} r={r} />
        ))}
      </g>
    </svg>
  );
}
