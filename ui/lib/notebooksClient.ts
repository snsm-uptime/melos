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

async function failure(response: Response): Promise<NotebookError> {
  let code: string | null = null;
  try {
    const body = (await response.json()) as { code?: unknown } | null;
    if (typeof body?.code === "string") code = body.code;
  } catch {
    code = null;
  }
  return { ok: false, status: response.status, code };
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
  if (!response.ok) return failure(response);
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

export function asNotebookList(data: unknown): NotebookResponse[] | null {
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

/** A new personal notebook with no recipes, owned by the caller (S-059). */
export function createNotebook(name: string): Promise<NotebookResult<NotebookResponse>> {
  return requestJson("/api/notebooks", asNotebook, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

/** A new, empty notebook in a kitchen, recorded as the caller's own (spec 059). */
export function createKitchenNotebook(
  kitchenId: string,
  name: string,
): Promise<NotebookResult<NotebookResponse>> {
  return requestJson(`/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}`, asNotebook, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

/** Mirrors the api's rule, to decide what to show. The api remains the rule (spec 059 R5). */
export function canManageNotebook(
  notebook: Pick<NotebookResponse, "access" | "kitchen_is_archived">,
): boolean {
  return (
    notebook.access === "owner" ||
    (notebook.access === "kitchen_member" && notebook.kitchen_is_archived === false)
  );
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

export type NotebookMember = {
  user_id: string;
  /** Null for an account with none; the screen shows "unknown". */
  alias: string | null;
  role: "owner" | "member";
  is_self: boolean;
};

export type NotebookInvite = {
  id: string;
  email: string;
  expires_at: string;
  expired: boolean;
};

const notebookPath = (notebookId: string) => `/api/notebooks/${encodeURIComponent(notebookId)}`;

function asInvite(data: unknown): NotebookInvite | null {
  if (!data || typeof data !== "object") return null;
  const row = data as { id?: unknown; email?: unknown };
  return typeof row.id === "string" && typeof row.email === "string"
    ? (data as NotebookInvite)
    : null;
}

function asSentInvite(data: unknown): NotebookInvite | null {
  return data && typeof data === "object" ? asInvite((data as { invite?: unknown }).invite) : null;
}

/** A refused or failed write keeps its status and code; a 204 is `ok` with nothing in it. */
async function requestEmpty(path: string): Promise<NotebookResult<null>> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "DELETE",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, status: 0, code: null };
  }
  return response.ok ? { ok: true, value: null } : failure(response);
}

/** The owner and members by alias, owner first (spec 057). No email appears here. */
export function fetchNotebookMembers(
  notebookId: string,
): Promise<NotebookResult<NotebookMember[]>> {
  return getJson(`${notebookPath(notebookId)}/members`, (data) => {
    const rows = (data as { members?: unknown } | null)?.members;
    return Array.isArray(rows) ? (rows as NotebookMember[]) : null;
  });
}

/** A notebook's open and expired invites, for its owner. */
export function fetchNotebookInvites(
  notebookId: string,
): Promise<NotebookResult<NotebookInvite[]>> {
  return getJson(`${notebookPath(notebookId)}/invites`, (data) => {
    const rows = (data as { invites?: unknown } | null)?.invites;
    return Array.isArray(rows) ? (rows as NotebookInvite[]) : null;
  });
}

/** Sends an invite by email; the answer never says whether the address has an account. */
export function inviteToNotebook(
  notebookId: string,
  email: string,
): Promise<NotebookResult<NotebookInvite>> {
  return requestJson(`${notebookPath(notebookId)}/invites`, asSentInvite, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

/** A new link and a new 7 days; any earlier link stops working. */
export function resendNotebookInvite(
  notebookId: string,
  inviteId: string,
): Promise<NotebookResult<NotebookInvite>> {
  return requestJson(
    `${notebookPath(notebookId)}/invites/${encodeURIComponent(inviteId)}/resend`,
    asSentInvite,
    { method: "POST", headers: { Accept: "application/json" } },
  );
}

export function cancelNotebookInvite(
  notebookId: string,
  inviteId: string,
): Promise<NotebookResult<null>> {
  return requestEmpty(`${notebookPath(notebookId)}/invites/${encodeURIComponent(inviteId)}`);
}

/** Gives a notebook a new name (spec 059). */
export function renameNotebook(
  notebookId: string,
  name: string,
): Promise<NotebookResult<NotebookResponse>> {
  return requestJson(notebookPath(notebookId), asNotebook, {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

/** Deletes a notebook and what it holds (spec 059). */
export function deleteNotebook(notebookId: string): Promise<NotebookResult<null>> {
  return requestEmpty(notebookPath(notebookId));
}

export function leaveNotebook(notebookId: string): Promise<NotebookResult<null>> {
  return requestEmpty(`${notebookPath(notebookId)}/members/me`);
}

export function removeNotebookMember(
  notebookId: string,
  userId: string,
): Promise<NotebookResult<null>> {
  return requestEmpty(`${notebookPath(notebookId)}/members/${encodeURIComponent(userId)}`);
}
