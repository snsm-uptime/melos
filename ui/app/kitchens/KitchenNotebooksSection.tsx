"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AddRecipeCallToAction } from "@/components/AddRecipeCallToAction";
import { useCartIdleToasts } from "@/components/Cart/useCartIdleToasts";
import { useToast } from "@/components/Toast";
import { RecipeList } from "@/components/RecipeList/RecipeList";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import {
  addDraftItem,
  cartRecipeIds,
  fetchCart,
  removeDraftItem,
  type Cart,
} from "@/lib/cartClient";
import { cartMessages } from "@/lib/i18n/cart";
import { listAddress, readListAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  fetchKitchenNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";
import { fetchKitchenRecipes } from "@/lib/recipesClient";

import styles from "../notebooks/notebooks.module.scss";

type KitchenNotebooksSectionProps = {
  kitchenId: string;
  /** An archived kitchen shows no add-recipe action (spec 016 FR-033). */
  isArchived: boolean;
  locale: Locale;
};

type SectionState =
  | { status: "loading" }
  | { status: "ready"; notebooks: NotebookResponse[] }
  | { status: "not_found" }
  | { status: "error" };

/**
 * A kitchen's recipes from all its notebooks: the filter with the add-recipe button beside it,
 * then the cards, each linking to its notebook. The notebooks are read for the capture picker.
 */
export function KitchenNotebooksSection({
  kitchenId,
  isArchived,
  locale,
}: KitchenNotebooksSectionProps) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const pathname = usePathname();
  const { page, q } = readListAddress(useSearchParams());
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const c = cartMessages[locale];
  // The cart is read once for the card checkboxes and the editing bar (spec 022 R12).
  const [cart, setCart] = useState<Cart | null>(null);
  const [cartAttempt, setCartAttempt] = useState(0);
  const loadCart = useCallback(() => setCartAttempt((n) => n + 1), []);

  useEffect(() => {
    let current = true;
    void fetchCart(kitchenId).then((result) => {
      if (current) setCart(result.ok ? result.value : null);
    });
    return () => {
      current = false;
    };
  }, [kitchenId, cartAttempt]);

  const toast = useToast();
  useCartIdleToasts(kitchenId, cart?.editor, locale, loadCart);
  const inCart = cart ? cartRecipeIds(cart) : null;
  // An archived kitchen's cart cannot change, so its cards get no button.
  const archivedCart = Boolean(cart && !cart.can_edit && !cart.editor);

  const cardCart = useCallback(
    (recipe: { id: string }) => {
      if (!cart || !inCart || archivedCart) return undefined;
      const added = inCart.has(recipe.id);
      return {
        inCart: added,
        // No message on success; a refusal while someone else edits is a toast (FR-017b).
        onToggle: () => {
          void (added ? removeDraftItem : addDraftItem)(kitchenId, recipe.id).then((result) => {
            if (result.ok) {
              setCart(result.value);
              return;
            }
            if (result.code === "cart_locked") {
              toast.show({ id: "cart-locked", text: c.editingCart(result.editorAlias ?? c.unknown) });
            }
            loadCart();
          });
        },
      };
    },
    [archivedCart, c, cart, inCart, kitchenId, loadCart, toast],
  );

  useEffect(() => {
    let current = true;

    function fail(error: NotebookError) {
      if (error.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/kitchens/${kitchenId}`)}`);
        return;
      }
      if (error.code === "kitchen_not_found") {
        setState({ status: "not_found" });
        return;
      }
      setState({ status: "error" });
    }

    async function load() {
      const result = await fetchKitchenNotebooks(kitchenId);
      if (!current) return;
      if (!result.ok) {
        fail(result);
        return;
      }
      setState({ status: "ready", notebooks: result.value });
    }

    void load();
    return () => {
      current = false;
    };
  }, [attempt, kitchenId, router]);

  const onListChange = useCallback(
    (nextPage: number, nextQ: string) => router.replace(listAddress(pathname, nextPage, nextQ)),
    [pathname, router],
  );
  const loadRecipes = useCallback(
    (nextPage: number, nextQ: string) => fetchKitchenRecipes(kitchenId, nextPage, nextQ),
    [kitchenId],
  );

  function retry() {
    // Drop the previous list before the reload, so no stale cards stay on screen.
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  return (
    <section className={styles.section}>
      <SavedNotice returnPath={`/kitchens/${kitchenId}`} />
      {state.status === "not_found" ? (
        <p className={styles.copy} role="alert">
          {t.detailNotFound}
        </p>
      ) : null}
      {state.status === "error" ? (
        <div className={styles.state}>
          <p className={styles.copy} role="alert">
            {t.loadError}
          </p>
          <button type="button" className={styles.retry} onClick={retry}>
            {t.retry}
          </button>
        </div>
      ) : null}
      {state.status === "ready" && state.notebooks.length === 0 ? (
        <p className={styles.copy}>{t.kitchenEmpty}</p>
      ) : null}
      {state.status === "ready" ? (
        <RecipeList
          scope="kitchen"
          locale={locale}
          page={page}
          q={q}
          onChange={onListChange}
          load={loadRecipes}
          returnPath={`/kitchens/${kitchenId}`}
          layout="wrap"
          cardCart={cardCart}
          filterAction={
            state.notebooks.length > 0 && !isArchived ? (
              <AddRecipeCallToAction
                variant="button"
                candidates={state.notebooks.map((notebook) => ({
                  id: notebook.id,
                  name: notebook.name,
                  kind: "kitchen",
                  kitchenId,
                }))}
                defaultId={state.notebooks[0]?.id ?? null}
                returnPath={`/kitchens/${kitchenId}`}
              />
            ) : undefined
          }
        />
      ) : null}
    </section>
  );
}
