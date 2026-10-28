/** Client helper for Save, through the same-origin BFF (spec 020, contracts/save-api.md). */

import type { CaptureMessage, CaptureState } from "./captureStore";

export type SaveResult = { ok: true } | { ok: false; message: CaptureMessage };

/** The body of POST /recipes for the draft on screen, or null when there is nothing to save. */
export function buildSaveBody(capture: CaptureState): Record<string, unknown> | null {
  const { draft, notebook, saveKey, text } = capture;
  if (!draft || !notebook || !saveKey) return null;
  return {
    save_key: saveKey,
    notebook_id: notebook.id,
    source_text: text.trim(),
    title: draft.title,
    base_servings: draft.baseServings,
    servings_estimated: draft.servingsEstimated,
    ingredient_lines: draft.lines.map((line) => ({
      name: line.name,
      vague: line.vague,
      quantity: line.quantity,
      unit: line.unit,
      size: line.size,
      preparation: line.preparation,
      note: line.note,
    })),
    steps: draft.steps.map((step) => step.text),
  };
}

function readMissing(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value.filter((item): item is string => typeof item === "string");
}

function readLineProblems(value: unknown): CaptureMessage["lineProblems"] {
  if (!Array.isArray(value)) return undefined;
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as { name?: unknown; kind?: unknown };
    if (typeof row.kind !== "string") return [];
    return [{ name: typeof row.name === "string" ? row.name : null, kind: row.kind }];
  });
}

/** Save the draft once. The same key is sent on a retry, so a repeat never makes a second recipe. */
export async function submitSave(capture: CaptureState): Promise<SaveResult> {
  const body = buildSaveBody(capture);
  if (!body) return { ok: false, message: { code: "save_unavailable" } };

  let response: Response;
  try {
    response = await fetch("/api/recipes", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
  } catch {
    return { ok: false, message: { code: "save_unavailable" } };
  }
  if (response.status === 200 || response.status === 201) return { ok: true };

  let data: { code?: unknown; missing?: unknown; line_problems?: unknown } = {};
  try {
    data = (await response.json()) as typeof data;
  } catch {
    data = {};
  }
  const code = typeof data.code === "string" ? data.code : "save_unavailable";
  return {
    ok: false,
    message: {
      code: code === "notebook_not_found" ? "notebook_gone" : code,
      missing: readMissing(data.missing),
      lineProblems: readLineProblems(data.line_problems),
    },
  };
}
