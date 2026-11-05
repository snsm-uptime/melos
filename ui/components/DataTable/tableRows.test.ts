import { describe, expect, it } from "vitest";

import {
  columnValue,
  filterRows,
  foldText,
  isEmpty,
  nextSort,
  sortRows,
} from "./tableRows";
import type { ColumnDef } from "./types";

type Row = {
  name: string | null;
  size: number | null;
  seen: string | null;
  tags?: (string | null)[];
};

const columns: ColumnDef<Row>[] = [
  { key: "name", label: "Name", sort: "text", searchable: true },
  { key: "size", label: "Size", sort: "number" },
  { key: "seen", label: "Seen", sort: "date" },
  {
    key: "tags",
    label: "Tags",
    sort: false,
    searchable: true,
    searchValue: (row) => row.tags,
  },
];

const row = (
  name: string | null,
  size: number | null = null,
  seen: string | null = null,
  tags: (string | null)[] = [],
): Row => ({ name, size, seen, tags });

const names = (rows: Row[]) => rows.map((r) => r.name);

describe("helpers", () => {
  it("folds case and accents", () => {
    expect(foldText("Sopa de MAÍZ")).toBe("sopa de maiz");
  });

  it("reads value() when given, else the attribute", () => {
    expect(columnValue(row("a", 3), columns[1])).toBe(3);
    expect(
      columnValue(row("a"), { key: "x", label: "", sort: false, value: () => "v" }),
    ).toBe("v");
  });

  it("treats null, undefined, empty text and invalid dates as empty", () => {
    expect([null, undefined, "", new Date("nope")].every(isEmpty)).toBe(true);
    expect([0, "a", false, new Date()].some(isEmpty)).toBe(false);
  });
});

describe("nextSort", () => {
  it("appends an unsorted key ascending", () => {
    expect(nextSort([{ key: "a", direction: "asc" }], "b")).toEqual([
      { key: "a", direction: "asc" },
      { key: "b", direction: "asc" },
    ]);
  });

  it("turns asc into desc in place", () => {
    expect(
      nextSort(
        [
          { key: "a", direction: "asc" },
          { key: "b", direction: "asc" },
        ],
        "a",
      ),
    ).toEqual([
      { key: "a", direction: "desc" },
      { key: "b", direction: "asc" },
    ]);
  });

  it("removes a desc key, and later levels move up", () => {
    expect(
      nextSort(
        [
          { key: "a", direction: "desc" },
          { key: "b", direction: "asc" },
        ],
        "a",
      ),
    ).toEqual([{ key: "b", direction: "asc" }]);
  });
});

describe("sortRows", () => {
  it("sorts text ignoring case and accents", () => {
    const rows = [row("sopa"), row("Ñoquis"), row("arroz"), row("Sopa"), row("Pan")];
    expect(names(sortRows(rows, [{ key: "name", direction: "asc" }], columns, "es"))).toEqual(
      ["arroz", "Ñoquis", "Pan", "sopa", "Sopa"],
    );
  });

  it("sorts numbers numerically and dates chronologically", () => {
    const rows = [row("a", 10, "2026-03-01"), row("b", 9, "2026-01-01"), row("c", 100, "2026-02-01")];
    expect(names(sortRows(rows, [{ key: "size", direction: "asc" }], columns, "en"))).toEqual([
      "b",
      "a",
      "c",
    ]);
    expect(names(sortRows(rows, [{ key: "seen", direction: "desc" }], columns, "en"))).toEqual([
      "a",
      "c",
      "b",
    ]);
  });

  it("puts empty values last in both directions", () => {
    const rows = [row("a", null, null), row("b", 2, "2026-01-01"), row("c", 1, "bad")];
    for (const direction of ["asc", "desc"] as const) {
      expect(sortRows(rows, [{ key: "size", direction }], columns, "en").at(-1)!.name).toBe("a");
      const byDate = names(sortRows(rows, [{ key: "seen", direction }], columns, "en"));
      expect(byDate[0]).toBe("b");
    }
  });

  it("keeps the loaded order on ties and with no sort, without mutating", () => {
    const rows = [row("x", 1), row("y", 1), row("z", 0)];
    const before = [...rows];
    expect(names(sortRows(rows, [{ key: "size", direction: "desc" }], columns, "en"))).toEqual([
      "x",
      "y",
      "z",
    ]);
    expect(sortRows(rows, [], columns, "en")).toEqual(rows);
    expect(rows).toEqual(before);
  });

  it("orders by level 1, breaking ties by level 2, each with its own direction", () => {
    const rows = [row("b", 2), row("a", 2), row("c", 9), row("d", null), row("a2", null)];
    const sorted = sortRows(
      rows,
      [
        { key: "size", direction: "desc" },
        { key: "name", direction: "asc" },
      ],
      columns,
      "en",
    );
    expect(names(sorted)).toEqual(["c", "a", "b", "a2", "d"]);
  });
});

describe("filterRows", () => {
  const rows = [row("Sopa de maíz", 1, null, ["ana"]), row("Pan", 2, null, [null, "Bén"])];

  it("returns every row for an empty or blank query", () => {
    expect(filterRows(rows, "", columns)).toHaveLength(2);
    expect(filterRows(rows, "   ", columns)).toHaveLength(2);
  });

  it("matches ignoring case and accents", () => {
    expect(names(filterRows(rows, "MAIZ", columns))).toEqual(["Sopa de maíz"]);
  });

  it("checks only searchable columns", () => {
    expect(filterRows(rows, "2", columns)).toEqual([]);
  });

  it("matches an array value when any element matches", () => {
    expect(names(filterRows(rows, "ben", columns))).toEqual(["Pan"]);
  });

  it("sorts and filters 1,000 rows in under 100 ms", () => {
    const many = Array.from({ length: 1000 }, (_, i) =>
      row(`item ${(i * 7919) % 1000}`, (i * 31) % 97, `2026-01-${String((i % 28) + 1).padStart(2, "0")}`),
    );
    const start = performance.now();
    sortRows(
      filterRows(many, "item", columns),
      [
        { key: "size", direction: "asc" },
        { key: "name", direction: "desc" },
      ],
      columns,
      "en",
    );
    expect(performance.now() - start).toBeLessThan(100);
  });
});
