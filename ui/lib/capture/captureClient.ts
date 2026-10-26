/** Client helpers for capture and the controlled lists, through the same-origin BFF (spec 016). */

import type { CaptureMessage } from "./captureStore";

export type CaptureDraftResponse = {
  outcome: "draft";
  notebook: { id: string; kind: "personal" | "kitchen"; name: string; kitchen_id: string | null };
  language: "en" | "es";
  draft: {
    title: string;
    base_servings: number;
    servings_estimated: boolean;
    main_ingredients: { id: string; label: string }[];
    cuisines: { id: string; label: string; tag: string | null }[];
    ingredient_lines: {
      name: string;
      vague: boolean;
      quantity: number | null;
      unit: string | null;
      size: string | null;
      preparation: string | null;
      note: string | null;
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
  max_main_ingredients: number;
  max_cuisines: number;
  max_text_chars: number;
  main_ingredients: { id: string; label: { en: string; es: string } }[];
  cuisines: { id: string; label: { en: string; es: string }; tag: string | null }[];
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

  const body = (data ?? {}) as { code?: unknown; detail?: unknown };
  const code = typeof body.code === "string" ? body.code : "ai_unavailable";
  const reason = code === "not_a_recipe" && typeof body.detail === "string" ? body.detail : undefined;
  const max = code === "text_too_long" ? extractMax(body.detail) : undefined;
  return {
    ok: false,
    message: { code: code === "bad_gateway" ? "ai_unavailable" : code, reason },
    max,
  };
}

function extractMax(detail: unknown): number | undefined {
  if (typeof detail !== "string") return undefined;
  const match = /up to (\d+) characters/.exec(detail);
  return match ? Number(match[1]) : undefined;
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
