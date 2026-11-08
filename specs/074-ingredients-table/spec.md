# Feature Specification: Ingredients Table Layout (user and admin)

**Feature Branch**: `074-ingredients-table` (not created yet)

**Created**: 2026-11-08

**Status**: Draft, pending implementation. Not yet in `dev/docs/backlog.yaml`; the owner assigns the story ID.

**Input**: Owner's revised outline, "organizing the ingredients table": one shared column order for the user's Ingredients page and the admin dashboard, with admin-only columns added after the shared ones.

## Review against existing specs and the constitution

Checked on 2026-11-08 against `.specify/memory/constitution.md` (3.0.0), specs 043, 055, 063, 066, 070 and 073, and the code.

**Constitution: no amendment needed.** This is a post-MVP story (principle 9): it needs a spec under `specs/` and a backlog entry before it is built. It reuses the shared table (principle 1), shows only names and counts to the admin, as the admin dashboard already does (principle 4), and adds no AI output (principle 5). Its admin review view is the same list spec 073 already requires.

**Existing specs that this story changes or must reconcile:**

| # | Source | Conflict or gap | Proposed resolution |
|---|---|---|---|
| 1 | Spec 066 FR-005 | The searchable columns are listed by name. New admin columns would need to be added there if searchable. | Add the new searchable columns to FR-005 in this story's spec; list status and source as sortable but not searchable. |
| 2 | Spec 066 Assumptions | "The default order of each tab stays as it is today." The owner's outline sorts the count columns descending by default. Today the admin ingredients table is ordered by recipes descending, then name, so this matches. The People column is new. | Keep the current default (recipes descending, then name). Do not add a new default. |
| 3 | Spec 070 FR-014 | Place tabs show defaults first, then custom places alphabetically. The outline puts custom places first in the Place picker. | **Decided by owner (2026-11-08):** the Place picker lists custom places first, then defaults (as the outline and current code do). FR-014 still governs the place tabs, which list defaults first. The two orders are separate rules. |
| 4 | Spec 043 (shopping list rule) | The name shown to a person follows their interface language, with the kept name as fallback. The outline shows `ingredient.name` as the main name. | Show the name in the viewer's interface language when one exists, else `ingredient.name`. Other names stay underneath. |
| 5 | Existing catalog view (`ui/components/CatalogManager/CatalogManager.tsx`) | It already has a Language column, always shown, plus Other names, Recipes (count) and Actions. The outline makes Language appear only with two or more languages, which is a change to behaviour that no spec asks for. | **Decided by owner (2026-11-08):** the Language column is always shown in the catalog view. The "only when two languages" rule is dropped. |
| 6 | Existing places view (`ui/components/Ingredients/IngredientsScreen.tsx`) | Name, Place, Last used and Recipes are shown, and this view is the "All notebooks" option. Actions (rename, merge, delete) appear only in the per-notebook catalog view. The outline puts Actions on the same table. | Keep two views with the same first columns. Actions appear only in the per-notebook catalog view, as spec 043 says. |
| 7 | Spec 055 (admin ingredients) | "Tomate ... appears once with 4 recipes and 2 people, whichever notebooks hold it." This confirms that the admin table groups by name, and that People counts distinct recipe authors. | Confirmed: group by name (decision 4a), People = authors (decision 4b). |
| 8 | Spec 073 FR-022 | The admin dashboard must list flagged values awaiting a decision (admin review items). Standard status as a per-row column does not replace that list. | **Decided by owner (2026-11-08):** a Standard status column doesn't replace that list, so the review list gets its own admin section. The Standard status column is a read-only extra on each row. |
| 9 | Spec 073 FR-020, principle 5 | AI-made standard names are saved without confirmation and must be listed for admin review. | The Source column (`discovery`, `ai`, `admin`) and Standard status meet this for the table. The review list (row 8) is still required. |

**Open items for the owner:** row 3 (picker order), row 5 (Language rule), row 8 (review list in addition to columns).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the ingredient list on the Ingredients page (Priority: P1)

A member opens Ingredients from the side panel and sees one row per ingredient name they work with, with its place, when it was last used and the recipes that use it.

**Why this priority**: The page is the way a member picks where each ingredient is bought (spec 070), so it must read clearly first.

**Independent Test**: Open the page in each interface language with two places and one ingredient used in two recipes; check the name, place picker, last used date and recipe links.

**Acceptance Scenarios**:

1. **Given** an ingredient with other names, **When** the page is shown, **Then** the name is in the viewer's interface language (when there is one), and the other names appear underneath in smaller text.
2. **Given** an ingredient, **When** the member opens its Place picker, **Then** the picker shows the current place, with custom places listed first, then defaults (owner decision, row 3). The place tabs keep the order of spec 070 FR-014.
3. **Given** an ingredient no recipe uses, **When** the page is shown, **Then** Last used reads "Never".
4. **Given** an ingredient used by recipes, **When** the Recipes count is shown, **Then** it expands to the recipe titles as links.
5. **Given** the Recipes or Place column, **When** it is sorted, **Then** it follows the shared table rules of spec 066 (FR-001 to FR-003).

### User Story 2 - Maintain the catalog of one notebook (Priority: P2)

A member who can write to a notebook opens its catalog and sees each kept name with its language, other names, recipe count and actions.

**Why this priority**: The actions change data, so they come after reading.

**Independent Test**: Open a notebook catalog as a writer and as a reader; check that Rename, Merge and Delete appear only for the writer.

**Acceptance Scenarios**:

1. **Given** a writer, **When** the catalog is shown, **Then** Rename, Merge and Delete are visible in the Actions column, at the far right.
2. **Given** a reader of the same notebook, **When** the catalog is shown, **Then** no Actions column is shown.
3. **Given** any ingredient, **When** the catalog is shown, **Then** the Language column is always shown in this view (owner decision, row 5).

### User Story 3 - Compare ingredients on the admin dashboard (Priority: P3)

The admin sees the same first columns as the user views, then admin-only columns, and can sort and search the table.

**Why this priority**: It is for maintenance, and it uses the same layout so the two views can be compared.

**Independent Test**: Seed two accounts with overlapping ingredients and check the admin figures against the known data (spec 055 SC).

**Acceptance Scenarios**:

1. **Given** "tomate" in 4 recipes by 2 different authors, **When** the admin opens the Ingredients section, **Then** it appears once with 4 recipes and 2 people, whichever notebooks hold it (spec 055).
2. **Given** the admin table, **When** it is first shown, **Then** it is sorted by Recipes, descending, then by name (spec 066 default).
3. **Given** the admin table, **When** a count column is sorted, **Then** the sort works in both directions with the shared rules of spec 066.
4. **Given** a row, **When** Standard status is shown, **Then** it reads "Checked", "Pending" or "Rejected" from `standard_ingredient.ai_checked_at` and whether it has an AI-made name.
5. **Given** a row, **When** Source is shown, **Then** it reads `discovery`, `ai` or `admin` from `standard_ingredient_name.source`.
6. **Given** the admin dashboard, **When** it opens the review list, **Then** each flagged value awaiting a decision is listed, with the AI-made entry it replaces and who entered it (spec 073 FR-022).

### Edge Cases

- An ingredient with no place chosen shows Supermarket (spec 070).
- An ingredient with no recipes shows 0 recipes and "Never" for Last used, and sorts last on Last used.
- An ingredient with no AI-made name and no admin name shows Standard status "Pending" until the job checks it (spec 073).
- A rejected translation keeps its discovery name and shows "Rejected" (spec 073).
- A name in more than one language appears once in the admin table, grouped by name (decision 4a).
- Empty values sort last in both directions (spec 066 FR-003).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Ingredients page and the admin Ingredients table MUST use the shared table layout (spec 066, `DataTable`) with the same first columns: Ingredient (name with other names), Recipes (count and recipe links), and the view's own columns (Place, Last used on the page; People on the admin table).
- **FR-002**: The admin table MUST group rows by name. People MUST count distinct recipe authors (spec 055).
- **FR-003**: The admin table MUST add Standard status, Source and Notebooks (the count of notebooks that hold the name) after the shared columns.
- **FR-004**: The main name MUST follow the viewer's interface language when a name exists in it, else `ingredient.name` (spec 043).
- **FR-005**: Searchable columns MUST be added to spec 066 FR-005 for each table that gains them. Standard status and Source are sortable and not searchable.
- **FR-006**: The Actions column (rename, merge, delete) MUST appear only in the per-notebook catalog view and only for members who can write to the notebook (spec 043).
- **FR-007**: The Language column MUST always be shown in the catalog view (owner decision, row 5).
- **FR-008**: The admin dashboard MUST list admin review items (spec 073 FR-022), as a section separate from the Ingredients table.
- **FR-009**: No new data MUST be stored. Every column reads existing tables: `ingredient`, `ingredient_name`, `ingredient_place`, `recipe_ingredient`, `recipe`, `standard_ingredient`, `standard_ingredient_name`, `standard_ingredient_review`.
- **FR-010**: All labels MUST be in English and Spanish (spec 063).
- **FR-011**: Sorting and searching MUST NOT call the server again (spec 066 FR-008).

### Key Entities

- **Ingredient row (user)**: one kept name in the person's view, with its place and recipe counts.
- **Ingredient row (admin)**: one name across all notebooks, with counts of recipes, authors and notebooks, and its standard status.
- **Admin review item**: a flagged value awaiting the admin's decision (spec 073).

## Success Criteria *(mandatory)*

- **SC-001**: The two views share their first columns, so an admin and a member see the same name and recipe count for the same ingredient.
- **SC-002**: The admin figures match the seeded test data (spec 055).
- **SC-003**: No write action is visible to a reader of a notebook.
- **SC-004**: No sort or search makes a server request.

## Assumptions

- Spec 066 remains the owner of table behaviour; this story only adds columns and searchable fields.
- Spec 070 remains the owner of place rules; the picker order follows its FR-014 unless the owner decides otherwise.
- The admin uses `users.is_admin` (spec 055).
- The Standard status and Source columns are read-only.

## Next steps before implementation

1. Done: added as S-074 in `dev/docs/backlog.yaml` (status backlog, priority should). The ID is proposed; the owner confirms it and sets the priority (principle 9).
2. Done: all open rows are decided. Row 3: custom places first in the picker. Row 5: Language always shown in the catalog view. Row 8: review list in its own admin section.
3. Done: spec 070 FR-014 has a note that the picker order differs from the tab order. Spec 043 FR-007 has a note that the viewer-language rule also applies to the catalog and places tables. Spec 066 FR-005 needs no change, because the new admin columns (Standard status, Source, Notebooks) are not searchable.
4. Not done: `plan.md`, `tasks.md` and tests. These belong to the implementation stage, after the owner confirms the story ID and priority.
