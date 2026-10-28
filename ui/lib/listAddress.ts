/** Page and filter text of a recipe list, kept in the address (spec 021 research R9). */

export function readListAddress(params: { get(name: string): string | null }): {
  page: number;
  q: string;
} {
  const parsed = Number.parseInt(params.get("page") ?? "1", 10);
  return { page: Number.isFinite(parsed) && parsed >= 1 ? parsed : 1, q: params.get("q") ?? "" };
}

/**
 * The address of a list page. `pathname` may already carry a query (a notebook opened with
 * `?from=`); that query is kept and only `page` and `q` are set or dropped.
 */
export function listAddress(pathname: string, page: number, q: string): string {
  const [path, existing = ""] = pathname.split("?");
  const params = new URLSearchParams(existing);
  params.delete("page");
  params.delete("q");
  if (page > 1) params.set("page", String(page));
  if (q.trim()) params.set("q", q);
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}
