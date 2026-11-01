---

description: "Task list for notebook snapshots"
---

# Tasks: Add a personal notebook to a kitchen as a snapshot

**Input**: Design documents from `specs/035-notebook-snapshot/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/snapshots-api.md](contracts/snapshots-api.md), [quickstart.md](quickstart.md)

**Tests**: Included, because constitution principle 6 requires them at the domain, application, integration and ui layers.

**Organization**: Tasks are grouped by user story so each can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Start from the right branch and a known test baseline

- [X] T001 Create branch `035-notebook-snapshot` from the current `main`, keeping `specs/035-notebook-snapshot/` and `.specify/feature.json`
- [X] T002 Record the baseline in `specs/035-notebook-snapshot/notes.md`: api failures from `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, and the ui result of `npm test`, so failures that predate this story are known

---

## Phase 2: Foundational

**Purpose**: The column and the read model every story needs

**CRITICAL**: No user story work starts until this phase is complete

- [X] T003 Add `snapshot_key` (uuid, nullable) to `NotebookModel`, with check `ck_notebook_snapshot_is_kitchen` ("snapshot_key IS NULL OR kitchen_id IS NOT NULL") and partial unique index `uq_notebook_kitchen_snapshot_key` on `(kitchen_id, snapshot_key)` where `snapshot_key IS NOT NULL`, in `api/adapters/persistence/models.py`
- [X] T004 Create migration `0011_notebook_snapshot_key` (add on upgrade, drop on downgrade; existing rows stay null) in `api/adapters/persistence/migrations/versions/0011_notebook_snapshot_key.py`
- [X] T005 Add `snapshot_key` to the `Notebook` dataclass, refusing a key on a notebook with no `kitchen_id`, in `api/domain/notebook.py`, with a test in `api/tests/test_notebook_domain.py`
- [X] T006 Add `SnapshotExistsError` with `CODE = "snapshot_exists"` in `api/domain/errors.py`
- [X] T007 Add `origin_notebook_name`, `is_snapshot` and `is_own_capture_notebook` to `NotebookFacts` and to `NotebookView` in `api/application/ports.py` and `api/application/notebooks.py`
- [X] T008 Fill those facts in `_facts_query` with a join on `source_notebook_id` and map `snapshot_key` in `_notebook` and `create`, in `api/adapters/persistence/notebooks.py`; `is_own_capture_notebook` is true only on the notebook `user_kitchen_notebook` returns
- [X] T009 Add the three fields to `NotebookResponse` in `api/api/schemas/notebooks.py` and to the `NotebookResponse` type in `ui/lib/notebooksClient.ts`
- [X] T010 Test upgrade, downgrade and upgrade on a scratch database with invented rows, and record the result in `specs/035-notebook-snapshot/notes.md`

**Checkpoint**: The stack runs and existing tests pass with the new fields null or false

---

## Phase 3: User Story 1 - Bring my notebook into a kitchen (Priority: P1) 🎯 MVP

**Goal**: A kitchen member adds a personal notebook they own, and every member of the kitchen can use the copies. Captures keep going where they did.

**Independent Test**: With two accounts in one kitchen, add a notebook with several recipes, then as the other member open the recipes and add one to the cart (quickstart steps 1, 2, 5 to 8, 10 to 12).

### Tests for User Story 1

- [X] T011 [P] [US1] Write application tests with fake ports for each row of the check table in `contracts/snapshots-api.md`, in order, in `api/tests/test_notebook_snapshots_application.py`
- [X] T012 [P] [US1] Write integration tests in `api/tests/test_notebook_snapshots_integration.py`: field-by-field copy (SC-003), unused catalog names, deleted author stays null, `cart_add_count` 0, `save_key` null, no cart entry, a separate `source` row per recipe, order kept, empty notebook, a member-only notebook refused, non-member 404, archived 403, forced failure leaves nothing (SC-005), same key in sequence and concurrently makes one snapshot, an edit lock left alone
- [X] T013 [P] [US1] Write capture tests in `api/tests/test_notebook_snapshots_integration.py`: an adder with only a snapshot gets a new own notebook, the default stays their own, and this still holds after `source_notebook_id` is cleared (FR-017)
- [X] T014 [P] [US1] Write a timing test for a 100-recipe notebook under 5 seconds (SC-002) in `api/tests/test_notebook_snapshots_integration.py`
- [X] T015 [P] [US1] Write ui tests in `ui/app/kitchens/AddNotebookSnapshot.test.tsx`: only owned personal notebooks offered, an immediate add with no confirmation, `snapshot_exists` shows the warning, cancel sends nothing, confirm resends the same key, pressing twice sends once, failure message and retry, no control in an archived kitchen, choosing a different notebook after a failure sends a new key
- [X] T015a [P] [US1] Write ui tests in `ui/app/kitchens/KitchenNotebooksScreen.test.tsx` and `ui/app/kitchens/KitchenDetailChrome.test.tsx`: the icon sits next to share and opens the view, every notebook is a card linking to its page, an empty notebook is included, cards show in an archived kitchen with no add action, and a new snapshot appears without a page reload (FR-007, FR-007a). The "shows no notebook cards" test in `KitchenNotebooksSection.test.tsx` stays unchanged
- [X] T016 [P] [US1] Write capture default tests in `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.test.tsx` and `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx`, including a kitchen with one other notebook, where the picker shows "My own notebook (new)" and the sentinel id `own-new` never reaches `submitCapture`
- [X] T017 [P] [US1] Add BFF tests for both new routes in `ui/app/api/notebooks.bff.test.ts`

### Implementation for User Story 1

- [X] T018 [US1] Add `find_snapshot(kitchen_id, snapshot_key)` and `has_snapshot_of(kitchen_id, source_notebook_id)` to `NotebookRepository`, `copy_names(source_id, target_id)` to `IngredientCatalog`, and `copy_all(source_id, target_id) -> int` to `RecipeRepository`, in `api/application/ports.py`
- [X] T019 [US1] Implement `find_snapshot` and `has_snapshot_of`, and add `NotebookModel.snapshot_key.is_(None)` to `user_kitchen_notebook` (research R2), in `api/adapters/persistence/notebooks.py`
- [X] T020 [P] [US1] Implement `copy_names` as one `INSERT … SELECT` in `api/adapters/persistence/ingredient_catalog.py`
- [X] T021 [US1] Implement `copy_all` in `api/adapters/persistence/recipes.py` per research R4 and R5 and the table in `data-model.md`: lock source recipes `FOR SHARE`, read recipes, sources, lines and steps, bulk insert with new ids, a new `source` row per recipe, keep `created_at`, null `save_key`, zero `cart_add_count`
- [X] T022 [US1] Add `AddNotebookSnapshotCommand` and `AddNotebookSnapshotService` in `api/application/notebooks.py`, running the checks in contract order under `lock_kitchen`, keeping the original's name, owner the caller, and logging counts only
- [X] T023 [US1] Add `POST /notebooks/kitchens/{kitchen_id}/snapshots` (201 new, 200 replay, 403, 404, 409) and its request schema in `api/api/routes/notebooks.py` and `api/api/schemas/notebooks.py`
- [X] T024 [US1] Add `POST /notebooks/kitchens/{kitchen_id}/capture-notebook`, which runs `ResolveCaptureNotebookService`, in `api/api/routes/notebooks.py`, and update the service's "no route" docstring in `api/application/notebooks.py`
- [X] T024a [US1] Update `test_notebook_routes_are_gets_on_the_four_contract_paths` in `api/tests/test_notebook_integration.py` to allow the two new POST routes and keep every other path GET-only
- [X] T025 [P] [US1] Add BFF routes in `ui/app/api/notebooks/kitchens/[kitchenId]/snapshots/route.ts` and `ui/app/api/notebooks/kitchens/[kitchenId]/capture-notebook/route.ts`, returning 502 `bad_gateway` when the api can't be reached
- [X] T026 [US1] Add `addNotebookSnapshot` and `resolveCaptureNotebook` in `ui/lib/notebooksClient.ts`
- [X] T027 [P] [US1] Add English and Spanish text in `ui/lib/i18n/notebooks.ts`: the action, the choice, the line saying kitchen members will see a copy, the repeat warning, success, each failure, and "My own notebook (new)"
- [X] T028 [US1] Build `ui/app/kitchens/AddNotebookSnapshot.tsx` on `ActionDialog`: load `GET /notebooks/default`, then `GET /notebooks`, offer rows with `kind = personal` and `access = owner`, make one key for each notebook chosen in an opening (research R3), show the line about who will see the copy (FR-002a leaves no confirmation), and announce the result to screen readers
- [X] T029 [US1] Build `ui/app/kitchens/KitchenNotebooksScreen.tsx`: load `fetchKitchenNotebooks`, render `styles.grid` from `notebooks.module.scss` with `NotebookCard`, `href` and no `access` chip (research R11), put the action from T028 in the first cell, hidden when `isArchived`, reload the cards without a page reload, and call `requestSidePanelRefresh`
- [X] T029a [US1] Add the route `ui/app/kitchens/[kitchenId]/notebooks/page.tsx` in the same shape as `cart/page.tsx`, add a `notebooks` prop with `NotebookIcon` next to the share icon in `ui/app/kitchens/KitchenDetailChrome.tsx`, pass it from `ui/app/kitchens/[kitchenId]/page.tsx`, and add its English and Spanish label in `ui/lib/i18n/notebooks.ts`
- [X] T030 [US1] Preselect the notebook with `is_own_capture_notebook`, or offer "My own notebook (new)" as a ui-only candidate with the sentinel id `own-new` when there is none (research R6), so the picker shows even with one other notebook, in `ui/app/kitchens/KitchenNotebooksSection.tsx` and `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx`
- [X] T031 [US1] When `own-new` is chosen, call `resolveCaptureNotebook` before `submitCapture` and capture into the returned notebook, in `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx`

**Checkpoint**: User Story 1 works alone and is the MVP

---

## Phase 4: User Story 2 - The two notebooks stay independent (Priority: P1)

**Goal**: No change on one side reaches the other, and neither side gains access to the other.

**Independent Test**: Edit, add and delete on both sides, then compare the two notebooks (quickstart step 3).

**Depends on**: User Story 1

- [X] T032 [P] [US2] Write integration tests in `api/tests/test_notebook_snapshots_integration.py`: recipe edit and delete each way, including the source link staying after a delete on the other side; new recipes and catalog names each way; adder leaves the kitchen, by removing the membership row because no route exists; kitchen deleted with the original untouched; a kitchen member gets 404 on the original; the original's answer shows nothing about a snapshot (FR-015, FR-016, FR-018, SC-004)
- [X] T033 [P] [US2] Write tests that the side panel count doesn't rise after a snapshot, and doesn't count a recipe later captured into a snapshot, in `api/tests/test_side_panel_integration.py` (FR-025)
- [X] T034 [US2] Leave recipes in snapshot notebooks out of `count_recipes_added` with `NotebookModel.snapshot_key.is_(None)` in `api/adapters/persistence/side_panel.py` (FR-025)
- [X] T035 [US2] Fix whatever T032 finds, in the file at fault, and record it in `specs/035-notebook-snapshot/notes.md`

**Checkpoint**: Stories 1 and 2 both hold

---

## Phase 5: User Story 3 - See where a snapshot came from (Priority: P2)

**Goal**: Kitchen members see the plain-text origin label, which goes away when the original is deleted.

**Independent Test**: Open a snapshot as a member with no access to the original, then delete the original in a test (quickstart step 4 and the automated-only cases).

**Depends on**: User Story 1

- [X] T036 [P] [US3] Write integration tests in `api/tests/test_notebook_snapshots_integration.py`: the label reads the original's current name after a rename, the origin id is never returned, deleting the original clears the label and the repeat warning and keeps recipes and catalog, and a plain kitchen notebook has no label
- [X] T037 [P] [US3] Write ui tests in `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.test.tsx`: the label appears as text with no link, and doesn't appear without `origin_notebook_name`
- [X] T038 [P] [US3] Add the English and Spanish label text in `ui/lib/i18n/notebooks.ts`
- [X] T039 [US3] Show `origin_notebook_name` under the title in `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.tsx`

**Checkpoint**: All stories work

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T040 [P] Add `notebook.snapshot_key` to PRD §1.6, and the capture-notebook route to the routes it lists, in `dev/docs/prd.md`
- [X] T041 [P] Replace the Picker assumption with research R10 in `specs/035-notebook-snapshot/spec.md`
- [X] T042 [P] Mark FR-009, FR-013 and SC-011 as amended by spec 035 research R6 in `specs/056-notebooks/spec.md`
- [X] T043 Run the full checks from `quickstart.md`, plus `uv run ruff check .` in `api/`, and compare with the baseline in `specs/035-notebook-snapshot/notes.md`
- [ ] T044 Walk `quickstart.md` in a browser with two accounts, at 360px and 1280px, in both languages, and once by keyboard only, and record the result in `specs/035-notebook-snapshot/notes.md`
- [X] T045 Update S-035's status and verification in `dev/docs/backlog.yaml`, and add a note on S-019 and S-048 that copied recipes need embeddings and that `copy_all` is the step to reuse
- [ ] T046 After the owner deploys, add a notebook of 100 invented recipes on the deployed server, and record the time against SC-002 in `dev/docs/backlog.yaml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Nothing before it
- **Foundational (Phase 2)**: After Setup. Blocks all stories.
- **User Story 1 (Phase 3)**: After Foundational
- **User Stories 2 and 3 (Phases 4 and 5)**: After User Story 1, since both need a snapshot to exist. They don't depend on each other.
- **Polish (Phase 6)**: After the stories you ship

### Within User Story 1

- Tests T011 to T017, including T015a, first, and they should fail
- Ports T018, then adapters T019 to T021, then service T022, then routes T023 and T024, then route guard T024a
- BFF T025, client T026 and text T027, then ui T028 to T031, including T029a

### Parallel Opportunities

```text
Foundational: T005 and T006 touch different files; T003 and T004 go first.

User Story 1 tests: T011, T015, T016, T017 together, then T012 to T014, which share a file.
User Story 1 build: T020 with T019 or T021; T025 and T027 together.

After User Story 1: Phases 4 and 5 can run side by side, apart from the shared test file.
Polish: T040, T041, T042 together.
```

## Implementation Strategy

### MVP first

1. Phases 1 and 2
2. Phase 3
3. Stop and walk quickstart steps 1, 2 and 5 to 8

User Story 1 is enough to ship for AC1a.4's copy. Independence comes from the design, and Phase 4 proves it, so don't call AC1a.4 met until Phase 4 passes.

### If time runs out

Phase 5 is the only part that can wait: the snapshot works without its label, though AC1a.4 asks for it. T030 and T031 fix a capture bug that exists today, and FR-017 depends on them, so they don't move out of the MVP.
