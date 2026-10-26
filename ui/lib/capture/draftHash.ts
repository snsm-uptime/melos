/**
 * A content hash of the draft's editable values, in order. It decides whether a draft is
 * "edited" (spec 016 FR-032): a change that is reverted by hand is not an edit. Client keys
 * (line and step ids) are left out, because they change with reordering only.
 */

import type { DraftView } from "./captureStore";

export function draftHash(draft: DraftView): string {
  return JSON.stringify({
    title: draft.title,
    baseServings: draft.baseServings,
    mainIngredients: draft.mainIngredients.map((item) => item.id),
    cuisines: draft.cuisines.map((item) => item.id),
    lines: draft.lines.map((line) => [
      line.name,
      line.vague,
      line.quantity,
      line.unit,
      line.size,
      line.preparation,
      line.note,
    ]),
    steps: draft.steps.map((step) => step.text),
  });
}
