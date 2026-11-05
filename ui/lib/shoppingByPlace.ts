/**
 * Store tabs and bought order for a shopping list (spec 070 FR-005, FR-014, FR-015, research R9).
 * Pure: the list components call these, the tests check them directly.
 */

import type { Locale } from "@/lib/i18n/locale";
import { allPlaces, placeKey, placeLabel, type CustomPlace, type PlaceRef } from "@/lib/places";

export const ALL_TAB = "all";

type Placed = { bought?: boolean; place?: PlaceRef | null };

export type PlaceTab = { key: string; label: string; left: number };

type Sections<L, Y, H> = { lines: L[]; your_call: Y[]; hand_items: H[] };

/** A tab per place with at least one item, defaults first in their order, then own places by name. */
export function placeTabs<L extends Placed, Y extends Placed, H extends Placed>(
  list: Sections<L, Y, H> & { custom_places?: CustomPlace[] },
  locale: Locale,
): PlaceTab[] {
  const items: Placed[] = [...list.lines, ...list.your_call, ...list.hand_items];
  const known = allPlaces(list.custom_places ?? [], locale);
  // A custom place the list names but the viewer no longer has still gets its tab.
  for (const item of items) {
    if (item.place && !known.some((p) => placeKey(p) === placeKey(item.place))) {
      known.push(item.place);
    }
  }
  return known
    .map((place) => {
      const here = items.filter((item) => placeKey(item.place) === placeKey(place));
      return {
        key: placeKey(place),
        label: placeLabel(place, locale),
        total: here.length,
        left: here.filter((item) => !item.bought).length,
      };
    })
    .filter((tab) => tab.total > 0)
    .map(({ key, label, left }) => ({ key, label, left }));
}

/** Items of the chosen tab, not-bought first; the order within each half is kept. */
export function inTab<T extends Placed>(items: T[], tab: string): T[] {
  const shown = tab === ALL_TAB ? items : items.filter((item) => placeKey(item.place) === tab);
  return [...shown.filter((item) => !item.bought), ...shown.filter((item) => item.bought)];
}

/** True when the list has stored items and every one is bought (FR-001 scenario 5). */
export function everythingBought<L extends Placed, Y extends Placed, H extends Placed>(
  list: Sections<L, Y, H>,
): boolean {
  const items: Placed[] = [...list.lines, ...list.your_call, ...list.hand_items];
  return items.length > 0 && items.every((item) => item.bought);
}

/** The list with one item's flag changed, for the optimistic update. */
export function withBought<
  T extends Sections<L, Y, H>,
  L extends Placed & { id?: string | null },
  Y extends Placed & { id?: string | null },
  H extends Placed & { id?: string | null },
>(list: T, itemId: string, bought: boolean): T {
  const flip = <I extends { id?: string | null }>(items: I[]): I[] =>
    items.map((item) => (item.id === itemId ? { ...item, bought } : item));
  return {
    ...list,
    lines: flip(list.lines),
    your_call: flip(list.your_call),
    hand_items: flip(list.hand_items),
  };
}
