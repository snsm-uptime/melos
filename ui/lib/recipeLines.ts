/** Number formatting for ingredient amounts on the recipe detail (spec 027 FR-002, spec 062 FR-004). */

/**
 * 1 → "1", 0.5 → "0.5", 1.250 → "1.25"; at most two decimals, never a trailing zero. An amount
 * above zero that would round to 0 reads "<0.01", so a scaled ingredient never shows as nothing.
 */
export function formatQuantity(quantity: number): string {
  const rounded = Math.round((quantity + Number.EPSILON) * 100) / 100;
  if (rounded === 0 && quantity > 0) return "<0.01";
  return String(rounded);
}
