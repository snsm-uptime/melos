"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { BackIcon, CloseIcon, SaveIcon, SpinnerIcon } from "@/app/icons";
import {
  HeaderAction,
  HeaderActions,
} from "@/components/RecipeDraft/HeaderActions";
import { IngredientLineRow } from "@/components/RecipeDraft/IngredientLineRow";
import { AddItemCard } from "@/components/Card";
import { StepCard } from "@/components/RecipeDraft/StepCard";
import { chooseLineMatch } from "@/lib/capture/captureStore";
import {
  ALLOWED_UNITS,
  checkDraft,
  hasErrors,
  SIZES,
} from "@/lib/capture/draftRules";
import { captureMessagesFor } from "@/lib/i18n/capture";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages, saveProblemText } from "@/lib/i18n/recipeDetail";
import { nameChanges } from "@/lib/capture/nameChanges";
import {
  applyLineChange,
  applyMatches,
  catalogOf,
  isEdited,
  moveItem,
  newLine,
  nextKey,
  pendingChecks,
  toEditState,
  toUpdateBody,
  type EditState,
} from "@/lib/recipeEdit";
import {
  matchRecipeNames,
  updateRecipe,
  type RecipeDetail,
} from "@/lib/recipesClient";

import { RecipeEditLeaveGuard } from "./RecipeEditLeaveGuard";

type Message =
  | { kind: "problem"; text: string }
  | { kind: "changed" }
  | { kind: "gone" }
  | { kind: "readonly" }
  | { kind: "failed" };

type RecipeEditFormProps = {
  recipe: RecipeDetail;
  locale: Locale;
  /** The detail page, where Cancel, Back and a successful Save go. */
  detailHref: string;
  /** Where the member goes when the recipe no longer exists. */
  listHref: string;
  /** Loads the latest version of the recipe and restarts the form from it. */
  onReload: () => void;
};

/**
 * The recipe edit form (spec 027 US2). The rows are the draft editor's, so an ingredient reads
 * and works the same in both places. Names the member types are checked against the notebook's
 * catalog when the field is left; each proposed change is listed with Undo before anything is
 * saved (FR-009).
 */
export function RecipeEditForm({
  recipe,
  locale,
  detailHref,
  listHref,
  onReload,
}: RecipeEditFormProps) {
  const t = recipeDetailMessages[locale];
  const c = captureMessagesFor(locale);
  const router = useRouter();
  const [state, setState] = useState<EditState>(() => toEditState(recipe));
  const stateRef = useRef(state);
  const checkedRef = useRef(new Map<string, string>());
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState<Message | null>(null);

  function commit(next: EditState) {
    stateRef.current = next;
    setState(next);
  }

  const errors = checkDraft({
    title: state.title,
    baseServings: state.baseServings,
    lines: state.lines,
    steps: state.steps,
  });
  const changesByLine = new Map(
    nameChanges(state.lines).map((change) => [change.line, change]),
  );
  const edited = !saved && isEdited(state, recipe);

  /** Check the typed names that were not checked yet; returns how many lines were changed. */
  async function runNameCheck(): Promise<number> {
    const pending = pendingChecks(stateRef.current.lines, checkedRef.current);
    if (pending.length === 0) return 0;
    const sent = new Map(pending.map((line) => [line.key, line.name]));
    setChecking(true);
    const result = await matchRecipeNames(recipe.id, [
      ...new Set(sent.values()),
    ]);
    setChecking(false);
    for (const [key, name] of sent) checkedRef.current.set(key, name);
    // A failed check is only a missed help: the save still checks the recipe on the server.
    if (!result.ok) return 0;
    const current = stateRef.current.lines;
    const next = applyMatches(current, sent, result.value);
    const changed = next.filter(
      (line, index) => line !== current[index],
    ).length;
    if (changed > 0) commit({ ...stateRef.current, lines: next });
    return changed;
  }

  async function save() {
    if (saving) return;
    setSaving(true);
    setMessage(null);
    // Proposals found now are shown first; the member presses Save again to accept or undo them.
    if ((await runNameCheck()) > 0) {
      setSaving(false);
      return;
    }
    const result = await updateRecipe(
      recipe.id,
      toUpdateBody(stateRef.current, recipe.version),
    );
    setSaving(false);
    if (result.ok) {
      setSaved(true);
      router.push(detailHref);
      return;
    }
    if (result.status === 409) setMessage({ kind: "changed" });
    else if (result.status === 404) setMessage({ kind: "gone" });
    else if (result.status === 403) setMessage({ kind: "readonly" });
    else if (result.status === 422) {
      setMessage({
        kind: "problem",
        text: saveProblemText(t, result.missing, result.lineProblems),
      });
    } else setMessage({ kind: "failed" });
  }

  const messageText = (() => {
    switch (message?.kind) {
      case "problem":
        return message.text;
      case "changed":
        return t.changed;
      case "gone":
        return t.gone;
      case "readonly":
        return t.readOnly;
      case "failed":
        return t.saveFailed;
      default:
        return null;
    }
  })();

  return (
    <div className="flex flex-col gap-6 pb-8 md:min-h-0 md:flex-1">
      {/* Same insets and Back slot as the draft page and AppShell's chrome header. */}
      <header className="flex items-center gap-2 bg-background pt-[max(0.5rem,env(safe-area-inset-top))] max-md:sticky max-md:top-0 max-md:z-10 pr-[max(1rem,env(safe-area-inset-right))] pb-1 pl-[max(0.5rem,env(safe-area-inset-left))]">
        <div className="flex w-10 shrink-0 items-center justify-start self-center">
          <Link
            href={detailHref}
            aria-label={t.back}
            title={t.back}
            className="m-0 inline-flex flex-shrink-0 items-center justify-center rounded-[8px] border-0 bg-transparent p-1 leading-none text-muted transition-all duration-150 hover:text-foreground"
          >
            <BackIcon className="size-6" />
          </Link>
        </div>
        <div className="flex min-w-0 flex-auto flex-col">
          <h1 className="m-0 min-w-0">
            <textarea
              aria-label={t.titleLabel}
              placeholder={t.titleLabel}
              rows={1}
              // A title is one line of text that wraps: Enter does not add a line break.
              onKeyDown={(event) => {
                if (event.key === "Enter") event.preventDefault();
              }}
              className="block max-w-full min-w-0 field-sizing-content resize-none rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-[1.5rem] font-[550] leading-normal text-foreground outline-none hover:bg-background focus:bg-background"
              value={state.title}
              onChange={(event) =>
                commit({ ...state, title: event.target.value })
              }
            />
          </h1>
          <h4 className="m-0 px-1 text-[0.9rem] font-normal text-muted">
            {recipe.notebook.name}
          </h4>
          {errors.title ? (
            <span role="alert" className="px-1 text-[0.8rem] text-owe">
              {c.errors[errors.title]}
            </span>
          ) : null}
        </div>
        <HeaderActions>
          <HeaderAction
            onClick={() => void save()}
            disabled={saving || hasErrors(errors)}
            label={saving ? t.saving : t.save}
            tone="accent"
            icon={
              saving ? (
                <SpinnerIcon className="size-5 animate-spin" />
              ) : (
                <SaveIcon className="size-5" />
              )
            }
          />
          <HeaderAction
            href={detailHref}
            label={t.cancel}
            icon={<CloseIcon className="size-5" />}
          />
        </HeaderActions>
      </header>

      <div className="flex flex-col gap-6 px-4 md:min-h-0 md:flex-1 md:flex-row">
        <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:max-w-[450px] md:flex-1 md:overflow-hidden">
          <div className="flex shrink-0 items-center justify-between gap-2">
            <h2 className="m-0 text-[1rem] font-[550] text-foreground">
              {t.ingredientsTitle}
            </h2>
            <div className="flex flex-col items-end gap-1">
              <label className="flex items-center gap-2 text-[0.85rem] text-muted">
                {t.servingsLabel}
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="w-20 rounded-[0.75rem] border border-border bg-background px-3 py-1 text-[1rem] text-foreground"
                  value={state.baseServings}
                  onChange={(event) =>
                    commit({
                      ...state,
                      baseServings: Number(event.target.value),
                      servingsEstimated: false,
                    })
                  }
                />
              </label>
              {errors.servings ? (
                <span role="alert" className="text-[0.8rem] text-owe">
                  {c.errors[errors.servings]}
                </span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
            {/* Leaving a name field checks the names typed so far (focusout bubbles to the list). */}
            <ul
              className="m-0 flex list-none flex-col gap-2 p-0"
              onBlur={(event) => {
                if (
                  (event.target as HTMLElement).getAttribute("aria-label") ===
                  c.ingredientName
                ) {
                  void runNameCheck();
                }
              }}
            >
              {state.lines.map((line, index) => (
                <IngredientLineRow
                  key={line.key}
                  locale={locale}
                  line={line}
                  index={index}
                  count={state.lines.length}
                  errors={errors.lines[index] ?? []}
                  units={[...ALLOWED_UNITS]}
                  sizes={[...SIZES]}
                  catalog={catalogOf(state.lines)}
                  change={changesByLine.get(index)}
                  onUndoChange={(at) =>
                    commit({
                      ...state,
                      lines: state.lines.map((item, i) =>
                        i === at ? chooseLineMatch(item, "__new__") : item,
                      ),
                    })
                  }
                  onChange={(next) =>
                    commit({
                      ...state,
                      lines: state.lines.map((item, i) =>
                        i === index ? applyLineChange(item, next) : item,
                      ),
                    })
                  }
                  onRemove={() =>
                    commit({
                      ...state,
                      lines: state.lines.filter((_, i) => i !== index),
                    })
                  }
                  onMove={(direction) =>
                    commit({
                      ...state,
                      lines: moveItem(state.lines, index, direction),
                    })
                  }
                />
              ))}
            </ul>
            <AddItemCard
              label={c.addIngredient}
              className="min-h-14"
              onClick={() =>
                commit({ ...state, lines: [...state.lines, newLine()] })
              }
            />
          </div>
        </section>

        <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-hidden">
          <h2 className="m-0 shrink-0 text-[1rem] font-[550] text-foreground">
            {t.stepsTitle}
          </h2>
          <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
            <ol className="m-0 flex list-none flex-col p-0">
              {state.steps.map((step, index) => (
                <StepCard
                  key={step.key}
                  locale={locale}
                  index={index}
                  count={state.steps.length}
                  text={step.text}
                  onChange={(text) =>
                    commit({
                      ...state,
                      steps: state.steps.map((item, i) =>
                        i === index ? { ...item, text } : item,
                      ),
                    })
                  }
                  onRemove={() =>
                    commit({
                      ...state,
                      steps: state.steps.filter((_, i) => i !== index),
                    })
                  }
                  onMove={(direction) =>
                    commit({
                      ...state,
                      steps: moveItem(state.steps, index, direction),
                    })
                  }
                />
              ))}
            </ol>
            {errors.steps ? (
              <span role="alert" className="text-[0.8rem] text-owe">
                {c.errors[errors.steps]}
              </span>
            ) : null}
            <AddItemCard
              label={c.addStep}
              className="min-h-14"
              onClick={() =>
                commit({
                  ...state,
                  steps: [
                    ...state.steps,
                    { key: nextKey("edit-step"), text: "" },
                  ],
                })
              }
            />
          </div>
        </section>
      </div>

      {checking ? (
        <p className="m-0 px-4 text-[0.85rem] text-muted" role="status">
          {t.checkingNames}
        </p>
      ) : null}
      {messageText ? (
        <div className="flex flex-col items-start gap-2 px-4">
          <p className="m-0 text-[0.9rem] text-owe" role="alert">
            {messageText}
          </p>
          {message?.kind === "changed" ? (
            <button
              type="button"
              className="rounded-[0.75rem] border border-border px-3 py-1 text-foreground"
              onClick={onReload}
            >
              {t.reload}
            </button>
          ) : null}
          {message?.kind === "gone" ? (
            <Link href={listHref}>{t.goToNotebooks}</Link>
          ) : null}
        </div>
      ) : null}

      <RecipeEditLeaveGuard edited={edited} locale={locale} />
    </div>
  );
}
