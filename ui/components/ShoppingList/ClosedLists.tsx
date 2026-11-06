"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CauldronLoader } from "@/components/CauldronLoader";
import { useChromeHeader } from "@/components/ChromeBack";

import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import {
  fetchClosedList,
  fetchClosedLists,
  type ClosedList,
  type ClosedListSummary,
} from "@/lib/shoppingListClient";
import { ALL_TAB, inTab, placeTabs } from "@/lib/shoppingByPlace";
import { formatHandItem } from "@/lib/shoppingListText";

import { BoughtToggle, boughtText } from "./BoughtToggle";
import { PlaceTabs } from "./PlaceTabs";
import { ShoppingLineRow } from "./ShoppingLine";
import { TruncatedText } from "./TruncatedText";
import { ITEM_GRID } from "./itemGrid";
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

  useChromeHeader({ backHref: base, title: t.pastLists });

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
      {rows === null ? (
        <CauldronLoader label={t.loading} />
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
  // A new list opens on All (spec 070 FR-017): this component mounts once per list.
  const [tab, setTab] = useState(ALL_TAB);
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
    <section className="@container flex flex-col gap-3 px-4">
      <Link href={back} className={BACK}>
        {t.backToPastLists}
      </Link>
      {list === null ? (
        <CauldronLoader label={t.loading} />
      ) : list === "error" ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.pastListsLoadError}
        </p>
      ) : (
        <>
          <h1 className="m-0 text-[1.25rem] font-[600] text-foreground">
            {t.closedOn(formatClosingDate(list.closing_date, locale))}
          </h1>
          <ClosedListItems
            list={list}
            tab={tab}
            onTab={setTab}
            kitchenId={kitchenId}
            locale={locale}
          />
        </>
      )}
    </section>
  );
}

type ClosedListItemsProps = {
  list: ClosedList;
  tab: string;
  onTab: (tab: string) => void;
  kitchenId: string;
  locale: Locale;
};

/** A closed list's items under its store tabs, with their saved bought state (spec 070 FR-004). */
function ClosedListItems({ list, tab, onTab, kitchenId, locale }: ClosedListItemsProps) {
  const t = shoppingListMessages[locale];
  const tabs = placeTabs(list, locale);
  const shown = tab === ALL_TAB || tabs.some((x) => x.key === tab) ? tab : ALL_TAB;
  const lines = inTab(list.lines, shown);
  const handItems = inTab(list.hand_items, shown);
  return (
    <>
      <PlaceTabs tabs={tabs} selected={shown} onSelect={onTab} locale={locale} />
      {lines.length > 0 ? (
        <ul className={ITEM_GRID}>
          {lines.map((line, index) => (
            <ShoppingLineRow
              key={line.id ?? `${line.name}|${line.kind}|${line.size ?? ""}|${index}`}
              line={line}
              kitchenId={kitchenId}
              locale={locale}
              frozen
            />
          ))}
        </ul>
      ) : null}
      <YourCallList
        entries={inTab(list.your_call, shown)}
        kitchenId={kitchenId}
        locale={locale}
        frozen
      />
      {handItems.length > 0 ? (
        <>
          <h2 className="m-0 text-[1rem] font-[600] text-foreground">{t.addedByHand}</h2>
          <ul className={ITEM_GRID}>
            {handItems.map((item) => (
              <li
                key={item.id}
                data-bought={item.bought ? "true" : undefined}
                className="flex min-w-0 items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface p-3"
              >
                <BoughtToggle name={item.name} bought={item.bought === true} locale={locale} />
                <TruncatedText
                  text={formatHandItem(item)}
                  className={`text-[1rem] font-[550] ${boughtText(item.bought)}`}
                />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}
