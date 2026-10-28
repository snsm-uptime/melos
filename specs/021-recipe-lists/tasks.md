# Tasks: Recipe Lists for a Personal Notebook and a Kitchen

**Input**: Design documents from `specs/021-recipe-lists/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/list-api.md, contracts/list-ui.md, quickstart.md

**Organization**: Grouped by user story (spec.md: US1 P1 personal notebook list, US2 P1 kitchen list, US3 P2 text filter). Phase 2 holds the migration, domain rules, port and page shell every story needs. The filter is added in US3 so US1 and US2 ship and test without it.

**Tests**: The spec does not request TDD, but constitution §6 requires domain tests, application tests with fakes and integration tests, so test tasks are included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 (story phases only)
- Paths are repository-relative. api code runs from `api/`, so `domain/…` in code means `api/domain/…` on disk.

## Path Conventions

- api: `api/domain/`, `api/application/`, `api/adapters/persistence/`, `api/api/routes/`, `api/api/schemas/`, `api/tests/`
- ui: `ui/app/api/`, `ui/app/notebooks/`, `ui/app/kitchens/`, `ui/components/`, `ui/lib/`, `ui/lib/i18n/`

---

## Phase 1: Setup

- [X] T001 Record the baseline: run `cd api && uv run pytest -q && uv run ruff check .` and `cd ui && npm test && npm run lint && npm run typecheck`. Write the pass counts under "Baseline" in `specs/021-recipe-lists/notes.md` (create it).

---

## Phase 2: Foundational (blocking prerequisites)

- [X] T002 [P] Create `api/adapters/persistence/migrations/versions/0006_unaccent.py` (revision `0006_unaccent`, down_revision `0005_recipes`): `upgrade` runs `CREATE EXTENSION IF NOT EXISTS unaccent`; `downgrade` is a no-op with a comment saying dropping the extension is left to the owner. Follow the docstring style of `0005_recipes.py`.
- [X] T003 [P] Create `api/domain/recipe_search.py` (pure, no I/O): constant `PAGE_SIZE = 12`; `search_key(text: str) -> str` returning `normalize_name(text)` from `domain/ingredient_catalog.py` (empty string for blank text); `clamp_page(requested: int, total: int, page_size: int = PAGE_SIZE) -> tuple[int, int]` returning `(page, total_pages)` with `total_pages = max(1, ceil(total / page_size))` and `page = min(requested, total_pages)`; raise `InvalidPageError` (add to `api/domain/errors.py`, `CODE = "invalid_page"`) when `requested < 1`.
- [X] T004 [P] Create `api/tests/test_recipe_search_domain.py`: `search_key` trims, drops accents ("Calabazá" → "calabaza"), case-folds, collapses spaces, and returns "" for spaces only; `clamp_page` for total 0 → (1, 1), total 12 → 1 page, total 13 → 2 pages, requested 9 with 13 recipes → (2, 2), requested 0 raises `InvalidPageError`.
- [X] T005 Add to `api/application/ports.py`: frozen slots dataclasses `RecipeCardRow` (`id`, `title`, `author_alias: str | None`, `ingredient_count: int`, `notebook_id`, `notebook_name`, `created_at: datetime`) and `RecipePage` (`items: list[RecipeCardRow]`, `total: int`); Protocol `RecipeListRepository` with `list_page(notebook_ids: Sequence[UUID], key: str, offset: int, limit: int) -> RecipePage` ("newest first: created_at desc, id desc; key is a search key, empty means no filter; empty notebook_ids gives an empty page").
- [X] T006 [P] Create `api/api/schemas/recipe_lists.py`: Pydantic `RecipeCardResponse` (fields as in `contracts/list-api.md`) and `RecipePageResponse` (`items`, `page`, `page_size`, `total`, `total_pages`).
- [X] T007 [P] Create `ui/lib/i18n/recipeLists.ts` in the shape of `ui/lib/i18n/notebooks.ts` (English only): empty notebook ("No recipes in this notebook yet."), empty kitchen, no match (with the typed text), clear filter, filter placeholder, "N ingredients" / "1 ingredient", author "unknown", page "Page X of Y", previous, next, not found, load error, retry.
- [X] T008 [P] Create `ui/lib/recipesClient.ts` in the pattern of `ui/lib/notebooksClient.ts`: types `RecipeCard` and `RecipePage` matching `contracts/list-api.md`; `fetchNotebookRecipes(notebookId, page, q)` and `fetchKitchenRecipes(kitchenId, page, q)` calling the BFF routes; failures keep `status` and `code`, network failure is status 0. Add `ui/lib/recipesClient.test.ts` covering success, 404 code kept, network failure, malformed body.
- [X] T009 [P] Create `ui/components/RecipeCard/RecipeCard.tsx` (display only, no link, no checkbox, no category chips): default cooking-pot icon, one-line title with ellipsis and full title as `title` attribute, author chip ("unknown" when null), ingredient count, and the notebook name only when a `notebookName` prop is passed. Add `RecipeCard.test.tsx` (card with and without notebook name, null author, singular count, long title).
- [X] T010 Create `ui/components/RecipeList/RecipeList.tsx`: props `load(page, q)`, `scope: "notebook" | "kitchen"`, `canAdd`, initial `page`/`q`; renders loading placeholders, the card grid (`ul` of `RecipeCard`), the pager from `contracts/list-ui.md` (previous, next, numbered buttons, "Page X of Y", `aria-current="page"`, hidden for one page), the empty, not found and error-with-Retry states. No filter box yet (US3). Add `RecipeList.test.tsx` for loading, cards, pager navigation, empty, error + retry.
- [X] T011 Run `cd api && uv run ruff check . && uv run pytest tests/test_recipe_search_domain.py -q` and `cd ui && npm run typecheck && npm test -- recipesClient RecipeCard RecipeList`; fix failures before Phase 3.

**Checkpoint**: migration, domain rules, port, schemas, client and list components exist; no route yet.

---

## Phase 3: User Story 1 - Personal notebook recipe list (Priority: P1)

**Goal**: A member opens a notebook and sees its recipes as cards, newest first, in numbered pages (spec FR-001..FR-006, FR-009, FR-010, FR-012, FR-013).

**Independent Test**: Save two recipes into a personal notebook, open `/notebooks/{id}`, and see two cards newest first with title, author alias, ingredient count; a non-member gets "not found". (quickstart §2)

- [X] T012 [P] [US1] Create `api/adapters/persistence/recipe_lists.py` with `SqlAlchemyRecipeListRepository(session)` implementing `list_page` (T005): select `RecipeModel` joined to `NotebookModel` (name) and left-joined to `UserModel` (alias), `ingredient_count` as a correlated `count()` over `RecipeIngredientModel`, `WHERE recipe.notebook_id IN notebook_ids`, `ORDER BY recipe.created_at DESC, recipe.id DESC`, `OFFSET`/`LIMIT`; `total` from a separate `count()` with the same `WHERE`. Return an empty `RecipePage` for empty `notebook_ids` without querying. The `key` argument is accepted and ignored until T028.
- [X] T013 [US1] Create `api/application/recipe_lists.py` with `ListNotebookRecipesCommand(actor_user_id, notebook_id, page, key)`, a result dataclass `RecipeListResult` (`items`, `page`, `page_size`, `total`, `total_pages`) and `ListNotebookRecipesService(notebooks: NotebookRepository, recipes: RecipeListRepository)`: `facts_for` then `notebook_view` rules; `None` or no access raises `NotebookNotFoundError` (same error for both, FR-010); count first with `clamp_page`, then fetch the clamped page. Reads only, no commit.
- [X] T014 [P] [US1] Create `api/tests/test_recipe_lists_application.py` with a `FakeRecipeListRepository` and the existing fake notebook repository: a reader sees the notebook's recipes; a stranger and a missing notebook raise the same `NotebookNotFoundError`; page past the end returns the last page; empty notebook returns page 1 of 1; page 0 raises `InvalidPageError`; nothing is written to any fake.
- [X] T015 [US1] Add the route `GET /notebooks/{notebook_id}/recipes` to `api/api/routes/notebooks.py` (query `page: int = 1`, `q: str = ""` with max length 100, accepted but unused until US3), mapping `NotebookNotFoundError` to the existing `_notebook_not_found()` body, `InvalidPageError` to 422 `{"code": "invalid_page"}`, and over-long `q` to 422 `{"code": "invalid_query"}`. Add the service provider to `api/api/deps.py`. Declare the route so it does not clash with `/{notebook_id}`.
- [X] T016 [US1] Create `api/tests/test_recipe_lists_integration.py` (Compose test overlay, pattern of `test_recipe_save_integration.py`; invented data only): personal notebook list newest first with alias and ingredient count; a member of another person's notebook sees the same list; a stranger gets the same 404 body as an unknown id; an author whose account is deleted shows `author_alias` null; 13 recipes → page 1 has 12, page 2 has 1, page 9 returns page 2; page 0 → 422; row counts of `notebook`, `recipe`, `ingredient` unchanged after the requests.
- [X] T017 [P] [US1] Create `ui/app/api/notebooks/[notebookId]/recipes/route.ts` forwarding `page`, `q` and the session cookie to the api and returning its status and body (pattern of `ui/app/api/notebooks/[notebookId]/route.ts`), with `route.test.ts`.
- [X] T018 [US1] Create `ui/app/notebooks/[notebookId]/page.tsx` (server component, pattern of `ui/app/notebooks/page.tsx`: `requireAlias`, locale cookie, `force-dynamic`) and a client `NotebookRecipesScreen.tsx` beside it that shows the notebook name, `SavedNotice` with `returnPath={`/notebooks/${notebookId}`}`, and `RecipeList` with scope "notebook" and `load` = `fetchNotebookRecipes`; `page` comes from `?page=`. The empty state offers the add-recipe action (`AddRecipeCallToAction`) with this notebook as the only candidate. Add `NotebookRecipesScreen.test.tsx` (cards, empty, not found, saved notice once).
- [X] T019 [P] [US1] Edit `ui/components/NotebookCard/NotebookCard.tsx`: add optional `href`; when given, render the card as a `next/link` wrapping the same content (keyboard focusable, visible focus), otherwise unchanged. Replace the "inert, no link" doc comment. Update `NotebookCard` tests for both modes.
- [X] T020 [US1] Edit `ui/app/notebooks/NotebookTabScreen.tsx` to pass `href={`/notebooks/${notebook.id}`}` to each `NotebookCard`, and `ui/app/kitchens/KitchenNotebooksSection.tsx` to do the same for its cards. Update `NotebookTabScreen.test.tsx` and `KitchenNotebooksSection.test.tsx` so cards are links and the old "inert" expectations are removed.
- [X] T021 [US1] Change the capture return path so a personal notebook Save returns to `/notebooks/{notebookId}` while a kitchen Save keeps `/kitchens/{kitchenId}`: find where the capture flow builds `returnPath` (start from `ui/components/AddRecipeCallToAction` and `ui/lib/capture/captureStore.ts`) and update it, with a unit test for both cases. Remove the now-unused `SavedNotice` from `NotebookTabScreen.tsx` only if no flow returns to `/notebooks` any more.

**Checkpoint**: `GET /notebooks/{id}/recipes` and the notebook page work; quickstart §2 and §6 pass for a personal notebook.

---

## Phase 4: User Story 2 - Kitchen recipe list across its notebooks (Priority: P1)

**Goal**: A kitchen member sees the recipes of all the kitchen's notebooks together, never a personal notebook's (spec FR-002, FR-004, FR-010, FR-011, FR-012).

**Independent Test**: In a kitchen with two members, each saves a recipe; both appear on the kitchen page with the right author chips and notebook names; a non-member gets "not found". (quickstart §3)

- [X] T022 [US2] Add `ListKitchenRecipesCommand(actor_user_id, kitchen_id, page, key)` and `ListKitchenRecipesService(kitchens: KitchenRepository, notebooks: NotebookRepository, recipes: RecipeListRepository)` to `api/application/recipe_lists.py`: authorize with `AuthorizeKitchenAccessService` action `read_kitchen` (missing kitchen and non-member both raise `KitchenNotFoundError`), load `kitchen_ids_for(kitchen_id)`, list across them with the same count-then-clamp flow as T013. It MUST NOT call `ensure_kitchen_notebook`; a kitchen with no notebook returns the empty page. An archived kitchen is allowed.
- [X] T023 [P] [US2] Extend `api/tests/test_recipe_lists_application.py`: recipes from two kitchen notebooks are merged newest first; a personal notebook's recipes are never returned; non-member and unknown kitchen raise the same `KitchenNotFoundError`; a kitchen with no notebook returns the empty page and the fake notebook repository records no `create`; an archived kitchen still lists.
- [X] T024 [US2] Add the route `GET /notebooks/kitchens/{kitchen_id}/recipes` to `api/api/routes/notebooks.py` (same query rules as T015), declared before `/{notebook_id}` next to `/kitchens/{kitchen_id}`, mapping `KitchenNotFoundError` to `_kitchen_not_found()`. Add its provider to `api/api/deps.py`.
- [X] T025 [US2] Extend `api/tests/test_recipe_lists_integration.py`: two members each save into a kitchen notebook and both see both recipes with the right `author_alias` and `notebook_name`; a member's personal-notebook recipe is absent from the kitchen list; non-member and unknown kitchen get identical 404 bodies; archived kitchen answers 200; a kitchen with no notebook returns the empty page and `notebook` row count is unchanged.
- [X] T026 [P] [US2] Create `ui/app/api/notebooks/kitchens/[kitchenId]/recipes/route.ts` (same forwarding as T017) with `route.test.ts`.
- [X] T027 [US2] Edit `ui/app/kitchens/KitchenNotebooksSection.tsx`: below the notebook cards, render `RecipeList` with scope "kitchen", `load` = `fetchKitchenRecipes`, `canAdd = !isArchived`, and the notebook name on each card; keep the existing `SavedNotice` for `/kitchens/{id}`. An archived kitchen shows the list and no add action. Update `KitchenNotebooksSection.test.tsx` for the list, the archived case and the not-found case.

**Checkpoint**: quickstart §3 passes; US1 and US2 both work with no filter.

---

## Phase 5: User Story 3 - Filter a list by text (Priority: P2)

**Goal**: Typing narrows either list to recipes whose title or any ingredient name contains the text, ignoring case and accents (spec FR-007, FR-008).

**Independent Test**: With "Lentil soup" (lentil, onion) and "Pancakes" (flour, milk): "onion" → soup only; "PANCAKE" → pancakes only; clear → both; "calabazá" finds "Crema de calabaza". (quickstart §4)

- [X] T028 [US3] Implement the filter in `api/adapters/persistence/recipe_lists.py`: when `key` is not empty, escape `\`, `%` and `_` in it, then add to both the page query and the count query `unaccent(lower(recipe.title)) LIKE :pattern ESCAPE '\'` OR `EXISTS (SELECT 1 FROM recipe_ingredient WHERE recipe_id = recipe.id AND unaccent(lower(name)) LIKE :pattern ESCAPE '\')`, with `:pattern = '%' || key || '%'` bound as a parameter, never concatenated. Order is unchanged.
- [X] T029 [US3] Pass the filter through: in `ListNotebookRecipesService` and `ListKitchenRecipesService` (`api/application/recipe_lists.py`) use `search_key(command.q)` as `key`; in both routes (`api/api/routes/notebooks.py`) pass `q` to the command. Extend `api/tests/test_recipe_lists_application.py`: spaces only behaves as no filter; the key reaches the fake repository trimmed and accent-free.
- [X] T030 [US3] Extend `api/tests/test_recipe_lists_integration.py` against Postgres: title match; ingredient-only match; "PANCAKE" case; "calabazá" finds "Crema de calabaza"; no match gives `items` `[]`, `total` 0; `q` of "%" and "_" match only literal characters; the filter applies across all pages (13 recipes, 3 matching, `total` 3, page 1 holds them); order is unchanged by the filter; on a kitchen list it searches all of the kitchen's notebooks. Add `api/tests/test_unaccent_migration.py`: upgrade to head works, `SELECT unaccent('é')` returns `e`, running `0006_unaccent` upgrade twice is harmless.
- [X] T031 [US3] Add the filter box to `ui/components/RecipeList/RecipeList.tsx`: text input (`maxLength` 100, accessible label, placeholder from `recipeLists.ts`), 300 ms pause before applying, `q` and `page` kept in the query string with `router.replace`, page returns to 1 when `q` changes, "No recipes match "…"" with a Clear filter button when `q` is set and nothing matches, and the plain empty message when `q` is empty. Extend `RecipeList.test.tsx` (debounce with fake timers, page reset, clear filter, no-match vs empty) and the two screen tests.

**Checkpoint**: quickstart §4 passes on both lists.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T032 [P] Run the full checks: `cd api && uv run ruff check . && uv run ruff format --check . && uv run pytest -q`, the Compose integration run for `tests/test_recipe_lists_integration.py` and `tests/test_unaccent_migration.py`, and `cd ui && npm run lint && npm run typecheck && npm test`. Compare counts with the baseline in `specs/021-recipe-lists/notes.md`.
- [ ] T033 Walk `specs/021-recipe-lists/quickstart.md` §2 to §6 in a browser at phone width and desktop width (constitution §6). Record what was checked in `specs/021-recipe-lists/notes.md`. Include the no-write counts of §5.
- [ ] T034 [P] Update `specs/060-notebook-list-tabs/spec.md` FR-014 with a one-line note that cards became links in spec 021, and update `dev/docs/backlog.yaml` S-021 to `status: done` with a short note (filter limited to title and ingredient name; S-047 owns the richer filters). Do this only after T032 and T033 pass.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. Phase 2 blocks every story.
- US1 (Phase 3) is the MVP. US2 reuses the port, adapter, schemas and `RecipeList` from US1/Phase 2 and adds its own use case, route and kitchen wiring. It can start after T013 is merged, in parallel with the UI tasks of US1.
- US3 depends on US1 and US2 existing (it extends both services and both routes) and on T028 before T029/T030.
- Inside a story: adapter and application before route, route before BFF route, BFF route before page.

### Parallel opportunities

- Phase 2: T002, T003, T004, T006, T007, T008, T009 touch different files.
- US1: T012 and T014 together; T017, T019 together once T015 is done.
- US2: T023 and T026 together after T022/T024.

## Implementation Strategy

1. MVP: Phase 1 + 2 + US1. A member sees a notebook's recipes and lands on them after Save.
2. Add US2 for the shared kitchen view.
3. Add US3, the filter, last (the lists are useful without it).
4. Polish, then mark S-021 done.
