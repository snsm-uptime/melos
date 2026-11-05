# Research: Sort and Search for Tables

## R1 Build the table in-house or add a library (TanStack Table)

- **Decision**: Build in-house: one component and about 80 lines of pure helpers.
- **Rationale**: Four small tables, client-side only, no paging, no column resizing. Constitution 2 asks for a stable stack; a headless library would add a dependency whose surface is mostly unused.
- **Alternatives**: TanStack Table (strong, typed, but larger than the need; can replace the helpers later without changing schemas much since `ColumnDef<T>` mirrors its shape).

## R2 Schema shape: by attribute, typed over the row

- **Decision**: `ColumnDef<T>` with `key: keyof T & string` for data columns, plus optional `id` for computed columns (Delete). A column declares `sort: "text" | "number" | "date" | false`, `searchable?: boolean`, optional `value(row)` for sort/search when the shown cell differs from the raw attribute, and optional `cell(row)` for rendering.
- **Rationale**: Matches the owner's intent (a schema per table, columns from attributes). Typing over `T` catches wrong keys at compile time; today rows are `Record<string, unknown>`, so each tab gets a row type matching spec 055's admin API.
- **Alternatives**: Inferring columns from the first row's keys (rejected: no labels, no order, no hidden `user_aliases`).

## R3 Text comparison and accent folding

- **Decision**: Sort text with `Intl.Collator(locale, { sensitivity: "base", numeric: true })`; search with `foldText = s.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase()` and `includes`.
- **Rationale**: The collator ignores case and accents (FR-003) and orders "á" with "a" in both en and es. `SearchableSelect` already folds with NFD; share one helper.

## R4 Empty values and stability

- **Decision**: `null`, `undefined`, `""` and invalid dates are empty and always go last regardless of direction; ties keep loaded order (Array.prototype.sort is stable in ES2019+).

## R5 Sort cycle and default order

- **Decision** (clarified 2026-11-04): Multi-level sort. Clicking a column not in the sort adds it as the next level, ascending; clicking a sorted column cycles asc → desc → removed, keeping its level; a "Clear sort" button resets. Headings show the level number and arrow. No modifier key, so it works on phones. No sort is active on first render, so the API's default order shows. Sort and search reset when the tab changes (the component remounts per tab via `key={section}`).
- **Rationale**: Spec Story 1 scenarios 1, 2 and 6 to 9; FR-002, FR-002a.

## R6 Accessibility

- **Decision**: The heading text is a `<button>` inside `<th aria-sort="ascending|descending|none">` (set on every sorted column; the button's label adds the level, e.g. "Name, sort level 2, ascending"); non-sortable headings are plain text with no `aria-sort`. The search input has a visible label (visually hidden ok) and a `role="status"` live region announcing the match count or "no matches".

## R7 Which columns sort and search

| Table | Sortable | Searchable |
|---|---|---|
| Units | name (text), reference_count (number), is_default (number: true=1), created_at (date); People (chips) not sortable | name, user_aliases |
| Ingredients | name, recipes, people | name |
| Recipes | title, cart_adds, notebook_name, notebook_kind (text of the shown label), people_with_access (number), id (text) | title, notebook_name, people_aliases, notebook_kind label, id |
| Users | all except none (alias text, counts number, dates date) | none, no search bar |

Not sortable: Delete and Units People (its count duplicates Count). Recipes People with access sorts by its count; chips are never compared (FR-001).
