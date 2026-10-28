/**
 * Pure rules for viewing a recipe at another number of servings (spec 062). Nothing here is
 * stored or sent: the chosen servings only change what the detail page shows.
 */

export const MIN_SERVINGS = 1;
export const MAX_SERVINGS = 100;

/** A whole number from 1 to 100, or null for anything else (FR-005). */
export function parseServings(text: string): number | null {
  const trimmed = text.trim();
  if (!/^[0-9]+$/.test(trimmed)) return null;
  const value = Number.parseInt(trimmed, 10);
  return value >= MIN_SERVINGS && value <= MAX_SERVINGS ? value : null;
}

export function scaleFactor(chosen: number, saved: number): number {
  return chosen / saved;
}

/**
 * The line as it reads at `chosen` servings. The quantity always comes from the saved line, so
 * 4 → 6 → 4 returns exactly to the saved amount. A line with no quantity (a vague amount) is
 * returned as it is; unit, size, name, preparation and note are never changed.
 */
export function scaleLine<T extends { quantity: number | null }>(
  line: T,
  chosen: number,
  saved: number,
): T {
  if (line.quantity === null) return line;
  return { ...line, quantity: (line.quantity * chosen) / saved };
}

/** One step up or down, kept within 1 to 100 (from above 100, down goes to 100). */
export function stepServings(current: number, direction: -1 | 1): number {
  return Math.min(MAX_SERVINGS, Math.max(MIN_SERVINGS, current + direction));
}
