"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { CloseIcon, CopyIcon, LocationIcon, PlusIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { CauldronLoader } from "@/components/CauldronLoader";
import { CountChips } from "@/components/Chip";
import { useChromeHeader } from "@/components/ChromeBack";
import { DataTable, type TableSchema } from "@/components/DataTable";
import { IconButton } from "@/components/IconButton";
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
  startsDefaults,
  type CustomPlace,
  type IngredientPlace,
  type PlaceRef,
  type PlaceSource,
} from "@/lib/places";

const BUTTON =
  "min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-4 text-[0.9rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50";

/** A place card: the name field reads as text (like the recipe title while editing). */
const CARD =
  "flex max-w-full items-center gap-1 rounded-[var(--radius-md)] border border-border bg-surface py-1 pr-1 pl-2";
const CARD_FIELD =
  "min-w-[3ch] max-w-full field-sizing-content rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-[0.95rem] text-foreground outline-none placeholder:text-muted hover:bg-background focus:bg-background";
const CARD_BUTTON =
  "inline-flex size-8 shrink-0 items-center justify-center rounded-[0.4rem] text-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50 disabled:hover:text-muted";

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
  const options = places.map((p, i) => ({
    value: placeKey(p),
    label: placeLabel(p, locale),
    dividerBefore: startsDefaults(places, i),
  }));
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
  const [placesOpen, setPlacesOpen] = useState(false);
  // Memoised: the header keeps this element, and a new one each render would update it forever.
  const trailing = useMemo(
    () => (
      <IconButton
        variant="ghost"
        className="size-10"
        label={t.location}
        aria-haspopup="dialog"
        icon={<LocationIcon className="size-6" />}
        onClick={() => setPlacesOpen(true)}
      />
    ),
    [t.location],
  );
  useChromeHeader({ title: t.title, trailing });
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

      <ActionDialog
        open={placesOpen}
        title={t.placesSection}
        closeLabel={t.close}
        onOpenChange={setPlacesOpen}
      >
        <PlacesRow
          locale={locale}
          custom={data.custom}
          sources={data.sources}
          onChanged={() => {
            setNotice(null);
            reload();
          }}
          onCopied={() => {
            setNotice(t.copied);
            reload();
          }}
        />
      </ActionDialog>

      <DataTable
        schema={ingredientsTable(t, locale, places, (item, value) => void choose(item, value))}
        rows={data.ingredients}
        locale={locale}
        labels={tableMessages[locale]}
        empty={t.noIngredients}
      />
    </section>
  );
}

/**
 * The Places dialog's one row of cards: copy from a member first, then the card that adds a
 * place, then the person's places (their own and the ones copied).
 */
function PlacesRow({
  locale,
  custom,
  sources,
  onChanged,
  onCopied,
}: {
  locale: Locale;
  custom: CustomPlace[];
  sources: PlaceSource[];
  onChanged: () => void;
  onCopied: () => void;
}) {
  const t = placesMessages[locale];
  const [name, setName] = useState("");
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

  /** A rename from a card; false puts the card's old name back. */
  async function rename(place: CustomPlace, next: string): Promise<boolean> {
    if (next.trim() === "" || next.trim() === place.name) return false;
    setError(null);
    const result = await renamePlace(place.id, next);
    if (result.ok) {
      onChanged();
      return true;
    }
    setError(nameError(result.code, t));
    return false;
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
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        <li className="min-w-0 max-w-full">
          <CopyPlaces
            locale={locale}
            sources={sources}
            onCopied={onCopied}
            onError={() => setError(t.saveError)}
          />
        </li>
        <li className="min-w-0 max-w-full">
          <form className={CARD} onSubmit={(e) => void add(e)}>
            <input
              aria-label={t.newPlace}
              placeholder={t.namePlaceholder}
              maxLength={40}
              value={name}
              readOnly={pending}
              onChange={(e) => setName(e.target.value)}
              className={CARD_FIELD}
            />
            <button
              type="submit"
              aria-label={t.addPlace}
              title={t.addPlace}
              disabled={pending || name.trim() === ""}
              className={CARD_BUTTON}
            >
              <PlusIcon className="size-4" />
            </button>
          </form>
        </li>
        {custom.map((place) => (
          <li key={place.id} className="min-w-0 max-w-full">
            <PlaceCard
              place={place}
              renameLabel={t.renamePlace(place.name)}
              deleteLabel={t.deletePlace(place.name)}
              onRename={(next) => rename(place, next)}
              onDelete={() => setDeleting(place)}
            />
          </li>
        ))}
      </ul>
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

/**
 * One of the person's places as a small card. The name is a field that reads as text, like the
 * recipe title while editing: click it to rename, Enter or leaving saves, Escape puts it back.
 * The ✕ at the end asks before deleting.
 */
function PlaceCard({
  place,
  renameLabel,
  deleteLabel,
  onRename,
  onDelete,
}: {
  place: CustomPlace;
  renameLabel: string;
  deleteLabel: string;
  onRename: (next: string) => Promise<boolean>;
  onDelete: () => void;
}) {
  const [name, setName] = useState(place.name);
  // A rename saved elsewhere (or a reload) shows the new name.
  const [shown, setShown] = useState(place.name);
  if (shown !== place.name) {
    setShown(place.name);
    setName(place.name);
  }

  async function save() {
    if (name === place.name) return;
    if (!(await onRename(name))) setName(place.name);
  }

  return (
    <div className={CARD}>
      <input
        aria-label={renameLabel}
        maxLength={40}
        value={name}
        onChange={(e) => setName(e.target.value)}
        onBlur={() => void save()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            e.currentTarget.blur();
          } else if (e.key === "Escape") {
            setName(place.name);
          }
        }}
        className={CARD_FIELD}
      />
      <button
        type="button"
        aria-label={deleteLabel}
        title={deleteLabel}
        onClick={onDelete}
        className={CARD_BUTTON}
      >
        <CloseIcon className="size-4" />
      </button>
    </div>
  );
}

/** The "Copy from a member" card: pick a member, then the copy button asks before adding. */
function CopyPlaces({
  locale,
  sources,
  onCopied,
  onError,
}: {
  locale: Locale;
  sources: PlaceSource[];
  onCopied: () => void;
  onError: () => void;
}) {
  const t = placesMessages[locale];
  const [source, setSource] = useState("");
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const chosen = sources.find((s) => s.user_id === source) ?? null;

  async function copy() {
    if (!chosen) return;
    setPending(true);
    const result = await copyPlaces(chosen.user_id);
    setPending(false);
    setOpen(false);
    if (result.ok) {
      setSource("");
      onCopied();
    } else onError();
  }

  return (
    <div className={CARD} title={sources.length === 0 ? t.noSources : undefined}>
      <SearchableSelect
        aria-label={t.copyFrom}
        placeholder={t.copyFrom}
        value={source}
        disabled={sources.length === 0}
        options={sources.map((s) => ({ value: s.user_id, label: s.alias }))}
        searchLabel={t.searchMembers}
        noResults={t.noMemberMatch}
        onChange={(value) => setSource(value)}
        action={{
          icon: <CopyIcon className="size-4" />,
          label: t.copy,
          onClick: () => setOpen(true),
        }}
        className="min-h-8 rounded-[0.4rem] px-1 text-[0.95rem] text-foreground hover:bg-background disabled:opacity-50"
      />
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
