"use client";

import { useEffect, useState } from "react";

import { IngredientsScreen } from "@/components/Ingredients/IngredientsScreen";
import { SearchableSelect } from "@/components/SearchableSelect";
import { fetchCatalogNotebooks, type CatalogNotebook } from "@/lib/catalogClient";
import { catalogMessages } from "@/lib/i18n/catalog";
import type { Locale } from "@/lib/i18n/locale";

import { CatalogManager } from "./CatalogManager";

const ALL = "";

/**
 * The Ingredients page (specs 070 and 043): "All notebooks" keeps the places view; choosing one
 * notebook shows its catalog, with rename, merge, delete, split and suggested pairs when the
 * person can write to it (FR-002).
 */
export function IngredientsPage({ locale }: { locale: Locale }) {
  const t = catalogMessages[locale];
  const [notebooks, setNotebooks] = useState<CatalogNotebook[]>([]);
  const [chosen, setChosen] = useState(ALL);

  useEffect(() => {
    let current = true;
    void fetchCatalogNotebooks().then((result) => {
      if (current && result.ok) setNotebooks(result.value);
    });
    return () => {
      current = false;
    };
  }, []);

  const options = [
    { value: ALL, label: t.allNotebooks, pinned: true },
    ...notebooks.map((n) => ({
      value: n.id,
      label: n.kitchen ? `${n.name} · ${n.kitchen}` : n.name,
    })),
  ];

  const top = (
    <div className="flex min-w-0 flex-col gap-1 sm:max-w-[24rem]">
      <span className="text-[0.9rem] text-muted">{t.notebookLabel}</span>
      <SearchableSelect
        aria-label={t.notebookLabel}
        value={chosen}
        options={options}
        searchLabel={t.searchNotebooks}
        noResults={t.noNotebookMatch}
        onChange={(value) => setChosen(value)}
        className="min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-left text-[0.95rem] text-foreground"
      />
    </div>
  );

  return (
    <IngredientsScreen
      locale={locale}
      top={top}
      catalog={chosen ? <CatalogManager key={chosen} locale={locale} notebookId={chosen} /> : undefined}
    />
  );
}
