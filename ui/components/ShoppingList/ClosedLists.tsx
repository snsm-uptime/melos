"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import {
  fetchClosedList,
  fetchClosedLists,
  type ClosedList,
  type ClosedListSummary,
} from "@/lib/shoppingListClient";
import { formatHandItem } from "@/lib/shoppingListText";

import { ShoppingLineRow } from "./ShoppingLine";
import { YourCallList } from "./YourCallList";

const BACK =
  "inline-flex min-h-11 items-center self-start text-[0.9rem] text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";

/** YYYY-MM-DD in the member's language. The date has no time zone, so it stays in UTC. */
export function formatClosingDate(date: string, locale: Locale): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString(locale, {
    dateStyle: "long",
    timeZone: "UTC",
  });
}

type ClosedListsProps = { kitchenId: string; locale: Locale };

/** The kitchen's closed lists, newest first (spec 025 FR-010). */
export function ClosedLists({ kitchenId, locale }: ClosedListsProps) {
  const t = shoppingListMessages[locale];
  const [rows, setRows] = useState<ClosedListSummary[] | null | "error">(null);
  const base = `/kitchens/${encodeURIComponent(kitchenId)}`;

  useEffect(() => {
    let current = true;
    void fetchClosedLists(kitchenId).then((result) => {
      if (current) setRows(result.ok ? result.value : "error");
    });
    return () => {
      current = false;
    };
  }, [kitchenId]);

  return (
    <section className="flex flex-col gap-3 px-4">
      <Link href={`${base}/cart`} className={BACK}>
        {t.backToCart}
      </Link>
      <h1 className="m-0 text-[1.25rem] font-[600] text-foreground">{t.pastLists}</h1>
      {rows === null ? (
        <p className="m-0 text-[0.9rem] text-muted" role="status">
          {t.loading}
        </p>
      ) : rows === "error" ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.pastListsLoadError}
        </p>
      ) : rows.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">{t.pastListsEmpty}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                href={`${base}/shopping-lists/${encodeURIComponent(row.id)}`}
                className="flex min-h-11 flex-col gap-1 rounded-[var(--radius-md)] border border-border bg-surface p-3 text-foreground no-underline hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                <span className="text-[1rem] font-[550]">
                  {t.closedOn(formatClosingDate(row.closing_date, locale))}
                </span>
                {row.recipe_titles.length > 0 ? (
                  <span className="text-[0.85rem] text-muted">{row.recipe_titles.join(", ")}</span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

type ClosedListDetailProps = { kitchenId: string; listId: string; locale: Locale };

/** One closed list, read only, exactly as saved (spec 025 FR-008). */
export function ClosedListDetail({ kitchenId, listId, locale }: ClosedListDetailProps) {
  const t = shoppingListMessages[locale];
  const [list, setList] = useState<ClosedList | null | "error">(null);
  const back = `/kitchens/${encodeURIComponent(kitchenId)}/shopping-lists`;

  useEffect(() => {
    let current = true;
    void fetchClosedList(kitchenId, listId).then((result) => {
      if (current) setList(result.ok ? result.value : "error");
    });
    return () => {
      current = false;
    };
  }, [kitchenId, listId]);

  return (
    <section className="flex flex-col gap-3 px-4">
      <Link href={back} className={BACK}>
        {t.backToPastLists}
      </Link>
      {list === null ? (
        <p className="m-0 text-[0.9rem] text-muted" role="status">
          {t.loading}
        </p>
      ) : list === "error" ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.pastListsLoadError}
        </p>
      ) : (
        <>
          <h1 className="m-0 text-[1.25rem] font-[600] text-foreground">
            {t.closedOn(formatClosingDate(list.closing_date, locale))}
          </h1>
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
          {list.hand_items.length > 0 ? (
            <>
              <h2 className="m-0 text-[1rem] font-[600] text-foreground">{t.addedByHand}</h2>
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {list.hand_items.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-[var(--radius-md)] border border-border bg-surface p-3 text-[1rem] font-[550] text-foreground"
                  >
                    {formatHandItem(item)}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
