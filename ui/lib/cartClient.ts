/** Client helpers for the kitchen cart via the same-origin BFF (spec 022, contracts/cart-api.md). */

export type CartEntry = {
  recipe_id: string;
  title: string;
  notebook_id: string;
  notebook_name: string;
  base_servings: number;
  meals: number;
  factor: string;
};

export type CartEditor = {
  /** Null when the editor has no alias; shown as "unknown". */
  alias: string | null;
  is_me: boolean;
  /** Only for my own lock: when it ends without activity. */
  idle_expires_at: string | null;
};

export type CartDraft = {
  people: number;
  people_is_default: boolean;
  entries: CartEntry[];
  dropped_recipe_ids: string[];
};

export type Cart = {
  kitchen_id: string;
  people: number;
  people_is_default: boolean;
  entries: CartEntry[];
  editor: CartEditor | null;
  draft: CartDraft | null;
  can_edit: boolean;
  /** Only in the answer to a save. */
  dropped_recipe_ids?: string[];
};

export type CartDraftBody = {
  /** Null keeps following the member count. */
  people: number | null;
  items: { recipe_id: string; meals: number }[];
};

/**
 * A refused call keeps the status and the api `code`, plus `editor_alias` (cart_locked) and
 * `field` (invalid_value). A network failure has status 0 and no code.
 */
export type CartFailure = {
  ok: false;
  status: number;
  code: string | null;
  editorAlias?: string | null;
  field?: string;
};

export type CartResult<T> = { ok: true; value: T } | CartFailure;

function asCart(data: unknown): Cart | null {
  if (!data || typeof data !== "object") return null;
  const cart = data as Partial<Record<keyof Cart, unknown>>;
  if (
    typeof cart.kitchen_id !== "string" ||
    typeof cart.people !== "number" ||
    !Array.isArray(cart.entries) ||
    typeof cart.can_edit !== "boolean"
  ) {
    return null;
  }
  return data as Cart;
}

async function call<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body: unknown,
  parse: (data: unknown) => T | null,
): Promise<CartResult<T>> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, code: null };
  }
  if (!response.ok) {
    let data: { code?: unknown; editor_alias?: unknown; field?: unknown } = {};
    try {
      data = (await response.json()) as typeof data;
    } catch {
      data = {};
    }
    const failure: CartFailure = {
      ok: false,
      status: response.status,
      code: typeof data.code === "string" ? data.code : null,
    };
    if ("editor_alias" in data) {
      failure.editorAlias = typeof data.editor_alias === "string" ? data.editor_alias : null;
    }
    if (typeof data.field === "string") failure.field = data.field;
    return failure;
  }
  let value: T | null = null;
  try {
    value = parse(response.status === 204 ? true : await response.json());
  } catch {
    value = null;
  }
  if (value === null) return { ok: false, status: response.status, code: null };
  return { ok: true, value };
}

function base(kitchenId: string): string {
  return `/api/kitchens/${encodeURIComponent(kitchenId)}/cart`;
}

export function fetchCart(kitchenId: string): Promise<CartResult<Cart>> {
  return call("GET", base(kitchenId), undefined, asCart);
}

/** Take the cart lock, or keep it alive for its holder. */
export function startCartEdit(kitchenId: string): Promise<CartResult<Cart>> {
  return call("POST", `${base(kitchenId)}/edit`, undefined, asCart);
}

export function putCartDraft(kitchenId: string, draft: CartDraftBody): Promise<CartResult<Cart>> {
  return call("PUT", `${base(kitchenId)}/draft`, draft, asCart);
}

export function addDraftItem(kitchenId: string, recipeId: string): Promise<CartResult<Cart>> {
  return call("POST", `${base(kitchenId)}/draft/items`, { recipe_id: recipeId }, asCart);
}

export function removeDraftItem(kitchenId: string, recipeId: string): Promise<CartResult<Cart>> {
  return call(
    "DELETE",
    `${base(kitchenId)}/draft/items/${encodeURIComponent(recipeId)}`,
    undefined,
    asCart,
  );
}

export function saveCart(kitchenId: string): Promise<CartResult<Cart>> {
  return call("POST", `${base(kitchenId)}/save`, undefined, asCart);
}

export function discardCart(kitchenId: string): Promise<CartResult<true>> {
  return call("DELETE", `${base(kitchenId)}/edit`, undefined, (data) =>
    data === true ? true : null,
  );
}

/** The recipes in the cart as I see it: my draft while I edit, else the saved cart. */
export function cartRecipeIds(cart: Cart): Set<string> {
  const entries = cart.editor?.is_me && cart.draft ? cart.draft.entries : cart.entries;
  return new Set(entries.map((entry) => entry.recipe_id));
}
