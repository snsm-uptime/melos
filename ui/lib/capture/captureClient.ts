/** Client helpers for capture and the controlled lists, through the same-origin BFF (spec 016). */

import type { CaptureMessage } from "./captureStore";

export type CaptureDraftResponse = {
  outcome: "draft";
  notebook: { id: string; kind: "personal" | "kitchen"; name: string; kitchen_id: string | null };
  language: "en" | "es";
  catalog: string[];
  draft: {
    title: string;
    base_servings: number;
    servings_estimated: boolean;
    // MVP-OUT: main_ingredients: { id: string; label: string }[];
    // MVP-OUT: cuisines: { id: string; label: string; tag: string | null }[];
    changes: { line: number; from: string; to: string }[];
    ingredient_lines: {
      name: string;
      vague: boolean;
      quantity: number | null;
      unit: string | null;
      size: string | null;
      preparation: string | null;
      note: string | null;
      text_name: string;
      match: { kind: "matched" | "new"; entry: string | null };
    }[];
    steps: string[];
  };
};

export type CaptureResult =
  | { ok: true; value: CaptureDraftResponse }
  | { ok: false; message: CaptureMessage; max?: number };

export type VocabularyResponse = {
  units: string[];
  sizes: string[];
  // MVP-OUT: max_main_ingredients: number;
  // MVP-OUT: max_cuisines: number;
  max_text_chars: number;
  // MVP-OUT: main_ingredients: { id: string; label: { en: string; es: string } }[];
  // MVP-OUT: cuisines: { id: string; label: { en: string; es: string }; tag: string | null }[];
};

function isDraftResponse(data: unknown): data is CaptureDraftResponse {
  if (!data || typeof data !== "object") return false;
  const row = data as { outcome?: unknown; draft?: unknown };
  return row.outcome === "draft" && typeof row.draft === "object" && row.draft !== null;
}

/** Submit one text for one notebook. One attempt; the member retries by submitting again (FR-025). */
export async function submitCapture(notebookId: string, text: string): Promise<CaptureResult> {
  let response: Response;
  try {
    response = await fetch(`/api/notebooks/${encodeURIComponent(notebookId)}/captures/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ text }),
    });
  } catch {
    return { ok: false, message: { code: "ai_unavailable" } };
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (response.ok && isDraftResponse(data)) return { ok: true, value: data };

  const body = (data ?? {}) as {
    code?: unknown;
    detail?: unknown;
    ingredient?: unknown;
    missing?: unknown;
    line_problems?: unknown;
  };
  const code = typeof body.code === "string" ? body.code : "ai_unavailable";
  const max = code === "text_too_long" ? extractMax(body.detail) : undefined;
  return {
    ok: false,
    message: {
      code: code === "bad_gateway" ? "ai_unavailable" : code,
      reason: code === "not_a_recipe" ? readReason(body.detail) : undefined,
      ingredient: code === "not_a_recipe" ? readIngredient(body.ingredient) : undefined,
      missing: readMissing(body.missing),
      lineProblems: readLineProblems(body.line_problems),
    },
    max,
  };
}

const NOT_A_RECIPE_REASONS = ["question_or_request", "not_food", "story_or_article"];

/** `detail` on not_a_recipe is a reason enum value only; any other text is dropped, never shown. */
function readReason(value: unknown): string | undefined {
  return typeof value === "string" && NOT_A_RECIPE_REASONS.includes(value) ? value : undefined;
}

function readIngredient(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function extractMax(detail: unknown): number | undefined {
  if (typeof detail !== "string") return undefined;
  const match = /up to (\d+) characters/.exec(detail);
  return match ? Number(match[1]) : undefined;
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

export async function fetchVocabulary(): Promise<VocabularyResponse | null> {
  try {
    const response = await fetch("/api/recipe-vocabulary", {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!response.ok) return null;
    return (await response.json()) as VocabularyResponse;
  } catch {
    return null;
  }
}
