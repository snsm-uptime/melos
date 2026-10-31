import type { HandItem, ShoppingLine, YourCallEntry } from "./shoppingListClient";

/**
 * A measured line as the member reads it (spec 023 FR-009): `{name}[, {size}] — {amounts}`.
 * Amounts of one kind are joined with " + "; a count shows the number only. Names, sizes and
 * unit codes are shown as stored, untranslated (FR-013).
 */
export function formatLine(line: ShoppingLine): string {
  const amounts = line.amounts
    .map((amount) => (line.kind === "count" ? amount.quantity : `${amount.quantity} ${amount.unit}`))
    .join(" + ");
  const name = line.size ? `${line.name}, ${line.size}` : line.name;
  return `${name} — ${amounts}`;
}

/** A "Your call" entry (spec 023 FR-007): the name, then every distinct note joined with ", ". */
export function formatYourCall(entry: YourCallEntry): string {
  return `${entry.name} — ${entry.notes.join(", ")}`;
}

/** An item added by hand: its name, then its amount when it has one (spec 025). */
export function formatHandItem(item: HandItem): string {
  if (item.quantity === null) return item.name;
  const amount = item.unit === "unit" ? item.quantity : `${item.quantity} ${item.unit}`;
  return `${item.name} — ${amount}`;
}
