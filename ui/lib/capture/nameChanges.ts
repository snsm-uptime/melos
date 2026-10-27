/**
 * The name changes the member sees before saving (spec 018 FR-003). Derived from the lines, so
 * the list always matches what is on the page: undo or a new choice removes or changes an item.
 */

import type { LineView } from "./captureStore";

export type NameChange = { line: number; from: string; to: string };

/** Two names differ only in letter case or spaces: no change is listed for them. */
export function sameSpelling(first: string, second: string): boolean {
  return collapse(first) === collapse(second);
}

function collapse(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

/** One item per matched line whose text name differs from the entry it matches. */
export function nameChanges(lines: LineView[]): NameChange[] {
  return lines.flatMap((line, index) => {
    if (line.match.kind !== "matched" || line.match.entry === null) return [];
    if (sameSpelling(line.textName, line.match.entry)) return [];
    return [{ line: index, from: line.textName, to: line.match.entry }];
  });
}
