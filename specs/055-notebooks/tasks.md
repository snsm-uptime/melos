# Tasks: Notebooks for Kitchens and Members

**Input**: `specs/055-notebooks/spec.md`. Prerequisite for `specs/016-capture-recipe-text`.

**Tests**: Domain tests are pure. Use-case tests use fake ports. Integration tests run in the Compose overlay with Postgres (constitution §6).

## Notes

- Authentication, signup and sign-in are not changed (AGENTS.md, FR-009).
- No task writes recipe, step, category, source or share rows (FR-008).
- Commit one task or one small group at a time. Do not push (AGENTS.md).

---

## Phase 1: Foundational

- [ ] T001 Add `api/domain/notebook.py`: frozen `Notebook(id, kitchen_id | None, user_id | None)`. Exactly one owner is set, otherwise a domain error. `kind` is `"kitchen"` or `"member"`. Add `NotebookNotFoundError` (404 `notebook_not_found`, one fixed message used for a missing notebook and for another member's notebook) to `api/domain/errors.py`, following the `MESSAGE` and `CODE` style of the existing errors. Pure tests in `api/tests/test_notebook_domain.py` (FR-003, FR-005)
- [ ] T002 [P] Add the ports to `api/application/ports.py`: `NotebookRepository` (`get`, `for_kitchen`, `for_member`, `create`) `IngredientCatalogReader` (`names_for_notebook`), and `UserDefaultNotebook` (`get(user_id)`, and `set_if_null(user_id, notebook_id)` which locks the user row and sets the value only when it is null) (FR-002, FR-004 to FR-006)
- [ ] T003 Add `NotebookModel` and `IngredientModel` to `api/adapters/persistence/models.py`. `notebook.kitchen_id` is unique and nullable. `notebook.name` is nullable text. `notebook.user_id` is nullable with an index and no unique constraint (FR-003). Add `UserModel.default_notebook_id`, a nullable uuid foreign key to `notebook.id` with `ON DELETE SET NULL`, added after both tables exist because the two reference each other (FR-002) `ingredient` has `unique(notebook_id, name)`
- [ ] T004 Create the Alembic revision `api/adapters/persistence/migrations/versions/0003_notebooks_ingredients.py`: create both tables, add `users.default_notebook_id`, backfill one notebook per existing kitchen and one per existing user that has an alias (named "{alias}'s Notebook"), set each such user's default, and write a working `downgrade` (FR-007)
- [ ] T005 [P] Add `api/adapters/persistence/notebooks.py` with `SqlAlchemyNotebookRepository`
- [ ] T006 [P] Add `api/adapters/persistence/ingredient_catalog.py` with `SqlAlchemyIngredientCatalogReader.names_for_notebook`: `SELECT name FROM ingredient WHERE notebook_id = :id ORDER BY name`
- [ ] T007 Add `api/tests/test_notebook_integration.py` (Compose Postgres): a second notebook for the same kitchen is rejected; a second notebook for the same user is allowed by the schema; a notebook with both owners or neither is rejected; the catalog reader returns only the given notebook's names; deleting a kitchen or user removes its notebook and ingredients (SC-003)

**Checkpoint**: Tables exist, the migration backfills, and the repositories pass their integration tests.

---

## Phase 2: User Story 1 - Every kitchen has its notebook (P1)

- [ ] T008 Make `CreateOwnedKitchenService` in `api/application/kitchens.py` create the kitchen's notebook in the same transaction as the kitchen and its owner membership. Update `api/api/routes/kitchens.py` and every test that builds the service (FR-001)
- [ ] T009 Extend `api/tests/test_kitchens_integration.py`: a created kitchen has exactly one notebook, owned by that kitchen (SC-001)
- [ ] T010 Add `GET /notebooks/kitchens/{kitchen_id}` in `api/api/routes/notebooks.py` after `read_kitchen` authorization. A missing kitchen and a non-member give 404 `kitchen_not_found` (FR-004)

## Phase 3: User Story 2 - Every member has a notebook on first use (P1)

- [ ] T011 Add `GetDefaultNotebook` in `api/application/notebooks.py`: read the member's `default_notebook_id`; when null, lock the user row, re-check, create a notebook named "{alias}'s Notebook", set it as the default, and return it, through `NotebookRepository` and `UserDefaultNotebook`. Unit tests against fake ports: the first call creates the notebook and sets the default, the second call returns the same id, a second first-call that finds the default already set creates nothing, and after the default is cleared the next call creates a new one (FR-002, FR-010, SC-002, SC-005)
- [ ] T012 Add the member routes in `api/api/routes/notebooks.py`: `GET /notebooks/members/{user_id}` (the default notebook, created when null) and `GET /notebooks/members/{user_id}/{notebook_id}`. Only the owner gets a notebook; any other caller and a missing notebook get 404 `notebook_not_found` (FR-002, FR-005)
- [ ] T013 Write the integration tests for the member routes in `api/tests/test_notebook_integration.py`: the owner reads the default (created on the first call, the same id on the second, two simultaneous first calls make one notebook) and reads by id; another member gets 404; a missing notebook gets 404 ; deleting the default notebook row clears `default_notebook_id` and the next call creates a new notebook with the same response shape; the first call and later calls answer 200 with the same fields (SC-002, SC-004, SC-005)
- [ ] T014 Include the notebooks router in `api/api/app.py` with `dependencies=[Depends(require_user_alias)]`, as the kitchens router does

## Phase 4: User Story 3 - Existing data has notebooks (P1)

- [ ] T015 Run the migration on a Compose database with existing kitchens and users: check the counts, run `downgrade`, then `upgrade` again. Record the result in `dev/memory/` (SC-003)

## Phase 5: UI read routes

- [ ] T016 [P] Add the same-origin BFF routes `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts`, `ui/app/api/notebooks/members/[userId]/route.ts` and `ui/app/api/notebooks/members/[userId]/[notebookId]/route.ts` (GET), forwarding the `cookie` header as the existing routes do. Route tests in the style of `ui/app/api/kitchens-invites.bff.test.ts`

## Phase 6: Polish

- [ ] T017 [P] Run `cd api && uv run ruff check .` and fix every finding in the touched files
- [ ] T018 Run the api suite in Compose: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`
- [ ] T019 Update the S-055 entry in `dev/docs/backlog.yaml` and status once verified. Do not push or deploy without review (AGENTS.md)
