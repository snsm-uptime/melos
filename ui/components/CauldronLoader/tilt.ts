/** Cauldron tilt angles in degrees each way (spec 065 FR-005, FR-006, data-model.md). */

export const CAULDRON_TILT_DEFAULT = 8;
export const CAULDRON_TILT_IN_BUTTON = 15;
export const CAULDRON_TILT_MAX = 45;

/**
 * The angle to rock to: a finite number keeps its size (the sign is ignored) up to the 45 limit;
 * anything that is not a finite number takes `fallback`. 0 stays 0, so the cauldron is upright.
 */
export function resolveTilt(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(Math.abs(value), CAULDRON_TILT_MAX);
}
