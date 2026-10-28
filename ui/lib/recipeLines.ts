/** Number formatting for ingredient amounts on the recipe detail (spec 027 FR-002). */

/** 1 → "1", 0.5 → "0.5", 1.250 → "1.25"; never a trailing zero. */
export function formatQuantity(quantity: number): string {
  return String(Math.round(quantity * 100) / 100);
}
