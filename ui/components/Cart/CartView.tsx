"use client";

import Link from "next/link";
import { useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { formatFactor } from "@/lib/cartFactor";
import type { Cart, CartEntry } from "@/lib/cartClient";
import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

import { CartEntryRow } from "./CartEntryRow";
import { EditorNotice } from "./EditorNotice";

/** My draft as the editing view holds it; sent whole to PUT …/cart/draft. */
export type LocalDraft = {
  entries: CartEntry[];
};

export function draftFromCart(cart: Cart): LocalDraft | null {
  if (!cart.editor?.is_me || !cart.draft) return null;
  return { entries: cart.draft.entries };
}

type CartViewProps = {
  cart: Cart;
  /** Set while my session edits the cart. */
  draft: LocalDraft | null;
  kitchenId: string;
  locale: Locale;
  /** Recipes removed on save because they were deleted. */
  dropped: number;
  pending?: boolean;
  onDraftChange: (next: LocalDraft) => void;
};

/**
 * The Cart page body (contracts/cart-ui.md): the saved cart for everyone, or my editing view,
 * which starts from the pencil at the end of the chrome,
 * with Servings, Remove and Clear; Save and Discard are on the docked editing bar. Factors in the draft are recomputed here
 * with the api's rounding.
 */
export function CartView({
  cart,
  draft,
  kitchenId,
  locale,
  dropped,
  pending = false,
  onDraftChange,
}: CartViewProps) {
  const t = cartMessages[locale];
  const [clearing, setClearing] = useState(false);
  const from = `/kitchens/${encodeURIComponent(kitchenId)}/cart`;
  const someoneElse = cart.editor && !cart.editor.is_me ? cart.editor : null;

  const entries = draft ? draft.entries : cart.entries;

  function setServings(index: number, servings: number) {
    if (!draft) return;
    const next = draft.entries.map((entry, at) => (at === index ? { ...entry, servings } : entry));
    onDraftChange({ ...draft, entries: next });
  }

  return (
    <section className="flex flex-col gap-4 px-4">
      {entries.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">
          {t.empty}.{" "}
          <Link href={`/kitchens/${encodeURIComponent(kitchenId)}`} className="text-accent">
            {t.emptyLink}
          </Link>
        </p>
      ) : null}
      {dropped > 0 ? (
        <p role="status" className="m-0 text-[0.9rem] text-muted">
          {t.dropped(dropped)}
        </p>
      ) : null}
      {someoneElse ? <EditorNotice alias={someoneElse.alias} kind="cart" locale={locale} /> : null}

      {draft ? (
        <div className="flex justify-end">
          <button
            type="button"
            className={SECONDARY}
            disabled={pending || draft.entries.length === 0}
            onClick={() => setClearing(true)}
          >
            {t.clear}
          </button>
        </div>
      ) : null}

      {entries.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {entries.map((entry, index) => (
            <CartEntryRow
              key={entry.recipe_id}
              entry={entry}
              locale={locale}
              from={from}
              factor={draft ? formatFactor(entry.servings, entry.base_servings) : entry.factor}
              onServingsChange={draft ? (servings) => setServings(index, servings) : undefined}
              onRemove={
                draft
                  ? () =>
                      onDraftChange({
                        ...draft,
                        entries: draft.entries.filter((_, at) => at !== index),
                      })
                  : undefined
              }
            />
          ))}
        </ul>
      ) : null}

      <ActionDialog
        open={clearing}
        title={t.clearConfirmTitle}
        confirmLabel={t.clearConfirm}
        cancelLabel={t.cancel}
        onOpenChange={setClearing}
        onConfirm={() => {
          setClearing(false);
          if (draft) onDraftChange({ ...draft, entries: [] });
        }}
      >
        <p className="m-0">{t.clearConfirmBody}</p>
      </ActionDialog>
    </section>
  );
}

const SECONDARY =
  "rounded-[var(--radius-md)] border border-border bg-background px-4 py-2 text-[0.9rem] text-foreground disabled:opacity-50";
