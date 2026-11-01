import { describe, expect, it } from "vitest";

import {
  BUBBLES,
  BUBBLE_TRAVEL,
  CAULDRON_SHAPES,
  PIVOT,
  VIEWBOX,
  boundsAt,
} from "./geometry";
import { CAULDRON_TILT_MAX } from "./tilt";

function inside(b: { minX: number; minY: number; maxX: number; maxY: number }) {
  expect(b.minX).toBeGreaterThanOrEqual(0);
  expect(b.minY).toBeGreaterThanOrEqual(0);
  expect(b.maxX).toBeLessThanOrEqual(VIEWBOX.width);
  expect(b.maxY).toBeLessThanOrEqual(VIEWBOX.height);
}

describe("cauldron geometry", () => {
  it("has the pivot inside the box, near the base of the feet", () => {
    expect(PIVOT.x).toBeGreaterThan(0);
    expect(PIVOT.x).toBeLessThan(VIEWBOX.width);
    expect(PIVOT.y).toBeGreaterThan(0);
    expect(PIVOT.y).toBeLessThan(VIEWBOX.height);
    const feet = [...CAULDRON_SHAPES.footLeft.points, ...CAULDRON_SHAPES.footRight.points];
    expect(Math.max(...feet.map(([, y]) => y))).toBe(PIVOT.y);
  });

  it("draws the parts the spec lists", () => {
    expect(Object.keys(CAULDRON_SHAPES).sort()).toEqual(
      ["body", "drip", "footLeft", "footRight", "handleLeft", "handleRight", "rim"].sort(),
    );
    for (const shape of Object.values(CAULDRON_SHAPES)) {
      expect(shape.d.startsWith("M")).toBe(true);
      expect(shape.points.length).toBeGreaterThan(2);
    }
  });

  it("fits the box upright", () => {
    inside(boundsAt(0));
  });

  it("fits the box at the largest tilt, both ways", () => {
    inside(boundsAt(CAULDRON_TILT_MAX));
    inside(boundsAt(-CAULDRON_TILT_MAX));
  });

  it("fits the box at every angle up to the largest tilt", () => {
    for (let angle = -CAULDRON_TILT_MAX; angle <= CAULDRON_TILT_MAX; angle += 1) {
      inside(boundsAt(angle));
    }
  });

  it("has at least two bubbles of different sizes", () => {
    expect(BUBBLES.length).toBeGreaterThanOrEqual(2);
    expect(new Set(BUBBLES.map((bubble) => bubble.r)).size).toBeGreaterThanOrEqual(2);
  });

  it("keeps every bubble inside the box over its whole rise", () => {
    for (const { cx, cy, r } of BUBBLES) {
      for (const offset of [BUBBLE_TRAVEL.from, BUBBLE_TRAVEL.to]) {
        expect(cx - r).toBeGreaterThanOrEqual(0);
        expect(cx + r).toBeLessThanOrEqual(VIEWBOX.width);
        expect(cy + offset - r).toBeGreaterThanOrEqual(0);
        expect(cy + offset + r).toBeLessThanOrEqual(VIEWBOX.height);
      }
    }
  });

  it("starts every bubble behind the rim and ends clear above it", () => {
    const rimTop = Math.min(...CAULDRON_SHAPES.rim.points.map(([, y]) => y));
    for (const { cy, r } of BUBBLES) {
      expect(cy + BUBBLE_TRAVEL.from).toBeGreaterThan(rimTop);
      expect(cy + BUBBLE_TRAVEL.to + r).toBeLessThan(rimTop);
    }
  });
});
