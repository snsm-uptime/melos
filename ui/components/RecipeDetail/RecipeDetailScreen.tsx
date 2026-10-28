"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { safeReturnPath } from "@/lib/recipeReturnPath";
import { fetchRecipe, type RecipeDetail } from "@/lib/recipesClient";

import styles from "@/app/notebooks/notebooks.module.scss";

import { DeleteRecipeDialog } from "./DeleteRecipeDialog";
import { RecipeDetailView } from "./RecipeDetailView";

type State =
  | { status: "loading" }
  | { status: "ready"; recipe: RecipeDetail }
  | { status: "not_found" }
  | { status: "error" };

/** The recipe detail page body: loads the recipe, then shows it with its actions (spec 027). */
export function RecipeDetailScreen({ recipeId, locale }: { recipeId: string; locale: Locale }) {
  const t = recipeDetailMessages[locale];
  const router = useRouter();
  const from = useSearchParams().get("from");
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    let current = true;
    void fetchRecipe(recipeId).then((result) => {
      if (!current) return;
      if (result.ok) setState({ status: "ready", recipe: result.value });
      else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/recipes/${recipeId}`)}`);
      } else if (result.status === 404) setState({ status: "not_found" });
      else setState({ status: "error" });
    });
    return () => {
      current = false;
    };
  }, [recipeId, router, attempt]);

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
          {t.notAvailable}
        </p>
        <Link href={from && safeReturnPath(from, "x") === from ? from : "/notebooks"}>
          {t.goToNotebooks}
        </Link>
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

  const { recipe } = state;
  const backHref = safeReturnPath(from, recipe.notebook.id);
  const editHref = `/recipes/${encodeURIComponent(recipe.id)}/edit${
    from ? `?from=${encodeURIComponent(backHref)}` : ""
  }`;
  return (
    <>
      <RecipeDetailView
        recipe={recipe}
        locale={locale}
        backHref={backHref}
        editHref={editHref}
        onDelete={() => setConfirming(true)}
      />
      <DeleteRecipeDialog
        open={confirming}
        onOpenChange={setConfirming}
        recipeId={recipe.id}
        title={recipe.title}
        locale={locale}
        onDeleted={() => router.replace(backHref)}
      />
    </>
  );
}
