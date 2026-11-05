# Implementation Plan: Sort and Search for Tables (generic DataTable)

**Branch**: `066-table-sort-search` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/066-table-sort-search/spec.md`

## Summary

Replace the private `SectionTable` in `ui/app/admin/AdminDashboard.tsx` with a shared, generic
`DataTable<T>` component in `ui/components/DataTable/`. A table is a typed schema (an array of
column definitions keyed by attributes of `T`) plus rows. Sorting (asc/desc, text, number, date,
empties last, stable) and search (accent- and case-insensitive "contains" over searchable columns)
live once in the component and in pure helper functions. The four dashboard tabs become four
schemas. UI only: no API change, no migration (owner confirmed on 2026-11-04 that these four are
the app's only tables).

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 16 (ui only)

**Primary Dependencies**: none new. Built in-house (research R1), Tailwind 4 for styles

**Storage**: N/A (rows already loaded by the dashboard; nothing persisted)

**Testing**: vitest + Testing Library (component and pure sort/search helpers); browser walk per quickstart

**Target Platform**: modern browsers, phone (360px) to desktop (1280px)

**Project Type**: web app (ui/ change only)

**Performance Goals**: sort or search of 1,000 rows renders in under 100 ms on a laptop (SC-001, SC-002 headroom)

**Constraints**: no extra server request on sort/search (FR-008); English and Spanish (FR-009); keyboard and `aria-sort` (FR-010)

**Scale/Scope**: 4 tables, 5 to 9 columns each, row counts in the hundreds (no paging exists)

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| 1 Simplicity and reuse | One shared component replaces one private table; no new service, no auth change | Pass |
| 2 Tech stack | No new dependency (R1); vitest/eslint as today | Pass |
| 3 Hexagonal | No api change; sort/search rules are pure functions in the ui, tested without the DOM | Pass |
| 4 Security/privacy | No new data shown; test rows invented | Pass |
| 6 Testing | vitest for helpers and component; browser walk in quickstart | Pass |
| 8 Git | Small commits; no migration | Pass |
| 9 Scope | S-066 is Should; it sits after open Must stories unless the owner decides otherwise. The owner asked for it now (2026-11-04); recorded in the backlog by T025 | Pass, noted |

Post-design re-check: unchanged, all pass.

## Project Structure

### Documentation (this feature)

```text
specs/066-table-sort-search/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/data-table.md
└── tasks.md            # next: /speckit-tasks
```

### Source Code

```text
ui/components/DataTable/
├── DataTable.tsx         # generic <DataTable<T> columns rows search? empty labels />
├── tableRows.ts          # pure: compareValues, sortRows, matchesSearch, foldText
├── types.ts              # ColumnDef<T>, SortState, DataTableLabels
├── index.ts
├── DataTable.test.tsx
└── tableRows.test.ts
ui/lib/i18n/table.ts      # en/es: search label, placeholder, no matches, sort announcements
ui/app/admin/
├── AdminDashboard.tsx    # SectionTable removed; renders <DataTable> per tab
├── adminTables.tsx       # four typed schemas: unitsColumns, ingredientsColumns, recipesColumns, usersColumns
└── AdminDashboard.test.tsx  # updated: sort and search per tab
```

**Structure Decision**: The generic component goes under `ui/components/` like other shared parts
(`SearchableSelect`, `Chip`). Schemas stay next to the dashboard, since they hold its labels and
cell renderers. The accent folding already in `SearchableSelect` moves to `tableRows.foldText` and
`SearchableSelect` imports it, so there is one copy.

## Complexity Tracking

None.
