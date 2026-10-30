import type { ShoppingLine, YourCallEntry } from "./shoppingListClient";

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
