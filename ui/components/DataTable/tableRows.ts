import type { CellValue, ColumnDef, SortState } from "./types";

/** Lower case, no accents: "maíz" is found by typing "MAIZ". */
export function foldText(s: string): string {
  return s.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase();
}

/** The column's value for sort and search: `value(row)` when given, else `row[key]`. */
export function columnValue<T>(row: T, column: ColumnDef<T>): CellValue {
  if (column.value) return column.value(row);
  return (row as Record<string, unknown>)[column.key] as CellValue;
}

/** Null, undefined, "" and invalid dates are empty; they sort last both ways. */
export function isEmpty(v: unknown): boolean {
  if (v === null || v === undefined || v === "") return true;
  if (v instanceof Date) return Number.isNaN(v.getTime());
  return false;
}

/** Next sort after a heading click: append asc, asc → desc in place, desc → removed. */
export function nextSort(sort: SortState, key: string): SortState {
  const index = sort.findIndex((level) => level.key === key);
  if (index === -1) return [...sort, { key, direction: "asc" }];
  if (sort[index].direction === "asc")
    return sort.map((level, i) =>
      i === index ? { key, direction: "desc" } : level,
    );
  return sort.filter((_, i) => i !== index);
}

/** A comparable key, or null when the value is empty for this kind. */
function sortKey(
  v: CellValue,
  kind: "text" | "number" | "date",
): string | number | null {
  if (isEmpty(v)) return null;
  if (kind === "number") {
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }
  if (kind === "date") {
    const time = new Date(String(v)).getTime();
    return Number.isNaN(time) ? null : time;
  }
  return Array.isArray(v) ? v.join(" ") : String(v);
}

/** Rows ordered level by level; stable; empties last within each level. Never mutates `rows`. */
export function sortRows<T>(
  rows: readonly T[],
  sort: SortState,
  columns: readonly ColumnDef<T>[],
  locale: string,
): T[] {
  const levels = sort.flatMap((level) => {
    const column = columns.find((c) => c.key === level.key);
    if (!column || column.sort === false) return [];
    return [
      { column, kind: column.sort, sign: level.direction === "asc" ? 1 : -1 },
    ];
  });
  if (levels.length === 0) return [...rows];
  const collator = new Intl.Collator(locale, {
    sensitivity: "base",
    numeric: true,
  });
  const keyed = rows.map((row) => ({
    row,
    keys: levels.map((l) => sortKey(columnValue(row, l.column), l.kind)),
  }));
  keyed.sort((a, b) => {
    for (let i = 0; i < levels.length; i++) {
      const x = a.keys[i];
      const y = b.keys[i];
      if (x === null && y === null) continue;
      if (x === null) return 1;
      if (y === null) return -1;
      const diff =
        typeof x === "string" && typeof y === "string"
          ? collator.compare(x, y)
          : (x as number) - (y as number);
      if (diff !== 0) return diff * levels[i].sign;
    }
    return 0;
  });
  return keyed.map((k) => k.row);
}

/** Rows where any searchable column contains the query, ignoring case and accents. */
export function filterRows<T>(
  rows: readonly T[],
  query: string,
  columns: readonly ColumnDef<T>[],
): T[] {
  const needle = foldText(query.trim());
  if (needle === "") return [...rows];
  const searchable = columns.filter((c) => c.searchable);
  return rows.filter((row) =>
    searchable.some((column) => {
      const v = column.searchValue
        ? column.searchValue(row)
        : columnValue(row, column);
      if (isEmpty(v)) return false;
      const text = Array.isArray(v)
        ? v.filter((x) => x !== null && x !== undefined).join(" ")
        : String(v);
      return foldText(text).includes(needle);
    }),
  );
}
