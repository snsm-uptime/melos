"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  AlertIcon,
  BasketIcon,
  HashtagIcon,
  NotebookBaseIcon,
  UsersIcon,
} from "@/app/icons";
import { useChromeHeader } from "@/components/ChromeBack";
import { CauldronLoader } from "@/components/CauldronLoader";
import { DataTable } from "@/components/DataTable";
import { TabButton, TabList } from "@/components/Tabs";
import { adminMessages } from "@/lib/i18n/admin";
import type { Locale } from "@/lib/i18n/locale";
import { tableMessages } from "@/lib/i18n/table";
import { withMinimumLoading } from "@/lib/minimumLoading";

import {
  ingredientsTable,
  recipesTable,
  refusedSitesTable,
  unitsTable,
  usersTable,
  type IngredientRow,
  type RecipeRow,
  type RefusedSiteRow,
  type UnitRow,
  type UserRow,
} from "./adminTables";

const SECTIONS = [
  "units",
  "ingredients",
  "recipes",
  "users",
  "refused-sites",
] as const;
type Section = (typeof SECTIONS)[number];

const TAB_ICONS: Record<Section, typeof BasketIcon> = {
  units: HashtagIcon,
  ingredients: BasketIcon,
  recipes: NotebookBaseIcon,
  users: UsersIcon,
  "refused-sites": AlertIcon,
};

/** The response key for each section's rows. */
const ROWS_KEY: Record<Section, string> = {
  units: "units",
  ingredients: "ingredients",
  recipes: "recipes",
  users: "users",
  "refused-sites": "refused_sites",
};

type Row = Record<string, unknown>;
type Loaded = { state: "ready"; rows: Row[] } | { state: "failed" };
async function loadSection(section: Section): Promise<Loaded> {
  try {
    const response = await fetch(`/api/admin/${section}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok) return { state: "failed" };
    const rows = ((await response.json()) as Record<string, unknown>)[
      ROWS_KEY[section]
    ];
    return Array.isArray(rows)
      ? { state: "ready", rows: rows as Row[] }
      : { state: "failed" };
  } catch {
    return { state: "failed" };
  }
}

/** True when the recipe is gone, including when another admin removed it first. */
async function deleteAdminRecipe(id: string): Promise<boolean> {
  try {
    const response = await fetch(
      `/api/admin/recipes/${encodeURIComponent(id)}`,
      {
        method: "DELETE",
        credentials: "same-origin",
        cache: "no-store",
      },
    );
    return response.ok || response.status === 404;
  } catch {
    return false;
  }
}

/** One tab's rows through the shared table, with that tab's schema. */
function SectionTable({
  section,
  rows,
  t,
  locale,
  deleteRecipe,
}: {
  section: Section;
  rows: Row[];
  t: (typeof adminMessages)[Locale];
  locale: Locale;
  deleteRecipe: (id: string) => Promise<boolean>;
}) {
  const common = { locale, labels: tableMessages[locale], empty: t.empty };
  switch (section) {
    case "units":
      return (
        <DataTable
          schema={unitsTable(t, locale)}
          rows={rows as UnitRow[]}
          {...common}
        />
      );
    case "ingredients":
      return (
        <DataTable
          schema={ingredientsTable(t)}
          rows={rows as IngredientRow[]}
          {...common}
        />
      );
    case "recipes":
      return (
        <DataTable
          schema={recipesTable(t, { deleteRecipe })}
          rows={rows as RecipeRow[]}
          {...common}
        />
      );
    case "users":
      return (
        <DataTable
          schema={usersTable(t, locale)}
          rows={rows as UserRow[]}
          {...common}
        />
      );
    case "refused-sites":
      return (
        <DataTable
          schema={refusedSitesTable(t, locale)}
          rows={rows as RefusedSiteRow[]}
          {...common}
        />
      );
  }
}

/** Five tabs, each loaded the first time it opens (spec 055 contracts/admin-api.md). */
export function AdminDashboard({ locale }: { locale: Locale }) {
  const t = adminMessages[locale];
  const [section, setSection] = useState<Section>("units");
  const [loaded, setLoaded] = useState<Partial<Record<Section, Loaded>>>({});
  const current = loaded[section];
  useChromeHeader({
    title: t.title,
    sidePanel: true,
  });

  // Going back to a section mid-load must not ask for it twice.
  const loading = useRef(new Set<Section>());

  const load = useCallback((target: Section) => {
    if (loading.current.has(target)) return;
    loading.current.add(target);
    void withMinimumLoading(loadSection(target)).then((result) => {
      loading.current.delete(target);
      setLoaded((before) => ({ ...before, [target]: result }));
    });
  }, []);

  /** Deletes a recipe, then takes its row out of the loaded table. */
  const deleteRecipe = useCallback(async (id: string) => {
    const deleted = await deleteAdminRecipe(id);
    if (deleted) {
      setLoaded((before) => {
        const recipes = before.recipes;
        if (recipes?.state !== "ready") return before;
        return {
          ...before,
          recipes: {
            state: "ready",
            rows: recipes.rows.filter((row) => row.id !== id),
          },
        };
      });
    }
    return deleted;
  }, []);

  /** Back to the first-load state, so a retry shows the cauldron again. */
  function retry() {
    setLoaded((before) => {
      const next = { ...before };
      delete next[section];
      return next;
    });
  }

  useEffect(() => {
    if (current === undefined) load(section);
  }, [current, load, section]);

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-4 p-4">
      <TabList
        label={t.tabsLabel}
        cycle={{ previousLabel: t.previousTab, nextLabel: t.nextTab }}
      >
        {SECTIONS.map((name) => {
          const Icon = TAB_ICONS[name];
          return (
            <TabButton
              key={name}
              id={`admin-tab-${name}`}
              selected={name === section}
              onSelect={() => setSection(name)}
              icon={<Icon className="size-5" />}
              label={t.tabs[name]}
            />
          );
        })}
      </TabList>
      <div
        role="tabpanel"
        aria-labelledby={`admin-tab-${section}`}
        className="flex min-w-0 flex-1 flex-col"
      >
        {current === undefined ? (
          <CauldronLoader label={t.tabs[section]} />
        ) : null}
        {current?.state === "ready" ? (
          <SectionTable
            // Remounts per tab, so sort and search start fresh (spec 066 US1 scenario 6).
            key={section}
            section={section}
            rows={current.rows}
            t={t}
            locale={locale}
            deleteRecipe={deleteRecipe}
          />
        ) : null}
        {current?.state === "failed" ? (
          <div className="flex flex-col items-start gap-2">
            <p role="alert" className="m-0 text-[0.9rem] text-error">
              {t.loadFailed}
            </p>
            <button
              type="button"
              className="rounded-[0.75rem] border border-border px-3 py-1 text-foreground"
              onClick={retry}
            >
              {t.retry}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
