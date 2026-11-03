---

description: "Task list for creating, renaming and deleting notebooks"
---

# Tasks: Create, rename and delete notebooks

**Input**: Design documents from `specs/059-notebook-management/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/notebooks-api.md](contracts/notebooks-api.md), [contracts/notebooks-ui.md](contracts/notebooks-ui.md), [quickstart.md](quickstart.md)

**Tests**: Included, because constitution principle 6 requires them at the domain, application, integration and ui layers.

**Organization**: Tasks are grouped by user story so each can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Start from a known test baseline

- [X] T001 In a worktree, first run `worktree-bootstrap.sh` from the primary checkout (see `scripts/worktree/README.md`) so it has its own `.env`, project, ports and data directory, and create the test database as in `specs/059-notebook-management/quickstart.md`. Then record the baseline in `specs/059-notebook-management/notes.md`: api results from `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api` and ui results from `cd ui && npm test && npm run lint && npm run typecheck`, listing any test that already fails. Do not start a second Compose project with the main `.env`.

---

## Phase 2: Foundational

**Purpose**: The permission rule and the shared ui pieces that rename and delete both use

**⚠️ CRITICAL**: Finish this phase before User Stories 1 and 2. User Story 3 needs only T004, T007 and T045.

- [X] T002 [P] Write domain tests for `assert_can_manage` in `api/tests/test_notebook_manage_domain.py`, one per row of the permission table in `specs/059-notebook-management/data-model.md`: `owner` allowed; `member` raises `NotebookOwnerOnlyError`; `kitchen_member` in an active kitchen allowed; `kitchen_member` in an archived kitchen raises `KitchenArchivedError`
- [X] T003 Add `assert_can_manage(access, kitchen_is_archived)` to `api/domain/notebook.py` so T002 passes (research R5)
- [X] T004 Add a `NameNotebookRequest` body with `name: str` to `api/api/schemas/notebooks.py`, with the name's rules left to the domain as in `CreateNotebookRequest`. Reuse it for rename and the kitchen create.
- [X] T045 Make `lock_kitchen` in `api/adapters/persistence/notebooks.py` raise `KitchenNotFoundError` on a missing row in place of `.one()` (research R2), with a Postgres test in `api/tests/test_notebook_manage_integration.py`. Check that the routes of its existing callers map the error to 404.
- [X] T005 Add a private helper to `api/application/notebooks.py` that runs research R2, after T045: read facts with no lock and raise `NotebookNotFoundError` when missing or not visible; `lock_kitchen` for a kitchen notebook, turning `KitchenNotFoundError` into `NotebookNotFoundError`; `lock_notebook`; read facts again, raise `NotebookNotFoundError` if access is gone, then `assert_can_manage`. Return the facts. Add application tests for its order and refusals with fakes in `api/tests/test_notebook_manage_application.py`, extending `api/tests/notebook_sharing_fakes.py` as needed.
- [X] T006 [P] Add `canManageNotebook(notebook)`, using the condition in `specs/059-notebook-management/contracts/notebooks-ui.md`, and its tests to `ui/lib/notebooksClient.ts` and its test file
- [X] T007 Extract `ui/app/notebooks/NotebookNameDialog.tsx` from `ui/app/notebooks/NewNotebookCard.tsx`: props for title, confirm label, start value and an async submit that returns a result; `maxLength` 200; the failure handling in the Name dialog table of the UI contract, with its notebook gone, kitchen gone and archived texts in English and Spanish in `ui/lib/i18n/notebooks.ts`. Keep `NewNotebookCard` behaviour and its tests unchanged, and add `ui/app/notebooks/NotebookNameDialog.test.tsx` covering kept text on failure and each of those messages.
- [X] T008 Add `goneHref` to `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.tsx` (research R10): with a loaded notebook, `/kitchens/{id}/notebooks` when it has a `kitchen_id`, otherwise `/notebooks`; with no loaded notebook, `backHref`. Use it in both existing 404 redirects, and cover all three cases in `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.test.tsx`.

**Checkpoint**: the rule, the name dialog and the gone address exist. No new action is visible yet.

---

## Phase 3: User Story 1 - Rename a notebook (Priority: P1) 🎯 MVP

**Goal**: The owner of a personal notebook, or any member of a kitchen, renames a notebook.

**Independent Test**: Quickstart steps 1 to 4 and the rename part of step 10.

### Tests for User Story 1

- [X] T009 [P] [US1] Add application tests to `api/tests/test_notebook_manage_application.py`: rename trims and stores; unchanged name is a no-op that neither validates nor writes, including a stored name over 200 characters; empty, spaces-only and 201-character names raise `InvalidNotebookNameError`, and 200 characters pass; the refusals come before name validation
- [X] T010 [P] [US1] Add HTTP tests to `api/tests/test_notebook_manage_integration.py` for `PATCH /notebooks/{id}` against `specs/059-notebook-management/contracts/notebooks-api.md`, one per role and status: owner 200; notebook member 403 `notebook_owner_only`; kitchen member 200, snapshot included; archived kitchen 403 `kitchen_archived`; outsider 404 `notebook_not_found`; a bad name by an outsider 404. Assert recipes, default status and access are unchanged, and that the snapshot's label shows the new name while its own name does not change.

### Implementation for User Story 1

- [X] T011 [US1] Add `rename(notebook_id, name)` to `NotebookRepository` in `api/application/ports.py`, `api/adapters/persistence/notebooks.py` and the fakes in `api/tests/notebook_sharing_fakes.py`
- [X] T012 [US1] Add `RenameNotebookCommand` and `RenameNotebookService` to `api/application/notebooks.py`: use the T005 helper; if the trimmed name equals the stored one, return the view (research R6); otherwise `validate_notebook_name`, `rename`, read the view, commit. Do not log the name.
- [X] T013 [US1] Add `PATCH /{notebook_id}` to `api/api/routes/notebooks.py` with `require_user_alias`, mapping errors as the contract says. Reuse `_sharing_refused` for `NotebookOwnerOnlyError` and `NotebookNotFoundError`.
- [X] T014 [P] [US1] Add a `PATCH` handler to `ui/app/api/notebooks/[notebookId]/route.ts`, forwarding cookie, body, status and content type as `GET` does, returning 502 `bad_gateway` when upstream is unreachable
- [X] T015 [P] [US1] Add `renameNotebook(id, name)` to `ui/lib/notebooksClient.ts` in the style of `createNotebook`
- [X] T016 [P] [US1] Add the rename and options texts in English and Spanish to `ui/lib/i18n/notebooks.ts`; the message parity test must pass
- [X] T017 [US1] Create `ui/app/notebooks/[notebookId]/NotebookOptionsMenu.tsx` with a test: `IconButton` with `DotsIcon` inside `IconButtonPopup`, and a Rename item
- [X] T018 [US1] Wire rename into `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.tsx`: show the menu after Share when `canManageNotebook`; open `NotebookNameDialog` with the current name; on success update the notebook in state so the chrome title changes; on 404 show the gone message and go to `goneHref` on close. Test each state in `NotebookRecipesScreen.test.tsx`, including no menu for a notebook member and in an archived kitchen.

**Checkpoint**: rename works on its own for every role.

---

## Phase 4: User Story 2 - Delete a notebook (Priority: P2)

**Goal**: The owner of a personal notebook, or any member of a kitchen, deletes a notebook after confirming what will be lost.

**Independent Test**: Quickstart steps 6 to 9, 11 and 12, and the delete part of step 10.

### Tests for User Story 2

- [X] T019 [P] [US2] Add application tests to `api/tests/test_notebook_manage_application.py`: delete calls `delete` after the T005 checks, commits once, and calls neither on a refusal
- [X] T020 [US2] Add HTTP tests for `DELETE /notebooks/{id}` to `api/tests/test_notebook_manage_integration.py`, one per role and status from the contract, plus a second delete answering 404
- [X] T021 [US2] Add outcome tests to `api/tests/test_notebook_manage_integration.py` for each row of "What a deletion does" in `specs/059-notebook-management/data-model.md`: recipes with lines and steps, catalog, memberships, invites, cart entries with other entries kept, edit locks with a lock held by someone else, sources only when no other recipe uses them, snapshot kept with its label cleared, the original untouched when a snapshot is deleted, adding it again with no repeat warning, default recreated empty, last kitchen notebook recreated on open, shopping list lines kept with their titles, a later refresh of the active list leaving out the deleted recipes and keeping hand-added items, a draft reporting `dropped_recipe_ids`, the person's units unchanged, and the next capture after deleting a person's capture notebook going to their next oldest own notebook, or to a new one if they have none, with a snapshot never chosen
- [X] T022 [US2] Add concurrent tests with two real sessions on Postgres to `api/tests/test_notebook_manage_integration.py`: two deletes, rename against delete, snapshot against delete of its original, invite accept against delete, capture save against delete, kitchen delete against rename, and archive against rename and delete. No request answers 500, and nothing is left half done. Add a test that a recipe saved during a delete leaves no orphaned source row.
- [X] T023 [US2] Add an all-or-nothing test to `api/tests/test_notebook_manage_integration.py`: force a failure in the delete and check the notebook is complete afterwards

### Implementation for User Story 2

- [X] T024 [US2] Rename `delete_personal` to `delete` across `api/application/ports.py`, `api/adapters/persistence/notebooks.py`, `api/application/notebook_ownership.py`, `api/tests/notebook_sharing_fakes.py` and `api/tests/test_notebook_ownership_application.py`, and make the adapter take `FOR UPDATE` on the notebook row before reading source ids (research R1)
- [X] T025 [US2] Add `DeleteNotebookCommand` and `DeleteNotebookService` to `api/application/notebooks.py`: use the T005 helper, `delete`, commit, and log the outcome with the notebook id only
- [X] T026 [US2] Add `DELETE /{notebook_id}` to `api/api/routes/notebooks.py`, 204 on success, with the same error mapping as T013
- [X] T027 [US2] In `AddNotebookSnapshotService` in `api/application/notebooks.py`, after the first ownership check, `lock_notebook` the source, turn a miss into `NotebookNotFoundError`, and read the source facts again (research R3). Update the snapshot fakes and tests that check call order in `api/tests/test_notebook_snapshots_application.py`.
- [X] T046 [US2] In `add` in `api/adapters/persistence/recipes.py`, raise `NotebookNotFoundError` when the `IntegrityError` is the foreign key on `recipe.notebook_id`, next to the save key check (research R4). Read the constraint's real name from the database, since the migration does not name it. The save route's existing mapping then answers 404, and T022's capture race passes.
- [X] T028 [P] [US2] Add a `DELETE` handler to `ui/app/api/notebooks/[notebookId]/route.ts`, passing a 204 through with no body
- [X] T029 [P] [US2] Add `deleteNotebook(id)` to `ui/lib/notebooksClient.ts`, treating 204 as success in the style of `leaveNotebook`
- [X] T030 [P] [US2] Add the delete dialog texts in English and Spanish to `ui/lib/i18n/notebooks.ts`, with singular, plural and zero recipe forms and singular and plural people forms
- [X] T031 [US2] Create `ui/app/notebooks/[notebookId]/NotebookDeleteDialog.tsx` per the Delete dialog section of the UI contract, and `NotebookDeleteDialog.test.tsx` covering each table row: on open read `fetchNotebook` and, for a personal notebook, `fetchNotebookMembers`; confirm disabled until both answer; count members without the owner; no people line at zero; the default notebook sentence; a read that answers 404 gives the gone message and closing goes to `goneHref`; any other failed read gives no confirm
- [X] T032 [US2] Add a Delete item in danger style to `ui/app/notebooks/[notebookId]/NotebookOptionsMenu.tsx`, and open the dialog from `NotebookRecipesScreen.tsx`. On success call `requestSidePanelRefresh()` and go to `goneHref`. Test it in `NotebookRecipesScreen.test.tsx`.

**Checkpoint**: delete and rename both work, and every race ends in a plain message.

---

## Phase 5: User Story 3 - Add an empty kitchen notebook (Priority: P3)

**Goal**: Any member of an active kitchen adds a named, empty notebook.

**Independent Test**: Quickstart step 5 and the add part of step 10.

### Tests for User Story 3

- [X] T033 [P] [US3] Add application tests to `api/tests/test_notebook_manage_application.py` in the order of research R11: non-member raises `KitchenNotFoundError` even with a bad name; the archived check runs on a read made after the kitchen lock, so a kitchen archived while waiting raises `KitchenArchivedError`; bad name raises `InvalidNotebookNameError` and creates nothing; success records the caller as owner, seeds the catalog and commits
- [X] T034 [P] [US3] Add HTTP tests for `POST /notebooks/kitchens/{id}` to `api/tests/test_notebook_manage_integration.py` per the contract, and a test that the new notebook becomes the caller's own capture notebook when they have none, while an older own notebook stays first, and a concurrent test with two real sessions that an archive and an add never leave a new notebook in an archived kitchen

### Implementation for User Story 3

- [X] T035 [US3] Give `_create_kitchen_notebook` a `name` parameter in `api/application/notebooks.py`, with its two callers passing `kitchen_notebook_name(...)`
- [X] T036 [US3] Add `CreateKitchenNotebookCommand` and `CreateKitchenNotebookService` to `api/application/notebooks.py` per research R11
- [X] T037 [US3] Add `POST /kitchens/{kitchen_id}` to `api/api/routes/notebooks.py` before `/{notebook_id}`, 201 on success, with `require_user_alias`
- [X] T038 [P] [US3] Add a `POST` handler to `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts`
- [X] T039 [P] [US3] Add `createKitchenNotebook(kitchenId, name)` to `ui/lib/notebooksClient.ts`
- [X] T040 [US3] Give `ui/app/notebooks/NewNotebookCard.tsx` an optional `kitchenId`: it calls `createKitchenNotebook` and opens the notebook with `?from=` set to the kitchen's notebooks. `kitchen_not_found` shows the kitchen gone message, and closing it goes to `/kitchens`. Test it in `ui/app/notebooks/NewNotebookCard.test.tsx`.
- [X] T041 [US3] Show the tile in `ui/app/kitchens/KitchenNotebooksScreen.tsx` next to `AddNotebookSnapshot`, under `canAdd`, and test it in `ui/app/kitchens/KitchenNotebooksScreen.test.tsx`

**Checkpoint**: all three stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T042 [P] Run the full checks from `specs/059-notebook-management/quickstart.md` and compare with the T001 baseline: api in the Compose test overlay, `uv run ruff check .`, and ui test, lint and typecheck
- [X] T043 Walk `specs/059-notebook-management/quickstart.md` in a browser on an isolated stack, at 360px and 1280px, in both languages and once by keyboard, covering FR-020. Time a rename and an add against SC-001 and SC-002. Record results and anything not done in `specs/059-notebook-management/notes.md`.
- [X] T044 [P] Update `AGENTS.md` only if the notebook rules there no longer match. Update S-059 in `dev/docs/backlog.yaml` with status and verification, and remove "No route deletes a personal notebook until S-059" from `specs/035-notebook-snapshot/quickstart.md`.

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: first.
- **Foundational (Phase 2)**: after Setup. Blocks User Stories 1 and 2.
- **User Story 1**: after Foundational. No dependency on other stories.
- **User Story 2**: after Foundational. T032 extends the menu from T017, so build US1 first, or create the menu in whichever comes first.
- **User Story 3**: needs T004, T007 and T045 only. It can run alongside User Stories 1 and 2.
- **Polish**: after the stories that are in scope.

### Within each story

Tests first and failing, then repository, service, route, BFF, client, screen.

T045 and T046 keep their IDs from a later review: T045 runs just before T005, and T046 after T027.

`ui/lib/notebooksClient.ts`, `ui/lib/i18n/notebooks.ts`, `api/application/notebooks.py` and `api/api/routes/notebooks.py` are each touched by several stories, so [P] holds only within one story.

## Parallel Example: User Story 2

```text
T019 application tests | T020 integration tests (T021 to T023 follow T020, same file)
T028 BFF handler | T029 client | T030 texts
```

## Implementation Strategy

- **MVP**: Phases 1 to 3. Rename alone is useful and ships with no data risk.
- **Next**: Phase 4, the only phase that destroys data. Do not skip T021 to T023.
- **Last**: Phase 5, then Polish.
