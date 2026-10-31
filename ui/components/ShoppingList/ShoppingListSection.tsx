"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Cart } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { fetchShoppingList, type ShoppingList } from "@/lib/shoppingListClient";

import { DoneButton } from "./DoneButton";
import { HandItems } from "./HandItems";
import { ShoppingLineRow } from "./ShoppingLine";
import { YourCallList } from "./YourCallList";

type State =
  | { status: "loading" }
  | { status: "ready"; list: ShoppingList }
  | { status: "error" };

/**
 * The kitchen's shopping list, below the cart's recipes on the Cart page (spec 023,
 * contracts/shopping-list-ui.md). A saved list also takes items added by hand, even with an empty
 * cart, and Done closes it (spec 025). An archived kitchen with nothing to show shows nothing.
 */
type ShoppingListSectionProps = {
  kitchenId: string;
  locale: Locale;
  /**
   * The Cart page's state. The list is fetched again whenever this is replaced (load, focus,
   * a draft change coming back from the api, save, discard), so it follows the cart with no
   * manual refresh. The previous list stays on screen while the next one loads.
   */
  cart: Cart;
  /** Done closed the list, which also emptied the cart. */
  onClosed: () => void;
};

export function ShoppingListSection({
  kitchenId,
  locale,
  cart,
  onClosed,
}: ShoppingListSectionProps) {
  const t = shoppingListMessages[locale];
  const [state, setState] = useState<State>({ status: "loading" });
  // Bumped by Retry so the effect below runs again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    void fetchShoppingList(kitchenId).then((result) => {
      if (current) {
        setState(result.ok ? { status: "ready", list: result.value } : { status: "error" });
      }
    });
    return () => {
      current = false;
    };
  }, [kitchenId, attempt, cart]);

  if (state.status === "loading") {
    return (
      <p className="m-0 px-4 text-[0.9rem] text-muted" role="status">
        {t.loading}
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <div className="flex flex-col items-start gap-2 px-4">
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.loadError}
        </p>
        <button
          type="button"
          className="rounded-[var(--radius-md)] border border-border bg-background px-4 py-2 text-[0.9rem] text-foreground"
          onClick={() => {
            setState({ status: "loading" });
            setAttempt((n) => n + 1);
          }}
        >
          {t.retry}
        </button>
      </div>
    );
  }

  const { list } = state;
  if (list.is_empty && list.kitchen_is_archived && list.list_id === null) return null;

  const statusText = {
    live: t.statusLive,
    active: t.statusActive,
    draft: t.statusDraft,
  }[list.status];
  const hasCartLines = list.lines.length > 0 || list.your_call.length > 0;
  const closedListsHref = `/kitchens/${encodeURIComponent(kitchenId)}/shopping-lists`;

  return (
    <section className="flex flex-col gap-3 px-4">
      <h2 className="m-0 text-[1.1rem] font-[600] text-foreground">{t.title}</h2>
      {list.is_empty ? null : <p className="m-0 text-[0.9rem] text-muted">{statusText}</p>}
      {list.lines.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {list.lines.map((line, index) => (
            <ShoppingLineRow
              key={`${line.name}|${line.kind}|${line.size ?? ""}|${index}`}
              line={line}
              kitchenId={kitchenId}
              locale={locale}
            />
          ))}
        </ul>
      ) : null}
      <YourCallList entries={list.your_call} kitchenId={kitchenId} locale={locale} />
      {!list.is_empty && !hasCartLines && list.hand_items.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">{t.noIngredients}</p>
      ) : null}
      <HandItems
        kitchenId={kitchenId}
        locale={locale}
        items={list.hand_items}
        readOnly={list.kitchen_is_archived}
        onChange={(next) => setState({ status: "ready", list: next })}
      />
      {list.list_id !== null && !list.kitchen_is_archived ? (
        <DoneButton
          kitchenId={kitchenId}
          locale={locale}
          listId={list.list_id}
          empty={!hasCartLines && list.hand_items.length === 0}
          editing={list.status === "draft"}
          onClosed={() => {
            setAttempt((n) => n + 1);
            onClosed();
          }}
        />
      ) : null}
      <Link
        href={closedListsHref}
        className="inline-flex min-h-11 items-center self-start text-[0.9rem] text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      >
        {t.pastLists}
      </Link>
    </section>
  );
}
