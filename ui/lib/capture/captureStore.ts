"use client";

/**
 * Client-only capture state (spec 016 data-model "Client-only state"). One store per tab;
 * a reload clears it. Nothing here is sent to the api except the text on submit.
 */

import { useSyncExternalStore } from "react";

import { draftHash } from "./draftHash";

export type CaptureNotebook = {
  id: string;
  kind: "personal" | "kitchen";
  name: string;
  kitchenId: string | null;
  /** Where Back and Discard return: the page that opened the capture. */
  returnPath: string;
};

export type CaptureMessage = {
  code: string;
  reason?: string;
  missing?: string[];
  lineProblems?: { name: string | null; kind: string }[];
  ingredient?: string | null;
};

// MVP-OUT: export type CategoryRef = { id: string; label: string; tag: string | null };

/** The label on an ingredient line (spec 018 FR-001): a catalog entry, or a new ingredient. */
export type LineMatch = { kind: "matched" | "new"; entry: string | null };

export type LineView = {
  key: string;
  name: string;
  vague: boolean;
  quantity: number | null;
  unit: string | null;
  size: string | null;
  preparation: string | null;
  note: string | null;
  /** The name as the text writes it; undo returns the line to it (spec 018 FR-004). */
  textName: string;
  match: LineMatch;
};

export type StepView = { key: string; text: string };

export type DraftView = {
  title: string;
  baseServings: number;
  servingsEstimated: boolean;
  // MVP-OUT: mainIngredients: CategoryRef[];
  // MVP-OUT: cuisines: CategoryRef[];
  lines: LineView[];
  steps: StepView[];
  /** The capture notebook's catalog entries, for the match control (spec 018 FR-005). */
  catalog: string[];
};

/** The match-control value that means "new ingredient". Not a catalog entry name. */
export const NEW_CHOICE = "__new__";

export type CaptureState = {
  notebook: CaptureNotebook | null;
  text: string;
  sheetOpen: boolean;
  phase: "idle" | "submitting" | "draft";
  message: CaptureMessage | null;
  draft: DraftView | null;
  originalHash: string | null;
  language: "en" | "es";
  /** The draft's key for Save, made when the draft is shown (spec 020 research R5). */
  saveKey: string | null;
  saving: boolean;
  /** Set by a successful Save: the page it returned to shows "Recipe saved" once (spec 020). */
  savedNotice: { returnPath: string } | null;
};

const EMPTY: CaptureState = {
  notebook: null,
  text: "",
  sheetOpen: false,
  phase: "idle",
  message: null,
  draft: null,
  originalHash: null,
  language: "en",
  saveKey: null,
  saving: false,
  savedNotice: null,
};

let state: CaptureState = EMPTY;
const listeners = new Set<() => void>();

function update(patch: Partial<CaptureState>): void {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener());
}

export function getCaptureState(): CaptureState {
  return state;
}

export function subscribeCapture(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useCaptureState(): CaptureState {
  return useSyncExternalStore(subscribeCapture, getCaptureState, () => EMPTY);
}

/** A draft is edited when its editable values differ from the draft first shown (FR-032). */
export function isDraftEdited(current: CaptureState): boolean {
  if (!current.draft || current.originalHash === null) return false;
  return draftHash(current.draft) !== current.originalHash;
}

export function openSheet(notebook: CaptureNotebook): void {
  const sameNotebook = state.notebook?.id === notebook.id;
  update({ notebook: sameNotebook ? state.notebook : notebook, sheetOpen: true });
}

export function closeSheet(): void {
  update({ sheetOpen: false, message: null });
}

export function setText(text: string): void {
  update({ text, message: null });
}

export function startSubmit(): void {
  update({ phase: "submitting", message: null });
}

export function failSubmit(message: CaptureMessage): void {
  update({ phase: "idle", message });
}

export function showDraft(draft: DraftView, language: "en" | "es"): void {
  update({
    phase: "draft",
    draft,
    originalHash: draftHash(draft),
    language,
    message: null,
    sheetOpen: false,
    saveKey: newSaveKey(),
    saving: false,
  });
}

function newSaveKey(): string {
  return globalThis.crypto.randomUUID();
}

export function startSave(): void {
  update({ saving: true, message: null });
}

/** A refused or failed Save: the draft and every edit stay; the same key is reused on retry. */
export function failSave(message: CaptureMessage): void {
  update({ saving: false, message });
}

/**
 * The page a successful Save returns to (spec 021 FR-013). A personal notebook has its own
 * page with the recipe list, so the member lands on the list showing the new recipe. A kitchen
 * capture returns to the kitchen page, which lists the kitchen's recipes.
 */
export function savedReturnPath(notebook: CaptureNotebook): string {
  return notebook.kind === "personal" ? `/notebooks/${notebook.id}` : notebook.returnPath;
}

/** A successful Save: the draft and text are gone, and the notebook page shows the notice. */
export function markSaved(returnPath: string): void {
  update({
    phase: "idle",
    draft: null,
    originalHash: null,
    text: "",
    sheetOpen: false,
    message: null,
    saveKey: null,
    saving: false,
    savedNotice: { returnPath },
  });
}

/** The notice for this page, if the last Save returned to it. Reading it clears it. */
export function takeSavedNotice(returnPath: string): boolean {
  if (state.savedNotice?.returnPath !== returnPath) return false;
  update({ savedNotice: null });
  return true;
}

export function editDraft(draft: DraftView): void {
  update({ draft });
}

/** The line back to "new ingredient", with the name the text wrote (spec 018 FR-004). */
export function undoLineChange(line: LineView): LineView {
  return { ...line, name: line.textName, match: { kind: "new", entry: null } };
}

/** The member's choice for one line: a catalog entry, or NEW_CHOICE for a new ingredient (FR-005). */
export function chooseLineMatch(line: LineView, choice: string): LineView {
  if (choice === NEW_CHOICE) return undoLineChange(line);
  return { ...line, name: choice, match: { kind: "matched", entry: choice } };
}

function mapDraftLine(index: number, change: (line: LineView) => LineView): void {
  if (!state.draft) return;
  const lines = state.draft.lines.map((line, i) => (i === index ? change(line) : line));
  update({ draft: { ...state.draft, lines } });
}

export function undoChange(index: number): void {
  mapDraftLine(index, undoLineChange);
}

export function chooseMatch(index: number, choice: string): void {
  mapDraftLine(index, (line) => chooseLineMatch(line, choice));
}

/** Back on the draft page: the pasted text stays, the draft is dropped (FR-031). */
export function backToSheet(): void {
  update({
    phase: "idle",
    draft: null,
    originalHash: null,
    sheetOpen: true,
    message: null,
    saveKey: null,
    saving: false,
  });
}

/** Discard: the draft and the text are cleared; no leave prompt (FR-020). */
export function discardDraft(): void {
  update({
    phase: "idle",
    draft: null,
    originalHash: null,
    text: "",
    sheetOpen: true,
    message: null,
    saveKey: null,
    saving: false,
  });
}

/** Leave by any other route: the store is emptied (FR-032). */
export function clearCapture(): void {
  state = EMPTY;
  listeners.forEach((listener) => listener());
}
