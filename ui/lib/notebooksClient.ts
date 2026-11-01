/** Client helpers for notebooks via same-origin BFF (specs 056 and 035). */

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
  /** The original's current name on a snapshot; null otherwise or once it is deleted. */
  origin_notebook_name: string | null;
  is_snapshot: boolean;
  /** True on the caller's own kitchen notebook, where captures go by default (spec 035 R6). */
  is_own_capture_notebook: boolean;
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

export function getJson<T>(
  path: string,
  parse: (data: unknown) => T | null,
): Promise<NotebookResult<T>> {
  return requestJson(path, parse, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
}

async function requestJson<T>(
  path: string,
  parse: (data: unknown) => T | null,
  init: RequestInit,
): Promise<NotebookResult<T>> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, credentials: "same-origin" });
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

export type NotebookSnapshotRequest = {
  sourceNotebookId: string;
  snapshotKey: string;
  confirmRepeat: boolean;
};

/** Adds a personal notebook to a kitchen; 409 `snapshot_exists` asks for a confirmation. */
export function addNotebookSnapshot(
  kitchenId: string,
  request: NotebookSnapshotRequest,
): Promise<NotebookResult<NotebookResponse>> {
  return requestJson(
    `/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}/snapshots`,
    asNotebook,
    {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        source_notebook_id: request.sourceNotebookId,
        snapshot_key: request.snapshotKey,
        confirm_repeat: request.confirmRepeat,
      }),
    },
  );
}

/** The caller's own notebook in a kitchen, created if needed (spec 035 research R6). */
export function resolveCaptureNotebook(
  kitchenId: string,
): Promise<NotebookResult<NotebookResponse>> {
  return requestJson(
    `/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}/capture-notebook`,
    asNotebook,
    { method: "POST", headers: { Accept: "application/json" } },
  );
}
