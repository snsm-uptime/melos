"use client";

import { useEffect, useState } from "react";

import { Sheet } from "@/app/kitchens/Sheet";
import {
  fetchVocabulary,
  submitCapture,
  type CaptureDraftResponse,
} from "@/lib/capture/captureClient";
import {
  closeSheet,
  failSubmit,
  openSheet,
  setText,
  showDraft,
  startSubmit,
  useCaptureState,
  type DraftView,
} from "@/lib/capture/captureStore";
import { captureMessages, messageForCode } from "@/lib/i18n/capture";

import type { CaptureCandidate } from "./AddRecipeCallToAction";

/** The api's default paste limit, used until the controlled lists load (RECIPE_TEXT_MAX_CHARS). */
const DEFAULT_MAX_CHARS = 5000;
const COUNTER_FROM_RATIO = 0.9;

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `draft-${keyCounter}`;
}

/** The API's draft answer, as the editable view the draft page changes (data-model "DraftView"). */
export function toDraftView(response: CaptureDraftResponse): DraftView {
  const draft = response.draft;
  return {
    title: draft.title,
    baseServings: draft.base_servings,
    servingsEstimated: draft.servings_estimated,
    mainIngredients: draft.main_ingredients.map((item) => ({ ...item, tag: null })),
    cuisines: draft.cuisines.map((item) => ({ ...item })),
    lines: draft.ingredient_lines.map((line) => ({ key: nextKey(), ...line })),
    steps: draft.steps.map((text) => ({ key: nextKey(), text })),
  };
}

type TextCaptureSheetProps = {
  open: boolean;
  candidates: CaptureCandidate[];
  onDraftReady: () => void;
};

const fieldClassName =
  "w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[0.95rem] text-foreground";

/**
 * The text sheet (spec 016 FR-002, FR-003, FR-004, FR-016 to FR-018). The pasted text stays
 * in the store, so a failure or Back keeps it. One submission at a time; no automatic retry.
 */
export function TextCaptureSheet({ open, candidates, onDraftReady }: TextCaptureSheetProps) {
  const capture = useCaptureState();
  const [max, setMax] = useState(DEFAULT_MAX_CHARS);

  // The paste limit is read when the sheet opens, not on page load.
  useEffect(() => {
    if (!open) return;
    let current = true;
    void fetchVocabulary().then((vocabulary) => {
      if (current && vocabulary) setMax(vocabulary.max_text_chars);
    });
    return () => {
      current = false;
    };
  }, [open]);

  const notebook = capture.notebook;
  const text = capture.text;
  const trimmed = text.trim();
  const tooLong = trimmed.length > max;
  const submitting = capture.phase === "submitting";
  const disabled = trimmed.length === 0 || tooLong || submitting || notebook === null;

  function chooseNotebook(id: string) {
    const picked = candidates.find((item) => item.id === id);
    if (!picked || !notebook) return;
    openSheet({
      id: picked.id,
      kind: picked.kind,
      name: picked.name,
      kitchenId: picked.kitchenId,
      returnPath: notebook.returnPath,
    });
  }

  async function submit() {
    if (!notebook || disabled) return;
    startSubmit();
    const result = await submitCapture(notebook.id, capture.text);
    if (!result.ok) {
      if (result.max !== undefined) setMax(result.max);
      failSubmit(result.message);
      return;
    }
    showDraft(toDraftView(result.value), result.value.language);
    onDraftReady();
  }

  const message = capture.message
    ? messageForCode(capture.message.code, capture.message.reason, max)
    : tooLong
      ? captureMessages.tooLong(max)
      : null;

  const body = (
    <div className="flex flex-col gap-4">
      {candidates.length > 1 && notebook ? (
        <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
          {captureMessages.notebookPicker}
          <select
            className={fieldClassName}
            value={notebook.id}
            disabled={submitting}
            onChange={(event) => chooseNotebook(event.target.value)}
          >
            {candidates.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
        {captureMessages.recipeText}
        <textarea
          className={`${fieldClassName} min-h-[12rem]`}
          value={text}
          readOnly={submitting}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      {text.length > max * COUNTER_FROM_RATIO ? (
        <p className="m-0 text-[0.8rem] text-muted">{captureMessages.counterNear(text.length, max)}</p>
      ) : null}
      {message ? (
        <p role="alert" className="m-0 text-[0.9rem] text-owe">
          {message}
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => void submit()}
        disabled={disabled}
        className="self-end rounded-[0.75rem] bg-accent px-4 py-2 text-[0.95rem] text-background disabled:opacity-50"
      >
        {submitting ? captureMessages.submitting : captureMessages.submit}
      </button>
    </div>
  );

  return (
    <Sheet
      open={open}
      onClose={closeSheet}
      closeLabel={captureMessages.close}
      title={notebook?.name ?? captureMessages.addRecipe}
      body={body}
    />
  );
}
