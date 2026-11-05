import type { ReactNode } from "react";

/** How a column compares its values; `false` makes its heading plain text. */
export type SortKind = "text" | "number" | "date" | false;

export type SortDirection = "asc" | "desc";

/** A value a column sorts and searches by. Arrays (aliases) are searched element by element. */
export type CellValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | readonly unknown[];

/** One column of a table schema (spec 066 data-model.md). */
export type ColumnDef<T> = {
  /** An attribute of `T`, or a free id for a computed column. Unique within a schema. */
  key: string;
  /** Already translated. */
  label: string;
  sort: SortKind;
  /** Only read when the table has a search bar. Default false. */
  searchable?: boolean;
  /** Value used for sort and search; default `row[key]`. */
  value?: (row: T) => CellValue;
  /** Value used for search only, when it differs from the sort value (count vs. aliases). */
  searchValue?: (row: T) => CellValue;
  /** Rendering; default `String(value)`. */
  cell?: (row: T) => ReactNode;
  /** Let the cell wrap (default: no wrap). */
  wrap?: boolean;
};

export type TableSchema<T> = {
  columns: ColumnDef<T>[];
  search: boolean;
  rowKey: (row: T) => string;
};

/** Ordered by level: index 0 is level 1. `[]` keeps the loaded order. */
export type SortState = Array<{ key: string; direction: SortDirection }>;

export type DataTableLabels = {
  searchLabel: string;
  searchPlaceholder: string;
  noMatches: string;
  matchCount: (n: number) => string;
  sortBy: (label: string) => string;
  sortLevel: (label: string, level: number, direction: SortDirection) => string;
  clearSort: string;
};
