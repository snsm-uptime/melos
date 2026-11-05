/**
 * The notebook picker rules shared by the text and link capture sheets (specs 016, 026, 035).
 */

import { openSheet, OWN_NEW_NOTEBOOK_ID, type CaptureNotebook } from "@/lib/capture/captureStore";
import { resolveCaptureNotebook } from "@/lib/notebooksClient";

import type { CaptureCandidate } from "./AddRecipeCallToAction";

/** The picker's rows. After a failed capture the "new" row has become the real notebook. */
export function pickerOptions(
  candidates: CaptureCandidate[],
  notebook: CaptureNotebook | null,
): CaptureCandidate[] {
  if (!notebook || candidates.some((item) => item.id === notebook.id)) return candidates;
  return candidates.map((item) =>
    item.id === OWN_NEW_NOTEBOOK_ID ? { ...item, id: notebook.id, name: notebook.name } : item,
  );
}

/** The member picked another notebook: the same sheet, the new notebook. */
export function chooseNotebook(
  options: CaptureCandidate[],
  id: string,
  notebook: CaptureNotebook | null,
): void {
  const picked = options.find((item) => item.id === id);
  if (!picked || !notebook) return;
  openSheet({
    id: picked.id,
    kind: picked.kind,
    name: picked.name,
    kitchenId: picked.kitchenId,
    returnPath: notebook.returnPath,
    opener: notebook.opener,
  });
}

/**
 * The notebook to capture into. The "new" row is made now, before extraction, and kept even if
 * no recipe is saved (spec 035 FR-017). Returns an error code when it cannot be made.
 */
export async function captureTarget(
  notebook: CaptureNotebook,
): Promise<{ ok: true; notebook: CaptureNotebook } | { ok: false; code: string }> {
  if (notebook.id !== OWN_NEW_NOTEBOOK_ID || !notebook.kitchenId) return { ok: true, notebook };
  const own = await resolveCaptureNotebook(notebook.kitchenId);
  if (!own.ok) return { ok: false, code: own.code ?? "unavailable" };
  const target = { ...notebook, id: own.value.id, name: own.value.name };
  openSheet(target);
  return { ok: true, notebook: target };
}
