/** Catalog management (spec 043): types and the BFF calls for one notebook's catalog. */

export type CatalogLanguage = "en" | "es";

export type CatalogVariant = { name: string; language: CatalogLanguage };

export type CatalogIngredient = {
  name: string;
  language: CatalogLanguage | null;
  recipe_count: number;
  variants: CatalogVariant[];
  spellings: string[];
};

export type NotebookCatalog = {
  notebook_id: string;
  can_write: boolean;
  ingredients: CatalogIngredient[];
};

export type MergePreview = {
  merged: string;
  kept: string;
  merged_language: CatalogLanguage | null;
  kept_language: CatalogLanguage | null;
  notebooks: { notebook_id: string; name: string; recipe_count: number }[];
};

export type MergeResult = {
  merged: { notebook_id: string; recipes_changed: number }[];
  skipped: { notebook_id: string; reason: "name_changed" | "no_access" }[];
};

export type RenamedIngredient = CatalogIngredient & { recipes_changed: number };

export type SplitResult = {
  kept: CatalogIngredient;
  split: CatalogIngredient;
  recipes_changed: number;
};

export type Pair = { en: string; es: string };

/** A notebook the person can open on the Ingredients page. */
export type CatalogNotebook = { id: string; name: string; kitchen: string | null };

/** A failure keeps the status, the api `code`, and the extra fields some codes carry. */
export type CatalogFailure = {
  ok: false;
  status: number;
  code: string | null;
  existing?: string;
  recipe_count?: number;
};
export type CatalogResult<T> = { ok: true; value: T } | CatalogFailure;

async function call<T>(
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  body?: unknown,
): Promise<CatalogResult<T>> {
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
    let data: { code?: unknown; existing?: unknown; recipe_count?: unknown } = {};
    try {
      data = (await response.json()) as typeof data;
    } catch {
      data = {};
    }
    return {
      ok: false,
      status: response.status,
      code: typeof data.code === "string" ? data.code : null,
      ...(typeof data.existing === "string" ? { existing: data.existing } : {}),
      ...(typeof data.recipe_count === "number" ? { recipe_count: data.recipe_count } : {}),
    };
  }
  if (response.status === 204) return { ok: true, value: undefined as T };
  try {
    return { ok: true, value: (await response.json()) as T };
  } catch {
    return { ok: false, status: response.status, code: null };
  }
}

function catalogPath(notebookId: string, rest = ""): string {
  return `/api/notebooks/${encodeURIComponent(notebookId)}/catalog${rest}`;
}

function namePath(notebookId: string, name: string, rest = ""): string {
  return catalogPath(notebookId, `/${encodeURIComponent(name)}${rest}`);
}

export function fetchCatalog(notebookId: string): Promise<CatalogResult<NotebookCatalog>> {
  return call(catalogPath(notebookId), "GET");
}

/** Rename, and/or set the kept name's language; `language` undefined leaves it as it is. */
export function renameName(
  notebookId: string,
  name: string,
  newName: string,
  language?: CatalogLanguage | null,
): Promise<CatalogResult<RenamedIngredient>> {
  return call(namePath(notebookId, name), "PATCH", {
    new_name: newName,
    ...(language === undefined ? {} : { language }),
  });
}

export function deleteName(notebookId: string, name: string): Promise<CatalogResult<void>> {
  return call(namePath(notebookId, name), "DELETE");
}

export function splitName(
  notebookId: string,
  name: string,
  otherName: string,
): Promise<CatalogResult<SplitResult>> {
  return call(namePath(notebookId, name, "/split"), "POST", { other_name: otherName });
}

export function previewMerge(
  fromNotebookId: string,
  merged: string,
  kept: string,
): Promise<CatalogResult<MergePreview>> {
  return call("/api/catalog/merge-preview", "POST", {
    from_notebook_id: fromNotebookId,
    merged,
    kept,
  });
}

export function mergeNames(body: {
  merged: string;
  kept: string;
  merged_language: CatalogLanguage | null;
  kept_language: CatalogLanguage | null;
  notebook_ids: string[];
}): Promise<CatalogResult<MergeResult>> {
  return call("/api/catalog/merge", "POST", body);
}

export async function suggestPairs(notebookId: string): Promise<CatalogResult<Pair[]>> {
  const result = await call<{ pairs: Pair[] }>(catalogPath(notebookId, "/pair-suggestions"), "POST");
  return result.ok ? { ok: true, value: result.value.pairs } : result;
}

export function dismissPair(notebookId: string, pair: Pair): Promise<CatalogResult<void>> {
  return call(catalogPath(notebookId, "/pair-dismissals"), "POST", pair);
}

type NotebookRow = { id: string; name: string };

/** The notebooks the person can read: personal ones, then each kitchen's, by kitchen. */
export async function fetchCatalogNotebooks(): Promise<CatalogResult<CatalogNotebook[]>> {
  const personal = await call<{ notebooks: NotebookRow[] }>("/api/notebooks", "GET");
  if (!personal.ok) return personal;
  const kitchens = await call<{ kitchens: NotebookRow[] }>("/api/kitchens", "GET");
  const found: CatalogNotebook[] = personal.value.notebooks.map((n) => ({
    id: n.id,
    name: n.name,
    kitchen: null,
  }));
  if (!kitchens.ok) return { ok: true, value: found };
  const lists = await Promise.all(
    kitchens.value.kitchens.map(async (kitchen) => {
      const notebooks = await call<{ notebooks: NotebookRow[] }>(
        `/api/notebooks/kitchens/${encodeURIComponent(kitchen.id)}`,
        "GET",
      );
      return notebooks.ok
        ? notebooks.value.notebooks.map((n) => ({ id: n.id, name: n.name, kitchen: kitchen.name }))
        : [];
    }),
  );
  return { ok: true, value: [...found, ...lists.flat()] };
}

/** A recipe's detected language applied, or with null dismissed (FR-005a). */
export function setRecipeLanguage(
  recipeId: string,
  language: CatalogLanguage | null,
): Promise<CatalogResult<unknown>> {
  return call(`/api/recipes/${encodeURIComponent(recipeId)}/language`, "PATCH", { language });
}
