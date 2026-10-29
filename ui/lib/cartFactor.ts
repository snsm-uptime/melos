/**
 * The cart's scale factor, people × meals / base servings, formatted as the api does
 * (domain/cart.py): half-up to 2 decimals, trailing zeros removed. Integer arithmetic, so the
 * draft shows exactly what the saved cart will.
 */

export const COUNT_MIN = 1;
export const COUNT_MAX = 99;

export function formatFactor(people: number, meals: number, base: number): string {
  // Hundredths, rounded half-up: floor((2n + d) / 2d) with n = people·meals·100, d = base.
  const numerator = people * meals * 100;
  const hundredths = Math.floor((2 * numerator + base) / (2 * base));
  const whole = Math.floor(hundredths / 100);
  const rest = hundredths % 100;
  if (rest === 0) return String(whole);
  const decimals = String(rest).padStart(2, "0").replace(/0$/, "");
  return `${whole}.${decimals}`;
}

/** A whole number from 1 to 99, or null. */
export function parseCount(text: string): number | null {
  if (!/^\d{1,2}$/.test(text.trim())) return null;
  const value = Number(text.trim());
  return value >= COUNT_MIN && value <= COUNT_MAX ? value : null;
}
