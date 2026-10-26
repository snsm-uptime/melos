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

export type CategoryRef = { id: string; label: string; tag: string | null };

export type LineView = {
  key: string;
  name: string;
  vague: boolean;
  quantity: number | null;
  unit: string | null;
  size: string | null;
  preparation: string | null;
  note: string | null;
};

export type StepView = { key: string; text: string };

export type DraftView = {
  title: string;
  baseServings: number;
  servingsEstimated: boolean;
  mainIngredients: CategoryRef[];
  cuisines: CategoryRef[];
  lines: LineView[];
  steps: StepView[];
};

export type CaptureState = {
  notebook: CaptureNotebook | null;
  text: string;
  sheetOpen: boolean;
  phase: "idle" | "submitting" | "draft";
  message: CaptureMessage | null;
  draft: DraftView | null;
  originalHash: string | null;
  language: "en" | "es";
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
  });
}

export function editDraft(draft: DraftView): void {
  update({ draft });
}

/** Back on the draft page: the pasted text stays, the draft is dropped (FR-031). */
export function backToSheet(): void {
  update({ phase: "idle", draft: null, originalHash: null, sheetOpen: true, message: null });
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
  });
}

/** Leave by any other route: the store is emptied (FR-032). */
export function clearCapture(): void {
  state = EMPTY;
  listeners.forEach((listener) => listener());
}
