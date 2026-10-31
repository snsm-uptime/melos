/** Client helpers for the kitchen shopping list via the same-origin BFF (specs 023, 025, contracts/shopping-list-api.md). */

export type ShoppingAmount = {
  /** A string, so no precision is lost: whole for counts, at most 2 decimals otherwise. */
  quantity: string;
  unit: string;
};

export type ShoppingRecipeRef = {
  recipe_id: string;
  title: string;
  /** False when a saved chip's recipe is gone. Absent means it exists. */
  exists?: boolean;
};

export type ShoppingLine = {
  name: string;
  kind: "mass" | "volume" | "count";
  /** Counts only. */
  size: "small" | "medium" | "large" | null;
  amounts: ShoppingAmount[];
  recipes: ShoppingRecipeRef[];
};

export type YourCallEntry = {
  name: string;
  notes: string[];
  recipes: ShoppingRecipeRef[];
};

/** An item a member added by hand. */
export type HandItem = {
  id: string;
  name: string;
  quantity: string | null;
  unit: string | null;
  size: "small" | "medium" | "large" | null;
};

export type ShoppingList = {
  /** True when there are no cart recipes and no saved items. */
  is_empty: boolean;
  /** live: built from the cart, not saved. active: saved. draft: my unsaved cart. */
  status: "live" | "active" | "draft";
  list_id: string | null;
  kitchen_is_archived: boolean;
  lines: ShoppingLine[];
  your_call: YourCallEntry[];
  hand_items: HandItem[];
};

export type ClosedListSummary = {
  id: string;
  /** YYYY-MM-DD. */
  closing_date: string;
  recipe_titles: string[];
};

export type ClosedList = {
  id: string;
  closing_date: string;
  lines: ShoppingLine[];
  your_call: YourCallEntry[];
  hand_items: HandItem[];
};

export type NewHandItem = { name: string; quantity?: string; unit?: string };

/** A refused call keeps the status and the api `code`. A network failure has status 0 and no code. */
export type ShoppingListFailure = { ok: false; status: number; code: string | null };

export type ShoppingResult<T> = { ok: true; value: T } | ShoppingListFailure;
export type ShoppingListResult = ShoppingResult<ShoppingList>;

function asShoppingList(data: unknown): ShoppingList | null {
  if (!data || typeof data !== "object") return null;
  const list = data as Partial<Record<keyof ShoppingList, unknown>>;
  if (typeof list.is_empty !== "boolean" || !Array.isArray(list.lines)) return null;
  return {
    is_empty: list.is_empty,
    status: list.status === "active" || list.status === "draft" ? list.status : "live",
    list_id: typeof list.list_id === "string" ? list.list_id : null,
    kitchen_is_archived: list.kitchen_is_archived === true,
    lines: list.lines as ShoppingLine[],
    your_call: Array.isArray(list.your_call) ? (list.your_call as YourCallEntry[]) : [],
    hand_items: Array.isArray(list.hand_items) ? (list.hand_items as HandItem[]) : [],
  };
}

function asClosedList(data: unknown): ClosedList | null {
  if (!data || typeof data !== "object") return null;
  const list = data as Partial<Record<keyof ClosedList, unknown>>;
  if (typeof list.id !== "string" || typeof list.closing_date !== "string") return null;
  return {
    id: list.id,
    closing_date: list.closing_date,
    lines: Array.isArray(list.lines) ? (list.lines as ShoppingLine[]) : [],
    your_call: Array.isArray(list.your_call) ? (list.your_call as YourCallEntry[]) : [],
    hand_items: Array.isArray(list.hand_items) ? (list.hand_items as HandItem[]) : [],
  };
}

function asClosedLists(data: unknown): ClosedListSummary[] | null {
  const items = (data as { items?: unknown } | null)?.items;
  return Array.isArray(items) ? (items as ClosedListSummary[]) : null;
}

async function call<T>(
  path: string,
  method: "GET" | "POST" | "DELETE",
  body: unknown,
  parse: (data: unknown) => T | null,
): Promise<ShoppingResult<T>> {
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
  let value: T | null = null;
  try {
    value = parse(await response.json());
  } catch {
    value = null;
  }
  if (value === null) return { ok: false, status: response.status, code: null };
  return { ok: true, value };
}

function listPath(kitchenId: string): string {
  return `/api/kitchens/${encodeURIComponent(kitchenId)}/shopping-list`;
}

function closedPath(kitchenId: string): string {
  return `/api/kitchens/${encodeURIComponent(kitchenId)}/shopping-lists`;
}

export function fetchShoppingList(kitchenId: string): Promise<ShoppingListResult> {
  return call(listPath(kitchenId), "GET", undefined, asShoppingList);
}

export function addShoppingItem(
  kitchenId: string,
  item: NewHandItem,
): Promise<ShoppingListResult> {
  return call(`${listPath(kitchenId)}/items`, "POST", item, asShoppingList);
}

export function removeShoppingItem(
  kitchenId: string,
  itemId: string,
): Promise<ShoppingListResult> {
  return call(
    `${listPath(kitchenId)}/items/${encodeURIComponent(itemId)}`,
    "DELETE",
    undefined,
    asShoppingList,
  );
}

export function closeShoppingList(
  kitchenId: string,
  listId: string,
): Promise<ShoppingResult<ClosedList>> {
  return call(`${listPath(kitchenId)}/done`, "POST", { list_id: listId }, asClosedList);
}

export function fetchClosedLists(kitchenId: string): Promise<ShoppingResult<ClosedListSummary[]>> {
  return call(closedPath(kitchenId), "GET", undefined, asClosedLists);
}

export function fetchClosedList(
  kitchenId: string,
  listId: string,
): Promise<ShoppingResult<ClosedList>> {
  return call(
    `${closedPath(kitchenId)}/${encodeURIComponent(listId)}`,
    "GET",
    undefined,
    asClosedList,
  );
}
