"use client";

import { useEffect, useId, useState } from "react";

import { Sheet } from "@/app/kitchens/Sheet";
import { CauldronLoader } from "@/components/CauldronLoader";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import {
  copyRecipeToKitchen,
  fetchPersonalNotebooks,
  type CopiedRecipe,
  type NotebookResponse,
  type RecipeCopyRepeat,
} from "@/lib/notebooksClient";
import { fetchNotebookRecipes, type RecipePage } from "@/lib/recipesClient";

export type KitchenChoice = { id: string; name: string };

type RecipeFromNotebookSheetProps = {
  open: boolean;
  onClose: () => void;
  /** The open kitchen: used without asking (spec 069 FR-009). */
  kitchenId?: string | null;
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

type Recipes = { status: "loading" } | { status: "error" } | { status: "ready"; page: RecipePage };

const fieldClassName =
  "w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[0.95rem] text-foreground";
const buttonClassName =
  "rounded-[0.75rem] px-4 py-2 text-[0.95rem] disabled:opacity-50";
const primaryClassName = `${buttonClassName} bg-accent text-background`;
const secondaryClassName = `${buttonClassName} border border-border text-foreground`;

/**
 * "Recipe from another notebook" (spec 069): pick one of my personal notebooks, then one of its
 * recipes, and copy it into my own notebook of the kitchen. A second add of the same recipe asks:
 * add another copy, overwrite the latest copy, or cancel.
 */
export function RecipeFromNotebookSheet({
  open,
  onClose,
  kitchenId,
  kitchens,
  onDone,
}: RecipeFromNotebookSheetProps) {
  const t = useCaptureMessages();
  const listName = useId();
  // Each answer keeps the request it answers, so a newer request reads as loading (no reset).
  const [notebooksAnswer, setNotebooksAnswer] = useState<{ key: number; value: Notebooks } | null>(
    null,
  );
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [recipesAnswer, setRecipesAnswer] = useState<{ key: string; value: Recipes } | null>(null);
  const [recipeId, setRecipeId] = useState<string | null>(null);
  const [chosenKitchen, setChosenKitchen] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [recipesAttempt, setRecipesAttempt] = useState(0);
  const notebooks: Notebooks =
    notebooksAnswer?.key === attempt ? notebooksAnswer.value : { status: "loading" };
  const recipesKey = `${notebookId}|${page}|${q}|${recipesAttempt}`;
  const recipes: Recipes =
    recipesAnswer?.key === recipesKey ? recipesAnswer.value : { status: "loading" };

  const targetKitchen =
    kitchenId ?? chosenKitchen ?? (kitchens && kitchens.length === 1 ? kitchens[0].id : null);

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
      const personal = result.value.filter((notebook) => notebook.kind === "personal");
      setNotebooksAnswer({ key: attempt, value: { status: "ready", notebooks: personal } });
      const first =
        personal.find((notebook) => notebook.is_default && notebook.recipe_count > 0) ??
        personal.find((notebook) => notebook.recipe_count > 0) ??
        personal[0];
      setNotebookId(first?.id ?? null);
    });
    return () => {
      current = false;
    };
  }, [open, attempt]);

  useEffect(() => {
    if (!open || !notebookId) return;
    let current = true;
    void fetchNotebookRecipes(notebookId, page, q).then((result) => {
      if (!current) return;
      setRecipesAnswer({
        key: recipesKey,
        value: result.ok ? { status: "ready", page: result.value } : { status: "error" },
      });
    });
    return () => {
      current = false;
    };
  }, [open, notebookId, page, q, recipesKey]);

  const personal = notebooks.status === "ready" ? notebooks.notebooks : [];
  const noRecipes =
    notebooks.status === "ready" && personal.every((notebook) => notebook.recipe_count === 0);
  const submitting = phase.kind === "submitting";
  const canConfirm = Boolean(recipeId && targetKitchen) && !submitting && phase.kind !== "repeat";

  async function submit(onRepeat: RecipeCopyRepeat) {
    if (!recipeId || !targetKitchen) return;
    setPhase({ kind: "submitting" });
    const result = await copyRecipeToKitchen(targetKitchen, recipeId, onRepeat);
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
      setPhase({ kind: "error", message: t.fromNotebookLocked(result.editorAlias ?? "?") });
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

  function recipeList() {
    if (recipes.status === "loading") return <CauldronLoader label={t.fromNotebookLoading} size="4rem" />;
    if (recipes.status === "error") {
      return (
        <p role="alert" className="m-0 text-[0.9rem] text-error">
          {t.fromNotebookLoadError}
        </p>
      );
    }
    const { items, total_pages: totalPages } = recipes.page;
    if (items.length === 0) {
      return <p className="m-0 text-[0.9rem] text-muted">{t.fromNotebookNoMatch}</p>;
    }
    return (
      <>
        <ul role="radiogroup" aria-label={t.fromNotebookSearch} className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {items.map((recipe) => (
            <li key={recipe.id}>
              <label className="flex cursor-pointer items-center gap-3 py-2 text-[0.95rem] text-foreground">
                <input
                  type="radio"
                  name={listName}
                  value={recipe.id}
                  checked={recipeId === recipe.id}
                  disabled={submitting}
                  onChange={() => {
                    setRecipeId(recipe.id);
                    setPhase({ kind: "idle" });
                  }}
                />
                <span className="min-w-0 flex-1 truncate">{recipe.title}</span>
              </label>
            </li>
          ))}
        </ul>
        {totalPages > 1 ? (
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              className={secondaryClassName}
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
            >
              {t.fromNotebookPrevious}
            </button>
            <span className="text-[0.85rem] text-muted">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              className={secondaryClassName}
              disabled={page >= totalPages}
              onClick={() => setPage((value) => value + 1)}
            >
              {t.fromNotebookNext}
            </button>
          </div>
        ) : null}
      </>
    );
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
        <button type="button" className={secondaryClassName} onClick={() => setAttempt((v) => v + 1)}>
          {t.fromNotebookRetry}
        </button>
      </div>
    );
  } else if (noRecipes) {
    body = <p className="m-0 text-[0.95rem] text-muted">{t.fromNotebookEmpty}</p>;
  } else {
    body = (
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (canConfirm) void submit("ask");
        }}
      >
        {!kitchenId && kitchens && kitchens.length > 1 ? (
          <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
            {t.fromNotebookKitchen}
            <select
              className={fieldClassName}
              value={chosenKitchen ?? ""}
              disabled={submitting}
              required
              onChange={(event) => {
                setChosenKitchen(event.target.value || null);
                setPhase({ kind: "idle" });
              }}
            >
              <option value="" disabled>
                {t.fromNotebookKitchen}
              </option>
              {kitchens.map((kitchen) => (
                <option key={kitchen.id} value={kitchen.id}>
                  {kitchen.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {personal.length > 1 ? (
          <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
            {t.notebookPicker}
            <select
              className={fieldClassName}
              value={notebookId ?? ""}
              disabled={submitting}
              onChange={(event) => {
                setNotebookId(event.target.value);
                setRecipeId(null);
                setPage(1);
                setPhase({ kind: "idle" });
              }}
            >
              {personal.map((notebook) => (
                <option key={notebook.id} value={notebook.id}>
                  {notebook.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
          {t.fromNotebookSearch}
          <input
            type="search"
            className={fieldClassName}
            value={q}
            disabled={submitting}
            onChange={(event) => {
              setQ(event.target.value);
              setPage(1);
            }}
          />
        </label>
        {recipeList()}
        {phase.kind === "error" ? (
          <p role="alert" className="m-0 text-[0.9rem] text-error">
            {phase.message}
          </p>
        ) : null}
        {phase.kind === "repeat" ? (
          <div role="alert" className="flex flex-col gap-3 rounded-[0.75rem] border border-border p-3">
            <p className="m-0 font-[550] text-foreground">{t.repeatTitle}</p>
            <p className="m-0 text-[0.9rem] text-muted">{t.repeatBody(phase.notebookName)}</p>
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className={secondaryClassName}
                onClick={() => setPhase({ kind: "idle" })}
              >
                {t.repeatCancel}
              </button>
              <button type="button" className={secondaryClassName} onClick={() => void submit("overwrite")}>
                {t.repeatOverwrite}
              </button>
              <button type="button" className={primaryClassName} onClick={() => void submit("add")}>
                {t.repeatAddAnother}
              </button>
            </div>
          </div>
        ) : (
          <button type="submit" disabled={!canConfirm} className={`self-end ${primaryClassName}`}>
            {submitting ? t.fromNotebookAdding : t.fromNotebookConfirm}
          </button>
        )}
      </form>
    );
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      closeLabel={t.close}
      title={t.optionFromNotebook}
      body={body}
    />
  );
}
