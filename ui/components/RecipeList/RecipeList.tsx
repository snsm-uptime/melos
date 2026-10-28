"use client";

import { useEffect, useState, type ReactNode } from "react";

import { AddRecipeCallToAction, type CaptureCandidate } from "@/components/AddRecipeCallToAction";
import { RecipeCard } from "@/components/RecipeCard/RecipeCard";
import { listAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { recipeListMessages } from "@/lib/i18n/recipeLists";
import type { NotebookResult } from "@/lib/notebooksClient";
import type { RecipePage } from "@/lib/recipesClient";

import styles from "@/app/notebooks/notebooks.module.scss";

const FILTER_PAUSE_MS = 300;
const FILTER_MAX_CHARS = 100;

type ListState =
  | { status: "loading" }
  | { status: "ready"; page: RecipePage }
  | { status: "not_found" }
  | { status: "error" };

type RecipeListProps = {
  scope: "notebook" | "kitchen";
  locale: Locale;
  /** Current page and filter text, read from the address by the screen. */
  page: number;
  q: string;
  /** Called when the member changes the page or the filter. The screen updates the address. */
  onChange: (page: number, q: string) => void;
  load: (page: number, q: string) => Promise<NotebookResult<RecipePage>>;
  /**
   * Capture choices for the add-recipe action, shown as the first card (or under the empty
   * text); omit to show none (archived kitchen).
   */
  addCandidates?: CaptureCandidate[];
  returnPath: string;
  /** Sits beside the filter (e.g. the add-recipe button). */
  filterAction?: ReactNode;
  /**
   * "columns" is the notebook layout (one column, two from 640px); "wrap" lays the cards in a
   * row that wraps with the window width.
   */
  layout?: "columns" | "wrap";
};

/** Cards in numbered pages with a text filter (spec 021 FR-003 to FR-009). */
export function RecipeList({
  scope,
  locale,
  page,
  q,
  onChange,
  load,
  addCandidates,
  returnPath,
  filterAction,
  layout = "columns",
}: RecipeListProps) {
  const t = recipeListMessages[locale];
  const [attempt, setAttempt] = useState(0);
  // The answer to one request. Loading is derived: no answer yet for the current request.
  const requestKey = `${page}|${q}|${attempt}`;
  const [answer, setAnswer] = useState<{ key: string; state: ListState } | null>(null);
  // Text typed since the address last matched; it is dropped when the address changes (Back).
  const [typed, setTyped] = useState<{ from: string; text: string } | null>(null);
  const text = typed && typed.from === q ? typed.text : q;
  const state: ListState = answer?.key === requestKey ? answer.state : { status: "loading" };

  // Apply the typed text after a pause; a new filter starts at page 1.
  useEffect(() => {
    if (text === q) return;
    const timer = setTimeout(() => onChange(1, text), FILTER_PAUSE_MS);
    return () => clearTimeout(timer);
  }, [text, q, onChange]);

  useEffect(() => {
    let current = true;
    void load(page, q).then((result) => {
      if (!current) return;
      const next: ListState = result.ok
        ? { status: "ready", page: result.value }
        : result.status === 404
          ? { status: "not_found" }
          : { status: "error" };
      setAnswer({ key: requestKey, state: next });
    });
    return () => {
      current = false;
    };
  }, [load, page, q, requestKey]);

  const filtering = q.trim().length > 0;
  const emptyText = scope === "kitchen" ? t.emptyKitchen : t.emptyNotebook;

  function clearFilter() {
    setTyped(null);
    onChange(1, "");
  }

  const filter = (
    <input
      type="search"
      value={text}
      maxLength={FILTER_MAX_CHARS}
      aria-label={t.filterLabel}
      placeholder={t.filterPlaceholder}
      onChange={(event) => setTyped({ from: q, text: event.target.value })}
      className="box-border w-full min-w-0 appearance-none rounded-[var(--radius-md)] border border-border bg-surface px-[var(--space-4)] py-[var(--space-3)] text-[1rem] leading-normal text-foreground placeholder:text-muted"
    />
  );

  return (
    <div className={styles.section}>
      {filterAction ? (
        <div className="flex min-w-0 items-stretch gap-[var(--space-2)]">
          <div className="min-w-0 flex-1">{filter}</div>
          {filterAction}
        </div>
      ) : (
        filter
      )}
      {state.status === "loading" ? (
        <p className={styles.copy} role="status">
          {t.loading}
        </p>
      ) : null}
      {state.status === "not_found" ? (
        <p className={styles.copy} role="alert">
          {scope === "kitchen" ? t.notFoundKitchen : t.notFoundNotebook}
        </p>
      ) : null}
      {state.status === "error" ? (
        <div className={styles.state}>
          <p className={styles.copy} role="alert">
            {t.loadError}
          </p>
          <button type="button" className={styles.retry} onClick={() => setAttempt((n) => n + 1)}>
            {t.retry}
          </button>
        </div>
      ) : null}
      {state.status === "ready" && state.page.items.length === 0 ? (
        filtering ? (
          <div className={styles.state}>
            <p className={styles.copy}>{t.noMatch(q.trim())}</p>
            <button type="button" className={styles.retry} onClick={clearFilter}>
              {t.clearFilter}
            </button>
          </div>
        ) : (
          <>
            <p className={styles.copy}>{emptyText}</p>
            {addCandidates && addCandidates.length > 0 ? (
              <AddRecipeCallToAction
                candidates={addCandidates}
                defaultId={addCandidates[0]?.id ?? null}
                returnPath={returnPath}
              />
            ) : null}
          </>
        )
      ) : null}
      {state.status === "ready" && state.page.items.length > 0 ? (
        <>
          <ul
            className={
              layout === "wrap"
                ? "m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(min(100%,18rem),1fr))] gap-[var(--space-2)] p-0"
                : styles.grid
            }
          >
            {addCandidates && addCandidates.length > 0 ? (
              <li>
                <AddRecipeCallToAction
                  candidates={addCandidates}
                  defaultId={addCandidates[0]?.id ?? null}
                  returnPath={returnPath}
                />
              </li>
            ) : null}
            {state.page.items.map((recipe) => (
              <li key={recipe.id}>
                <RecipeCard
                  recipe={recipe}
                  locale={locale}
                  showNotebook={scope === "kitchen"}
                  from={listAddress(returnPath, page, q)}
                />
              </li>
            ))}
          </ul>
          {state.page.total_pages > 1 ? (
            <Pager
              locale={locale}
              page={state.page.page}
              totalPages={state.page.total_pages}
              onGo={(next) => onChange(next, q)}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function Pager({
  locale,
  page,
  totalPages,
  onGo,
}: {
  locale: Locale;
  page: number;
  totalPages: number;
  onGo: (page: number) => void;
}) {
  const t = recipeListMessages[locale];
  const numbers = Array.from({ length: totalPages }, (_, index) => index + 1);
  return (
    <nav aria-label={t.pageOf(page, totalPages)} className="flex flex-wrap items-center gap-[var(--space-1)]">
      <button type="button" className={styles.retry} disabled={page <= 1} onClick={() => onGo(page - 1)}>
        {t.previous}
      </button>
      {numbers.map((number) => (
        <button
          key={number}
          type="button"
          className={styles.retry}
          aria-current={number === page ? "page" : undefined}
          aria-label={t.pageLabel(number)}
          onClick={() => onGo(number)}
        >
          {number}
        </button>
      ))}
      <button
        type="button"
        className={styles.retry}
        disabled={page >= totalPages}
        onClick={() => onGo(page + 1)}
      >
        {t.next}
      </button>
      <span className="text-[0.85rem] text-muted">{t.pageOf(page, totalPages)}</span>
    </nav>
  );
}
