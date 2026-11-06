"use client";

import { useEffect, useState } from "react";

import { ArrowIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import { SearchableSelect } from "@/components/SearchableSelect";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import {
  copyRecipeToKitchen,
  fetchPersonalNotebooks,
  type CopiedRecipe,
  type NotebookResponse,
  type RecipeCopyRepeat,
} from "@/lib/notebooksClient";
import { fetchNotebookRecipes, type RecipeCard } from "@/lib/recipesClient";

export type KitchenChoice = { id: string; name: string };

type RecipeFromNotebookSheetProps = {
  open: boolean;
  onClose: () => void;
  /**
   * The personal notebook the recipe comes from, when the add starts on that notebook's page.
   * Fixed then; without it (quick add, kitchen pages) the person picks one.
   */
  sourceNotebookId?: string | null;
  /** The open kitchen: used without asking (spec 069 FR-009). */
  kitchenId?: string | null;
  /** The name of `kitchenId`, shown instead of a choice. */
  kitchenName?: string | null;
  /** Outside a kitchen: the active kitchens to choose from; with one, it is preselected. */
  kitchens?: KitchenChoice[];
  onDone: (copied: CopiedRecipe, kitchenId: string) => void;
};

type Phase =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "repeat"; notebookName: string }
  | { kind: "error"; message: string };

type Notebooks =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; notebooks: NotebookResponse[] };

type Recipes =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; items: RecipeCard[] };

/** The longest a notebook is read in full for the select; a notebook is far smaller. */
const MAX_PAGES = 50;

/** Every recipe of a notebook, page by page, for the searchable select. */
async function fetchAllRecipes(
  notebookId: string,
): Promise<RecipeCard[] | null> {
  const items: RecipeCard[] = [];
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const result = await fetchNotebookRecipes(notebookId, page, "");
    if (!result.ok) return null;
    items.push(...result.value.items);
    if (page >= result.value.total_pages) break;
  }
  return items;
}

const fieldClassName =
  "w-full justify-between rounded-[0.75rem] border border-border bg-background px-3 py-2 text-left text-[0.95rem] text-foreground disabled:opacity-60";
const buttonClassName =
  "rounded-[0.75rem] px-4 py-2 text-[0.95rem] disabled:opacity-50";
const primaryClassName = `${buttonClassName} bg-primary text-on-primary`;
const secondaryClassName = `${buttonClassName} border border-border text-foreground`;

/**
 * "Recipe from another notebook" (spec 069), laid out as one row: original notebook, then the
 * recipe search select with a save icon, then the target kitchen. The original notebook is fixed
 * when the add starts on a personal notebook's page, so the recipes listed are that notebook's.
 * A second add of the same recipe asks: add another copy, overwrite the latest copy, or cancel.
 */
export function RecipeFromNotebookSheet({
  open,
  onClose,
  sourceNotebookId,
  kitchenId,
  kitchenName,
  kitchens,
  onDone,
}: RecipeFromNotebookSheetProps) {
  const t = useCaptureMessages();
  const [notebooksAnswer, setNotebooksAnswer] = useState<{
    key: number;
    value: Notebooks;
  } | null>(null);
  const [notebookId, setNotebookId] = useState<string | null>(
    sourceNotebookId ?? null,
  );
  const [recipesAnswer, setRecipesAnswer] = useState<{
    key: string;
    value: Recipes;
  } | null>(null);
  const [recipeId, setRecipeId] = useState<string | null>(null);
  const [chosenKitchen, setChosenKitchen] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [recipesAttempt, setRecipesAttempt] = useState(0);

  const sourceFixed = Boolean(sourceNotebookId);
  const notebooks: Notebooks =
    notebooksAnswer?.key === attempt
      ? notebooksAnswer.value
      : { status: "loading" };
  const recipesKey = `${notebookId}|${recipesAttempt}`;
  const recipes: Recipes =
    notebookId && recipesAnswer?.key === recipesKey
      ? recipesAnswer.value
      : { status: "loading" };

  const personal = notebooks.status === "ready" ? notebooks.notebooks : [];
  const source =
    personal.find((notebook) => notebook.id === notebookId) ?? null;
  const kitchenFixed = Boolean(kitchenId);
  const onlyKitchen =
    !kitchenFixed && kitchens && kitchens.length === 1 ? kitchens[0] : null;
  const targetKitchen = kitchenId ?? chosenKitchen ?? onlyKitchen?.id ?? null;
  const targetKitchenName = kitchenFixed
    ? (kitchenName ?? "")
    : (onlyKitchen?.name ?? "");
  const noRecipes =
    notebooks.status === "ready" &&
    personal.every((notebook) => notebook.recipe_count === 0);
  const submitting = phase.kind === "submitting";

  // The caller remounts the sheet each time it opens, so every open starts fresh.
  useEffect(() => {
    if (!open) return;
    let current = true;
    void fetchPersonalNotebooks().then((result) => {
      if (!current) return;
      if (!result.ok) {
        setNotebooksAnswer({ key: attempt, value: { status: "error" } });
        return;
      }
      // Every notebook the person can read: their personal ones and those of their kitchens.
      setNotebooksAnswer({
        key: attempt,
        value: { status: "ready", notebooks: result.value },
      });
    });
    return () => {
      current = false;
    };
  }, [open, attempt]);

  useEffect(() => {
    if (!open || !notebookId) return;
    let current = true;
    void fetchAllRecipes(notebookId).then((items) => {
      if (!current) return;
      setRecipesAnswer({
        key: `${notebookId}|${recipesAttempt}`,
        value: items ? { status: "ready", items } : { status: "error" },
      });
    });
    return () => {
      current = false;
    };
  }, [open, notebookId, recipesAttempt]);

  async function submit(onRepeat: RecipeCopyRepeat, chosen: string) {
    if (!targetKitchen) return;
    setRecipeId(chosen);
    setPhase({ kind: "submitting" });
    const result = await copyRecipeToKitchen(targetKitchen, chosen, onRepeat);
    if (result.ok) {
      setPhase({ kind: "idle" });
      onDone(result.value, targetKitchen);
      return;
    }
    if (result.code === "recipe_already_in_kitchen") {
      setPhase({ kind: "repeat", notebookName: result.notebookName ?? "" });
      return;
    }
    if (result.code === "recipe_not_found") {
      setRecipeId(null);
      setPhase({ kind: "error", message: t.fromNotebookGone });
      setRecipesAttempt((value) => value + 1);
      return;
    }
    if (result.code === "recipe_locked") {
      setPhase({
        kind: "error",
        message: t.fromNotebookLocked(result.editorAlias ?? "?"),
      });
      return;
    }
    if (result.code === "kitchen_archived") {
      setPhase({ kind: "error", message: t.archived });
      return;
    }
    if (result.code === "kitchen_not_found") {
      setPhase({ kind: "error", message: t.notFound });
      return;
    }
    setPhase({ kind: "error", message: t.fromNotebookFailed });
  }

  let body;
  if (notebooks.status === "loading") {
    body = <CauldronLoader label={t.fromNotebookLoading} size="4rem" />;
  } else if (notebooks.status === "error") {
    body = (
      <div className="flex flex-col gap-3">
        <p role="alert" className="m-0 text-[0.9rem] text-error">
          {t.fromNotebookLoadError}
        </p>
        <button
          type="button"
          className={secondaryClassName}
          onClick={() => setAttempt((v) => v + 1)}
        >
          {t.fromNotebookRetry}
        </button>
      </div>
    );
  } else if (noRecipes) {
    body = (
      <p className="m-0 text-[0.95rem] text-muted">{t.fromNotebookEmpty}</p>
    );
  } else {
    const recipeOptions =
      recipes.status === "ready"
        ? recipes.items.map((recipe) => ({
            value: recipe.id,
            label: recipe.title,
          }))
        : [];
    const recipePlaceholder = !notebookId
      ? t.fromNotebookChooseNotebook
      : recipes.status === "loading"
        ? t.fromNotebookLoading
        : t.fromNotebookChooseRecipe;
    const recipeSelectable = Boolean(notebookId) && recipes.status === "ready";
    const saveDisabled =
      !recipeId || !targetKitchen || submitting || phase.kind === "repeat";

    body = (
      <div className="flex w-full flex-col items-center gap-3">
        <label className="flex w-full flex-col gap-1 text-[0.85rem] text-muted">
          {t.fromNotebookOriginal}
          {sourceFixed || submitting ? (
            <span className={fieldClassName}>{source?.name ?? ""}</span>
          ) : (
            <SearchableSelect
              aria-label={t.fromNotebookOriginal}
              placeholder={t.fromNotebookChooseNotebook}
              searchLabel={t.fromNotebookSearch}
              noResults={t.fromNotebookNoMatch}
              className={fieldClassName}
              panelWidth={240}
              disabled={submitting}
              value={notebookId ?? ""}
              options={personal.map((notebook) => ({
                value: notebook.id,
                label: notebook.name,
              }))}
              onChange={(id) => {
                setNotebookId(id);
                setRecipeId(null);
                setPhase({ kind: "idle" });
              }}
            />
          )}
        </label>

        <ArrowIcon
          aria-hidden="true"
          className="size-4 -rotate-90 text-muted"
        />

        <div className="flex w-full flex-col gap-1 text-[0.85rem] text-muted">
          <span>{t.fromNotebookSearch}</span>
          {submitting && recipeId ? (
            <span className={fieldClassName}>
              {recipeOptions.find((option) => option.value === recipeId)?.label}
            </span>
          ) : (
            <SearchableSelect
              aria-label={t.fromNotebookSearch}
              placeholder={recipePlaceholder}
              searchLabel={t.fromNotebookSearch}
              noResults={t.fromNotebookNoMatch}
              className={fieldClassName}
              panelWidth={260}
              disabled={!recipeSelectable || submitting}
              value={recipeId ?? ""}
              options={recipeOptions}
              onChange={(id) => {
                setRecipeId(id);
                setPhase({ kind: "idle" });
              }}
            />
          )}
        </div>

        <ArrowIcon
          aria-hidden="true"
          className="size-4 -rotate-90 text-muted"
        />

        <div className="flex w-full flex-col gap-1 text-[0.85rem] text-muted">
          <span>{t.fromNotebookTarget}</span>
          {kitchenFixed || onlyKitchen || submitting ? (
            <span className={fieldClassName}>
              {kitchenFixed || onlyKitchen
                ? targetKitchenName
                : (kitchens ?? []).find((kitchen) => kitchen.id === chosenKitchen)?.name}
            </span>
          ) : (
            <SearchableSelect
              aria-label={t.fromNotebookTarget}
              placeholder={t.fromNotebookKitchen}
              searchLabel={t.fromNotebookKitchen}
              noResults={t.fromNotebookNoMatch}
              className={fieldClassName}
              panelWidth={240}
              disabled={submitting}
              value={chosenKitchen ?? ""}
              options={(kitchens ?? []).map((kitchen) => ({
                value: kitchen.id,
                label: kitchen.name,
              }))}
              onChange={(id) => {
                setChosenKitchen(id || null);
                setPhase({ kind: "idle" });
              }}
            />
          )}
        </div>

        {phase.kind === "repeat" ? null : (
          <button
            type="button"
            disabled={saveDisabled}
            className={`w-full ${primaryClassName}`}
            onClick={() => recipeId && void submit("ask", recipeId)}
          >
            {submitting ? t.fromNotebookAdding : t.fromNotebookSave}
          </button>
        )}

        {recipes.status === "error" ? (
          <p role="alert" className="m-0 text-[0.9rem] text-error">
            {t.fromNotebookLoadError}
          </p>
        ) : null}
        {phase.kind === "error" ? (
          <p role="alert" className="m-0 text-[0.9rem] text-error">
            {phase.message}
          </p>
        ) : null}
        {phase.kind === "repeat" ? (
          <div
            role="alert"
            className="flex flex-col gap-3 rounded-[0.75rem] border border-border p-3"
          >
            <p className="m-0 font-[550] text-foreground">{t.repeatTitle}</p>
            <p className="m-0 text-[0.9rem] text-muted">
              {t.repeatBody(phase.notebookName)}
            </p>
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className={secondaryClassName}
                onClick={() => setPhase({ kind: "idle" })}
              >
                {t.repeatCancel}
              </button>
              <button
                type="button"
                className={secondaryClassName}
                onClick={() => recipeId && void submit("overwrite", recipeId)}
              >
                {t.repeatOverwrite}
              </button>
              <button
                type="button"
                className={primaryClassName}
                onClick={() => recipeId && void submit("add", recipeId)}
              >
                {t.repeatAddAnother}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <ActionDialog
      open={open}
      title={t.optionFromNotebook}
      closeLabel={t.close}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      {body}
    </ActionDialog>
  );
}
