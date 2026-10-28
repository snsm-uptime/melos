# Tasks: Save a Confirmed Draft into Its Notebook

**Input**: Design documents from `specs/020-save-confirmed-draft/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/save-api.md, contracts/save-ui.md, quickstart.md

**Organization**: Grouped by user story (spec.md: US1 P1 save the draft, US2 P1 catalog grows, US3 P2 refusals keep the draft). Phase 2 holds the schema and domain work every story needs.

**Tests**: The spec does not request TDD, but constitution §6 requires domain tests, application tests with fakes and integration tests, so test tasks are included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 (story phases only)
- Paths are repository-relative. api code runs from `api/`, so `domain/…` in code means `api/domain/…` on disk.

## Path Conventions

- api: `api/domain/`, `api/application/`, `api/adapters/persistence/`, `api/api/routes/`, `api/api/schemas/`, `api/tests/`
- ui: `ui/app/api/`, `ui/lib/capture/`, `ui/lib/i18n/`, `ui/components/RecipeDraft/`, `ui/app/notebooks/`

---

## Phase 1: Setup

- [X] T001 Record the baseline: run `cd api && uv run pytest -q && uv run ruff check .` and `cd ui && npm test && npm run lint && npm run typecheck`. Write the pass counts under "Baseline" in `specs/020-save-confirmed-draft/notes.md` (create it).

---

## Phase 2: Foundational (blocking prerequisites)

**⚠️ CRITICAL**: No story phase starts until this phase is complete.

- [X] T002 Add the models `SourceModel`, `RecipeModel`, `RecipeIngredientModel`, `StepModel` to `api/adapters/persistence/models.py` as in `data-model.md`. Constraints, verbatim: `source.type` check in (`text`, `url`, `photo`); `recipe.title` check `btrim(title) <> ''`; `recipe.base_servings` check `>= 1`; `recipe.save_key` nullable uuid, unique with `author_id` where not null; `recipe_ingredient.quantity` check `> 0` when set; `recipe_ingredient.unit` check in (`g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`); `recipe_ingredient.size` check in (`small`, `medium`, `large`) and `unit = 'unit'`; vague (`vague_note` set) means `quantity` and `unit` are null, non-vague means both are set; `recipe_ingredient.position` unique with `recipe_id`; `step.text` check `btrim(text) <> ''`; `step.position` unique with `recipe_id`. FKs: `recipe.notebook_id` → `notebook.id` ON DELETE CASCADE; `recipe.author_id` → `users.id` and `recipe.source_id` → `source.id` and `source.user_id` → `users.id`, all ON DELETE SET NULL; lines and steps → `recipe.id` ON DELETE CASCADE.
- [X] T003 Write Alembic migration `api/adapters/persistence/migrations/versions/0005_recipes.py` (revision `0005_recipes`, down revision `0004_drop_kitchen_hide`) that creates the four tables, checks and indexes of T002, with a downgrade that drops them in reverse order.
- [X] T004 [P] Write `api/tests/test_recipes_migration.py` (skips when `DATABASE_URL` is unset): upgrade to `0005_recipes`, downgrade to `0004_drop_kitchen_hide`, upgrade again, with invented rows in `ingredient` and `notebook` that must be unchanged; insert one violating row per check of T002 and assert each is rejected.
- [X] T005 Add a public `check_edited_draft(draft: DraftRecipe) -> DraftRecipe` to `api/domain/recipe_draft.py`: it runs the existing missing-parts and line-problem collection (`DraftProblems`), `_check_title`, `_check_steps`, `_check_servings` and `_check_line`, and does not run `_match_lines`. Same errors as `check_draft`.
- [X] T006 Create `api/domain/recipe.py` with `NewRecipe` (frozen dataclass: title, base_servings, servings_estimated, lines, steps, source_text, author_id, notebook_id, save_key) and `resolve_line_names(lines, catalog_names) -> tuple[lines, new_names]`: for each line name, if a catalog entry has the same spelling (`same_spelling` from `domain/ingredient_catalog.py`) the line takes the entry's spelling; otherwise the name stays and is added once to `new_names` (order of first appearance). Pure: no I/O.
- [X] T007 [P] Write `api/tests/test_recipe_domain.py`: `check_edited_draft` accepts an edited draft and raises `DraftProblems` for a missing title, missing steps and a line with no unit; keeps vague lines without quantity and unit; refuses a size on a non-`unit` line. `resolve_line_names`: "Onions " resolves to existing "onions"; two lines with the same new name give one new name; empty catalog gives every distinct name.
- [X] T008 Add `RecipeRepository` (Protocol) to `api/application/ports.py` with `find_by_save_key(author_id, save_key) -> SavedRecipe | None` and `add(recipe: NewRecipe) -> UUID`, and add `add_names(notebook_id, names) -> None` to the existing `IngredientCatalog` Protocol. The use case calls both ports in the same request transaction; neither adapter calls the other. Define `SavedRecipe` (recipe id, notebook id, title) next to the use case in T012.
- [X] T009 Implement `api/adapters/persistence/recipes.py` (`SqlAlchemyRecipeRepository`): `find_by_save_key` and `add`, which inserts the source (type `text`, `raw_text`, `user_id`), the recipe, its lines and steps (positions from 0) inside a savepoint and returns the id; on the unique violation of `(author_id, save_key)` it rolls back the savepoint and raises `DuplicateSaveKey`, which `SaveRecipeDraft` catches (T012). Add `add_names` to `api/adapters/persistence/ingredient_catalog.py` using `insert(...).on_conflict_do_nothing(index_elements=["notebook_id", "name"])`.

**Checkpoint**: schema, domain rules and ports exist. Story phases can start.

---

## Phase 3: User Story 1 - Member saves a reviewed draft into the notebook (Priority: P1) 🎯 MVP

**Goal**: Save stores one recipe in the capture's notebook with the member as author, once, and returns the member to the notebook with "Recipe saved".

**Independent Test**: Capture in a personal notebook, press Save; one `recipe` row with the member as author and the edited values; pressing Save twice leaves one row.

### Tests for User Story 1

- [X] T010 [P] [US1] Write `api/tests/test_recipe_save_application.py` with fake repositories: personal notebook saves one recipe with the actor as author; kitchen notebook saves one recipe and writes nothing to a personal notebook; edited title, servings flag, lines and steps are stored as sent; the same `save_key` twice returns the first recipe with `created=False` and adds nothing; a `DuplicateSaveKey` from the repository returns the stored recipe; more than 100 lines or 100 steps is refused and stores nothing; `source_text` is stored on the source.
- [X] T011 [P] [US1] Write `api/tests/test_recipe_save_integration.py` (skips when `DATABASE_URL` is unset) with the fake extractor override as in `test_recipe_capture_integration.py`: `POST /recipes` returns 201 and the recipe, line, step and source rows exist; a second identical request returns 200 and the row counts do not change; a non-member gets 404 `notebook_not_found` and no rows; the author is the signed-in user even if the body names another.

### Implementation for User Story 1

- [X] T012 [US1] Create `api/application/recipe_save.py`: `SaveRecipeCommand`, `SavedRecipe` and `SaveRecipeDraft.execute`. Order: text length (`load_recipe_text_max_chars`) and the limits of 100 ingredient lines and 100 steps (spec FR-019) → replay lookup by `(actor, save_key)` → notebook access (`facts_for`; `None` raises `NotebookNotFoundError`; kitchen archived raises `KitchenArchivedError`) → `check_edited_draft` → `resolve_line_names` against `names_for_notebook` → `RecipeRepository.add`; on `DuplicateSaveKey` it re-reads `find_by_save_key` and returns that recipe with `created=False`. Exactly one of `notebook_id` or `kitchen_id` must be set (else `InvalidDraftError`). With `notebook_id` that exact notebook is used and never replaced; only the `kitchen_id` path uses `ResolveCaptureNotebookService` (spec FR-011). Log outcome, line count and step count only, never the title, text or names (research R11).
- [X] T013 [US1] Create `api/api/schemas/recipes.py` (request body per `contracts/save-api.md`, with `ingredient_lines` and `steps` limited to 100 items each) and `api/api/routes/recipes.py` with `POST /recipes` returning 201 (200 on replay) and the success body of the contract; the author comes only from `require_user_alias`. Register the router where the capture router is registered, and add `get_save_recipe_draft` to `api/api/deps.py`.
- [X] T014 [P] [US1] Create the BFF route `ui/app/api/recipes/route.ts`: pass `POST` body, cookie and `Accept-Language` to the api `/recipes`, return status and body unchanged, answer a network failure with 503 `{"code": "save_unavailable"}`. Follow `ui/app/api/notebooks/[notebookId]/captures/text/route.ts`.
- [X] T015 [P] [US1] Create `ui/lib/capture/saveClient.ts` with `submitSave(state)` that builds the body of `contracts/save-api.md` from the edited draft, `source_text`, `saveKey` and notebook id, and returns `{ ok: true }` or `{ ok: false, message }` in the `CaptureMessage` shape; write `ui/lib/capture/saveClient.test.ts` (success, 200 replay, network failure, error codes).
- [X] T016 [US1] Edit `ui/lib/capture/captureStore.ts`: add `saveKey` (made in `showDraft`, cleared in `discardDraft`, `backToSheet`, `clearCapture`), `saving`, and `savedNotice` (`{ notebookId }`) with `markSaved`, `consumeSavedNotice`; extend `captureStore.test.ts`.
- [X] T017 [US1] Edit `ui/components/RecipeDraft/RecipeDraftEditor.tsx`: add the Save control beside Discard per `contracts/save-ui.md` (disabled while saving or when the draft has no title, ingredient line or step); on success call `markSaved`, clear the draft and navigate to `returnPath` without the leave prompt (`LeaveDraftGuard`); extend `RecipeDraftEditor.test.tsx`.
- [X] T018 [US1] Edit `ui/app/notebooks/NotebookTabScreen.tsx` (and the kitchen notebook page that shows the same list, if separate) to show "Recipe saved" once when `consumeSavedNotice` matches the page's notebook; extend `NotebookTabScreen.test.tsx`. Add the message to `ui/lib/i18n/capture.ts`.

**Checkpoint**: a captured draft can be saved and the member lands on the notebook with the notice.

---

## Phase 4: User Story 2 - New ingredient names join the notebook's catalog (Priority: P1)

**Goal**: Names not in the catalog are added once each, in the same transaction as the recipe.

**Independent Test**: Save "onion" (existing) and "leek" (new): catalog has "onion" once and "leek" once; a later capture of "leeks" matches.

### Tests for User Story 2

- [X] T019 [P] [US2] Extend `api/tests/test_recipe_save_application.py`: matched name adds nothing; undone change keeps "onions" and adds "onions"; duplicate new name adds once; empty catalog gets every distinct name; a failure in `RecipeRepository.add` leaves the fake catalog unchanged.
- [X] T020 [P] [US2] Extend `api/tests/test_recipe_save_integration.py`: after saving "onion" matched and "leek" new, `ingredient` has "onion" once and "leek" once for the notebook; "Onions " saved against entry "onions" adds no row; an invalid unit returns 422 and adds no `ingredient` row; two concurrent saves with the same new name leave one row and two recipes.

### Implementation for User Story 2

- [X] T021 [US2] In `api/application/recipe_save.py` call `IngredientCatalog.add_names(notebook_id, new_names)` (names from `resolve_line_names`) right after `RecipeRepository.add`, in the same request transaction, so a failure in either rolls back both; return them as `created_catalog_names` in the response of `api/api/routes/recipes.py` (empty list on replay).

**Checkpoint**: US1 and US2 both work; the catalog grows with each saved recipe.

---

## Phase 5: User Story 3 - Refusals are plain and keep the draft (Priority: P2)

**Goal**: An invalid target or an invalid draft stores nothing, shows a plain message, and leaves the draft on screen.

**Independent Test**: Archive the kitchen after capture, press Save: message shown, draft intact, no rows.

### Tests for User Story 3

- [X] T022 [P] [US3] Extend `api/tests/test_recipe_save_application.py`: archived kitchen raises `KitchenArchivedError` and stores nothing; missing notebook and no-access both raise `NotebookNotFoundError`; no notebook in the kitchen with `kitchen_id` creates one and saves into it, and the notebook remains when the save then fails; several kitchen notebooks with no pick raises `NotebookChoiceRequiredError`; both or neither of `notebook_id`/`kitchen_id` is refused.
- [X] T023 [P] [US3] Extend `api/tests/test_recipe_save_integration.py` with the status and `code` table of `contracts/save-api.md` (404, 409 ×2, 422 ×4) including identical bodies for a missing and a forbidden notebook, and assert no rows after each refusal.
- [X] T024 [P] [US3] Extend `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: on each error code the draft, pasted text and edits stay and the matching message of `contracts/save-ui.md` shows; Save re-enables; a retry after a network failure reuses the same `saveKey`.

### Implementation for User Story 3

- [X] T025 [US3] In `api/api/routes/recipes.py` map `NotebookNotFoundError` → 404, `KitchenArchivedError` → 409, `NotebookChoiceRequiredError` → 409 `notebook_choice_required`, `DraftProblems` → 422 `draft_incomplete` or `ingredient_line_problem` (same body shape as `api/api/routes/recipe_capture.py`), `InvalidDraftError` → 422 `invalid_recipe`, over-long text → 422 `text_too_long`. Return JSON errors only from code paths that run before any insert (research R4).
- [X] T026 [US3] In `ui/lib/capture/saveClient.ts` and `ui/lib/i18n/capture.ts` map each code to the English message table of `contracts/save-ui.md` (reuse the spec 017 wording for `draft_incomplete` and `ingredient_line_problem`); in `RecipeDraftEditor.tsx` show the message at the top of the draft and keep all state.

**Checkpoint**: all three stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T027 Run `cd api && uv run ruff check . && uv run pytest -q` in the Compose test overlay and `cd ui && npm test && npm run lint && npm run typecheck`; compare with the T001 baseline and record the result in `specs/020-save-confirmed-draft/notes.md`.
- [ ] T028 Walk `specs/020-save-confirmed-draft/quickstart.md` sections 2 to 5 in the running stack and note the result under "Verification" in `notes.md`.
- [ ] T029 Update `dev/docs/backlog.yaml` S-020: set `status` to `in_design` while unbuilt, `done` once T027 and T028 pass, and add `specs/020-save-confirmed-draft` to its `source`.
- [X] T030 [P] Update `specs/016-capture-recipe-text/spec.md` FR-019 note only if wording now conflicts with the shipped Save (Discard-only text); do not change other specs.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories → Polish.
- Phase 2: T002 → T003 → T004; T005 and T006 → T007; T008 → T009 (needs T002, T006).
- US1 needs Phase 2. US2 needs US1's use case (T012) for T021. US3 needs US1's route (T013) for T025. UI tasks T014 to T018 need only the contract and can start after T013's schema is fixed.
- Within a story: tests first, then use case, route, ui.

## Parallel Opportunities

- Phase 2: T004, T007 in parallel with each other once T003 and T006 are done.
- US1: T010 and T011 (tests); T014 and T015 (BFF and client) in parallel with api work.
- US2: T019 and T020. US3: T022, T023, T024.

## Implementation Strategy

- **MVP**: Phases 1, 2 and 3 (US1). That already stores recipes and returns the member to the notebook; catalog growth (US2) follows immediately because Save is not useful for matching without it.
- Ship in order US1 → US2 → US3, running the Compose tests after each phase.
