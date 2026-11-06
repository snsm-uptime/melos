/** Client for sharing a recipe with a co-member (spec 071). Same-origin BFF, cookie session. */

export type ShareCandidate = { user_id: string; alias: string };

export type ShareResult =
  | { ok: true; recipientAlias: string }
  | { ok: false; code: string | null };

function asCandidates(data: unknown): ShareCandidate[] | null {
  const list = (data as { candidates?: unknown } | null)?.candidates;
  if (!Array.isArray(list)) return null;
  return list.flatMap((item) => {
    const row = item as { user_id?: unknown; alias?: unknown } | null;
    if (typeof row?.user_id !== "string" || typeof row?.alias !== "string") return [];
    return [{ user_id: row.user_id, alias: row.alias }];
  });
}

/** The people the caller can share with, in display order; null when they could not be loaded. */
export async function listShareCandidates(): Promise<ShareCandidate[] | null> {
  try {
    const response = await fetch("/api/recipes/share-candidates", {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!response.ok) return null;
    return asCandidates(await response.json());
  } catch {
    return null;
  }
}

async function failureCode(response: Response): Promise<string | null> {
  try {
    const data = (await response.json()) as { code?: unknown };
    return typeof data.code === "string" ? data.code : null;
  } catch {
    return null;
  }
}

/** Copies the recipe into the recipient's default notebook (FR-008). */
export async function shareRecipe(recipeId: string, recipientId: string): Promise<ShareResult> {
  let response: Response;
  try {
    response = await fetch(`/api/recipes/${encodeURIComponent(recipeId)}/share`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ recipient_user_id: recipientId }),
    });
  } catch {
    return { ok: false, code: null };
  }
  if (!response.ok) return { ok: false, code: await failureCode(response) };
  const data = (await response.json()) as { recipient_alias?: unknown };
  return {
    ok: true,
    recipientAlias: typeof data.recipient_alias === "string" ? data.recipient_alias : "",
  };
}
