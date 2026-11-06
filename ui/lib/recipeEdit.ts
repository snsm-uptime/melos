/**
 * Pure helpers for the recipe edit form (spec 027). Independent of the capture store: the form
 * starts from a stored recipe and keeps its state locally. The line shape is the draft editor's
 * `LineView`, so the same rows are reused (research R9).
 */

import {
  chooseLineMatch,
  type LineView,
  type StepView,
} from "./capture/captureStore";
import { sameSpelling } from "./capture/nameChanges";
import type {
  NameMatch,
  RecipeDetail,
  RecipeUpdateBody,
} from "./recipesClient";

export type EditState = {
  title: string;
  baseServings: number;
  servingsEstimated: boolean;
  lines: LineView[];
  steps: StepView[];
  /** Words the person said yes to, sent on update (spec 055). */
  keptUnits: string[];
  /** Words the person said no to on this screen. Never remembered (FR-006). */
  declinedUnits: string[];
  /** The recipe photo as a data URI, or null (S-067). */
  previewImage: string | null;
  /** The recipe's language (spec 043); its lines show the names of this language. */
  language: "en" | "es";
  /** True once the member picks or removes the photo; only then is it sent on update. */
  imageChanged: boolean;
};

let counter = 0;
export function nextKey(prefix: string): string {
  counter += 1;
  return `${prefix}-${counter}`;
}

/**
 * A stored recipe as form state. Each stored name is already a catalog name, so it is matched.
 * A line shows its name in the recipe's language (spec 043); Save maps it back to the kept name.
 */
export function toEditState(recipe: RecipeDetail): EditState {
  return {
    title: recipe.title,
    baseServings: recipe.base_servings,
    servingsEstimated: recipe.servings_estimated,
    language: recipe.language ?? "es",
    lines: recipe.ingredient_lines.map((line) => {
      const name = line.shown_name ?? line.name;
      return {
        key: nextKey("edit-line"),
        name,
        vague: line.vague,
        quantity: line.quantity,
        unit: line.unit,
        size: line.size,
        preparation: line.preparation,
        note: line.note,
        textName: name,
        match: { kind: "matched", entry: name },
      };
    }),
    steps: recipe.steps.map((text) => ({ key: nextKey("edit-step"), text })),
    keptUnits: [],
    declinedUnits: [],
    previewImage: recipe.preview_image ?? null,
    imageChanged: false,
  };
}

export function toUpdateBody(
  state: EditState,
  version: string,
): RecipeUpdateBody {
  return {
    version,
    title: state.title,
    base_servings: state.baseServings,
    servings_estimated: state.servingsEstimated,
    ingredient_lines: state.lines.map((line) => ({
      name: line.name,
      vague: line.vague,
      quantity: line.quantity,
      unit: line.unit,
      size: line.size,
      preparation: line.preparation,
      note: line.note,
    })),
    steps: state.steps.map((step) => step.text),
    keep_units: state.keptUnits,
    language: state.language,
    // Left out keeps the stored photo; null removes it; a data URI replaces it (S-067).
    ...(state.imageChanged ? { preview_image: state.previewImage } : {}),
  };
}

/** True when the form differs from the recipe as it was loaded. */
export function isEdited(state: EditState, original: RecipeDetail): boolean {
  const version = original.version;
  return (
    JSON.stringify(toUpdateBody(state, version)) !==
    JSON.stringify(toUpdateBody(toEditState(original), version))
  );
}

/**
 * Apply a change to one line coming from the shared row. A change that only edits the name
 * field (the match object is the same one) is typed text: it becomes the line's text name and
 * its match is dropped until the next check. Choosing a match or undoing one replaces the match
 * object, so those pass through unchanged.
 */
export function applyLineChange(previous: LineView, next: LineView): LineView {
  if (next.name !== previous.name && next.match === previous.match) {
    return {
      ...next,
      textName: next.name,
      match: { kind: "new", entry: null },
    };
  }
  return next;
}

/** Lines whose typed name was not checked yet: new, named, and not checked under this name. */
export function pendingChecks(
  lines: LineView[],
  checked: Map<string, string>,
): LineView[] {
  return lines.filter(
    (line) =>
      line.match.kind === "new" &&
      line.name.trim() !== "" &&
      checked.get(line.key) !== line.name,
  );
}

/**
 * Put the proposals on the lines. A line is changed only if it still has the name that was
 * checked and still has no match; a proposal that differs by case or spacing only is no change.
 */
export function applyMatches(
  lines: LineView[],
  checkedNames: Map<string, string>,
  matches: NameMatch[],
): LineView[] {
  const entryByName = new Map(
    matches.map((match) => [match.name, match.entry]),
  );
  return lines.map((line) => {
    const entry = entryByName.get(checkedNames.get(line.key) ?? "\u0000");
    if (
      !entry ||
      line.match.kind !== "new" ||
      line.name !== checkedNames.get(line.key)
    )
      return line;
    if (sameSpelling(entry, line.name)) return line;
    return chooseLineMatch(line, entry);
  });
}

/** The catalog entries the match control may show: the entries the lines are matched to. */
export function catalogOf(lines: LineView[]): string[] {
  const entries = lines.flatMap((line) =>
    line.match.kind === "matched" && line.match.entry ? [line.match.entry] : [],
  );
  return [...new Set(entries)];
}

export function moveItem<T>(items: T[], index: number, direction: -1 | 1): T[] {
  const target = index + direction;
  if (target < 0 || target >= items.length) return items;
  const next = [...items];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

export function newLine(): LineView {
  return {
    key: nextKey("edit-line"),
    name: "",
    vague: false,
    quantity: null,
    unit: null,
    size: null,
    preparation: null,
    note: null,
    textName: "",
    match: { kind: "new", entry: null },
  };
}
