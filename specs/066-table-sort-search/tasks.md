---
description: "Tasks for 066 Sort and Search for Tables (generic DataTable)"
---

# Tasks: Sort and Search for Tables (generic DataTable)

**Input**: `specs/066-table-sort-search/` (plan.md, spec.md, research.md, data-model.md, contracts/data-table.md, quickstart.md)

**Tests**: Included. Constitution 6 requires vitest for UI components; the pure helpers get unit tests first.

**Paths**: UI only, under `ui/`. No API change, no migration.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create `ui/components/DataTable/` with `index.ts` exporting `DataTable` and the types from `types.ts` (empty stubs), following the folder layout of `ui/components/SearchableSelect/`
- [X] T002 [P] Add `ui/lib/i18n/table.ts` with `tableMessages: Record<Locale, DataTableLabels>` in en and es, using the strings in `contracts/data-table.md`: `searchLabel`, `searchPlaceholder`, `noMatches`, `matchCount(n)`, `sortBy(label)`, `sortLevel(label, level, direction)`, `clearSort`. The parity test in `ui/lib/i18n/parity.test.ts` must still pass (register the new module there if it lists modules)

---

## Phase 2: Foundational (blocks every story)

- [X] T003 Define types in `ui/components/DataTable/types.ts` exactly as `data-model.md`: `ColumnDef<T>` { `key: string` (attribute of `T` or a free id for computed columns, unique within a schema), `label: string`, `sort: "text" | "number" | "date" | false`, `searchable?: boolean` (default false), `value?: (row: T) => string | number | null`, `cell?: (row: T) => ReactNode` }; `TableSchema<T>` { `columns`, `search: boolean`, `rowKey: (row: T) => string` }; `SortState = Array<{ key: string; direction: "asc" | "desc" }>` (index 0 = level 1; `[]` = API order); `DataTableLabels`
- [X] T004 Move the NFD accent folding from `ui/components/SearchableSelect/SearchableSelect.tsx` into `foldText(s)` in `ui/components/DataTable/tableRows.ts` (`s.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase()`), and make `SearchableSelect` import it; its existing tests must pass unchanged
- [X] T005 Add helper `columnValue(row, column)` in `ui/components/DataTable/tableRows.ts`: returns `column.value(row)` when given, else `row[column.key]`; and `isEmpty(v)` true for `null`, `undefined`, `""` and invalid dates
- [X] T006 Create typed row types `UnitRow`, `IngredientRow`, `RecipeRow`, `UserRow` in `ui/app/admin/adminTables.tsx` with the fields read today in `columnsFor` in `ui/app/admin/AdminDashboard.tsx` (spec 055 admin API), including `user_aliases` and `people_aliases`

**Checkpoint**: types and helpers compile (`npm run typecheck`).

---

## Phase 3: User Story 1 - Sort any dashboard column (P1) 🎯 MVP

**Goal**: Each of the four tabs sorts by any sortable column, asc then desc.

**Independent Test**: Open each tab, click each sortable heading twice; order goes asc then desc; Delete is plain text.

### Tests (write first, they fail)

- [X] T007 [P] [US1] Unit tests in `ui/components/DataTable/tableRows.test.ts` for `sortRows(rows, sort, columns, locale)`: text ignores case and accents ("Ñoquis" with N, "sopa"/"Sopa" adjacent); numbers numeric (9 before 10); dates chronological; empty values last in BOTH directions; ties keep loaded order; `sort` = `[]` returns rows in their original order; two levels (Units: reference_count then name) order by the first and break ties by the second, each with its own direction and empties last within each level; plus `nextSort(sort, key)` cases: unsorted key appended asc, asc → desc in place, desc → removed with later levels moving up
- [X] T008 [P] [US1] Component tests in `ui/components/DataTable/DataTable.test.tsx`: sortable heading is a `<button>` inside `<th aria-sort>`; first click gives `aria-sort="ascending"`, second `"descending"`, third removes it (`aria-sort` gone); clicking a second column adds level 2 and both headings show their level numbers; "Clear sort" appears only while a sort is active and resets to the loaded order; a column with `sort: false` renders plain text with no button and no `aria-sort`; Enter on a focused heading button sorts; no `fetch` call happens on sort (spy on `global.fetch`); `rows` prop is not mutated; empty `rows` renders the `empty` text

### Implementation

- [X] T009 [US1] Implement `nextSort(sort, key)` and multi-level `sortRows` in `ui/components/DataTable/tableRows.ts` per research R3/R4/R5: copy the array, stable sort comparing level by level, `Intl.Collator(locale, { sensitivity: "base", numeric: true })` for text, numeric compare for number, `Date` timestamp for date, empties always last regardless of direction
- [X] T010 [US1] Implement `DataTable<T>` in `ui/components/DataTable/DataTable.tsx` per `contracts/data-table.md`: props `schema`, `rows`, `locale`, `labels`, `empty`; `SortState` in `useState([])` updated with `nextSort`; headings as buttons with `aria-sort` and `aria-label` from `labels.sortBy` / `labels.sortLevel`, showing the level number and a direction icon; a "Clear sort" button (`labels.clearSort`) above the table, next to the search bar where there is one, while any level is active and never when `rows` is empty; cells use `column.cell(row)` else `String(value)`; keep today's styles from `SectionTable` (scroll box `max-w-full overflow-x-auto`, borders, `text-[0.85rem]`) so 360px still fits
- [X] T011 [US1] Write the four schemas in `ui/app/admin/adminTables.tsx` (`unitsTable`, `ingredientsTable`, `recipesTable`, `usersTable`) moving labels and cell renderers (`PeopleWithAccess`, check/close icon, date, notebook kind, `DeleteItemButton`) out of `columnsFor`. Sort kinds from research R7: Units name text, reference_count number, is_default number (true=1), created_at date, People (user_references) `sort: false` because Count already holds that number; Ingredients name text, recipes and people number; Recipes title text, cart_adds number, notebook_name text, notebook_kind text of the shown label, people_with_access number, id text, delete `sort: false`; Users alias text, counts number, newest_session_at and latest_recipe_at date. Schemas are built by functions taking `(t, locale, actions)` because labels and the delete action depend on them
- [X] T012 [US1] In `ui/app/admin/AdminDashboard.tsx` remove `SectionTable`, `Column` and `columnsFor`; render `<DataTable key={section} schema={…} rows={current.rows} locale={locale} labels={tableMessages[locale]} empty={t.empty} />` so sort resets when the tab changes (spec US1 scenario 6)
- [X] T013 [US1] Update `ui/app/admin/AdminDashboard.test.tsx`: existing tests pass; add one sort test per tab (click a numeric heading twice, check row order), one two-level test on Units (Quantity then Name) and one that switching tab and back restores the default order

**Checkpoint**: US1 works alone; all four tabs sort.

---

## Phase 4: User Story 2 - Search Units, Ingredients and Recipes (P2)

**Goal**: A search bar above those three tables filters rows; Users has none.

**Independent Test**: On Recipes type part of a title, only matches remain; clear it, all return.

### Tests (write first)

- [X] T014 [P] [US2] Unit tests in `ui/components/DataTable/tableRows.test.ts` for `filterRows(rows, query, columns)`: empty or whitespace query returns all rows; "MAIZ" matches "Sopa de maíz"; only columns with `searchable: true` are checked; array values (aliases) match when any element matches
- [X] T015 [P] [US2] Component tests in `ui/components/DataTable/DataTable.test.tsx`: search input shown only when `schema.search` is true, with an accessible label `labels.searchLabel`; typing filters; sort applies to the filtered rows; no match shows `labels.noMatches` and the input stays editable; clearing restores every row; a `role="status"` region announces `labels.matchCount(n)`; no `fetch` call on typing

### Implementation

- [X] T016 [US2] Implement `filterRows` in `ui/components/DataTable/tableRows.ts` with `foldText` and `includes`, joining array values
- [X] T017 [US2] Add the search bar to `ui/components/DataTable/DataTable.tsx` above the table: query in `useState("")`; visible rows = `sortRows(filterRows(rows, query, columns), sort, columns, locale)`; when filtered rows are empty but `rows` is not, show `noMatches` instead of the body; the live region with the count. When `rows` is empty, show only `empty` (no search bar acts)
- [X] T018 [US2] In `ui/app/admin/adminTables.tsx` set `search: true` for units, ingredients and recipes and `false` for users; mark searchable columns per research R7 (Units: name, user_aliases via `value`; Ingredients: name; Recipes: title, notebook_name, people_aliases via `value`, notebook_kind via its shown label, id)
- [X] T019 [US2] Add tests to `ui/app/admin/AdminDashboard.test.tsx`: Recipes search "sop" filters, Users tab has no search bar, switching tab clears the search

**Checkpoint**: US1 and US2 work together.

---

## Phase 5: User Story 3 - One shared table layout (P3)

**Goal**: A new behaviour or table needs only a schema.

**Independent Test**: A test schema over an invented row type renders, sorts and searches with no component change.

- [X] T020 [P] [US3] In `ui/components/DataTable/DataTable.test.tsx` add a test with an invented row type (`{ name: string; size: number; seen: string | null }`) and a schema only, checking it renders, sorts and searches; and that a column without `sort` set to a kind is not clickable
- [X] T021 [US3] Confirm by grep that no `<table` remains outside `ui/components/DataTable/` (`grep -rn "<table" ui/app ui/components`); add a short doc comment at the top of `ui/components/DataTable/DataTable.tsx` saying every table in the app uses this component with a schema

---

## Phase 6: Polish

- [X] T022 [P] Run `cd ui && npm run test && npm run lint && npm run typecheck`; fix any failure
- [X] T023 [P] Check performance: in a vitest case, sort and filter 1,000 invented rows and assert under 100 ms (plan Performance Goals)
- [ ] T024 Browser walk of `specs/066-table-sort-search/quickstart.md` steps 1 to 8 at 360px and 1280px, in en and es, once keyboard only (see memory: Playwright on the host against an isolated stack); and time SC-001 (open a tab, sort, under 2 s) and SC-002 (search result under 1 s) on the dev stack; record results in `specs/066-table-sort-search/notes.md`
- [X] T025 Update S-066 in `dev/docs/backlog.yaml`: add to notes "The owner approved building it before the open Must stories on 2026-11-04 (constitution 9)."; status `in_progress` while building, `verification` with test counts and walk results; ask the owner to review the Spanish strings in `ui/lib/i18n/table.ts`

---

## Dependencies

- Setup (T001–T002) → Foundational (T003–T006) → US1 (T007–T013) → US2 (T014–T019) → US3 (T020–T021) → Polish.
- US2 builds on the `DataTable` from US1 (same file), so it follows US1. US3 only adds tests and a check.
- Within a story: tests first, then `tableRows.ts`, then `DataTable.tsx`, then schemas, then dashboard.

## Parallel examples

- Phase 1: T001 and T002.
- US1: T007 and T008 together (different test files).
- US2: T014 and T015 together.
- Polish: T022 and T023.

## Implementation strategy

- **MVP**: Phases 1–3 (sort on all four tables through the shared component). Validate with quickstart steps 1, 2, 5 (sort part), 6, 7, 8.
- **Next**: Phase 4 adds search; Phase 5 locks the shared-layout guarantee; Phase 6 verifies.
