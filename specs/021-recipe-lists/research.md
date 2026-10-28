# Research: Recipe Lists for a Personal Notebook and a Kitchen

Resolves the design questions for [plan.md](./plan.md). No NEEDS CLARIFICATION markers remain.

## R1. Where the notebook recipe list lives in the ui

- **Decision**: A new page `/notebooks/[notebookId]` shows one notebook's list. The cards of the Notebook tab (personal) and of the kitchen notebooks section both link to it. A kitchen page also shows the combined list of all its notebooks.
- **Rationale**: Spec 060 promised the cards open "the notebook's recipe list". Checked in code: the cards are inert and no notebook page exists. One page and one route serve personal and kitchen notebooks because access is decided by `facts_for` for both kinds.
- **Alternatives considered**: Listing personal recipes inside the Notebook tab (cannot show several notebooks cleanly); a kitchen-only combined list with inert notebook cards (leaves FR-013 half done).

## R2. Two routes

- **Decision**: `GET /notebooks/{notebook_id}/recipes` and `GET /notebooks/kitchens/{kitchen_id}/recipes`, both with `page` and `q`. The kitchen route is declared before `/{notebook_id}`, like the existing `/kitchens/{kitchen_id}`.
- **Rationale**: Mirrors the spec 056 read routes. The kitchen route is a different scope (all notebooks, kitchen authorization), so it is its own route.
- **Alternatives considered**: One route with a `scope` parameter (mixes two access rules in one handler); `GET /recipes?notebook_id=` (a second naming scheme next to `POST /recipes`).

## R3. Access without side effects

- **Decision**: Notebook list: `facts_for(actor, notebook_id)`; `None` or no access raises `NotebookNotFoundError` (404 `notebook_not_found`). Kitchen list: `AuthorizeKitchenAccessService` with action `read_kitchen` (404 for missing and non-member), then `kitchen_ids_for(kitchen_id)`. If it returns nothing, the list is empty. The kitchen list never calls `ensure_kitchen_notebook`.
- **Rationale**: FR-010, FR-011, FR-012. `ListKitchenNotebooksService` creates a notebook on first open (spec 056 FR-008a); a recipe list must not. Archived kitchens pass `read_kitchen`, so they are readable.
- **Alternatives considered**: Reusing `ListKitchenNotebooksService` (writes on first open, breaks FR-012).

## R4. Accent- and case-insensitive filter

- **Decision**: Migration `0006_unaccent` enables the `unaccent` extension. The adapter compares `unaccent(lower(title))` and `unaccent(lower(ingredient.name))` with `LIKE '%' || :key || '%' ESCAPE '\'`. `:key` is the filter text from `domain/recipe_search.search_key` (the existing `normalize_name`: accents dropped, case-folded, spaces collapsed, trimmed). Ingredient matching uses `EXISTS` over `recipe_ingredient`.
- **Rationale**: FR-007 and Story 3 scenario 3 ("calabazá" finds "calabaza"). Done in SQL so paging and total count stay correct (FR-008). The `vector` extension already sets the precedent for extensions in migrations (`0002`), and `pgvector/pgvector:pg16` ships contrib.
- **Alternatives considered**: A stored `search_text` column (needs a backfill and a write path change in spec 020); filtering in Python after loading all rows (breaks paging and scales badly); `pg_trgm` (fuzzy matching is not asked for).
- **Known gap**: `normalize_name` uses `casefold`, SQL uses `lower`; characters such as "ß" fold differently. Not relevant to English and Spanish recipes; noted, no action.

## R5. Wildcards typed by the member

- **Decision**: Escape `\`, `%` and `_` in the key before binding, and use `ESCAPE '\'`. The key is a bound parameter, never concatenated into SQL.
- **Rationale**: "50%" or "a_b" must match literally, and a wildcard-only filter must not return everything (constitution §4).
- **Alternatives considered**: `position()` / `strpos()` (no escaping needed, but loses the planner's option of an index later; equivalent today — rejected only for consistency with LIKE-based code elsewhere).

## R6. Page size, order, clamping

- **Decision**: Page size 12 (clarified). Order `created_at DESC, id DESC`. `page` below 1 is rejected (422 `invalid_page`); a page past the last one returns the last page, and the response carries the page actually returned. An empty list returns page 1 of 1 with no items.
- **Rationale**: FR-005, FR-006, edge case "a page number past the last page". The `id` tiebreak keeps the order stable when two recipes share a timestamp.
- **Alternatives considered**: Offset errors for out-of-range pages (a stale link would show an error instead of the list); keyset paging (cannot jump to a page by number).

## R7. Card data

- **Decision**: Each row has `id`, `title`, `author_alias` (null when the account is gone), `ingredient_count`, `notebook_id`, `notebook_name`, `created_at`. The author is a left join to `users`; the count is a correlated count over `recipe_ingredient`. No image field: the ui always draws the default cooking-pot icon.
- **Rationale**: FR-003, FR-004. Checked in code: `recipe` has no image column (the preview image is a later story), so the contract does not invent one.
- **Alternatives considered**: Returning `image: null` now (a field nothing reads).

## R8. Return path after Save

- **Decision**: After a personal capture, the return path becomes `/notebooks/{notebook_id}`; a kitchen capture keeps returning to `/kitchens/{kitchen_id}`. `SavedNotice` is rendered on both pages with that `returnPath`.
- **Rationale**: FR-013 needs the member to land on the list that shows the new recipe first. The kitchen page shows the combined list, so it is already that list.
- **Alternatives considered**: Returning personal saves to `/notebooks` (the tab lists notebooks, not recipes).

## R9. URL state for the filter and page

- **Decision**: The ui keeps `q` and `page` in the page's query string, replaces (not pushes) the entry as the member types (with a 300 ms pause), and returns to page 1 when `q` changes.
- **Rationale**: FR-006 (filter change returns to page 1) and a working Back button and reload.
- **Alternatives considered**: Component state only (loses the page on reload or Back).

## R10. Empty-state copy source

- **Decision**: New English messages in `ui/lib/i18n/recipeLists.ts`, in the shape of `notebooks.ts`, English only until the account language setting exists (as spec 060 decided).
- **Rationale**: FR-015, consistent with spec 060.
