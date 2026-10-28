/**
 * Where Back and the post-delete landing go (spec 027, research R8). The recipe can be opened
 * from a notebook list or a kitchen list, so the list travels in `?from=`. Only a path inside
 * the app's notebook and kitchen pages is trusted; anything else falls back to the recipe's
 * notebook, so the parameter can never redirect off the site.
 */
export function safeReturnPath(from: string | null | undefined, notebookId: string): string {
  const fallback = `/notebooks/${notebookId}`;
  if (!from) return fallback;
  if (!from.startsWith("/notebooks/") && !from.startsWith("/kitchens/")) return fallback;
  const beforeQuery = from.split("?")[0];
  if (beforeQuery.includes("//") || beforeQuery.includes("\\") || beforeQuery.includes(":")) {
    return fallback;
  }
  if (/\s/.test(from)) return fallback;
  return from;
}

/**
 * Where a notebook's Back goes: the kitchen or notebook list it was opened from (`?from=`, the
 * same trust rule as above), else the Notebook tab.
 */
export function notebookBackPath(from: string | null | undefined): string {
  return from && safeReturnPath(from, "x") === from ? from : "/notebooks";
}
