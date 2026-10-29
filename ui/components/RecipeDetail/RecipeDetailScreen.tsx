"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useCartIdleToasts } from "@/components/Cart/useCartIdleToasts";
import { useToast } from "@/components/Toast";
import { addDraftItem, cartRecipeIds, removeDraftItem } from "@/lib/cartClient";
import { cartMessages } from "@/lib/i18n/cart";
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
  const c = cartMessages[locale];
  const toast = useToast();
  const ready = state.status === "ready" ? state.recipe : null;
  useCartIdleToasts(ready?.notebook.kitchen_id ?? null, ready?.cart_editor, locale, () =>
    setAttempt((n) => n + 1),
  );

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
  const kitchenId = recipe.notebook.kitchen_id;

  // Add to / Remove from cart goes through my draft, as the card checkbox does (spec 022 R7).
  function toggleCart() {
    if (!kitchenId) return;
    const call = recipe.in_cart ? removeDraftItem : addDraftItem;
    void call(kitchenId, recipe.id).then((result) => {
      if (!result.ok) {
        if (result.code === "cart_locked") {
          toast.show({ id: "cart-locked", text: c.editingCart(result.editorAlias ?? c.unknown) });
        }
        setAttempt((n) => n + 1);
        return;
      }
      setState({
        status: "ready",
        recipe: {
          ...recipe,
          in_cart: cartRecipeIds(result.value).has(recipe.id),
          cart_editor: result.value.editor,
        },
      });
    });
  }
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
        cartAction={
          // Only kitchen recipes carry the cart fields; no message on success (FR-017a).
          kitchenId && typeof recipe.in_cart === "boolean"
            ? { inCart: recipe.in_cart, onToggle: toggleCart }
            : undefined
        }
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
