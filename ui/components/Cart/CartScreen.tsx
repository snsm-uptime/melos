"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useChromeHeader } from "@/components/ChromeBack";
import { useToastDock } from "@/components/Toast";

import {
  discardCart,
  fetchCart,
  putCartDraft,
  saveCart,
  startCartEdit,
  type Cart,
  type CartFailure,
} from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

import styles from "@/app/notebooks/notebooks.module.scss";

import { ShoppingListSection } from "@/components/ShoppingList";

import { CartEditingBar } from "./CartEditingBar";
import { CartView, draftFromCart, type LocalDraft } from "./CartView";

/** How long after the last change the whole draft is sent (one PUT per pause). */
export const DRAFT_DEBOUNCE_MS = 300;

type State =
  | { status: "loading" }
  | { status: "ready"; cart: Cart }
  | { status: "not_found" }
  | { status: "error" };

function body(draft: LocalDraft) {
  return {
    people: draft.peopleIsDefault ? null : draft.people,
    items: draft.entries.map((entry) => ({ recipe_id: entry.recipe_id, meals: entry.meals })),
  };
}

/**
 * The Cart page (spec 022): loads the cart, refreshes on focus so other members' saves and
 * lock changes show without a reload, and drives the editing view. A lost lock (sign-out
 * elsewhere, idle limit) says the changes were discarded and shows the saved cart again.
 */
export function CartScreen({ kitchenId, locale }: { kitchenId: string; locale: Locale }) {
  const t = cartMessages[locale];
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });
  const [draft, setDraft] = useState<LocalDraft | null>(null);
  const [dropped, setDropped] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queued = useRef<LocalDraft | null>(null);
  useChromeHeader({ backHref: `/kitchens/${encodeURIComponent(kitchenId)}`, title: t.cart });

  const show = useCallback((cart: Cart, keepDraft = false) => {
    setState({ status: "ready", cart });
    if (!keepDraft) setDraft(draftFromCart(cart));
  }, []);

  const load = useCallback(async () => {
    const result = await fetchCart(kitchenId);
    if (result.ok) {
      // A change waiting to be sent stays on screen.
      show(result.value, queued.current !== null);
      return;
    }
    if (result.code === "alias_required") {
      router.replace(`/alias?returnTo=${encodeURIComponent(`/kitchens/${kitchenId}/cart`)}`);
    } else if (result.status === 404) setState({ status: "not_found" });
    else setState({ status: "error" });
  }, [kitchenId, router, show]);

  useEffect(() => {
    void load();
    const refresh = () => {
      if (document.visibilityState === "visible") void load();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [load]);

  const lost = useCallback(
    (failure: CartFailure) => {
      if (failure.code === "not_editing" || failure.code === "cart_locked") {
        setNotice(t.cartDiscarded);
        setDraft(null);
        void load();
        return true;
      }
      return false;
    },
    [load, t.cartDiscarded],
  );

  const flush = useCallback(async (): Promise<boolean> => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const next = queued.current;
    queued.current = null;
    if (!next) return true;
    const result = await putCartDraft(kitchenId, body(next));
    if (result.ok) {
      show(result.value, true);
      return true;
    }
    if (!lost(result)) setNotice(t.saveError);
    return false;
  }, [kitchenId, lost, show, t.saveError]);

  function change(next: LocalDraft) {
    setDraft(next);
    setNotice(null);
    queued.current = next;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void flush(), DRAFT_DEBOUNCE_MS);
  }

  async function edit() {
    setPending(true);
    setNotice(null);
    setDropped(0);
    const result = await startCartEdit(kitchenId);
    setPending(false);
    if (result.ok) show(result.value);
    else void load();
  }

  async function save() {
    setPending(true);
    const sent = await flush();
    if (!sent) {
      setPending(false);
      return;
    }
    const result = await saveCart(kitchenId);
    setPending(false);
    if (result.ok) {
      setDropped(result.value.dropped_recipe_ids?.length ?? 0);
      show(result.value);
    } else if (!lost(result)) setNotice(t.saveError);
  }

  async function discard() {
    if (timer.current) clearTimeout(timer.current);
    queued.current = null;
    setPending(true);
    await discardCart(kitchenId);
    setPending(false);
    setDraft(null);
    void load();
  }

  const idleExpiresAt =
    state.status === "ready" && state.cart.editor?.is_me ? state.cart.editor.idle_expires_at : null;
  const editing = state.status === "ready" && Boolean(state.cart.editor?.is_me);
  // The bar keeps one element between renders; its actions read the latest handlers.
  const actions = useRef({ save, discard, load });
  useEffect(() => {
    actions.current = { save, discard, load };
  });
  const bar = useMemo(
    () =>
      editing ? (
        <CartEditingBar
          kitchenId={kitchenId}
          idleExpiresAt={idleExpiresAt}
          locale={locale}
          onChanged={() => void actions.current.load()}
          onSave={() => void actions.current.save()}
          onDiscard={() => void actions.current.discard()}
          pending={pending}
        />
      ) : null,
    [editing, idleExpiresAt, kitchenId, locale, pending],
  );
  // The editing bar is docked above the tab bar, on this page only (FR-017a).
  useToastDock(bar);

  if (state.status === "loading") {
    return (
      <p className={styles.copy} role="status">
        {t.loading}
      </p>
    );
  }
  if (state.status === "not_found") {
    return (
      <p className={styles.copy} role="alert">
        {t.notFound}
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <div className={styles.state}>
        <p className={styles.copy} role="alert">
          {t.loadError}
        </p>
        <button type="button" className={styles.retry} onClick={() => void load()}>
          {t.retry}
        </button>
      </div>
    );
  }

  const { cart } = state;
  return (
    <div className="flex flex-col gap-4">
      {notice ? (
        <p role="alert" className="m-0 px-4 text-[0.9rem] text-muted">
          {notice}
        </p>
      ) : null}
      <CartView
        cart={cart}
        draft={draft}
        kitchenId={kitchenId}
        locale={locale}
        dropped={dropped}
        pending={pending}
        onEdit={() => void edit()}
        onDraftChange={change}
      />
      <ShoppingListSection kitchenId={kitchenId} locale={locale} cart={cart} />
    </div>
  );
}
