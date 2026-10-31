/** Client helpers for notebook reads via same-origin BFF (spec 056 routes). */

export type NotebookResponse = {
  id: string;
  name: string;
  kind: "personal" | "kitchen";
  owner_alias: string | null;
  access: "owner" | "member" | "kitchen_member";
  is_default: boolean;
  recipe_count: number;
  kitchen_id: string | null;
  kitchen_is_archived: boolean | null;
};

/**
 * A failed read keeps the HTTP status and the api `code` (`alias_required`,
 * `kitchen_not_found`, …). A network failure has status 0 and no code.
 */
export type NotebookError = { ok: false; status: number; code: string | null };

type Ok<T> = { ok: true; value: T };

export type NotebookResult<T> = Ok<T> | NotebookError;

function isNotebook(data: unknown): data is NotebookResponse {
  if (!data || typeof data !== "object") return false;
  const row = data as { id?: unknown; name?: unknown };
  return typeof row.id === "string" && typeof row.name === "string";
}

export async function getJson<T>(
  path: string,
  parse: (data: unknown) => T | null,
): Promise<NotebookResult<T>> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, status: 0, code: null };
  }
  if (!response.ok) {
    let code: string | null = null;
    try {
      const body = (await response.json()) as { code?: unknown } | null;
      if (typeof body?.code === "string") code = body.code;
    } catch {
      code = null;
    }
    return { ok: false, status: response.status, code };
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

function asNotebook(data: unknown): NotebookResponse | null {
  return isNotebook(data) ? data : null;
}

function asNotebookList(data: unknown): NotebookResponse[] | null {
  if (!data || typeof data !== "object") return null;
  const rows = (data as { notebooks?: unknown }).notebooks;
  if (!Array.isArray(rows)) return null;
  for (const row of rows) {
    if (!isNotebook(row)) return null;
  }
  return rows as NotebookResponse[];
}

/** The caller's default personal notebook, created on the first call. */
export function fetchDefaultNotebook(): Promise<NotebookResult<NotebookResponse>> {
  return getJson("/api/notebooks/default", asNotebook);
}

/** The caller's personal notebooks, oldest first. */
export function fetchPersonalNotebooks(): Promise<NotebookResult<NotebookResponse[]>> {
  return getJson("/api/notebooks", asNotebookList);
}

/** The notebooks of one kitchen, for a member of it. */
export function fetchKitchenNotebooks(
  kitchenId: string,
): Promise<NotebookResult<NotebookResponse[]>> {
  return getJson(
    `/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}`,
    asNotebookList,
  );
}

/** One notebook the caller may read; 404 `notebook_not_found` otherwise. */
export function fetchNotebook(notebookId: string): Promise<NotebookResult<NotebookResponse>> {
  return getJson(`/api/notebooks/${encodeURIComponent(notebookId)}`, asNotebook);
}
