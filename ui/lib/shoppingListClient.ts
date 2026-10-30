/** Client helper for the kitchen shopping list via the same-origin BFF (spec 023, contracts/shopping-list-api.md). */

export type ShoppingAmount = {
  /** A string, so no precision is lost: whole for counts, at most 2 decimals otherwise. */
  quantity: string;
  unit: string;
};

export type ShoppingRecipeRef = {
  recipe_id: string;
  title: string;
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

export type ShoppingList = {
  /** True when the cart has no recipes. */
  is_empty: boolean;
  lines: ShoppingLine[];
  your_call: YourCallEntry[];
};

/** A refused call keeps the status and the api `code`. A network failure has status 0 and no code. */
export type ShoppingListFailure = { ok: false; status: number; code: string | null };

export type ShoppingListResult = { ok: true; value: ShoppingList } | ShoppingListFailure;

function asShoppingList(data: unknown): ShoppingList | null {
  if (!data || typeof data !== "object") return null;
  const list = data as Partial<Record<keyof ShoppingList, unknown>>;
  if (typeof list.is_empty !== "boolean" || !Array.isArray(list.lines)) return null;
  return {
    is_empty: list.is_empty,
    lines: list.lines as ShoppingLine[],
    your_call: Array.isArray(list.your_call) ? (list.your_call as YourCallEntry[]) : [],
  };
}

export async function fetchShoppingList(kitchenId: string): Promise<ShoppingListResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/shopping-list`, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
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
  let value: ShoppingList | null = null;
  try {
    value = asShoppingList(await response.json());
  } catch {
    value = null;
  }
  if (value === null) return { ok: false, status: response.status, code: null };
  return { ok: true, value };
}
