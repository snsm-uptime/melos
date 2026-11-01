import { describe, expect, it } from "vitest";

import {
  CAULDRON_TILT_DEFAULT,
  CAULDRON_TILT_IN_BUTTON,
  CAULDRON_TILT_MAX,
  resolveTilt,
} from "./tilt";

describe("resolveTilt", () => {
  const fallback = 20;

  it("exports the two defaults inside the allowed range, and the limit", () => {
    for (const value of [CAULDRON_TILT_DEFAULT, CAULDRON_TILT_IN_BUTTON]) {
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(CAULDRON_TILT_MAX);
    }
    expect(CAULDRON_TILT_MAX).toBe(45);
  });

  it("keeps a finite number from 0 to 45", () => {
    expect(resolveTilt(10, fallback)).toBe(10);
    expect(resolveTilt(12.5, fallback)).toBe(12.5);
    expect(resolveTilt(45, fallback)).toBe(45);
  });

  it("limits a number above 45 to 45", () => {
    expect(resolveTilt(46, fallback)).toBe(45);
    expect(resolveTilt(90, fallback)).toBe(45);
    expect(resolveTilt(Number.MAX_VALUE, fallback)).toBe(45);
  });

  it("uses the size of a negative number, then the limit", () => {
    expect(resolveTilt(-10, fallback)).toBe(10);
    expect(resolveTilt(-90, fallback)).toBe(45);
  });

  it("keeps 0 as 0, not the fallback", () => {
    expect(resolveTilt(0, fallback)).toBe(0);
    expect(Object.is(resolveTilt(-0, fallback), 0)).toBe(true);
  });

  it("takes the fallback for anything that is not a finite number", () => {
    expect(resolveTilt(Number.NaN, fallback)).toBe(fallback);
    expect(resolveTilt(Number.POSITIVE_INFINITY, fallback)).toBe(fallback);
    expect(resolveTilt(Number.NEGATIVE_INFINITY, fallback)).toBe(fallback);
    expect(resolveTilt(undefined, fallback)).toBe(fallback);
    expect(resolveTilt(null, fallback)).toBe(fallback);
    expect(resolveTilt("12", fallback)).toBe(fallback);
    expect(resolveTilt("x", fallback)).toBe(fallback);
  });

  it("returns whichever fallback it is given", () => {
    expect(resolveTilt(undefined, CAULDRON_TILT_IN_BUTTON)).toBe(CAULDRON_TILT_IN_BUTTON);
  });
});
