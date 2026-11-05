"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { BoxIcon, HashtagIcon, NotebookIcon, UsersIcon } from "@/app/icons";
import { useChromeHeader } from "@/components/ChromeBack";
import { CauldronLoader } from "@/components/CauldronLoader";
import { DataTable } from "@/components/DataTable";
import { TabButton, TabList } from "@/components/Tabs";
import { adminMessages } from "@/lib/i18n/admin";
import type { Locale } from "@/lib/i18n/locale";
import { tableMessages } from "@/lib/i18n/table";
import { withMinimumLoading } from "@/lib/minimumLoading";

const SECTIONS = [
  "units",
  "ingredients",
  "recipes",
  "users",
  "refused-sites",
] as const;
type Section = (typeof SECTIONS)[number];

/** The response key for each section's rows. */
const ROWS_KEY: Record<Section, string> = {
  units: "units",
  ingredients: "ingredients",
  recipes: "recipes",
  users: "users",
  "refused-sites": "refused_sites",
};

/** Cells that wrap instead of keeping to one line. */
const WRAPPING = new Set(["user_references", "last_message"]);

type Row = Record<string, unknown>;
type Loaded = { state: "ready"; rows: Row[] } | { state: "failed" };
type Messages = (typeof adminMessages)[Locale];

type Column = {
  key: string;
  label: string;
  show?: (value: unknown, row: Row) => ReactNode;
};

type Actions = { deleteRecipe: (id: string) => Promise<boolean> };

/** The count of people with access, then the aliases of each as a row of chips that scrolls. */
function PeopleWithAccess({
  count,
  aliases,
  noAlias,
}: {
  count: unknown;
  aliases: unknown;
  noAlias: string;
}) {
  const names = Array.isArray(aliases) ? aliases : [];
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="shrink-0 font-semibold">{String(count)}</span>
      <div className="flex max-w-[14rem] gap-1 overflow-x-auto pb-1">
        {names.map((alias, index) => (
          <Chip key={index}>{typeof alias === "string" ? alias : noAlias}</Chip>
        ))}
      </div>
    </div>
  );
}

function columnsFor(
  section: Section,
  t: Messages,
  locale: Locale,
  actions: Actions,
): Column[] {
  const date = (value: unknown) =>
    typeof value === "string"
      ? new Date(value).toLocaleDateString(locale)
      : t.none;
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
          show: (_value, row) => (
            <PeopleWithAccess
              count={row.reference_count}
              aliases={row.user_aliases}
              noAlias={t.noAlias}
            />
          ),
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
        {
          key: "people_with_access",
          label: c.peopleWithAccess,
          show: (count, row) => (
            <PeopleWithAccess
              count={count}
              aliases={row.people_aliases}
              noAlias={t.noAlias}
            />
          ),
        },
        { key: "id", label: c.id },
        {
          key: "delete",
          label: c.delete,
          show: (_value, row) => {
            const title = typeof row.title === "string" ? row.title : "";
            return (
              <DeleteItemButton
                label={t.actions.deleteLabel(title)}
                dialogTitle={t.actions.deleteTitle(title)}
                message={t.actions.deleteMessage}
                confirmLabel={t.actions.confirm}
                cancelLabel={t.actions.cancel}
                errorMessage={t.actions.deleteFailed}
                onDelete={() => actions.deleteRecipe(String(row.id))}
              />
            );
          },
        },
      ];
    }
    case "users": {
      const c = t.columns.users;
      return [
        {
          key: "alias",
          label: c.alias,
          show: (v) => (typeof v === "string" ? v : t.noAlias),
        },
        { key: "open_sessions", label: c.openSessions },
        { key: "newest_session_at", label: c.newestSessionAt, show: date },
        { key: "recipes_authored", label: c.recipesAuthored },
        { key: "latest_recipe_at", label: c.latestRecipeAt, show: date },
        { key: "carts_created", label: c.cartsCreated },
        { key: "carts_edited", label: c.cartsEdited },
        { key: "carts_closed", label: c.cartsClosed },
        {
          key: "latest_cart_action_at",
          label: c.latestCartActionAt,
          show: date,
        },
        { key: "id", label: c.id },
      ];
    }
    case "refused-sites": {
      const c = t.columns.refusedSites;
      return [
        { key: "domain", label: c.domain },
        { key: "total_refusals", label: c.totalRefusals },
        { key: "distinct_members", label: c.distinctMembers },
        { key: "first_seen_at", label: c.firstSeenAt, show: date },
        { key: "last_seen_at", label: c.lastSeenAt, show: date },
        { key: "last_status", label: c.lastStatus },
        {
          key: "last_message",
          label: c.lastMessage,
          // The site's own text: a React text node, so it is never read as HTML (spec 067 R7).
          show: (v) => (
            <span className="block max-w-[28rem] min-w-[12rem] break-words whitespace-normal">
              {typeof v === "string" && v ? v : t.none}
            </span>
          ),
        },
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
  if (rows.length === 0)
    return <p className="m-0 text-[0.9rem] text-muted">{empty}</p>;
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
            <tr
              key={
                typeof row.id === "string"
                  ? row.id
                  : typeof row.domain === "string"
                    ? row.domain
                    : index
              }
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`border-b border-border px-3 py-2 text-foreground ${WRAPPING.has(column.key) ? "" : "whitespace-nowrap"
                    }`}
                >
                  {column.show
                    ? column.show(row[column.key], row)
                    : String(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
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
      <TabList label={t.tabsLabel}>
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
