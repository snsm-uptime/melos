"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { CheckIcon, CloseIcon } from "@/app/icons";
import { useChromeHeader } from "@/components/ChromeBack";
import { CauldronLoader } from "@/components/CauldronLoader";
import { adminMessages } from "@/lib/i18n/admin";
import type { Locale } from "@/lib/i18n/locale";
import { withMinimumLoading } from "@/lib/minimumLoading";

const SECTIONS = ["units", "ingredients", "recipes", "users"] as const;
type Section = (typeof SECTIONS)[number];

type Row = Record<string, unknown>;
type Loaded = { state: "ready"; rows: Row[] } | { state: "failed" };
type Messages = (typeof adminMessages)[Locale];

type Column = { key: string; label: string; show?: (value: unknown) => ReactNode };

function columnsFor(section: Section, t: Messages, locale: Locale): Column[] {
  const date = (value: unknown) =>
    typeof value === "string" ? new Date(value).toLocaleDateString(locale) : t.none;
  switch (section) {
    case "units": {
      const c = t.columns.units;
      return [
        { key: "name", label: c.name },
        { key: "reference_count", label: c.referenceCount },
        {
          key: "is_default",
          label: c.isDefault,
          show: (v) => (
            <span
              role="img"
              aria-label={v ? t.yes : t.no}
              className={`inline-flex align-middle ${v ? "text-accent" : "text-error"}`}
            >
              {v ? <CheckIcon /> : <CloseIcon />}
            </span>
          ),
        },
        { key: "created_at", label: c.createdAt, show: date },
        {
          key: "user_references",
          label: c.userReferences,
          show: (v) => (Array.isArray(v) && v.length > 0 ? v.join(", ") : t.none),
        },
      ];
    }
    case "ingredients": {
      const c = t.columns.ingredients;
      return [
        { key: "name", label: c.name },
        { key: "recipes", label: c.recipes },
        { key: "people", label: c.people },
      ];
    }
    case "recipes": {
      const c = t.columns.recipes;
      return [
        { key: "title", label: c.title },
        { key: "cart_adds", label: c.cartAdds },
        { key: "notebook_name", label: c.notebookName },
        {
          key: "notebook_kind",
          label: c.notebookKind,
          show: (v) => (v === "kitchen" ? t.kinds.kitchen : t.kinds.personal),
        },
        { key: "people_with_access", label: c.peopleWithAccess },
        { key: "id", label: c.id },
      ];
    }
    case "users": {
      const c = t.columns.users;
      return [
        { key: "alias", label: c.alias, show: (v) => (typeof v === "string" ? v : t.noAlias) },
        { key: "open_sessions", label: c.openSessions },
        { key: "newest_session_at", label: c.newestSessionAt, show: date },
        { key: "recipes_authored", label: c.recipesAuthored },
        { key: "latest_recipe_at", label: c.latestRecipeAt, show: date },
        { key: "carts_created", label: c.cartsCreated },
        { key: "carts_edited", label: c.cartsEdited },
        { key: "carts_closed", label: c.cartsClosed },
        { key: "latest_cart_action_at", label: c.latestCartActionAt, show: date },
        { key: "id", label: c.id },
      ];
    }
  }
}

async function loadSection(section: Section): Promise<Loaded> {
  try {
    const response = await fetch(`/api/admin/${section}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok) return { state: "failed" };
    const rows = ((await response.json()) as Record<string, unknown>)[section];
    return Array.isArray(rows) ? { state: "ready", rows: rows as Row[] } : { state: "failed" };
  } catch {
    return { state: "failed" };
  }
}

function SectionTable({ columns, rows, empty }: { columns: Column[]; rows: Row[]; empty: string }) {
  if (rows.length === 0) return <p className="m-0 text-[0.9rem] text-muted">{empty}</p>;
  return (
    // Wide sections scroll inside their box, so the page itself fits a 360px screen.
    <div className="max-w-full overflow-x-auto rounded-[0.75rem] border border-border">
      <table className="w-full border-collapse text-left text-[0.85rem]">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className="border-b border-border px-3 py-2 font-semibold whitespace-nowrap text-muted"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`border-b border-border px-3 py-2 text-foreground ${
                    column.key === "user_references" ? "" : "whitespace-nowrap"
                  }`}
                >
                  {column.show ? column.show(row[column.key]) : String(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Four tabs, each loaded the first time it opens (spec 055 contracts/admin-api.md). */
export function AdminDashboard({ locale }: { locale: Locale }) {
  const t = adminMessages[locale];
  const [section, setSection] = useState<Section>("units");
  const [loaded, setLoaded] = useState<Partial<Record<Section, Loaded>>>({});
  const current = loaded[section];
  useChromeHeader({
    title: t.title,
    sidePanel: true,
    titleAside: (
      <div role="tablist" aria-label={t.tabsLabel} className="flex w-max gap-2">
        {SECTIONS.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={name === section}
            className={`min-h-10 rounded-[0.75rem] border px-3 py-1 text-[0.9rem] whitespace-nowrap ${
              name === section
                ? "border-accent text-foreground"
                : "border-border text-muted hover:text-foreground"
            }`}
            onClick={() => setSection(name)}
          >
            {t.tabs[name]}
          </button>
        ))}
      </div>
    ),
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
      <div role="tabpanel" className="flex min-w-0 flex-1 flex-col">
        {current === undefined ? <CauldronLoader label={t.tabs[section]} /> : null}
        {current?.state === "ready" ? (
          <SectionTable
            columns={columnsFor(section, t, locale)}
            rows={current.rows}
            empty={t.empty}
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
