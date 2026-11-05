"use client";

/**
 * The one table of the app (spec 066). Every table uses this component with a typed schema:
 * sort (multi-level, asc → desc → off) and search live here once, so a new table or a new
 * table behaviour needs only a schema, never a second `<table>`.
 */

import { useId, useMemo, useState } from "react";

import { ArrowIcon } from "@/app/icons";

import { columnValue, filterRows, nextSort, sortRows } from "./tableRows";
import type { DataTableLabels, SortState, TableSchema } from "./types";

export type DataTableProps<T> = {
  schema: TableSchema<T>;
  /** Already loaded; the table never fetches and never changes them. */
  rows: T[];
  locale: string;
  labels: DataTableLabels;
  /** Shown when `rows` is empty. */
  empty: string;
};

export function DataTable<T>({
  schema,
  rows,
  locale,
  labels,
  empty,
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState>([]);
  const [query, setQuery] = useState("");
  const searchId = useId();
  const { columns } = schema;

  const visible = useMemo(
    () =>
      sortRows(
        schema.search ? filterRows(rows, query, columns) : rows,
        sort,
        columns,
        locale,
      ),
    [rows, query, sort, columns, locale, schema.search],
  );

  if (rows.length === 0)
    return <p className="m-0 text-[0.9rem] text-muted">{empty}</p>;

  const clearButton =
    sort.length > 0 ? (
      <button
        type="button"
        className="min-h-10 shrink-0 rounded-[0.75rem] border border-border px-3 py-1 text-[0.85rem] whitespace-nowrap text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        onClick={() => setSort([])}
      >
        {labels.clearSort}
      </button>
    ) : null;

  return (
    <div className="flex min-w-0 flex-col gap-3">
      {schema.search || clearButton ? (
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {schema.search ? (
            <>
              <label htmlFor={searchId} className="sr-only">
                {labels.searchLabel}
              </label>
              <input
                id={searchId}
                type="search"
                value={query}
                placeholder={labels.searchPlaceholder}
                onChange={(event) => setQuery(event.target.value)}
                className="min-h-10 min-w-0 flex-1 rounded-[0.75rem] border border-border bg-transparent px-3 py-1 text-[0.9rem] text-foreground outline-none placeholder:text-muted focus:border-accent"
              />
              <p role="status" className="sr-only">
                {visible.length === 0
                  ? labels.noMatches
                  : labels.matchCount(visible.length)}
              </p>
            </>
          ) : null}
          {clearButton}
        </div>
      ) : null}
      {visible.length === 0 ? (
        <p className="m-0 text-[0.9rem] text-muted">{labels.noMatches}</p>
      ) : (
        // Wide tables scroll inside their box, so the page itself fits a 360px screen.
        <div className="max-w-full overflow-x-auto rounded-[0.75rem] border border-border">
          <table className="w-full border-collapse text-left text-[0.85rem]">
            <thead>
              <tr>
                {columns.map((column) => {
                  const level = sort.findIndex((s) => s.key === column.key);
                  const active = level === -1 ? null : sort[level];
                  return (
                    <th
                      key={column.key}
                      scope="col"
                      aria-sort={
                        active
                          ? active.direction === "asc"
                            ? "ascending"
                            : "descending"
                          : undefined
                      }
                      className="border-b border-border px-3 py-2 font-semibold whitespace-nowrap text-muted"
                    >
                      {column.sort === false ? (
                        column.label
                      ) : (
                        <button
                          type="button"
                          aria-label={
                            active
                              ? labels.sortLevel(
                                  column.label,
                                  level + 1,
                                  active.direction,
                                )
                              : labels.sortBy(column.label)
                          }
                          className={`inline-flex items-center gap-1 rounded-sm font-semibold hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
                            active ? "text-foreground" : ""
                          }`}
                          onClick={() =>
                            setSort((before) => nextSort(before, column.key))
                          }
                        >
                          {column.label}
                          {active ? (
                            <span
                              aria-hidden="true"
                              className="inline-flex items-center"
                            >
                              <ArrowIcon
                                className={`h-3.5 w-3.5 ${
                                  active.direction === "asc"
                                    ? "rotate-90"
                                    : "-rotate-90"
                                }`}
                              />
                              {sort.length > 1 ? (
                                <span className="text-[0.7rem]">
                                  {level + 1}
                                </span>
                              ) : null}
                            </span>
                          ) : null}
                        </button>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={schema.rowKey(row)}>
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`border-b border-border px-3 py-2 text-foreground ${
                        column.wrap ? "" : "whitespace-nowrap"
                      }`}
                    >
                      {column.cell
                        ? column.cell(row)
                        : String(columnValue(row, column))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
