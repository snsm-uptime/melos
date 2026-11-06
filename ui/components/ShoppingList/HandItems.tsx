"use client";

import { useState, type FormEvent } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import {
  allPlaces,
  placeFromKey,
  placeKey,
  placeLabel,
  startsDefaults,
  type CustomPlace,
} from "@/lib/places";
import {
  addShoppingItem,
  removeShoppingItem,
  type HandItem,
  type ShoppingList,
} from "@/lib/shoppingListClient";

import { ShoppingRow } from "./ShoppingLine";

const UNITS = [
  "unit",
  "g",
  "kg",
  "oz",
  "lb",
  "ml",
  "l",
  "cup",
  "tbsp",
  "tsp",
] as const;

const FIELD =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-[1rem] text-foreground";

/** A hand item's amount, or nothing when it has none. */
function handAmount(item: HandItem): string {
  if (item.quantity === null) return "";
  return item.unit === "unit" ? item.quantity : `${item.quantity} ${item.unit}`;
}

type HandItemsProps = {
  kitchenId: string;
  locale: Locale;
  items: HandItem[];
  /** Hides the form and Remove (archived kitchen). */
  readOnly: boolean;
  onChange: (list: ShoppingList) => void;
  /** The member's own places for the optional place picker (spec 070 FR-016a). */
  customPlaces?: CustomPlace[];
  /** Shown only for a stored, writable list (spec 070 R3). */
  onToggle?: (itemId: string, bought: boolean) => void;
};

/** The form that adds an item by hand (spec 025 FR-003). Saves at once. */
export function AddItemForm({
  kitchenId,
  locale,
  onChange,
  customPlaces = [],
}: Pick<HandItemsProps, "kitchenId" | "locale" | "onChange" | "customPlaces">) {
  const t = shoppingListMessages[locale];
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [place, setPlace] = useState("");
  const places = allPlaces(customPlaces, locale);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (pending || name.trim() === "") return;
    setPending(true);
    setError(null);
    const amount = quantity.trim();
    const chosen = place === "" ? null : placeFromKey(place, places);
    const result = await addShoppingItem(kitchenId, {
      name,
      ...(amount === "" ? {} : { quantity: amount, unit: unit || "unit" }),
      ...(chosen ? { place: chosen } : {}),
    });
    setPending(false);
    if (result.ok) {
      setName("");
      setQuantity("");
      setUnit("");
      setPlace("");
      onChange(result.value);
    } else {
      setError(result.code === "invalid_item" ? t.itemError : t.changeError);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => void add(e)}
      >
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-[0.85rem] text-muted">
          {t.itemName}
          <input
            className={FIELD}
            value={name}
            maxLength={120}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="flex w-[9rem] flex-col gap-1 text-[0.85rem] text-muted">
          {t.itemQuantity}
          <input
            className={FIELD}
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </label>
        <label className="flex w-[7rem] flex-col gap-1 text-[0.85rem] text-muted">
          {t.itemUnit}
          <select
            className={FIELD}
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          >
            <option value="">{t.noUnit}</option>
            {UNITS.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>
        <label className="flex w-[12rem] flex-col gap-1 text-[0.85rem] text-muted">
          {t.itemPlace}
          <select
            className={FIELD}
            value={place}
            onChange={(e) => setPlace(e.target.value)}
          >
            <option value="">{t.noPlace}</option>
            {places.map((p, i) => [
              // Own places, a divider, then the default places (a native select has no rule).
              startsDefaults(places, i) ? (
                <option key="divider" disabled value="__divider__">
                  ──────────
                </option>
              ) : null,
              <option key={placeKey(p)} value={placeKey(p)}>
                {placeLabel(p, locale)}
              </option>,
            ])}
          </select>
        </label>
        <button
          type="submit"
          disabled={pending || name.trim() === ""}
          className="min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-4 text-[0.9rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
        >
          {pending ? t.adding : t.addItem}
        </button>
      </form>
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** Items a member added by hand, each with Remove (spec 025 FR-003). */
export function HandItemsList({
  kitchenId,
  locale,
  items,
  readOnly,
  onChange,
  onToggle,
}: Omit<HandItemsProps, "customPlaces">) {
  const t = shoppingListMessages[locale];
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove(itemId: string) {
    if (pending) return;
    setPending(true);
    setError(null);
    const result = await removeShoppingItem(kitchenId, itemId);
    setPending(false);
    if (result.ok) onChange(result.value);
    else setError(t.changeError);
  }

  return (
    <div className="flex flex-col gap-2">
      {items.length > 0 ? (
        <>
          <h3 className="m-0 text-[1rem] font-[600] text-foreground">
            {t.addedByHand}
          </h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {items.map((item) => (
              <ShoppingRow
                key={item.id}
                name={item.name}
                detail={handAmount(item)}
                recipes={[]}
                bought={item.bought}
                kitchenId={kitchenId}
                locale={locale}
                showToggle={Boolean(onToggle)}
                onToggle={
                  onToggle ? (bought) => onToggle(item.id, bought) : undefined
                }
                trailing={
                  readOnly ? null : (
                    <button
                      type="button"
                      aria-label={t.removeItem(item.name)}
                      disabled={pending}
                      className="min-h-8 min-w-8 rounded-[var(--radius-md)] text-[1.1rem] text-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
                      onClick={() => void remove(item.id)}
                    >
                      <span aria-hidden="true">×</span>
                    </button>
                  )
                }
              />
            ))}
          </ul>
        </>
      ) : null}
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** The hand-item list followed by the add form. */
export function HandItems(props: HandItemsProps) {
  return (
    <div className="flex flex-col gap-2">
      <HandItemsList {...props} />
      {props.readOnly ? null : <AddItemForm {...props} />}
    </div>
  );
}
