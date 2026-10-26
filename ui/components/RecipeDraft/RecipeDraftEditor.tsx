"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchVocabulary,
  type VocabularyResponse,
} from "@/lib/capture/captureClient";
import { checkDraft, type DraftInput } from "@/lib/capture/draftRules";
import {
  backToSheet,
  discardDraft,
  editDraft,
  useCaptureState,
  type DraftView,
  type LineView,
} from "@/lib/capture/captureStore";
import { pickLabel } from "@/lib/capture/labels";
import { captureMessages } from "@/lib/i18n/capture";

import { CategoryChips } from "./CategoryChips";
import { IngredientLineRow } from "./IngredientLineRow";

const MAX_MAIN = 2;
const MAX_CUISINES = 2;

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `draft-new-${keyCounter}`;
}

/**
 * The draft review page body (spec 016 US1, US4). Edits stay in the store until the member
 * leaves. There is no Save: the draft is not stored in this feature (FR-019).
 */
export function RecipeDraftEditor() {
  const router = useRouter();
  const capture = useCaptureState();
  const [vocabulary, setVocabulary] = useState<VocabularyResponse | null>(null);

  useEffect(() => {
    let current = true;
    void fetchVocabulary().then((value) => {
      if (current) setVocabulary(value);
    });
    return () => {
      current = false;
    };
  }, []);

  const draft = capture.draft;
  const notebook = capture.notebook;

  useEffect(() => {
    if (!draft || !notebook) router.replace(notebook?.returnPath ?? "/notebooks");
  }, [draft, notebook, router]);

  if (!draft || !notebook) return null;

  const language = capture.language;
  const input: DraftInput = {
    title: draft.title,
    baseServings: draft.baseServings,
    lines: draft.lines,
    steps: draft.steps,
    mainIngredientCount: draft.mainIngredients.length,
    cuisineCount: draft.cuisines.length,
  };
  const errors = checkDraft(input);

  function update(patch: Partial<DraftView>) {
    editDraft({ ...draft!, ...patch });
  }

  function updateLine(index: number, next: LineView) {
    update({ lines: draft!.lines.map((line, i) => (i === index ? next : line)) });
  }

  function moveItem<T>(items: T[], index: number, direction: -1 | 1): T[] {
    const target = index + direction;
    if (target < 0 || target >= items.length) return items;
    const next = [...items];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
  }

  const units = vocabulary?.units ?? [];
  const sizes = vocabulary?.sizes ?? [];
  const tagLabel = (tag: string) => {
    const match = vocabulary?.cuisines.find((item) => item.id === tag);
    return match ? pickLabel(match.label, language) : tag;
  };

  function back() {
    backToSheet();
    router.push(notebook!.returnPath);
  }

  function discard() {
    discardDraft();
    router.push(notebook!.returnPath);
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="m-0 text-[0.9rem] text-muted">{captureMessages.forNotebook(notebook.name)}</p>

      <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
        {captureMessages.titleLabel}
        <input
          className="w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[1rem] text-foreground"
          value={draft.title}
          onChange={(event) => update({ title: event.target.value })}
        />
        {errors.title ? (
          <span role="alert" className="text-[0.8rem] text-owe">
            {captureMessages.errors[errors.title]}
          </span>
        ) : null}
      </label>

      <div className="flex flex-col gap-1">
        <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
          {captureMessages.servingsLabel}
          <input
            type="number"
            min="1"
            step="1"
            className="w-32 rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[1rem] text-foreground"
            value={draft.baseServings}
            onChange={(event) =>
              update({ baseServings: Number(event.target.value), servingsEstimated: false })
            }
          />
        </label>
        {draft.servingsEstimated ? (
          <span className="text-[0.75rem] text-muted">{captureMessages.estimated}</span>
        ) : null}
        {errors.servings ? (
          <span role="alert" className="text-[0.8rem] text-owe">
            {captureMessages.errors[errors.servings]}
          </span>
        ) : null}
      </div>

      <CategoryChips
        title={captureMessages.mainIngredients}
        addLabel={captureMessages.addMainIngredient}
        selected={draft.mainIngredients}
        max={MAX_MAIN}
        tagLabel={tagLabel}
        options={(vocabulary?.main_ingredients ?? []).map((item) => ({
          id: item.id,
          label: pickLabel(item.label, language),
          tag: null,
        }))}
        onChange={(next) => update({ mainIngredients: next })}
      />

      <CategoryChips
        title={captureMessages.cuisines}
        addLabel={captureMessages.addCuisine}
        selected={draft.cuisines}
        max={MAX_CUISINES}
        tagLabel={tagLabel}
        options={(vocabulary?.cuisines ?? []).map((item) => ({
          id: item.id,
          label: pickLabel(item.label, language),
          tag: item.tag,
        }))}
        onChange={(next) => update({ cuisines: next })}
      />

      <section className="flex flex-col gap-2">
        <h2 className="m-0 text-[1rem] font-[550] text-foreground">{captureMessages.ingredients}</h2>
        <ul className="m-0 flex list-none flex-col p-0">
          {draft.lines.map((line, index) => (
            <IngredientLineRow
              key={line.key}
              line={line}
              index={index}
              count={draft.lines.length}
              errors={errors.lines[index] ?? []}
              units={units}
              sizes={sizes}
              onChange={(next) => updateLine(index, next)}
              onRemove={() => update({ lines: draft.lines.filter((_, i) => i !== index) })}
              onMove={(direction) => update({ lines: moveItem(draft.lines, index, direction) })}
            />
          ))}
        </ul>
        <button
          type="button"
          className="self-start text-[0.9rem] text-accent"
          onClick={() =>
            update({
              lines: [
                ...draft.lines,
                {
                  key: nextKey(),
                  name: "",
                  vague: false,
                  quantity: null,
                  unit: null,
                  size: null,
                  preparation: null,
                  note: null,
                },
              ],
            })
          }
        >
          {captureMessages.addIngredient}
        </button>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="m-0 text-[1rem] font-[550] text-foreground">{captureMessages.steps}</h2>
        <ol className="m-0 flex list-none flex-col gap-2 p-0">
          {draft.steps.map((step, index) => (
            <li key={step.key} className="flex flex-col gap-1">
              <label className="flex flex-col gap-1 text-[0.8rem] text-muted">
                {captureMessages.stepLabel(index + 1)}
                <textarea
                  className="w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[0.95rem] text-foreground"
                  value={step.text}
                  onChange={(event) =>
                    update({
                      steps: draft.steps.map((item, i) =>
                        i === index ? { ...item, text: event.target.value } : item,
                      ),
                    })
                  }
                />
              </label>
              <div className="flex gap-2 text-[0.8rem]">
                <button
                  type="button"
                  className="text-muted"
                  disabled={index === 0}
                  onClick={() => update({ steps: moveItem(draft.steps, index, -1) })}
                >
                  {captureMessages.moveUp}
                </button>
                <button
                  type="button"
                  className="text-muted"
                  disabled={index === draft.steps.length - 1}
                  onClick={() => update({ steps: moveItem(draft.steps, index, 1) })}
                >
                  {captureMessages.moveDown}
                </button>
                <button
                  type="button"
                  className="text-muted"
                  onClick={() => update({ steps: draft.steps.filter((_, i) => i !== index) })}
                >
                  {captureMessages.remove}
                </button>
              </div>
            </li>
          ))}
        </ol>
        {errors.steps ? (
          <span role="alert" className="text-[0.8rem] text-owe">
            {captureMessages.errors[errors.steps]}
          </span>
        ) : null}
        <button
          type="button"
          className="self-start text-[0.9rem] text-accent"
          onClick={() => update({ steps: [...draft.steps, { key: nextKey(), text: "" }] })}
        >
          {captureMessages.addStep}
        </button>
      </section>

      <div className="flex flex-wrap justify-between gap-3 pt-2">
        <button type="button" onClick={back} className="text-[0.95rem] text-muted">
          {captureMessages.back}
        </button>
        <button type="button" onClick={discard} className="text-[0.95rem] text-owe">
          {captureMessages.discard}
        </button>
      </div>
    </div>
  );
}
