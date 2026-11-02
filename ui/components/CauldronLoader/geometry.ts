/**
 * Cauldron drawing (spec 065 FR-001, FR-013, research R2/R3). Redrawn by eye from the supplied
 * picture: a dark pot with a rim, two side handles, two feet and a drip running down from the rim.
 *
 * Shapes are written relative to the pivot (the base of the feet) and stored in box coordinates.
 * Only M, L, C and Z are used, so every number pair in a path is a point of its convex hull and
 * `points` bounds the drawn shape even where a curve bulges.
 */

export type Point = readonly [number, number];
export type Shape = { d: string; points: readonly Point[] };

export const VIEWBOX = { width: 140, height: 118 } as const;
export const VIEWBOX_ATTR = `0 0 ${VIEWBOX.width} ${VIEWBOX.height}`;
export const ASPECT_RATIO = `${VIEWBOX.width} / ${VIEWBOX.height}`;

/** A square crop around the still drawing, for the logo and the browser icon (app/icon.svg). */
export const MARK_VIEWBOX_ATTR = "26 13 88 88";

/**
 * How much of its theme colour each part of the logo keeps, in percent; the rest is the page
 * background, so a lower number is softer. app/icon.svg can't read the theme and holds the
 * resulting colours: after changing these, update it and favicon.ico (app/icon.test.ts fails
 * until the colours match, and prints the values).
 */
export const MARK_POT_STRENGTH = 85;
export const MARK_INK_STRENGTH = 75;

/** The cauldron rocks about this point: the base of the feet, horizontally centred. */
export const PIVOT = { x: 70, y: 88 } as const;

type Step =
  | readonly ["M" | "L", number, number]
  | readonly ["C", number, number, number, number, number, number]
  | readonly ["Z"];

/** Builds a shape from steps given relative to the pivot. */
function shape(steps: readonly Step[]): Shape {
  const points: Point[] = [];
  const d = steps
    .map((step) => {
      if (step[0] === "Z") return "Z";
      const [command, ...numbers] = step;
      const parts: string[] = [];
      for (let i = 0; i < numbers.length; i += 2) {
        const x = PIVOT.x + numbers[i];
        const y = PIVOT.y + numbers[i + 1];
        points.push([x, y]);
        parts.push(`${x} ${y}`);
      }
      return `${command}${parts.join(" ")}`;
    })
    .join("");
  return { d, points };
}

/** Left-right mirror of steps about the pivot, for the paired parts. */
function mirror(steps: readonly Step[]): Step[] {
  return steps.map((step): Step => {
    if (step[0] === "Z") return step;
    if (step[0] === "C") {
      const [, x1, y1, x2, y2, x, y] = step;
      return ["C", -x1, y1, -x2, y2, -x, y];
    }
    return [step[0], -step[1], step[2]];
  });
}

/** Quarter-circle control distance for a cubic curve: 4/3 * (sqrt 2 - 1). */
const ARC = 0.5523;

/**
 * A handle drawn as a half ring: a semicircle of outer radius `outer` and inner radius `inner`
 * centred on the pot's side, opening towards the pot. Left side; `mirror` makes the right one.
 */
function halfRing(cx: number, cy: number, outer: number, inner: number): Step[] {
  const o = outer * ARC;
  const i = inner * ARC;
  return [
    ["M", cx, cy - outer],
    ["C", cx - o, cy - outer, cx - outer, cy - o, cx - outer, cy],
    ["C", cx - outer, cy + o, cx - o, cy + outer, cx, cy + outer],
    ["L", cx, cy + inner],
    ["C", cx - i, cy + inner, cx - inner, cy + i, cx - inner, cy],
    ["C", cx - inner, cy - i, cx - i, cy - inner, cx, cy - inner],
    ["Z"],
  ];
}

const HANDLE: Step[] = halfRing(-29, -26, 12, 7);

const FOOT: Step[] = [["M", -19, -8], ["L", -10, -8], ["L", -12, 0], ["L", -17, 0], ["Z"]];

export const CAULDRON_SHAPES = {
  body: shape([
    ["M", -26, -42],
    ["C", -36, -36, -34, -10, -20, -7],
    ["L", 20, -7],
    ["C", 34, -10, 36, -36, 26, -42],
    ["Z"],
  ]),
  rim: shape([["M", -31, -48], ["L", 31, -48], ["L", 31, -40], ["L", -31, -40], ["Z"]]),
  handleLeft: shape(HANDLE),
  handleRight: shape(mirror(HANDLE)),
  footLeft: shape(FOOT),
  footRight: shape(mirror(FOOT)),
  drip: shape([
    ["M", 8, -40],
    ["L", 16, -40],
    ["L", 16, -26],
    ["C", 16, -20, 8, -20, 8, -26],
    ["Z"],
  ]),
} as const satisfies Record<string, Shape>;

/**
 * Bubbles in their still pose: visible, just above the mouth. The rise animation moves each one
 * from `BUBBLE_TRAVEL.from` (behind the rim) to `BUBBLE_TRAVEL.to` (above it) in box units; the
 * stylesheet repeats these two numbers.
 */
export const BUBBLES = [
  { cx: PIVOT.x - 14, cy: PIVOT.y - 58, r: 5 },
  { cx: PIVOT.x + 3, cy: PIVOT.y - 60, r: 3 },
  { cx: PIVOT.x + 15, cy: PIVOT.y - 57, r: 4 },
] as const;

export const BUBBLE_TRAVEL = { from: 14, to: -22 } as const;

/** Where the cauldron's outline lies after rocking `angleDeg` about the pivot. */
export function boundsAt(angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const { points } of Object.values(CAULDRON_SHAPES)) {
    for (const [x, y] of points) {
      const dx = x - PIVOT.x;
      const dy = y - PIVOT.y;
      const rx = PIVOT.x + dx * cos - dy * sin;
      const ry = PIVOT.y + dx * sin + dy * cos;
      minX = Math.min(minX, rx);
      minY = Math.min(minY, ry);
      maxX = Math.max(maxX, rx);
      maxY = Math.max(maxY, ry);
    }
  }
  return { minX, minY, maxX, maxY };
}
