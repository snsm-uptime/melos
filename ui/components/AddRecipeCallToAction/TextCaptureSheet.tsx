"use client";

import { NotebookPicker } from "@/components/NotebookPicker";
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
  setText,
  showDraft,
  startSubmit,
  useCaptureState,
  type DraftView,
} from "@/lib/capture/captureStore";
import { messageForCode } from "@/lib/i18n/capture";
import { useLocale } from "@/lib/i18n/useLocale";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

import type { CaptureCandidate } from "./AddRecipeCallToAction";
import {
  captureTarget,
  chooseNotebook,
  pickerOptions,
} from "./captureNotebook";

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
    unknownUnits: (draft.unknown_units ?? []).map((unknown) => unknown.word),
    keptUnits: [],
    declinedUnits: [],
    title: draft.title,
    baseServings: draft.base_servings,
    servingsEstimated: draft.servings_estimated,
    // MVP-OUT: mainIngredients: draft.main_ingredients.map((item) => ({ ...item, tag: null })),
    // MVP-OUT: cuisines: draft.cuisines.map((item) => ({ ...item })),
    lines: draft.ingredient_lines.map((line) => ({
      key: nextKey(),
      name: line.name,
      vague: line.vague,
      quantity: line.quantity,
      unit: line.unit,
      size: line.size,
      preparation: line.preparation,
      note: line.note,
      textName: line.text_name,
      match: line.match,
    })),
    steps: draft.steps.map((text) => ({ key: nextKey(), text })),
    catalog: response.catalog,
    // Link capture only (spec 026).
    ...(response.page
      ? {
          sourceUrl: response.page.source_url,
          previewImage: response.page.preview_image,
          pageCut: response.page.cut,
        }
      : {}),
  };
}

type TextCaptureSheetProps = {
  open: boolean;
  candidates: CaptureCandidate[];
  onDraftReady: () => void;
};

const fieldClassName =
  "w-full rounded-[0.75rem] border border-field-border bg-background px-3 py-2 text-[0.95rem] text-foreground";

/**
 * The text sheet (spec 016 FR-002, FR-003, FR-004, FR-016 to FR-018). The pasted text stays
 * in the store, so a failure or Back keeps it. One submission at a time; no automatic retry.
 */
export function TextCaptureSheet({
  open,
  candidates,
  onDraftReady,
}: TextCaptureSheetProps) {
  const t = useCaptureMessages();
  const locale = useLocale();
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
  const disabled =
    trimmed.length === 0 || tooLong || submitting || notebook === null;

  async function submit() {
    if (!notebook || disabled) return;
    startSubmit();
    const target = await captureTarget(notebook);
    if (!target.ok) {
      failSubmit({ code: target.code });
      return;
    }
    const result = await submitCapture(target.notebook.id, capture.text);
    if (!result.ok) {
      if (result.max !== undefined) setMax(result.max);
      failSubmit(result.message);
      return;
    }
    showDraft(toDraftView(result.value), result.value.language);
    onDraftReady();
  }

  const options = pickerOptions(candidates, notebook);

  const message = capture.message
    ? messageForCode(capture.message, locale, max)
    : tooLong
      ? t.tooLong(max)
      : null;

  const body = (
    <div className="flex flex-col gap-4">
      {candidates.length > 1 && notebook ? (
        <div className="flex flex-col gap-1 text-[0.85rem] text-muted">
          <span aria-hidden="true">{t.notebookPicker}</span>
          <NotebookPicker
            locale={locale}
            label={t.notebookPicker}
            value={notebook.id}
            disabled={submitting}
            notebooks={options}
            onChange={(id) => chooseNotebook(options, id, notebook)}
          />
        </div>
      ) : null}
      <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
        {t.recipeText}
        <textarea
          className={`${fieldClassName} min-h-[12rem]`}
          value={text}
          readOnly={submitting}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      {text.length > max * COUNTER_FROM_RATIO ? (
        <p className="m-0 text-[0.8rem] text-muted">
          {t.counterNear(text.length, max)}
        </p>
      ) : null}
      {message ? (
        <p role="alert" className="m-0 text-[0.9rem] text-error">
          {message}
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => void submit()}
        disabled={disabled}
        className="self-end rounded-[0.75rem] bg-primary px-4 py-2 text-[0.95rem] text-on-primary disabled:opacity-50"
      >
        {submitting ? t.submitting : t.submit}
      </button>
    </div>
  );

  return (
    <Sheet
      open={open}
      onClose={closeSheet}
      closeLabel={t.close}
      title={notebook?.name ?? t.addRecipe}
      body={body}
    />
  );
}
