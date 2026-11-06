"use client";

import { useEffect, useState, type FormEvent } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import { CountChips } from "@/components/Chip";
import { useChromeHeader } from "@/components/ChromeBack";
import { DataTable, type TableSchema } from "@/components/DataTable";
import { SearchableSelect } from "@/components/SearchableSelect";
import type { Locale } from "@/lib/i18n/locale";
import { placesMessages } from "@/lib/i18n/places";
import { tableMessages } from "@/lib/i18n/table";
import {
  addPlace,
  allPlaces,
  copyPlaces,
  deletePlace,
  fetchIngredientPlaces,
  fetchPlaces,
  fetchPlaceSources,
  placeFromKey,
  placeKey,
  placeLabel,
  renamePlace,
  setIngredientPlace,
  type CustomPlace,
  type IngredientPlace,
  type PlaceRef,
  type PlaceSource,
} from "@/lib/places";

const FIELD =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-[1rem] text-foreground";
const BUTTON =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-4 text-[0.9rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50";

type Data = { ingredients: IngredientPlace[]; custom: CustomPlace[]; sources: PlaceSource[] };
type State = { status: "loading" } | { status: "ready"; data: Data } | { status: "error" };

/** The ingredients table: name, place (a picker), last use and the recipes that use it. */
function ingredientsTable(
  t: (typeof placesMessages)[Locale],
  locale: Locale,
  places: PlaceRef[],
  choose: (item: IngredientPlace, value: string) => void,
): TableSchema<IngredientPlace> {
  const c = t.columns;
  const options = places.map((p) => ({ value: placeKey(p), label: placeLabel(p, locale) }));
  return {
    search: true,
    rowKey: (row) => row.name,
    columns: [
      { key: "name", label: c.name, sort: "text", searchable: true },
      {
        key: "place",
        label: c.place,
        sort: "text",
        searchable: true,
        value: (row) => placeLabel(row.place, locale),
        cell: (row) => (
          <SearchableSelect
            aria-label={t.placeFor(row.name)}
            value={placeKey(row.place)}
            options={options}
            panelWidth={224}
            searchLabel={t.searchPlaces}
            noResults={t.noPlaceMatch}
            onChange={(value) => choose(row, value)}
          />
        ),
      },
      {
        key: "last_used_at",
        label: c.lastUsed,
        sort: "date",
        cell: (row) =>
          row.last_used_at ? new Date(row.last_used_at).toLocaleDateString(locale) : t.never,
      },
      {
        key: "recipes",
        label: c.recipes,
        sort: "number",
        searchable: true,
        wrap: true,
        value: (row) => row.recipes.length,
        searchValue: (row) => row.recipes.map((r) => r.title),
        cell: (row) => (
          <CountChips
            count={row.recipes.length}
            names={row.recipes.map((r) => ({
              label: r.title,
              // The recipe page's Back returns here (safeReturnPath).
              href: `/recipes/${encodeURIComponent(r.id)}?from=${encodeURIComponent("/ingredients")}`,
            }))}
          />
        ),
      },
    ],
  };
}

function nameError(code: string | null, t: (typeof placesMessages)[Locale]): string {
  if (code === "place_name_taken") return t.nameTaken;
  if (code === "place_limit") return t.limit;
  if (code === "place_name_invalid") return t.nameInvalid;
  return t.saveError;
}

async function load(): Promise<State> {
  const [ingredients, places, sources] = await Promise.all([
    fetchIngredientPlaces(),
    fetchPlaces(),
    fetchPlaceSources(),
  ]);
  if (!ingredients.ok || !places.ok) return { status: "error" };
  return {
    status: "ready",
    data: {
      ingredients: ingredients.value,
      custom: places.value.custom,
      sources: sources.ok ? sources.value : [],
    },
  };
}

/**
 * The Ingredients page (spec 070 US2): where the person buys each ingredient, their own places,
 * and a copy of another member's places. Every choice is the person's own (FR-010).
 */
export function IngredientsScreen({ locale }: { locale: Locale }) {
  const t = placesMessages[locale];
  useChromeHeader({ title: t.title });
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    void load().then((next) => {
      if (current) setState(next);
    });
    return () => {
      current = false;
    };
  }, [attempt]);

  const reload = () => setAttempt((n) => n + 1);

  if (state.status === "loading") return <CauldronLoader label={t.loading} />;
  if (state.status === "error") {
    return (
      <div className="flex flex-col items-start gap-2">
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.loadError}
        </p>
        <button
          type="button"
          className={BUTTON}
          onClick={() => {
            setState({ status: "loading" });
            reload();
          }}
        >
          {t.retry}
        </button>
      </div>
    );
  }

  const { data } = state;
  const places = allPlaces(data.custom, locale);

  async function choose(item: IngredientPlace, value: string) {
    const place = placeFromKey(value, places);
    if (!place || state.status !== "ready") return;
    setError(null);
    const before = state.data;
    // Shown at once, put back if the api refuses.
    setState({
      status: "ready",
      data: {
        ...before,
        ingredients: before.ingredients.map((i) => (i.name === item.name ? { ...i, place } : i)),
      },
    });
    const result = await setIngredientPlace(item.name, place);
    if (!result.ok) {
      setState({ status: "ready", data: before });
      setError(t.saveError);
    }
  }

  return (
    <section className="flex min-w-0 flex-col gap-4">
      <p className="m-0 text-[0.95rem] text-muted">{t.intro}</p>
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="m-0 text-[0.9rem] text-foreground" role="status">
          {notice}
        </p>
      ) : null}

      <DataTable
        schema={ingredientsTable(t, locale, places, (item, value) => void choose(item, value))}
        rows={data.ingredients}
        locale={locale}
        labels={tableMessages[locale]}
        empty={t.noIngredients}
      />

      <MyPlaces
        locale={locale}
        custom={data.custom}
        onChanged={() => {
          setNotice(null);
          reload();
        }}
      />
      <CopyPlaces
        locale={locale}
        sources={data.sources}
        onCopied={() => {
          setNotice(t.copied);
          reload();
        }}
      />
    </section>
  );
}

function MyPlaces({
  locale,
  custom,
  onChanged,
}: {
  locale: Locale;
  custom: CustomPlace[];
  onChanged: () => void;
}) {
  const t = placesMessages[locale];
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState<CustomPlace | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    const result = await addPlace(name);
    setPending(false);
    if (result.ok) {
      setName("");
      onChanged();
    } else setError(nameError(result.code, t));
  }

  async function rename(event: FormEvent) {
    event.preventDefault();
    if (pending || !editing) return;
    setPending(true);
    setError(null);
    const result = await renamePlace(editing.id, editing.name);
    setPending(false);
    if (result.ok) {
      setEditing(null);
      onChanged();
    } else setError(nameError(result.code, t));
  }

  async function remove() {
    if (!deleting) return;
    setPending(true);
    setError(null);
    const result = await deletePlace(deleting.id);
    setPending(false);
    setDeleting(null);
    if (result.ok) onChanged();
    else setError(t.saveError);
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="m-0 text-[1.05rem] font-[600] text-foreground">{t.myPlaces}</h2>
      {custom.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {custom.map((place) => (
            <li
              key={place.id}
              className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-border bg-surface p-3"
            >
              {editing?.id === place.id ? (
                <form className="flex flex-1 flex-wrap gap-2" onSubmit={(e) => void rename(e)}>
                  <input
                    className={`${FIELD} min-w-0 flex-1`}
                    aria-label={t.renamePlace(place.name)}
                    maxLength={40}
                    value={editing.name}
                    onChange={(e) => setEditing({ id: place.id, name: e.target.value })}
                  />
                  <button type="submit" className={BUTTON} disabled={pending}>
                    {t.save}
                  </button>
                  <button type="button" className={BUTTON} onClick={() => setEditing(null)}>
                    {t.cancel}
                  </button>
                </form>
              ) : (
                <>
                  <span className="min-w-0 flex-1 break-words text-[1rem] text-foreground">
                    {place.name}
                  </span>
                  <button
                    type="button"
                    className={BUTTON}
                    onClick={() => setEditing({ id: place.id, name: place.name })}
                  >
                    {t.renamePlace(place.name)}
                  </button>
                  <button type="button" className={BUTTON} onClick={() => setDeleting(place)}>
                    {t.deletePlace(place.name)}
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => void add(e)}>
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-[0.85rem] text-muted">
          {t.newPlace}
          <input
            className={FIELD}
            maxLength={40}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <button type="submit" className={BUTTON} disabled={pending || name.trim() === ""}>
          {t.addPlace}
        </button>
      </form>
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {error}
        </p>
      ) : null}
      <ActionDialog
        open={deleting !== null}
        title={deleting ? t.deleteTitle(deleting.name) : ""}
        confirmLabel={t.delete}
        cancelLabel={t.cancel}
        pending={pending}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        onConfirm={() => void remove()}
      >
        {t.deleteBody}
      </ActionDialog>
    </div>
  );
}

function CopyPlaces({
  locale,
  sources,
  onCopied,
}: {
  locale: Locale;
  sources: PlaceSource[];
  onCopied: () => void;
}) {
  const t = placesMessages[locale];
  const [source, setSource] = useState("");
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const chosen = sources.find((s) => s.user_id === source) ?? null;

  async function copy() {
    if (!chosen) return;
    setPending(true);
    setError(false);
    const result = await copyPlaces(chosen.user_id);
    setPending(false);
    setOpen(false);
    if (result.ok) {
      setSource("");
      onCopied();
    } else setError(true);
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="m-0 text-[1.05rem] font-[600] text-foreground">{t.copyTitle}</h2>
      <p className="m-0 text-[0.9rem] text-muted">{t.copyHelp}</p>
      {sources.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">{t.noSources}</p>
      ) : (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex min-w-[12rem] flex-col gap-1 text-[0.85rem] text-muted">
            {t.copyFrom}
            <select className={FIELD} value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="" />
              {sources.map((s) => (
                <option key={s.user_id} value={s.user_id}>
                  {s.alias}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={BUTTON}
            disabled={!chosen}
            onClick={() => setOpen(true)}
          >
            {t.copy}
          </button>
        </div>
      )}
      {error ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {t.saveError}
        </p>
      ) : null}
      <ActionDialog
        open={open}
        title={chosen ? t.copyConfirmTitle(chosen.alias) : ""}
        confirmLabel={t.copy}
        cancelLabel={t.cancel}
        pending={pending}
        onOpenChange={setOpen}
        onConfirm={() => void copy()}
      >
        {t.copyConfirmBody}
      </ActionDialog>
    </div>
  );
}
