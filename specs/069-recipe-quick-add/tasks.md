---
description: "Tasks for 069 recipe quick add"
---

# Tasks: Recipe quick add, and a recipe from another notebook

**Input**: `specs/069-recipe-quick-add/` (plan.md, spec.md, research.md, data-model.md, contracts/recipe-copy-api.md, quickstart.md)

**Tests**: Included. The plan (constitution principle 6) requires domain, application (fake ports), Compose integration and ui tests, plus a browser walk. api tests live flat in `api/tests/` (`test_<area>_<layer>.py`).

**Format**: `- [ ] T### [P?] [US?] Description with file path`

---

## Phase 1: Setup

- [X] T001 Read `api/adapters/persistence/recipes.py` (`copy_all`, line ~185), `api/application/notebooks.py` (`ensure_member_kitchen_notebook` ~164, `AddNotebookSnapshotService` ~658) and `api/application/recipe_locks.py` to confirm the helpers to reuse; no code change

---

## Phase 2: Foundational (blocks both stories)

- [X] T002 Add `copied_from_recipe_id = mapped_column(UUID, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True, index=True)` to `RecipeModel` in `api/adapters/persistence/models.py`; never add it to any response schema
- [X] T003 Create reversible Alembic migration `api/adapters/persistence/migrations/versions/0016_recipe_copied_from.py` (down_revision = 0015's id): add `recipes.copied_from_recipe_id UUID NULL REFERENCES recipes(id) ON DELETE SET NULL` and index `ix_recipes_copied_from_recipe_id`; downgrade drops index then column
- [X] T004 [P] Add migration test `api/tests/test_recipe_copied_from_migration.py` (pattern of `test_recipe_preview_migration.py`): upgrade adds nullable column + index, deleting a source recipe sets the column to NULL, downgrade removes it
- [X] T005 [P] Add domain errors in `api/domain/errors.py`: `RecipeAlreadyInKitchenError(existing_recipe_id, notebook_name)` (code `recipe_already_in_kitchen`) next to `SnapshotExistsError`; reuse existing recipe-locked / kitchen-archived / not-found errors if present, otherwise add `recipe_locked` and `kitchen_archived` equivalents

**Checkpoint**: migration applies; `uv run pytest tests -k migration` passes.

---

## Phase 3: User Story 1 – Add a recipe to the open kitchen from a personal notebook (P1) 🎯 MVP

**Goal**: From a kitchen's add dialog, "Recipe from another notebook" copies a chosen personal recipe into the member's own kitchen notebook, with repeat handling.

**Independent Test**: In active kitchen K, member A picks "Lentil soup" from a personal notebook → copy appears in A's kitchen notebook of K; original unchanged; second add → already-added dialog (quickstart steps 3, 4, 6, 7).

### Tests (write first, expect fail)

- [X] T006 [P] [US1] Application tests with fake ports in `api/tests/test_recipe_copy_application.py`: new copy (author = caller, created_at = now, target = caller's own kitchen notebook, notebook created via `ensure_member_kitchen_notebook` when missing); non-member → `kitchen_not_found`; archived kitchen → `kitchen_archived`; source missing/unreadable/not in a personal notebook → `recipe_not_found`; `on_repeat="ask"` with existing copy → `RecipeAlreadyInKitchenError` carrying latest copy id and notebook name; `"add"` → second copy; `"overwrite"` → latest copy (by `created_at`) replaced in place, same id and notebook, author = caller, source untouched; edit lock held → `recipe_locked`; missing ingredient names passed to `IngredientCatalog.add_names`; embedding enqueued for new/overwritten id
- [X] T007 [P] [US1] Compose integration tests in `api/tests/test_recipe_copy_integration.py` against `POST /notebooks/kitchens/{kitchen_id}/recipe-copies`: 201 body `{recipe_id, notebook_id, notebook_name, overwritten: false}`; full content copied (title, base_servings, servings_estimated, preview image, new source row with type/url/raw_text, lines with amounts/units, steps); copy and original independent on edit and delete (SC-003); 409 `recipe_already_in_kitchen` body includes `existing_recipe_id`, `notebook_name`; 200 `overwritten: true`; B posting A's recipe id → 404 (SC-004); archived → 409 `kitchen_archived`; 422 on bad `on_repeat`; deleting source then re-adding → 201 with no warning; `copied_from_recipe_id` absent from recipe read responses
- [X] T008 [P] [US1] Refactor-safety: run `api/tests/test_notebook_snapshots_integration.py` after T010 and keep it green

### api implementation

- [X] T009 [US1] Extend ports in `api/application/ports.py`: `RecipeRepository.copy_one(recipe_id, target_notebook_id, author_id, copied_from) -> UUID`, `RecipeRepository.overwrite_from(target_recipe_id, source_recipe_id, author_id) -> None`, `RecipeRepository.latest_copy_in_kitchen(source_recipe_id, kitchen_id) -> (recipe_id, notebook_name) | None`; `IngredientCatalog.add_names(notebook_id, names) -> None`
- [X] T010 [US1] Implement in `api/adapters/persistence/recipes.py`: extract row-copy helpers (source row, recipe, lines, steps, preview image) from `copy_all` and use them in `copy_all`, `copy_one` (source locked `FOR SHARE`, author = caller, created_at = now, sets `copied_from_recipe_id`) and `overwrite_from` (replaces title, servings, image, source, lines, steps; keeps id, notebook_id, `copied_from_recipe_id`; sets author); `latest_copy_in_kitchen` = recipes with `copied_from_recipe_id = source` whose notebook's `kitchen_id = kitchen`, newest `created_at`
- [X] T011 [P] [US1] Implement `add_names` in `api/adapters/persistence/ingredient_catalog.py`: insert only names missing in the notebook's catalog, as-is (no normalization, FR-010)
- [X] T012 [P] [US1] Add the new port methods to the fakes used by application tests (`api/tests/notebook_sharing_fakes.py` or the recipe fakes T006 imports)
- [X] T013 [US1] Create `api/application/recipe_copy.py` with `CopyRecipeToKitchenCommand(actor_id, kitchen_id, source_recipe_id, on_repeat: Literal["ask","add","overwrite"])`, result `CopiedRecipe(recipe_id, notebook_id, notebook_name, overwritten)` and `CopyRecipeToKitchenService`: check active membership (404) and not archived; check source readable and in a personal notebook the actor owns or is a member of (404); take the kitchen lock; `ensure_member_kitchen_notebook`; repeat check per `on_repeat`; overwrite takes the recipe edit-lock row lock and fails `recipe_locked` if held; `add_names`; commit; `embedding_jobs.enqueue([id])` + `wake_embedding_worker` after commit
- [X] T014 [P] [US1] Add `CopyRecipeRequest(source_recipe_id: UUID, on_repeat: Literal["ask","add","overwrite"] = "ask")` and `CopiedRecipeResponse` in `api/api/schemas/notebooks.py`
- [X] T015 [US1] Add route `POST /notebooks/kitchens/{kitchen_id}/recipe-copies` in `api/api/routes/notebooks.py`: 201 new / 200 overwrite; map errors to 409 `recipe_already_in_kitchen` (with `existing_recipe_id`, `notebook_name`), 409 `recipe_locked`, 409 `kitchen_archived`, 404 `kitchen_not_found`, 404 `recipe_not_found`; wire the service in the dependency setup used by the snapshot route

### ui implementation

- [X] T016 [P] [US1] Add en/es strings in `ui/lib/i18n/capture.ts` (or the capture messages source used by `useCaptureMessages.ts`): `optionFromNotebook` "Recipe from another notebook" / "Receta de otro cuaderno", picker titles, search placeholder, no-personal-recipes empty state, confirm, success toast, repeat dialog title/body, "Add another copy", "Overwrite", "Cancel", source-deleted error, locked error; keep `parity.test.ts` green
- [X] T017 [US1] Extend `ui/components/AddRecipeCallToAction/AddRecipeOptionsDialog.tsx` with optional `onChooseFromNotebook` and `fromNotebookDisabledReason`; render the 4th option after URL, Picture, Text only when `onChooseFromNotebook` is given; disabled with reason text when `fromNotebookDisabledReason` is set
- [X] T018 [US1] Create `ui/components/AddRecipeCallToAction/RecipeFromNotebookSheet.tsx` (props: `kitchenId?`, `kitchens?`, `onDone`, `onClose`): notebook list from `GET /api/notebooks` filtered `kind === "personal"`; recipes from `GET /api/notebooks/{id}/recipes?q=` with search and paging; empty state without confirm; confirm posts `{source_recipe_id, on_repeat: "ask"}` to `/api/notebooks/kitchens/{kitchenId}/recipe-copies`; on 409 `recipe_already_in_kitchen` show Add another copy / Overwrite / Cancel and re-post with `add`/`overwrite`; on 404 `recipe_not_found` show clear message; on success show confirmation and refresh the kitchen list; export from `ui/components/AddRecipeCallToAction/index.ts`
- [X] T019 [US1] Pass `onChooseFromNotebook` (opens the sheet with the open `kitchenId`) through `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx` and enable it from `ui/app/kitchens/KitchenNotebooksSection.tsx` only for active kitchens (absent when archived; absent on personal-notebook pages)
- [X] T020 [P] [US1] Tests `ui/components/AddRecipeCallToAction/RecipeFromNotebookSheet.test.tsx`: personal-only filter, search, empty state, success, 409 repeat dialog with all three choices posting the right `on_repeat`, 404 message, Spanish labels
- [X] T021 [P] [US1] Tests `ui/components/AddRecipeCallToAction/AddRecipeOptionsDialog.test.tsx`: option absent without prop, order URL/Picture/Text/from-notebook, disabled reason shown

**Checkpoint**: US1 works end to end from a kitchen page (quickstart 3, 4, 6, 7).

---

## Phase 4: User Story 2 – Quick add from the navigation (P1)

**Goal**: Header button on every signed-in page opens URL, Picture, Text and Recipe from another notebook with context-aware defaults.

**Independent Test**: From the shopping list page, quick add → Text → capture into default notebook; Back returns to the list; outside a kitchen with two kitchens a kitchen choice is shown (quickstart 5).

- [X] T022 [P] [US2] Add en/es quick add label "Add recipe" / "Añadir receta", kitchen-choice title, and no-active-kitchen disabled reason to `ui/lib/i18n/capture.ts`
- [X] T023 [US2] Create `ui/components/QuickAddRecipe/QuickAddRecipe.tsx` (+ `index.ts`): `IconButton` with `PlusIcon` and aria-label; derive kitchen context from pathname `/kitchens/[kitchenId]…`; candidates/default from `GET /api/notebooks/kitchens/{id}` + `captureNotebook.ts` inside a kitchen, else `GET /api/notebooks` with default personal notebook; reuse `AddRecipeOptionsDialog`, `UrlCaptureSheet`, `TextCaptureSheet` and capture state from `AddRecipeCallToAction`; return path = current pathname for Back/Discard; from-notebook: inside a kitchen use it, outside pass active (non-archived) kitchens from the membership store to `RecipeFromNotebookSheet` with single kitchen preselected, none → `fromNotebookDisabledReason`; inside an archived kitchen hide the option
- [X] T024 [US2] Mount `QuickAddRecipe` in the header trailing area of `ui/components/AppShell.tsx` for signed-in pages, mobile (360px) and desktop
- [X] T025 [P] [US2] Tests `ui/components/QuickAddRecipe/QuickAddRecipe.test.tsx`: four options; Text capture defaults to default personal notebook outside a kitchen and own kitchen notebook inside; kitchen chooser shown with 2 kitchens, preselected with 1, disabled reason with 0; option hidden in archived kitchen; Back returns to pathname; Spanish label
- [X] T026 [P] [US2] Update `ui/components/AppShell` tests (if present) for the new header button

**Checkpoint**: Both stories work independently.

---

## Phase 5: Polish & Cross-Cutting

- [X] T027 Run `cd api && uv run pytest tests -k "recipe_copy or snapshot or migration"` and the Compose integration overlay; fix failures
- [X] T028 [P] Run `cd ui && npm test && npm run lint && npm run typecheck`
- [ ] T029 Browser walk on the host (see browser-walk memory, isolated stack) at 360px and 1280px, light/dark, en/es covering quickstart steps 3–7; record results in `specs/069-recipe-quick-add/quickstart.md`
- [X] T030 [P] Mark S-069 status in `dev/docs/backlog.yaml` and verify no finance-derived names in new code

---

## Dependencies

- Phase 1 → Phase 2 → US1 (Phase 3) → US2 (Phase 4) → Polish.
- US2's from-notebook option depends on `RecipeFromNotebookSheet` (T018) and the endpoint (T015); its URL/Text quick add parts (T023 capture half, T024) only need Phase 2 and could start in parallel with US1.
- Within US1: T009 → T010/T011/T012 → T013 → T014/T015; ui T016 → T017 → T018 → T019.

## Parallel examples

- Phase 2: T004 ∥ T005 after T002/T003.
- US1: T006 ∥ T007 ∥ T016; then T011 ∥ T012 ∥ T014; T020 ∥ T021 after T018.
- US2: T022 ∥ T025 scaffold; T026 after T024.

## Implementation strategy

1. MVP = Phases 1–3 (kitchen dialog option + endpoint): delivers the new capability; validate with quickstart 3, 4, 6, 7.
2. Add Phase 4 (quick add header button) and validate quickstart 5.
3. Polish: full test runs, browser walk, backlog update.
