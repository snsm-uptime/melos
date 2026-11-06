"use client";

import { useEffect, useState } from "react";

import { CauldronLoader } from "@/components/CauldronLoader";
import type { Cart } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import {
  ALL_TAB,
  everythingBought,
  inTab,
  placeTabs,
  withBought,
} from "@/lib/shoppingByPlace";
import {
  fetchShoppingList,
  setItemBought,
  type ShoppingList,
} from "@/lib/shoppingListClient";

import { DoneButton } from "./DoneButton";
import { AddItemForm, HandItemsList } from "./HandItems";
import { PlaceTabs } from "./PlaceTabs";
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
  // The chosen store tab stays while the member is on this list (spec 070 FR-017).
  const [tab, setTab] = useState(ALL_TAB);
  const [toggleError, setToggleError] = useState(false);

  async function toggle(list: ShoppingList, itemId: string, bought: boolean) {
    setToggleError(false);
    // Shown at once; put back if the api refuses (SC-001).
    setState({ status: "ready", list: withBought(list, itemId, bought) });
    const result = await setItemBought(kitchenId, itemId, bought);
    if (result.ok) {
      setState({ status: "ready", list: result.value });
    } else {
      setState((now) =>
        now.status === "ready"
          ? { status: "ready", list: withBought(now.list, itemId, !bought) }
          : now,
      );
      setToggleError(true);
    }
  }

  useEffect(() => {
    let current = true;
    void fetchShoppingList(kitchenId).then((result) => {
      if (current) {
        setState(
          result.ok
            ? { status: "ready", list: result.value }
            : { status: "error" },
        );
      }
    });
    return () => {
      current = false;
    };
  }, [kitchenId, attempt, cart]);

  if (state.status === "loading") {
    return <CauldronLoader label={t.loading} />;
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
  if (list.is_empty && list.kitchen_is_archived && list.list_id === null)
    return null;

  const statusText = {
    live: t.statusLive,
    active: t.statusActive,
    draft: t.statusDraft,
  }[list.status];
  const hasCartLines = list.lines.length > 0 || list.your_call.length > 0;
  // Only a stored list in a kitchen that is not archived can be marked (spec 070 R3).
  const canMark = list.status === "active" && !list.kitchen_is_archived;
  const onToggle = canMark
    ? (itemId: string, bought: boolean) => void toggle(list, itemId, bought)
    : undefined;
  const tabs = placeTabs(list, locale);
  const shownTab =
    tab === ALL_TAB || tabs.some((t) => t.key === tab) ? tab : ALL_TAB;
  const lines = inTab(list.lines, shownTab);
  const yourCall = inTab(list.your_call, shownTab);
  const handItems = inTab(list.hand_items, shownTab);

  return (
    <section className="flex flex-col gap-3 px-4 [overflow-anchor:none]">
      <h2 className="m-0 text-[1.1rem] font-[600] text-foreground">
        {t.title}
      </h2>
      {list.is_empty ? null : (
        <p className="m-0 text-[0.9rem] text-muted">{statusText}</p>
      )}
      {list.kitchen_is_archived ? null : (
        <AddItemForm
          kitchenId={kitchenId}
          locale={locale}
          onChange={(next) => setState({ status: "ready", list: next })}
          customPlaces={list.custom_places}
        />
      )}
      {list.is_empty ? null : (
        <PlaceTabs
          tabs={tabs}
          selected={shownTab}
          onSelect={setTab}
          locale={locale}
        />
      )}
      {canMark && everythingBought(list) ? (
        <p className="m-0 text-[0.9rem] text-foreground" role="status">
          {t.allBought}
        </p>
      ) : null}
      {toggleError ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.changeError}
        </p>
      ) : null}
      {lines.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {lines.map((line, index) => (
            <ShoppingLineRow
              key={
                line.id ??
                `${line.name}|${line.kind}|${line.size ?? ""}|${index}`
              }
              line={line}
              kitchenId={kitchenId}
              locale={locale}
              onToggle={
                onToggle && line.id
                  ? (bought) => onToggle(line.id as string, bought)
                  : undefined
              }
            />
          ))}
        </ul>
      ) : null}
      <YourCallList
        entries={yourCall}
        kitchenId={kitchenId}
        locale={locale}
        onToggle={onToggle}
      />
      {!list.is_empty && !hasCartLines && list.hand_items.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">{t.noIngredients}</p>
      ) : null}
      <HandItemsList
        kitchenId={kitchenId}
        locale={locale}
        items={handItems}
        readOnly={list.kitchen_is_archived}
        onChange={(next) => setState({ status: "ready", list: next })}
        onToggle={onToggle}
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
    </section>
  );
}
