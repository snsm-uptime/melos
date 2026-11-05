/** Places to buy things (spec 070): types, labels, tab order and the BFF calls for /me/places. */

import type { Locale } from "@/lib/i18n/locale";
import { placesMessages } from "@/lib/i18n/places";

/** The api's default keys, in the order tabs are shown in (research R4, R9). */
export const PLACE_ORDER = [
  "supermarket",
  "farmers_market",
  "butcher",
  "fish_market",
  "bakery",
  "pharmacy",
  "other",
] as const;

export type DefaultPlaceKey = (typeof PLACE_ORDER)[number];

export type PlaceRef =
  | { kind: "default"; key: DefaultPlaceKey; id?: null; name?: null }
  | { kind: "custom"; id: string; name: string; key?: null };

export type CustomPlace = { id: string; name: string };

export const SUPERMARKET: PlaceRef = { kind: "default", key: "supermarket" };

/** One string per place, for tab ids, select values and grouping. */
export function placeKey(place: PlaceRef | null | undefined): string {
  if (!place) return "default:supermarket";
  return place.kind === "default" ? `default:${place.key}` : `custom:${place.id}`;
}

export function placeLabel(place: PlaceRef, locale: Locale): string {
  return place.kind === "default" ? placesMessages[locale].defaults[place.key] : place.name;
}

/** Every place a person can pick: the defaults in order, then their own places by name. */
export function allPlaces(custom: CustomPlace[], locale: Locale): PlaceRef[] {
  const own = [...custom]
    .sort((a, b) => a.name.localeCompare(b.name, locale))
    .map((p): PlaceRef => ({ kind: "custom", id: p.id, name: p.name }));
  return [...PLACE_ORDER.map((key): PlaceRef => ({ kind: "default", key })), ...own];
}

/** The place a picker value stands for, among `places`. */
export function placeFromKey(value: string, places: PlaceRef[]): PlaceRef | null {
  return places.find((p) => placeKey(p) === value) ?? null;
}

/** The body the api takes for a place (contracts/places.md). */
export function placeBody(place: PlaceRef): { kind: string; key?: string; id?: string } {
  return place.kind === "default" ? { kind: "default", key: place.key } : { kind: "custom", id: place.id };
}

export type IngredientPlace = { name: string; place: PlaceRef };
export type PlaceSource = { user_id: string; alias: string };

export type PlacesFailure = { ok: false; status: number; code: string | null };
export type PlacesResult<T> = { ok: true; value: T } | PlacesFailure;

async function call<T>(
  path: string,
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
): Promise<PlacesResult<T>> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: {
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      credentials: "same-origin",
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch {
    return { ok: false, status: 0, code: null };
  }
  if (!response.ok) {
    let code: unknown = null;
    try {
      code = ((await response.json()) as { code?: unknown }).code;
    } catch {
      code = null;
    }
    return { ok: false, status: response.status, code: typeof code === "string" ? code : null };
  }
  if (response.status === 204) return { ok: true, value: undefined as T };
  try {
    return { ok: true, value: (await response.json()) as T };
  } catch {
    return { ok: false, status: response.status, code: null };
  }
}

export type PlacesBody = { defaults: string[]; custom: CustomPlace[] };

export function fetchPlaces(): Promise<PlacesResult<PlacesBody>> {
  return call("/api/me/places", "GET");
}

export function addPlace(name: string): Promise<PlacesResult<CustomPlace>> {
  return call("/api/me/places", "POST", { name });
}

export function renamePlace(id: string, name: string): Promise<PlacesResult<CustomPlace>> {
  return call(`/api/me/places/${encodeURIComponent(id)}`, "PATCH", { name });
}

export function deletePlace(id: string): Promise<PlacesResult<void>> {
  return call(`/api/me/places/${encodeURIComponent(id)}`, "DELETE");
}

export async function fetchIngredientPlaces(): Promise<PlacesResult<IngredientPlace[]>> {
  const result = await call<{ items: IngredientPlace[] }>("/api/me/ingredient-places", "GET");
  return result.ok ? { ok: true, value: result.value.items } : result;
}

export function setIngredientPlace(
  name: string,
  place: PlaceRef,
): Promise<PlacesResult<IngredientPlace>> {
  return call("/api/me/ingredient-places", "PUT", { name, place: placeBody(place) });
}

export async function fetchPlaceSources(): Promise<PlacesResult<PlaceSource[]>> {
  const result = await call<{ items: PlaceSource[] }>("/api/me/place-sources", "GET");
  return result.ok ? { ok: true, value: result.value.items } : result;
}

export function copyPlaces(sourceUserId: string): Promise<PlacesResult<PlacesBody>> {
  return call("/api/me/places/copy", "POST", { source_user_id: sourceUserId });
}
