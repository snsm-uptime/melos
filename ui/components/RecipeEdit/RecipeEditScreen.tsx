"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { EditorNotice } from "@/components/Cart/EditorNotice";
import { useLockKeepAlive } from "@/hooks/useLockKeepAlive";
import { cartMessages } from "@/lib/i18n/cart";

import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { safeReturnPath } from "@/lib/recipeReturnPath";
import {
  acquireRecipeLock,
  fetchRecipe,
  releaseRecipeLock,
  type RecipeDetail,
} from "@/lib/recipesClient";

import styles from "@/app/notebooks/notebooks.module.scss";

import { RecipeEditForm } from "./RecipeEditForm";

type State =
  | { status: "loading" }
  | { status: "ready"; recipe: RecipeDetail }
  | { status: "not_found" }
  | { status: "error" };

/** The recipe edit lock as this page holds it (spec 022 US4). */
type Lock =
  | { status: "pending" }
  | { status: "held"; idleExpiresAt: string | null }
  | { status: "refused"; alias: string | null }
  /** Lost while editing (idle limit, sign-out elsewhere): the typed edits stay. */
  | { status: "ended"; alias: string | null };

/**
 * The edit page body: loads the recipe, takes the edit lock, then shows the form if the member
 * may write (spec 027, spec 022 US4). The lock is freed on Cancel and on leaving the page (best
 * effort); typing keeps it alive, and a minute before the idle limit the page warns.
 */
export function RecipeEditScreen({ recipeId, locale }: { recipeId: string; locale: Locale }) {
  const t = recipeDetailMessages[locale];
  const c = cartMessages[locale];
  const [lock, setLock] = useState<Lock>({ status: "pending" });
  const saved = useRef(false);

  const applyLock = useCallback((result: Awaited<ReturnType<typeof acquireRecipeLock>>) => {
    if (result.ok) setLock({ status: "held", idleExpiresAt: result.value.idle_expires_at });
    else if (result.code === "recipe_locked") {
      setLock((now) =>
        now.status === "held" || now.status === "ended"
          ? { status: "ended", alias: result.editorAlias ?? null }
          : { status: "refused", alias: result.editorAlias ?? null },
      );
    } else setLock((now) => (now.status === "held" ? { status: "ended", alias: null } : now));
  }, []);
  const takeLock = useCallback(
    () => void acquireRecipeLock(recipeId).then(applyLock),
    [recipeId, applyLock],
  );

  const { notifyActivity, keepNow, warning, expired } = useLockKeepAlive({
    keepAlive: takeLock,
    idleExpiresAt: lock.status === "held" ? lock.idleExpiresAt : null,
  });
  const router = useRouter();
  const from = useSearchParams().get("from");
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    void fetchRecipe(recipeId).then((result) => {
      if (!current) return;
      if (result.ok) setState({ status: "ready", recipe: result.value });
      else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/recipes/${recipeId}/edit`)}`);
      } else if (result.status === 404) setState({ status: "not_found" });
      else setState({ status: "error" });
    });
    return () => {
      current = false;
    };
  }, [recipeId, router, attempt]);

  const canWrite = state.status === "ready" && state.recipe.can_write;
  useEffect(() => {
    if (!canWrite) return;
    saved.current = false;
    void acquireRecipeLock(recipeId).then(applyLock);
    const leave = () => {
      if (!saved.current) void releaseRecipeLock(recipeId, true);
    };
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      // Cancel, Back or any navigation away; a successful save was freed by the api.
      leave();
    };
  }, [canWrite, recipeId, applyLock]);

  // Past the idle limit the lock is gone, though no call said so yet.
  const ended: { alias: string | null } | null =
    lock.status === "ended" ? lock : lock.status === "held" && expired ? { alias: null } : null;

  const listHref = from && safeReturnPath(from, "x") === from ? from : "/notebooks";
  const detailBase = `/recipes/${encodeURIComponent(recipeId)}`;
  const detailHref = from ? `${detailBase}?from=${encodeURIComponent(listHref)}` : detailBase;

  if (state.status === "loading") {
    return (
      <main className={styles.main}>
        <p className={styles.copy} role="status">
          {t.loading}
        </p>
      </main>
    );
  }
  if (state.status === "not_found") {
    return (
      <main className={styles.main}>
        <p className={styles.copy} role="alert">
          {t.gone}
        </p>
        <Link href={listHref}>{t.goToNotebooks}</Link>
      </main>
    );
  }
  if (state.status === "error") {
    return (
      <main className={styles.main}>
        <div className={styles.state}>
          <p className={styles.copy} role="alert">
            {t.loadError}
          </p>
          <button
            type="button"
            className={styles.retry}
            onClick={() => {
              setState({ status: "loading" });
              setAttempt((n) => n + 1);
            }}
          >
            {t.retry}
          </button>
        </div>
      </main>
    );
  }
  if (!state.recipe.can_write) {
    return (
      <main className={styles.main}>
        <p className={styles.copy} role="alert">
          {t.readOnly}
        </p>
        <Link href={detailHref}>{t.back}</Link>
      </main>
    );
  }
  if (lock.status === "refused") {
    return (
      <main className={styles.main}>
        <EditorNotice alias={lock.alias} kind="recipe" locale={locale} />
        <Link href={detailHref}>{t.back}</Link>
      </main>
    );
  }
  return (
    <main
      className="mx-auto flex w-full flex-col gap-4 md:min-h-0 md:flex-1"
      // Typing or selecting is activity; an open page alone is not (spec 022 FR-020a).
      onInputCapture={notifyActivity}
      onChangeCapture={notifyActivity}
    >
      {lock.status === "held" && warning && !ended ? (
        <div role="status" className={LOCK_BAR}>
          <span className="min-w-0 flex-1">{c.recipeIdleWarning}</span>
          <button type="button" className={LOCK_ACTION} onClick={keepNow}>
            {c.keepEditing}
          </button>
        </div>
      ) : null}
      {ended ? (
        <div role="alert" className={LOCK_BAR}>
          <span className="min-w-0 flex-1">
            {ended.alias ? c.editingRecipe(ended.alias) : c.recipeEditEnded}
          </span>
          <button type="button" className={LOCK_ACTION} onClick={takeLock}>
            {c.startNewEdit}
          </button>
        </div>
      ) : null}
      <RecipeEditForm
        key={state.recipe.version}
        recipe={state.recipe}
        locale={locale}
        detailHref={detailHref}
        listHref={listHref}
        onReload={() => {
          setState({ status: "loading" });
          setAttempt((n) => n + 1);
        }}
        onLockLost={(alias) => setLock({ status: "ended", alias })}
        onSaved={() => {
          saved.current = true;
        }}
      />
    </main>
  );
}

const LOCK_BAR =
  "mx-4 flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-accent bg-surface px-3 py-2 text-[0.9rem] text-foreground";
const LOCK_ACTION =
  "rounded-[var(--radius-md)] border border-border bg-background px-3 py-1 text-[0.85rem] text-foreground hover:border-accent";
