"use client";

import { useState, type FormEvent } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import {
  addShoppingItem,
  removeShoppingItem,
  type HandItem,
  type ShoppingList,
} from "@/lib/shoppingListClient";
import { formatHandItem } from "@/lib/shoppingListText";

const UNITS = ["unit", "g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp"] as const;

const FIELD =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-[1rem] text-foreground";

type HandItemsProps = {
  kitchenId: string;
  locale: Locale;
  items: HandItem[];
  /** Hides the form and Remove (archived kitchen). */
  readOnly: boolean;
  onChange: (list: ShoppingList) => void;
};

/** Items a member adds by hand to the kitchen's list (spec 025 FR-003). Each change saves at once. */
export function HandItems({ kitchenId, locale, items, readOnly, onChange }: HandItemsProps) {
  const t = shoppingListMessages[locale];
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (pending || name.trim() === "") return;
    setPending(true);
    setError(null);
    const amount = quantity.trim();
    const result = await addShoppingItem(kitchenId, {
      name,
      ...(amount === "" ? {} : { quantity: amount, unit: unit || "unit" }),
    });
    setPending(false);
    if (result.ok) {
      setName("");
      setQuantity("");
      setUnit("");
      onChange(result.value);
    } else {
      setError(result.code === "invalid_item" ? t.itemError : t.changeError);
    }
  }

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
          <h3 className="m-0 text-[1rem] font-[600] text-foreground">{t.addedByHand}</h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface p-3"
              >
                <span className="min-w-0 break-words text-[1rem] font-[550] text-foreground">
                  {formatHandItem(item)}
                </span>
                {readOnly ? null : (
                  <button
                    type="button"
                    aria-label={t.removeItem(item.name)}
                    disabled={pending}
                    className="min-h-11 min-w-11 rounded-[var(--radius-md)] text-[1.1rem] text-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
                    onClick={() => void remove(item.id)}
                  >
                    <span aria-hidden="true">×</span>
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {readOnly ? null : (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => void add(e)}>
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
            <select className={FIELD} value={unit} onChange={(e) => setUnit(e.target.value)}>
              <option value="">{t.noUnit}</option>
              {UNITS.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
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
      )}
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
