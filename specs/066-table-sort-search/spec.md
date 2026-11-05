# Feature Specification: Sort and Search for Dashboard Tables

**Feature Branch**: `066-table-sort-search`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "add alphabetical and numerical asc and desc sort to all column tables and include a search bar above the units, ingredients and recipes in the dashboard. make this a standard layout for table views. this way the maintenance of table features get implemented everywhere."

## Clarifications

### Session 2026-11-04

- Q: When the admin clicks a second column heading, should it become a tie-breaker under the first, or only with a held key? → A: Every click on an unsorted column adds it as the next tie-breaker; clicking a sorted column toggles its direction and keeps its place; a third click removes it; a "Clear sort" button resets; each heading shows its level number and direction.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sort any dashboard column (Priority: P1)

An admin opens a dashboard tab (Units, Ingredients, Recipes or Users) and wants to find the biggest, smallest, first or latest item. They click a column heading to sort the table by that column, and click again to reverse the order.

**Why this priority**: Sorting works on every table and is the most common way to read these figures, so it delivers value on its own.

**Independent Test**: Open each of the four tabs, click each sortable heading twice, and check the row order changes ascending, then descending.

**Acceptance Scenarios**:

1. **Given** the Recipes tab is open sorted by its default order, **When** the admin clicks "Added to carts", **Then** rows are ordered from smallest to largest count, and the heading shows the ascending direction.
2. **Given** a column is sorted ascending, **When** the admin clicks the same heading again, **Then** the rows are ordered descending (a third click removes that column from the sort).
3. **Given** a text column such as Name or Title, **When** it is sorted, **Then** rows follow alphabetical order, ignoring letter case and accents.
4. **Given** a numeric column, **When** it is sorted, **Then** numbers are compared as numbers (for example 9 comes before 10), not as text.
5. **Given** a date column, **When** it is sorted, **Then** rows are ordered by date, and rows with no date are placed last in both directions.
6. **Given** the Units tab sorted by Count ("Cantidad"), **When** the admin clicks Name, **Then** rows are ordered by Count first and, among equal counts, by Name; Count shows level 1 and Name level 2.
7. **Given** a column already in the sort, **When** the admin clicks it, **Then** its direction flips and its level stays; **When** clicked a third time, **Then** it leaves the sort and the levels after it move up one.
8. **Given** any sort is active, **When** the admin presses "Clear sort", **Then** the table returns to its default order.
9. **Given** a column that is sorted, **When** the admin switches to another tab and back, **Then** the tab shows its default order again (the sort is not remembered).

---

### User Story 2 - Search the Units, Ingredients and Recipes tables (Priority: P2)

An admin types part of a name or title into a search bar above the Units, Ingredients or Recipes table and sees only the matching rows.

**Why this priority**: These three tables can grow long, so search makes them usable. It depends on the same shared table layout as Story 1.

**Independent Test**: Open the Recipes tab, type part of a recipe title, and confirm only matching rows remain; clear the box and confirm all rows return.

**Acceptance Scenarios**:

1. **Given** the Recipes tab, **When** the admin types "sop", **Then** only rows where any visible text (title, notebook name, person alias) contains "sop" remain, ignoring case and accents.
2. **Given** a search is active, **When** the admin sorts a column, **Then** the sort applies to the filtered rows only.
3. **Given** a search matches nothing, **When** the table is shown, **Then** it says that nothing matches the search, and the search box stays available.
4. **Given** the search box has text, **When** the admin clears it, **Then** every row is shown again.
5. **Given** the Users tab, **When** it is open, **Then** no search bar is shown (search is required only for Units, Ingredients and Recipes).

---

### User Story 3 - One shared table layout (Priority: P3)

A developer adds a new sort or search behaviour once and every dashboard table gets it. Each table is described by its columns and what each column can do, not by its own code.

**Why this priority**: It is what makes later maintenance cheap. It does not change what an admin sees, so it can ship last.

**Independent Test**: Add a test column flagged as sortable to one table's definition and confirm it sorts without any change to the table component.

**Acceptance Scenarios**:

1. **Given** the four dashboard tables, **When** their sortable and searchable columns are listed, **Then** they are all rendered by the same table layout.
2. **Given** a column is not marked sortable, **When** the table is shown, **Then** its heading is plain text and cannot be clicked to sort.

---

### Edge Cases

- A recipe with no notebook name, an ingredient with no recipes, or a user with no alias sorts as empty and is placed last.
- Ties left after every sort level keep the loaded order, so repeated clicks never shuffle equal rows.
- Empty values go last within each level, in both directions.
- The Delete column and the Units "People" (chip) column are not sortable; the Recipes "People with access" column sorts by its count only. Both chip columns are searched by alias.
- A table with no rows shows its existing empty message, with no search bar content to act on.
- Sorting or searching never changes the data on the server or the numbers shown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every column table on the dashboard MUST let the admin sort by any column that holds text, numbers or dates, except the Delete column and the Units "People" (chip) column, whose count is already the "Count" column. The Recipes "People with access" column sorts by its count.
- **FR-002**: Sorting MUST support several levels. A click on a column not in the sort MUST add it as the last level, ascending. A click on a column in the sort MUST cycle ascending → descending → removed; removing a level moves the later levels up, and other levels keep their place and direction. Rows MUST be ordered by level 1, ties by level 2, and so on. Each sorted heading MUST show its level number and direction.
- **FR-002a**: When any sort is active, a "Clear sort" control MUST be shown above the table, next to the search bar where there is one; it returns the table to its default order. It is not shown when the table has no rows.
- **FR-003**: Text MUST sort alphabetically, ignoring letter case and accents. Numbers MUST sort numerically. Dates MUST sort chronologically. Empty values MUST sort last in both directions.
- **FR-004**: The Units, Ingredients and Recipes tables MUST each show a search bar above the table.
- **FR-005**: Search MUST match part of the text in the columns marked searchable in the table's schema, ignoring letter case and accents, and MUST show only matching rows. Searchable: Units name and people aliases; Ingredients name; Recipes title, notebook name, notebook kind (as shown), people aliases and id.
- **FR-006**: When no row matches, the table MUST say so in words, and the search bar MUST stay usable.
- **FR-007**: Sort and search MUST be applied by the same shared table layout used by all four dashboard tables. The layout MUST accept a list of any kind of row object and a per-table schema of column definitions keyed by the row's attributes; a column's sort and search behaviour MUST be set in that schema, not in the table's own code. A new table MUST need only a schema and its rows.
- **FR-008**: Sorting and searching MUST happen on the rows already loaded in the browser. They MUST NOT call the server again.
- **FR-009**: Sort and search text MUST be available in English and Spanish.
- **FR-010**: The search bar and sortable headings MUST be usable with a keyboard, and each sortable heading MUST announce its sort direction and level to screen readers.

### Key Entities

- **Table view**: a dashboard table defined by its columns, its rows, its default order, and which columns can be sorted or searched.
- **Column definition**: one column's heading, how to show its value, whether it can be sorted, and whether it takes part in search.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can sort any sortable column ascending or descending in under 2 seconds from the tab being opened, with no page reload.
- **SC-002**: On the Units, Ingredients and Recipes tabs, a search for part of a name returns the matching rows in under 1 second.
- **SC-003**: All four dashboard tables use one shared layout, so a new table feature needs one change and reaches all four tables.
- **SC-004**: 100% of sorted headings report their current direction and sort level to assistive technology.
- **SC-005**: No sort or search action makes an additional request to the server.

## Assumptions

- The admin dashboard's four tables (Units, Ingredients, Recipes, Users) are every table the app has today (owner, 2026-11-04). Card lists such as recipe and notebook lists are not tables and are out of scope.
- Searching is a plain "contains" match across the visible text of a row, not a ranked search.
- The default order of each tab stays as it is today. A tab's sort resets when the admin leaves the tab; it is not remembered.
- Search covers only Units, Ingredients and Recipes, as asked. Users keep sort only.
- Sorting uses the browser's loaded rows, which the dashboard already fetches in full (no paging exists).
- The shared table layout is an internal change. It must not change the data the API returns.
