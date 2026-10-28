"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { safeReturnPath } from "@/lib/recipeReturnPath";
import { fetchRecipe, type RecipeDetail } from "@/lib/recipesClient";

import styles from "@/app/notebooks/notebooks.module.scss";

import { RecipeEditForm } from "./RecipeEditForm";

type State =
  | { status: "loading" }
  | { status: "ready"; recipe: RecipeDetail }
  | { status: "not_found" }
  | { status: "error" };

/** The edit page body: loads the recipe, then shows the form if the member may write (spec 027). */
export function RecipeEditScreen({ recipeId, locale }: { recipeId: string; locale: Locale }) {
  const t = recipeDetailMessages[locale];
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
  return (
    <main className="mx-auto flex w-full flex-col gap-4 md:min-h-0 md:flex-1">
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
      />
    </main>
  );
}
