/** Notebook invite preview and accept through the same-origin BFF (spec 057). */

export type NotebookInvitePreview = {
  notebook_name: string;
  inviter_alias: string | null;
  email_hint: string;
};

export type NotebookInvitePreviewResult =
  | { ok: true; preview: NotebookInvitePreview }
  | { ok: false; code: string };

export type AcceptNotebookInviteResult =
  | { ok: true; notebookId: string }
  | { ok: false; code: string };

const KNOWN_REFUSALS = new Set([
  "alias_required",
  "email_not_verified",
  "invite_email_mismatch",
  "invalid_invite_token",
]);

export async function fetchNotebookInvitePreview(
  token: string,
  fetchImpl: typeof fetch = fetch,
): Promise<NotebookInvitePreviewResult> {
  try {
    const response = await fetchImpl(
      `/api/invites/notebook/preview?token=${encodeURIComponent(token)}`,
      { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin" },
    );
    if (response.status === 410) return { ok: false, code: "invalid_invite_token" };
    const data = (await response.json().catch(() => ({}))) as Partial<NotebookInvitePreview>;
    if (
      !response.ok ||
      typeof data.notebook_name !== "string" ||
      typeof data.email_hint !== "string"
    ) {
      return { ok: false, code: "error" };
    }
    return {
      ok: true,
      preview: {
        notebook_name: data.notebook_name,
        inviter_alias: data.inviter_alias ?? null,
        email_hint: data.email_hint,
      },
    };
  } catch {
    return { ok: false, code: "error" };
  }
}

export async function acceptNotebookInvite(
  token: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AcceptNotebookInviteResult> {
  try {
    const response = await fetchImpl("/api/invites/notebook/accept", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ token }),
      credentials: "same-origin",
    });
    if (response.status === 401) return { ok: false, code: "unauthorized" };
    const data = (await response.json().catch(() => ({}))) as {
      notebook_id?: string;
      code?: string;
    };
    if (!response.ok) {
      const code = data.code && KNOWN_REFUSALS.has(data.code) ? data.code : "error";
      return { ok: false, code };
    }
    if (typeof data.notebook_id !== "string" || !data.notebook_id) {
      return { ok: false, code: "error" };
    }
    return { ok: true, notebookId: data.notebook_id };
  } catch {
    return { ok: false, code: "error" };
  }
}
