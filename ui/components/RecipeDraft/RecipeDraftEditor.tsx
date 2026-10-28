"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BackIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import {
  fetchVocabulary,
  type VocabularyResponse,
} from "@/lib/capture/captureClient";
import { checkDraft, hasErrors, type DraftInput } from "@/lib/capture/draftRules";
import { submitSave } from "@/lib/capture/saveClient";
import {
  backToSheet,
  discardDraft,
  editDraft,
  failSave,
  getCaptureState,
  markSaved,
  savedReturnPath,
  startSave,
  undoChange,
  useCaptureState,
  type DraftView,
  type LineView,
} from "@/lib/capture/captureStore";
import { nameChanges } from "@/lib/capture/nameChanges";
// MVP-OUT: import { pickLabel } from "@/lib/capture/labels";
import { captureMessages, messageForCode } from "@/lib/i18n/capture";

// MVP-OUT: import { CategoryChips } from "./CategoryChips";
import { IngredientLineRow } from "./IngredientLineRow";
import { StepCard } from "./StepCard";

// MVP-OUT: const MAX_MAIN = 2;
// MVP-OUT: const MAX_CUISINES = 2;

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `draft-new-${keyCounter}`;
}

/**
 * The draft review page body (spec 016 US1, US4; Save is spec 020). Edits stay in the store
 * until the member saves, discards or leaves.
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
    if (!draft || !notebook)
      router.replace(notebook?.returnPath ?? "/notebooks");
  }, [draft, notebook, router]);

  if (!draft || !notebook) return null;

  // MVP-OUT: const language = capture.language; (only the category labels used it)
  const input: DraftInput = {
    title: draft.title,
    baseServings: draft.baseServings,
    lines: draft.lines,
    steps: draft.steps,
    // MVP-OUT: mainIngredientCount: draft.mainIngredients.length,
    // MVP-OUT: cuisineCount: draft.cuisines.length,
  };
  const errors = checkDraft(input);
  const changesByLine = new Map(
    nameChanges(draft.lines).map((change) => [change.line, change]),
  );

  function update(patch: Partial<DraftView>) {
    editDraft({ ...draft!, ...patch });
  }

  function updateLine(index: number, next: LineView) {
    update({
      lines: draft!.lines.map((line, i) => (i === index ? next : line)),
    });
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
  // MVP-OUT: const tagLabel = (tag: string) => {
  // MVP-OUT:   const match = vocabulary?.cuisines.find((item) => item.id === tag);
  // MVP-OUT:   return match ? pickLabel(match.label, language) : tag;
  // MVP-OUT: };

  function back() {
    backToSheet();
    router.push(notebook!.returnPath);
  }

  async function save() {
    if (capture.saving) return;
    startSave();
    const result = await submitSave(getCaptureState());
    if (!result.ok) {
      failSave(result.message);
      return;
    }
    const savedPath = savedReturnPath(notebook!);
    markSaved(savedPath);
    router.push(savedPath);
  }

  function discard() {
    discardDraft();
    router.push(notebook!.returnPath);
  }

  return (
    <div className="flex flex-col gap-6 md:min-h-0 md:flex-1">
      {/* Same insets and Back slot as AppShell's chrome header. */}
      <header className="flex items-center gap-2 pt-[max(0.5rem,env(safe-area-inset-top))] pr-[max(1rem,env(safe-area-inset-right))] pb-1 pl-[max(0.5rem,env(safe-area-inset-left))]">
        <div className="flex w-10 shrink-0 items-center justify-start self-center">
          <IconButton
            variant="ghost"
            label={captureMessages.back}
            icon={<BackIcon className="size-6" />}
            onClick={back}
          />
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <h1 className="m-0 min-w-0">
            <input
              aria-label={captureMessages.titleLabel}
              placeholder={captureMessages.titleLabel}
              className="w-full min-w-0 rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-[1.5rem] font-[550] leading-normal text-foreground outline-none hover:bg-background focus:bg-background"
              value={draft.title}
              onChange={(event) => update({ title: event.target.value })}
            />
          </h1>
          <h4 className="m-0 px-1 text-[0.9rem] font-normal text-muted">
            {notebook.name}
          </h4>
          {errors.title ? (
            <span role="alert" className="px-1 text-[0.8rem] text-owe">
              {captureMessages.errors[errors.title]}
            </span>
          ) : null}
        </div>
      </header>

      {/* MVP-OUT: the main ingredient and cuisine chip groups (S-061)
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
      */}

      <div className="flex flex-col gap-6 px-4 md:min-h-0 md:flex-1 md:flex-row">
        <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:max-w-[450px] md:flex-1 md:overflow-hidden">
          <div className="flex shrink-0 items-center justify-between gap-2">
            <h2 className="m-0 text-[1rem] font-[550] text-foreground">
              {captureMessages.ingredients}
            </h2>
            <div className="flex flex-col items-end gap-1">
              <label className="flex items-center gap-2 text-[0.85rem] text-muted">
                {captureMessages.servingsLabel}
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="w-20 rounded-[0.75rem] border border-border bg-background px-3 py-1 text-[1rem] text-foreground"
                  value={draft.baseServings}
                  onChange={(event) =>
                    update({
                      baseServings: Number(event.target.value),
                      servingsEstimated: false,
                    })
                  }
                />
              </label>
              {errors.servings ? (
                <span role="alert" className="text-[0.8rem] text-owe">
                  {captureMessages.errors[errors.servings]}
                </span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {draft.lines.map((line, index) => (
                <IngredientLineRow
                  key={line.key}
                  line={line}
                  index={index}
                  count={draft.lines.length}
                  errors={errors.lines[index] ?? []}
                  units={units}
                  sizes={sizes}
                  catalog={draft.catalog}
                  change={changesByLine.get(index)}
                  onUndoChange={undoChange}
                  onChange={(next) => updateLine(index, next)}
                  onRemove={() =>
                    update({ lines: draft.lines.filter((_, i) => i !== index) })
                  }
                  onMove={(direction) =>
                    update({ lines: moveItem(draft.lines, index, direction) })
                  }
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
                      textName: "",
                      match: { kind: "new", entry: null },
                    },
                  ],
                })
              }
            >
              {captureMessages.addIngredient}
            </button>
          </div>
        </section>

        <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-hidden">
          <h2 className="m-0 shrink-0 text-[1rem] font-[550] text-foreground">
            {captureMessages.steps}
          </h2>
          <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
            <ol className="m-0 flex list-none flex-col gap-2 p-0">
              {draft.steps.map((step, index) => (
                <StepCard
                  key={step.key}
                  index={index}
                  count={draft.steps.length}
                  text={step.text}
                  onChange={(text) =>
                    update({
                      steps: draft.steps.map((item, i) =>
                        i === index ? { ...item, text } : item,
                      ),
                    })
                  }
                  onRemove={() =>
                    update({ steps: draft.steps.filter((_, i) => i !== index) })
                  }
                  onMove={(direction) =>
                    update({ steps: moveItem(draft.steps, index, direction) })
                  }
                />
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
              onClick={() =>
                update({
                  steps: [...draft.steps, { key: nextKey(), text: "" }],
                })
              }
            >
              {captureMessages.addStep}
            </button>
          </div>
        </section>
      </div>

      {capture.message ? (
        <p role="alert" className="px-4 text-[0.9rem] text-owe">
          {messageForCode(capture.message)}
        </p>
      ) : null}

      <div className="flex items-center justify-end gap-4 px-4">
        <button
          type="button"
          onClick={discard}
          disabled={capture.saving}
          className="text-[0.95rem] text-owe disabled:opacity-50"
        >
          {captureMessages.discard}
        </button>
        <button
          type="button"
          onClick={() => void save()}
          disabled={capture.saving || hasErrors(errors)}
          className="rounded-[0.75rem] bg-accent px-4 py-2 text-[0.95rem] font-semibold text-on-accent disabled:opacity-50"
        >
          {capture.saving ? captureMessages.saving : captureMessages.save}
        </button>
      </div>
    </div>
  );
}
