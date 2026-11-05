# Data Model: Sort and Search for Tables

UI types only. No database or API change.

## ColumnDef<T>

| Field | Type | Rule |
|---|---|---|
| key | `keyof T & string` or a free id for computed columns | unique within a schema |
| label | string | already translated |
| sort | `"text" \| "number" \| "date" \| false` | false = plain heading (FR-001 exceptions) |
| searchable | boolean, default false | only read when the table has a search bar |
| value | `(row: T) => string \| number \| null` (optional) | value used for sort and search; default `row[key]` |
| cell | `(row: T) => ReactNode` (optional) | rendering; default `String(value)` or the "none" label |

## TableSchema<T>

`{ columns: ColumnDef<T>[]; search: boolean; rowKey: (row: T) => string }`
One per table: `unitsTable`, `ingredientsTable`, `recipesTable`, `usersTable`. `search` is true for the first three.

## SortState

`Array<{ key: string; direction: "asc" | "desc" }>`, ordered by level (index 0 = level 1). Starts `[]` (API order). Click on a key not in it: append asc. Click on a key in it: asc → desc in place; desc → removed (later levels move up). Clear sort: `[]`. Lives in the component; reset when the tab remounts.

## View derivation (pure)

`visibleRows = sortRows(filterRows(rows, query, searchableColumns), sort, columns, locale)`
- `filterRows`: empty query returns rows unchanged; otherwise keeps rows where any searchable column's folded value includes the folded query.
- `sortRows`: compares by level 1, then level 2 on ties, and so on; stable; empties last within each level in both directions; text by collator, number numeric, date by timestamp.

## Row types (from spec 055 admin API)

`UnitRow`, `IngredientRow`, `RecipeRow`, `UserRow`: the fields already read in `columnsFor` today, typed instead of `Record<string, unknown>`.
