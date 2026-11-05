"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AddRecipeCallToAction, type CaptureCandidate } from "@/components/AddRecipeCallToAction";
import { CauldronLoader } from "@/components/CauldronLoader";
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
import { OWN_NEW_NOTEBOOK_ID } from "@/lib/capture/captureStore";
import { cartMessages } from "@/lib/i18n/cart";
import { usePublishKitchenCartCount } from "./cartCount";
import { listAddress, readListAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  fetchKitchenNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";
import { fetchKitchenRecipes, type RecipePage } from "@/lib/recipesClient";

import styles from "../notebooks/notebooks.module.scss";

type KitchenNotebooksSectionProps = {
  kitchenId: string;
  /** An archived kitchen shows no add-recipe action (spec 016 FR-033). */
  isArchived: boolean;
  locale: Locale;
  /**
   * What the server read while the route's loader was up, so the first paint is the finished list
   * with no second loader. Each is omitted if its read failed. The reads below still run: they
   * refresh this data, which a Back navigation restores from the router cache as it was.
   */
  initialNotebooks?: NotebookResponse[];
  initialRecipes?: RecipePage;
  initialCart?: Cart;
};

type SectionState =
  | { status: "loading" }
  | { status: "ready"; notebooks: NotebookResponse[] }
  | { status: "not_found" }
  | { status: "error" };

/**
 * A kitchen's recipes from all its notebooks: the filter with the add-recipe button beside it,
 * then the cards, each linking to its notebook; an empty kitchen shows the plus square instead.
 * The notebooks are read for the capture picker.
 */
export function KitchenNotebooksSection({
  kitchenId,
  isArchived,
  locale,
  initialNotebooks,
  initialRecipes,
  initialCart,
}: KitchenNotebooksSectionProps) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const pathname = usePathname();
  const { page, q } = readListAddress(useSearchParams());
  const [attempt, setAttempt] = useState(0);
  // Moves after a recipe is copied in (spec 069), so the list and the notebooks are read again.
  const [listVersion, setListVersion] = useState(0);
  const [state, setState] = useState<SectionState>(
    initialNotebooks ? { status: "ready", notebooks: initialNotebooks } : { status: "loading" },
  );
  const c = cartMessages[locale];
  // The cart is read once for the card checkboxes and the editing bar (spec 022 R12).
  const [cart, setCart] = useState<Cart | null>(initialCart ?? null);
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
  // The header's cart button shows this count on its badge.
  usePublishKitchenCartCount(inCart ? inCart.size : null);
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
    // listVersion is not read: a new value makes a new function, which RecipeList reloads on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [kitchenId, listVersion],
  );

  function retry() {
    // Drop the previous list before the reload, so no stale cards stay on screen.
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  // Captures default to the member's own notebook, never to whichever notebook is first. Someone
  // with none yet is offered a new one, made when they submit (spec 035 FR-017, research R6).
  const notebooks = state.status === "ready" ? state.notebooks : [];
  const ownNotebook = notebooks.find((notebook) => notebook.is_own_capture_notebook);
  const candidates: CaptureCandidate[] = notebooks.map((notebook) => ({
    id: notebook.id,
    name: notebook.name,
    kind: "kitchen",
    kitchenId,
  }));
  if (!ownNotebook) {
    candidates.unshift({
      id: OWN_NEW_NOTEBOOK_ID,
      name: t.ownNotebookNew,
      kind: "kitchen",
      kitchenId,
    });
  }

  const canAdd = notebooks.length > 0 && !isArchived;
  const addProps = {
    candidates,
    defaultId: ownNotebook?.id ?? OWN_NEW_NOTEBOOK_ID,
    returnPath: `/kitchens/${kitchenId}`,
    // "Recipe from another notebook" targets this kitchen (spec 069 FR-003, FR-009).
    fromNotebook: {
      kitchenId,
      onCopied: () => {
        setListVersion((value) => value + 1);
        setAttempt((value) => value + 1);
      },
    },
  };

  return (
    <section className={`${styles.section} flex-1`}>
      <SavedNotice returnPath={`/kitchens/${kitchenId}`} />
      {state.status === "loading" ? <CauldronLoader label={t.loading} /> : null}
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
          initialPage={initialRecipes}
          filterAction={canAdd ? <AddRecipeCallToAction variant="button" {...addProps} /> : undefined}
          emptyAction={canAdd ? <AddRecipeCallToAction {...addProps} /> : undefined}
        />
      ) : null}
    </section>
  );
}
