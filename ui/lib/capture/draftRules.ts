/**
 * Draft checks shown next to each field while the member edits (spec 016 FR-013).
 * They mirror the api's check_draft rules. Pure: no I/O. The caller passes the units allowed
 * here, because they depend on the person and, on an edit, on the stored recipe (spec 055 R15).
 */

export const ALLOWED_UNITS = ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"] as const;
export const SIZES = ["small", "medium", "large"] as const;
export const MAX_TITLE_CHARS = 200;
// MVP-OUT: export const MAX_MAIN_INGREDIENTS = 2;
// MVP-OUT: export const MAX_CUISINES = 2;

export type LineInput = {
  vague: boolean;
  quantity: number | null;
  unit: string | null;
  size: string | null;
  /** The words of a vague amount; checked only when the line carries the field. */
  vagueText?: string | null;
};

export type DraftInput = {
  title: string;
  baseServings: number;
  lines: LineInput[];
  steps: { text: string }[];
  // MVP-OUT: mainIngredientCount: number;
  // MVP-OUT: cuisineCount: number;
};

/** Error codes, mapped to text in lib/i18n/capture.ts (`captureMessagesFor(locale).errors`). */
export type DraftErrors = {
  title?: "titleRequired" | "titleTooLong";
  servings?: "servingsInvalid";
  steps?: "stepsRequired";
  lines: Record<number, ("amountAndUnit" | "vagueHasAmount" | "vagueNeedsNote" | "sizeOnlyForUnit" | "sizeInvalid")[]>;
};

export function lineErrors(
  line: LineInput,
  allowedUnits: readonly string[],
): DraftErrors["lines"][number] {
  const errors: NonNullable<DraftErrors["lines"][number]> = [];
  if (line.vague) {
    if (line.quantity !== null || line.unit !== null) errors.push("vagueHasAmount");
    if (line.vagueText !== undefined && (line.vagueText ?? "").trim().length === 0) {
      errors.push("vagueNeedsNote");
    }
  } else {
    const measured =
      line.quantity !== null &&
      Number.isFinite(line.quantity) &&
      line.quantity > 0 &&
      line.unit !== null &&
      allowedUnits.includes(line.unit);
    if (!measured) errors.push("amountAndUnit");
  }
  if (line.size !== null) {
    if (line.unit !== "unit") errors.push("sizeOnlyForUnit");
    else if (!(SIZES as readonly string[]).includes(line.size)) errors.push("sizeInvalid");
  }
  return errors;
}

export function checkDraft(draft: DraftInput, allowedUnits: readonly string[]): DraftErrors {
  const errors: DraftErrors = { lines: {} };
  const title = draft.title.trim();
  if (title.length === 0) errors.title = "titleRequired";
  else if (title.length > MAX_TITLE_CHARS) errors.title = "titleTooLong";

  if (!Number.isInteger(draft.baseServings) || draft.baseServings < 1) {
    errors.servings = "servingsInvalid";
  }

  draft.lines.forEach((line, index) => {
    const found = lineErrors(line, allowedUnits);
    if (found.length > 0) errors.lines[index] = found;
  });

  if (!draft.steps.some((step) => step.text.trim().length > 0)) errors.steps = "stepsRequired";
  return errors;
}

/**
 * The words to ask about (spec 055): used by a line and neither allowed nor answered. Derived, so
 * a question goes away once no line uses its word.
 */
export function pendingUnitQuestions(
  lines: readonly LineInput[],
  allowedUnits: readonly string[],
  keptUnits: readonly string[],
  declinedUnits: readonly string[],
): string[] {
  const answered = new Set([...allowedUnits, ...keptUnits, ...declinedUnits]);
  const words = lines.flatMap((line) =>
    !line.vague && line.unit && !answered.has(line.unit) ? [line.unit] : [],
  );
  return [...new Set(words)];
}

/** Choosing a word again asks about it again: a no is not remembered (FR-006). */
export function withoutRechosenUnit(
  declinedUnits: readonly string[],
  previousUnit: string | null,
  nextUnit: string | null,
): string[] {
  if (previousUnit === nextUnit) return [...declinedUnits];
  return declinedUnits.filter((word) => word !== nextUnit);
}

export function hasErrors(errors: DraftErrors): boolean {
  return (
    errors.title !== undefined ||
    errors.servings !== undefined ||
    errors.steps !== undefined ||
    Object.keys(errors.lines).length > 0
  );
}
