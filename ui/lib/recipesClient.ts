/** Client helpers for recipe lists via the same-origin BFF (spec 021 routes). */

import { getJson, type NotebookResult } from "@/lib/notebooksClient";

export type RecipeCard = {
  id: string;
  title: string;
  author_alias: string | null;
  ingredient_count: number;
  notebook_id: string;
  notebook_name: string;
  created_at: string;
};

export type RecipePage = {
  items: RecipeCard[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

function isCard(row: unknown): row is RecipeCard {
  if (!row || typeof row !== "object") return false;
  const card = row as Partial<Record<keyof RecipeCard, unknown>>;
  return (
    typeof card.id === "string" &&
    typeof card.title === "string" &&
    typeof card.ingredient_count === "number" &&
    typeof card.notebook_name === "string"
  );
}

function asPage(data: unknown): RecipePage | null {
  if (!data || typeof data !== "object") return null;
  const page = data as Partial<Record<keyof RecipePage, unknown>>;
  if (
    !Array.isArray(page.items) ||
    typeof page.page !== "number" ||
    typeof page.total_pages !== "number" ||
    typeof page.total !== "number"
  ) {
    return null;
  }
  if (!page.items.every(isCard)) return null;
  return data as RecipePage;
}

function query(page: number, q: string): string {
  const params = new URLSearchParams({ page: String(page) });
  if (q.trim()) params.set("q", q);
  return params.toString();
}

export function fetchNotebookRecipes(
  notebookId: string,
  page: number,
  q: string,
): Promise<NotebookResult<RecipePage>> {
  return getJson(
    `/api/notebooks/${encodeURIComponent(notebookId)}/recipes?${query(page, q)}`,
    asPage,
  );
}

export function fetchKitchenRecipes(
  kitchenId: string,
  page: number,
  q: string,
): Promise<NotebookResult<RecipePage>> {
  return getJson(
    `/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}/recipes?${query(page, q)}`,
    asPage,
  );
}

// --- One recipe: detail, edit and delete (spec 027) ---

export type RecipeLine = {
  name: string;
  vague: boolean;
  quantity: number | null;
  unit: string | null;
  size: string | null;
  preparation: string | null;
  note: string | null;
};

export type RecipeDetail = {
  id: string;
  title: string;
  base_servings: number;
  servings_estimated: boolean;
  author_alias: string | null;
  created_at: string;
  /** Sent back on save; the api refuses the save if the recipe changed since (FR-011). */
  version: string;
  notebook: { id: string; name: string; kind: "personal" | "kitchen"; kitchen_id: string | null };
  can_write: boolean;
  ingredient_lines: RecipeLine[];
  steps: string[];
  source: { type: string; url: string | null } | null;
  /** Who edits the recipe now (spec 022); null when nobody does. Absent from older answers. */
  editor?: LockEditor | null;
  /** Kitchen recipes only (null for personal notebooks): in the cart as I see it. */
  in_cart?: boolean | null;
  /** Kitchen recipes only: who edits the kitchen's cart. */
  cart_editor?: LockEditor | null;
};

/** The holder of an edit lock (spec 022). `idle_expires_at` is set only for my own lock. */
export type LockEditor = { alias: string | null; is_me: boolean; idle_expires_at: string | null };

export type NameMatch = { name: string; entry: string | null };

/** A refused change keeps what the member needs to fix: status, code, and the named problems. */
export type RecipeFailure = {
  ok: false;
  status: number;
  code: string | null;
  missing?: string[];
  lineProblems?: { name: string | null; kind: string }[];
  /** The other editor of a 409 recipe_locked (spec 022). */
  editorAlias?: string | null;
};

export type RecipeResult<T> = { ok: true; value: T } | RecipeFailure;

export type RecipeUpdateBody = {
  version: string;
  title: string;
  base_servings: number;
  servings_estimated: boolean;
  ingredient_lines: RecipeLine[];
  steps: string[];
};

function asDetail(data: unknown): RecipeDetail | null {
  if (!data || typeof data !== "object") return null;
  const recipe = data as Partial<Record<keyof RecipeDetail, unknown>>;
  if (
    typeof recipe.id !== "string" ||
    typeof recipe.title !== "string" ||
    typeof recipe.version !== "string" ||
    typeof recipe.can_write !== "boolean" ||
    !Array.isArray(recipe.ingredient_lines) ||
    !Array.isArray(recipe.steps) ||
    !recipe.notebook ||
    typeof (recipe.notebook as { id?: unknown }).id !== "string"
  ) {
    return null;
  }
  return data as RecipeDetail;
}

function asMatches(data: unknown): NameMatch[] | null {
  if (!data || typeof data !== "object") return null;
  const matches = (data as { matches?: unknown }).matches;
  if (!Array.isArray(matches)) return null;
  const valid = matches.every(
    (row) =>
      row &&
      typeof row === "object" &&
      typeof (row as { name?: unknown }).name === "string" &&
      ((row as { entry?: unknown }).entry === null ||
        typeof (row as { entry?: unknown }).entry === "string"),
  );
  return valid ? (matches as NameMatch[]) : null;
}

async function failure(response: Response): Promise<RecipeFailure> {
  let data: { code?: unknown; missing?: unknown; line_problems?: unknown; editor_alias?: unknown } =
    {};
  try {
    data = (await response.json()) as typeof data;
  } catch {
    data = {};
  }
  const missing = Array.isArray(data.missing)
    ? data.missing.filter((item): item is string => typeof item === "string")
    : undefined;
  const lineProblems = Array.isArray(data.line_problems)
    ? data.line_problems.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const row = item as { name?: unknown; kind?: unknown };
        if (typeof row.kind !== "string") return [];
        return [{ name: typeof row.name === "string" ? row.name : null, kind: row.kind }];
      })
    : undefined;
  const result: RecipeFailure = {
    ok: false,
    status: response.status,
    code: typeof data.code === "string" ? data.code : null,
    missing,
    lineProblems,
  };
  if ("editor_alias" in data) {
    result.editorAlias = typeof data.editor_alias === "string" ? data.editor_alias : null;
  }
  return result;
}

async function send<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body: unknown,
  parse: (data: unknown) => T | null,
): Promise<RecipeResult<T>> {
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
  if (!response.ok) return failure(response);
  let value: T | null = null;
  try {
    value = parse(response.status === 204 ? true : await response.json());
  } catch {
    value = null;
  }
  if (value === null) return { ok: false, status: response.status, code: null };
  return { ok: true, value };
}

export function fetchRecipe(id: string): Promise<NotebookResult<RecipeDetail>> {
  return getJson(`/api/recipes/${encodeURIComponent(id)}`, asDetail);
}

export function matchRecipeNames(
  id: string,
  names: string[],
): Promise<RecipeResult<NameMatch[]>> {
  return send("POST", `/api/recipes/${encodeURIComponent(id)}/name-matches`, { names }, asMatches);
}

export function updateRecipe(
  id: string,
  body: RecipeUpdateBody,
): Promise<RecipeResult<RecipeDetail>> {
  return send("PUT", `/api/recipes/${encodeURIComponent(id)}`, body, asDetail);
}

export function deleteRecipe(id: string): Promise<RecipeResult<true>> {
  return send("DELETE", `/api/recipes/${encodeURIComponent(id)}`, undefined, (data) =>
    data === true ? true : null,
  );
}

// --- The recipe edit lock (spec 022, contracts/recipe-lock-api.md) ---

function asLock(data: unknown): LockEditor | null {
  if (!data || typeof data !== "object") return null;
  const editor = (data as { editor?: unknown }).editor;
  if (!editor || typeof editor !== "object") return null;
  return typeof (editor as { is_me?: unknown }).is_me === "boolean" ? (editor as LockEditor) : null;
}

/** Take the recipe lock, or keep it alive for its holder. A 409 carries `editorAlias`. */
export function acquireRecipeLock(id: string): Promise<RecipeResult<LockEditor>> {
  return send("POST", `/api/recipes/${encodeURIComponent(id)}/edit-lock`, undefined, asLock);
}

/**
 * Free the recipe. `leaving` sends it with `keepalive`, so it still goes out while the page
 * closes; the session-scoped lock covers what is lost (research R8).
 */
export async function releaseRecipeLock(id: string, leaving = false): Promise<void> {
  try {
    await fetch(`/api/recipes/${encodeURIComponent(id)}/edit-lock`, {
      method: "DELETE",
      credentials: "same-origin",
      keepalive: leaving,
    });
  } catch {
    // Best effort; the lock ends with the session or after the idle limit anyway.
  }
}
