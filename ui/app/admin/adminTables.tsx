/** The dashboard's five table schemas (spec 066 research R7), over spec 055's admin API rows. */

import { CheckIcon, CloseIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import type { ColumnDef, TableSchema } from "@/components/DataTable";
import { DeleteItemButton } from "@/components/DeleteItemButton";
import type { adminMessages } from "@/lib/i18n/admin";
import type { Locale } from "@/lib/i18n/locale";

type Messages = (typeof adminMessages)[Locale];
type Alias = string | null;

export type UnitRow = {
  name: string;
  user_references: string[];
  user_aliases: Alias[];
  reference_count: number;
  is_default: boolean;
  created_at: string | null;
};

export type IngredientRow = { name: string; recipes: number; people: number };

export type RecipeRow = {
  id: string;
  title: string;
  cart_adds: number;
  notebook_name: string;
  notebook_kind: "kitchen" | "personal";
  people_with_access: number;
  people_aliases: Alias[];
};

export type UserRow = {
  id: string;
  alias: Alias;
  open_sessions: number;
  newest_session_at: string | null;
  recipes_authored: number;
  latest_recipe_at: string | null;
  carts_created: number;
  carts_edited: number;
  carts_closed: number;
  latest_cart_action_at: string | null;
};

export type RefusedSiteRow = {
  domain: string;
  total_refusals: number;
  distinct_members: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  last_status: number | null;
  last_message: string | null;
};

export type AdminActions = { deleteRecipe: (id: string) => Promise<boolean> };

/** The count of people with access, then the aliases of each as a row of chips that scrolls. */
function PeopleWithAccess({
  count,
  aliases,
  noAlias,
}: {
  count: number;
  aliases: Alias[] | undefined;
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

function dateColumn<T>(
  key: keyof T & string,
  label: string,
  t: Messages,
  locale: Locale,
): ColumnDef<T> {
  return {
    key,
    label,
    sort: "date",
    cell: (row) => {
      const value = row[key];
      return typeof value === "string"
        ? new Date(value).toLocaleDateString(locale)
        : t.none;
    },
  };
}

export function unitsTable(t: Messages, locale: Locale): TableSchema<UnitRow> {
  const c = t.columns.units;
  return {
    search: true,
    rowKey: (row) => row.name,
    columns: [
      { key: "name", label: c.name, sort: "text", searchable: true },
      { key: "reference_count", label: c.referenceCount, sort: "number" },
      {
        key: "is_default",
        label: c.isDefault,
        sort: "number",
        value: (row) => (row.is_default ? 1 : 0),
        cell: (row) => (
          <span
            role="img"
            aria-label={row.is_default ? t.yes : t.no}
            className={`inline-flex align-middle ${row.is_default ? "text-accent" : "text-error"}`}
          >
            {row.is_default ? <CheckIcon /> : <CloseIcon />}
          </span>
        ),
      },
      dateColumn<UnitRow>("created_at", c.createdAt, t, locale),
      {
        // Not sortable: its number is the Count column.
        key: "user_references",
        label: c.userReferences,
        sort: false,
        searchable: true,
        wrap: true,
        searchValue: (row) => row.user_aliases,
        cell: (row) => (
          <PeopleWithAccess
            count={row.reference_count}
            aliases={row.user_aliases}
            noAlias={t.noAlias}
          />
        ),
      },
    ],
  };
}

export function ingredientsTable(t: Messages): TableSchema<IngredientRow> {
  const c = t.columns.ingredients;
  return {
    search: true,
    rowKey: (row) => row.name,
    columns: [
      { key: "name", label: c.name, sort: "text", searchable: true },
      { key: "recipes", label: c.recipes, sort: "number" },
      { key: "people", label: c.people, sort: "number" },
    ],
  };
}

export function recipesTable(
  t: Messages,
  actions: AdminActions,
): TableSchema<RecipeRow> {
  const c = t.columns.recipes;
  const kind = (row: RecipeRow) =>
    row.notebook_kind === "kitchen" ? t.kinds.kitchen : t.kinds.personal;
  return {
    search: true,
    rowKey: (row) => row.id,
    columns: [
      { key: "title", label: c.title, sort: "text", searchable: true },
      { key: "cart_adds", label: c.cartAdds, sort: "number" },
      {
        key: "notebook_name",
        label: c.notebookName,
        sort: "text",
        searchable: true,
      },
      {
        key: "notebook_kind",
        label: c.notebookKind,
        sort: "text",
        searchable: true,
        value: kind,
        cell: kind,
      },
      {
        key: "people_with_access",
        label: c.peopleWithAccess,
        sort: "number",
        searchable: true,
        searchValue: (row) => row.people_aliases,
        cell: (row) => (
          <PeopleWithAccess
            count={row.people_with_access}
            aliases={row.people_aliases}
            noAlias={t.noAlias}
          />
        ),
      },
      { key: "id", label: c.id, sort: "text", searchable: true },
      {
        key: "delete",
        label: c.delete,
        sort: false,
        cell: (row) => (
          <DeleteItemButton
            label={t.actions.deleteLabel(row.title)}
            dialogTitle={t.actions.deleteTitle(row.title)}
            message={t.actions.deleteMessage}
            confirmLabel={t.actions.confirm}
            cancelLabel={t.actions.cancel}
            errorMessage={t.actions.deleteFailed}
            onDelete={() => actions.deleteRecipe(row.id)}
          />
        ),
      },
    ],
  };
}

export function usersTable(t: Messages, locale: Locale): TableSchema<UserRow> {
  const c = t.columns.users;
  return {
    search: true,
    rowKey: (row) => row.id,
    columns: [
      {
        key: "alias",
        label: c.alias,
        sort: "text",
        searchable: true,
        cell: (row) => row.alias ?? t.noAlias,
      },
      { key: "open_sessions", label: c.openSessions, sort: "number" },
      dateColumn<UserRow>("newest_session_at", c.newestSessionAt, t, locale),
      { key: "recipes_authored", label: c.recipesAuthored, sort: "number" },
      dateColumn<UserRow>("latest_recipe_at", c.latestRecipeAt, t, locale),
      { key: "carts_created", label: c.cartsCreated, sort: "number" },
      { key: "carts_edited", label: c.cartsEdited, sort: "number" },
      { key: "carts_closed", label: c.cartsClosed, sort: "number" },
      dateColumn<UserRow>(
        "latest_cart_action_at",
        c.latestCartActionAt,
        t,
        locale,
      ),
      { key: "id", label: c.id, sort: "text", searchable: true },
    ],
  };
}

export function refusedSitesTable(
  t: Messages,
  locale: Locale,
): TableSchema<RefusedSiteRow> {
  const c = t.columns.refusedSites;
  return {
    search: true,
    rowKey: (row) => row.domain,
    columns: [
      { key: "domain", label: c.domain, sort: "text", searchable: true },
      { key: "total_refusals", label: c.totalRefusals, sort: "number" },
      { key: "distinct_members", label: c.distinctMembers, sort: "number" },
      dateColumn<RefusedSiteRow>("first_seen_at", c.firstSeenAt, t, locale),
      dateColumn<RefusedSiteRow>("last_seen_at", c.lastSeenAt, t, locale),
      {
        key: "last_status",
        label: c.lastStatus,
        sort: "number",
        cell: (row) =>
          row.last_status === null ? t.none : String(row.last_status),
      },
      {
        key: "last_message",
        label: c.lastMessage,
        sort: false,
        searchable: true,
        wrap: true,
        // The site's own text: a React text node, so it is never read as HTML (spec 067 R7).
        cell: (row) => (
          <span className="block max-w-[28rem] min-w-[12rem] break-words whitespace-normal">
            {row.last_message ? row.last_message : t.none}
          </span>
        ),
      },
    ],
  };
}
