import type { ShoppingResult } from "@/lib/shoppingListClient";

/** Client calls for the shopping list export via the same-origin BFF (spec 024). */

export type ExportFile = { blob: Blob; fileName: string };

const FALLBACK_FILE_NAME = "shopping-list.pdf";

function exportPath(
  kitchenId: string,
  listId: string,
  format: "markdown" | "pdf",
): string {
  return `/api/kitchens/${encodeURIComponent(kitchenId)}/shopping-lists/${encodeURIComponent(listId)}/export?format=${format}`;
}

async function get(path: string, accept: string): Promise<Response | null> {
  try {
    return await fetch(path, {
      headers: { Accept: accept },
      credentials: "same-origin",
    });
  } catch {
    return null;
  }
}

/** The Markdown copy of a list, as the api makes it. */
export async function fetchExportText(
  kitchenId: string,
  listId: string,
): Promise<ShoppingResult<string>> {
  const response = await get(
    exportPath(kitchenId, listId, "markdown"),
    "text/markdown",
  );
  if (response === null) return { ok: false, status: 0, code: null };
  if (!response.ok) return { ok: false, status: response.status, code: null };
  return { ok: true, value: await response.text() };
}

/** The PDF of a list, with the file name the api sent. */
export async function fetchExportPdf(
  kitchenId: string,
  listId: string,
): Promise<ShoppingResult<ExportFile>> {
  const response = await get(
    exportPath(kitchenId, listId, "pdf"),
    "application/pdf",
  );
  if (response === null) return { ok: false, status: 0, code: null };
  if (!response.ok) return { ok: false, status: response.status, code: null };
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  return {
    ok: true,
    value: {
      blob: await response.blob(),
      fileName: match?.[1] ?? FALLBACK_FILE_NAME,
    },
  };
}

/** The Markdown lists each item as a "- " line; a list with no items has none. */
export function hasItems(text: string): boolean {
  return text.split("\n").some((line) => line.startsWith("- "));
}
