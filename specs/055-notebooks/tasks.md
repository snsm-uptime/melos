# Tasks: Notebooks That Belong to People and Are Linked to Kitchens

**Input**: Design documents from `specs/055-notebooks/` (spec.md re-specified 2026-10-23, plan.md, research.md R1–R11, data-model.md, contracts/notebooks-api.md, quickstart.md). Prerequisite for `specs/016-capture-recipe-text`.

**Prerequisites**: plan.md, spec.md (both required); research.md, data-model.md, contracts/ (used below)

**Tests**: Included. The constitution (§6) requires them: domain tests are pure, use-case tests use fake ports, integration tests run in the Compose overlay with Postgres. Within each story, write the tests first and check that they fail.

**Organization**: Tasks are grouped by user story. This list replaces the 2026-10-22 task list (T001–T025 for the kitchen-owned notebook, kept in git history at `064d344`). The branch already holds that code; the plan's "Reuse" section says what carries over, and the tasks below rework it in place.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1–US4, spec.md)
- Paths are relative to the repo root (`api/`, `ui/`, per plan.md)

## Notes

- Signup, sign-in, alias claim and sessions are not changed (FR-005, constitution §1). The only change to the user is `users.default_notebook_id`, which already exists on the branch.
- No task writes recipe, step, category, source, invite or cart rows, adds notebook members through the app, or links notebooks other than the default and first-capture notebooks (FR-018). Integration tests may insert membership rows directly to set up a scenario.
- A caller with no access gets the same 404 body as for something that does not exist, never 403 (SC-003).
- Commit one task or one small group at a time. Do not push (AGENTS.md).

---

## Phase 1: Setup

- [ ] T001 Bring the local dev and test databases off the old revision: a database that ran `0003_notebooks_ingredients` must go back to `0002_pgvector_kitchen_lang` before the new code runs. Either run `docker compose exec api uv run alembic downgrade 0002_pgvector_kitchen_lang` on a checkout of commit `7031e7a` (the last one with the old revision), or recreate the dev database (quickstart.md, Prerequisites; research R10). Production is at `0002` and needs nothing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain rules, schema, ports, adapters, the shared read model, and the removal of the 2026-10-22 code. Every story depends on this phase.

- [ ] T002 [P] Rewrite `api/tests/test_notebook_domain.py` first and check that it fails. Cases:
  - `Notebook(id, name, kitchen_id)`: a name and no kitchen is valid (`kind == "personal"`); no name and a kitchen is valid (`kind == "kitchen"`); a name and a kitchen, or neither, raise `InvalidNotebookError` (invariant "kitchen_id is None ⇔ name is not None").
  - `default_notebook_name("ana") == "ana's Notebook"`; `kitchen_capture_notebook_name("ana", "Home") == "ana's Notebook (Home)"`.
  - `notebook_access(role, via_kitchen, is_kitchen_nb)`: role `"owner"` → `"owner"`; role `"member"` → `"member"`; no role and `via_kitchen` on a personal notebook → `"reader"`; no role and `via_kitchen` on a kitchen notebook → `"member"`; no role and no `via_kitchen` → `None`; the strongest wins (`"member"` with `via_kitchen` → `"member"`).
  - `choose_capture_notebook(candidate_ids, picked)`: no candidates and no pick → `None` (create); one candidate and no pick → it; a pick among the candidates → the pick; a pick that is not a candidate (also with no candidates) → `NotebookNotFoundError`; several and no pick → `NotebookChoiceRequiredError` whose `candidate_ids` equal the candidates in order.
  - `NotebookNotFoundError` keeps one fixed message and code `notebook_not_found`.
- [ ] T003 In `api/domain/errors.py`, following the `MESSAGE` and `CODE` style of the existing errors:
  - rename `InvalidNotebookOwnerError` to `InvalidNotebookError` (message: "A notebook has a name, or belongs to a kitchen, but not both.");
  - add `NotebookChoiceRequiredError` (code `notebook_choice_required`, carries `candidate_ids: list[UUID]`);
  - add `KitchenArchivedError` (code `kitchen_archived`).
  Add no HTTP mapping for the two new errors: S-016 maps them (research R11)
- [ ] T004 Rework `api/domain/notebook.py` so that T002 passes:
  - `Notebook(id, name: str | None, kitchen_id: UUID | None)`, frozen, with the invariant from T002 and `kind` `"personal" | "kitchen"` (drop `user_id`);
  - keep `default_notebook_name`; add `kitchen_capture_notebook_name(alias, kitchen_name)`;
  - add `NotebookRole = Literal["owner", "member"]`, `NotebookAccess = Literal["owner", "member", "reader"]`, `notebook_access(...)` and `choose_capture_notebook(...)` as in data-model.md "Domain".
  Pure: import only from `domain.errors` and the standard library
- [ ] T005 Rework `api/adapters/persistence/models.py` (data-model.md "Tables"):
  - **`NotebookModel`**: drop `user_id` and its index. `name` is nullable text. `kitchen_id` is nullable, unique, FK `kitchens.id` `ON DELETE CASCADE`. Replace `ck_notebook_one_owner` with `CheckConstraint("(kitchen_id IS NULL) = (name IS NOT NULL)", name="ck_notebook_name_or_kitchen")`.
  - **Add `NotebookMembershipModel`** (`notebook_membership`):
    - `notebook_id` FK `notebook.id` `ON DELETE CASCADE`;
    - `user_id` FK `users.id` `ON DELETE CASCADE`, index `ix_notebook_membership_user_id`;
    - `role` text with `CheckConstraint("role IN ('owner', 'member')")`;
    - `created_at` default `now()`;
    - primary key `(notebook_id, user_id)`;
    - partial unique index `uq_notebook_one_owner` on `(notebook_id) WHERE role = 'owner'`.
  - **Add `NotebookKitchenModel`** (`notebook_kitchen`):
    - `notebook_id` FK `notebook.id` `ON DELETE CASCADE`;
    - `kitchen_id` FK `kitchens.id` `ON DELETE CASCADE`, index `ix_notebook_kitchen_kitchen_id`;
    - `linked_by` nullable FK `users.id` `ON DELETE SET NULL`;
    - `created_at` default `now()`;
    - primary key `(notebook_id, kitchen_id)`.
  - **Keep** `IngredientModel` (`uq_ingredient_notebook_name` on `(notebook_id, name)`) and `UserModel.default_notebook_id` (FK `notebook.id` `ON DELETE SET NULL`, `use_alter`) as they are.
- [ ] T006 Delete `api/adapters/persistence/migrations/versions/0003_notebooks_ingredients.py` and add `0003_notebooks_people.py` (revision `0003_notebooks_people`, down revision `0002_pgvector_kitchen_lang`):
  - **Upgrade**: create `notebook`, `notebook_membership`, `notebook_kitchen` and `ingredient` with the constraints, indexes and names of T005, and add `users.default_notebook_id` with its foreign key `users_default_notebook_id_fkey` after `notebook` exists. No backfill (FR-019).
  - **Downgrade**: drop the foreign key and column, then `notebook_kitchen`, `notebook_membership`, `ingredient` and `notebook`.
- [ ] T007 Rework `api/application/ports.py`:
  - **Add a frozen `NotebookFacts`**: `notebook: Notebook`, `role: NotebookRole | None`, `via_kitchen: bool`, `owner_alias: str | None`, `is_default: bool`.
  - **`NotebookRepository` becomes**:
    - `get(notebook_id) -> Notebook | None`;
    - `facts_for(user_id, notebook_id) -> NotebookFacts | None`;
    - `list_for_member(user_id) -> list[NotebookFacts]` (only notebooks where the user has a membership);
    - `list_for_kitchen(user_id, kitchen_id) -> list[NotebookFacts]` (notebooks linked to the kitchen, plus its kitchen notebook);
    - `create(notebook: Notebook) -> None`;
    - `add_owner(notebook_id, user_id) -> None`;
    - `link(notebook_id, kitchen_id, linked_by) -> None`;
    - `capture_candidates(user_id, kitchen_id) -> list[UUID]` (linked to the kitchen, the user is owner or member, never a kitchen notebook, oldest first);
    - `lock_kitchen_membership(user_id, kitchen_id) -> None`;
    - `signup_kitchen_for(user_id) -> UUID | None` (research R4).
  - **Rename `IngredientCatalogReader` to `IngredientCatalog`**: keep `names_for_notebook(notebook_id) -> list[str]`; add `names_for_person(user_id) -> list[str]` and `seed_from_person(notebook_id, user_id) -> None`.
  - **Keep `UserDefaultNotebook`** (`get_for_update`, `set`) as it is.
  - **Lists** are ordered by `notebook.created_at, notebook.id` (FR-015).
- [ ] T008 [P] Rework `api/adapters/persistence/notebooks.py` into `SqlAlchemyNotebookRepository` implementing T007, and keep `SqlAlchemyUserDefaultNotebook` unchanged:
  - **Facts queries**: one query per method, joining `notebook_membership` (the caller's role and the owner's alias through `users.alias`), `notebook_kitchen` with `kitchen_memberships` (`via_kitchen`: a link to a kitchen the caller belongs to, or `notebook.kitchen_id` of such a kitchen), and `users.default_notebook_id` (`is_default`). Hidden and archived memberships count, as in `read_kitchen`.
  - **Writes**: `link` uses `INSERT … ON CONFLICT DO NOTHING`.
  - **`lock_kitchen_membership`**: `SELECT … FROM kitchen_memberships WHERE … FOR UPDATE`.
  - **`signup_kitchen_for`**: the oldest kitchen with `owner_id = user_id` (`ORDER BY created_at, id LIMIT 1`), returned only while the user still has a `kitchen_memberships` row for it.
  - **Access**: the repository returns facts and never decides access (research R8).
- [ ] T009 [P] Rework `api/adapters/persistence/ingredient_catalog.py` into `SqlAlchemyIngredientCatalog`:
  - `names_for_notebook`: kept as built.
  - `names_for_person`: the sorted distinct names in every notebook the user has a `notebook_membership` in, plus the kitchen notebooks of kitchens they belong to.
  - `seed_from_person(notebook_id, user_id)`: one `INSERT INTO ingredient (notebook_id, name) SELECT DISTINCT … ON CONFLICT DO NOTHING` over the same source (research R7).
- [ ] T010 Remove the 2026-10-22 code that the new model replaces:
  - `GetKitchenNotebookService`, `GetMemberNotebookService` and their commands in `api/application/notebooks.py`;
  - `KitchenNotebookResponse` and `MemberNotebookResponse` in `api/api/schemas/notebooks.py`;
  - the three handlers in `api/api/routes/notebooks.py`.
  Keep the `_kitchen_not_found` and `_notebook_not_found` helpers, and keep the router included behind `require_user_alias` in `api/api/app.py`
- [ ] T011 Add the shared read model:
  - **In `api/application/notebooks.py`**:
    - a frozen `NotebookView(id, name, kind, access, owner_alias, is_default)`;
    - `notebook_view(facts, kitchen_name: str | None) -> NotebookView`. `name` is the kitchen's current name for a kitchen notebook. It applies `notebook_access` and raises `NotebookNotFoundError` when the access is `None`.
  - **In `api/api/schemas/notebooks.py`**:
    - `NotebookResponse` with `id`, `name`, `kind: Literal["personal", "kitchen"]`, `access: Literal["owner", "member", "reader"]`, `owner_alias: str | None` and `is_default: bool`;
    - `NotebooksResponse` with `notebooks: list[NotebookResponse]`.
- [ ] T012 Stop creating a notebook with a kitchen (plan "Kitchen creation clean-up"):
  - **`api/application/kitchens.py`**: remove the `NotebookRepository` dependency and the notebook insert from `CreateOwnedKitchenService`, taking it back to its pre-055 form.
  - **Callers**: update `api/api/routes/kitchens.py` and `api/scripts/seed_dev_user.py`.
  - **`api/tests/test_kitchens_domain.py`**: drop `FakeNotebookRepo`.
  - **`api/tests/test_kitchens_integration.py`**: a created kitchen now has no notebook and no `notebook_kitchen` row.
- [ ] T013 Rewrite the fakes at the top of `api/tests/test_notebooks_application.py`:
  - **New fakes**: an in-memory `FakeNotebookRepo` implementing T007 (notebooks, memberships with join order, links, kitchen notebooks, a fake signup kitchen, and a call log for `lock_kitchen_membership`), a `FakeIngredientCatalog` and a `FakeUserDefaultNotebook`.
  - **Kitchen authorization**: reuse the existing kitchen repository fake.
  - **Old tests**: delete the tests written for the 2026-10-22 services.
- [ ] T014 Rewrite the schema part of `api/tests/test_notebook_integration.py` (Compose Postgres) and delete its 2026-10-22 tests. New tests (FR-001 to FR-006, SC-007):
  - **Rejected writes**:
    - a second `owner` row for one notebook;
    - the same person twice in one notebook;
    - a second kitchen notebook for one kitchen;
    - a notebook with both a name and a `kitchen_id`, or neither.
  - **Duplicate link**: linking the same notebook to the same kitchen twice through the repository leaves one row.
  - **Deleting a kitchen**: removes its links and its kitchen notebook, and keeps every notebook that was linked to it, with its catalog (SC-007).
  - **Deleting a notebook**: removes its memberships, links and catalog, and sets `users.default_notebook_id` to null where it pointed at it.
  - **Deleting a user**: removes their memberships and sets `notebook_kitchen.linked_by` to null.
  - **`names_for_notebook`**: returns only that notebook's names, sorted.
  - **`names_for_person`**: returns each name once across the user's notebooks.

**Checkpoint**: The schema migrates, the domain and adapters pass their tests, kitchen creation no longer makes a notebook, and the api suite passes without any notebook route.

---

## Phase 3: User Story 1 - Every person has a default notebook on first use (Priority: P1) 🎯 MVP

**Goal**: The first `GET /notebooks/default` creates "{alias}'s Notebook" with the caller as owner, a seeded catalog and a link to their signup kitchen, and records it as their default. Later calls return the same notebook.

**Independent Test**: As a person with no default notebook, ask for it twice. One notebook exists, named after the alias, owned by the person, recorded as their default and linked to "My kitchen".

- [ ] T015 [US1] Add `GetDefaultNotebookService` tests to `api/tests/test_notebooks_application.py` (fakes from T013), first, and check that they fail (spec User Story 1, scenarios 1–6):
  - **First call**: creates the notebook named "ana's Notebook" and an owner membership for Ana, seeds the catalog, links it to the signup kitchen with `linked_by` Ana, sets the default, and returns `access "owner"`, `is_default True`.
  - **Second call**: returns the same id.
  - **Default set by another call under the lock**: a call that finds it creates nothing.
  - **Default deleted**: the next call creates a new one.
  - **Seed**: with other notebooks holding "onion" and "garlic", the new catalog has both.
  - **No longer a member of the signup kitchen**: the notebook is linked to no kitchen.
  - **No alias**: raises `AliasRequiredError` and creates nothing.
- [ ] T016 [US1] Rework `GetDefaultNotebookService` in `api/application/notebooks.py` so that T015 passes:
  - **Command**: `GetDefaultNotebookCommand(actor_user_id)`; drop the `user_id` path argument.
  - **Order**: read the default; if unset, `get_for_update`, then re-check. To create: `create(Notebook(name=default_notebook_name(alias)))`, `seed_from_person`, `add_owner`, `link` to `signup_kitchen_for(user)` when it is not `None`, then `set` the default.
  - **Return**: a `NotebookView`.
  - **Helper**: move the creation steps into a helper that `ResolveCaptureNotebookService` reuses (research R6, step 5).
- [ ] T017 [US1] Add `GET /notebooks/default` to `api/api/routes/notebooks.py`, answering `NotebookResponse`, always 200, the same body whether or not the notebook was just created (contract). Declare it before `/notebooks/{notebook_id}`
- [ ] T018 [US1] Add integration tests to `api/tests/test_notebook_integration.py` (SC-001, SC-005, SC-008):
  - **First calls**: a signed-up user's first `GET /notebooks/default` returns 200 with `name "{alias}'s Notebook"`, `kind "personal"`, `access "owner"`, `owner_alias` the alias and `is_default true`. The second call returns an identical body.
  - **Rows**: one owner membership; `users.default_notebook_id` points at the notebook; one `notebook_kitchen` row to the signup kitchen.
  - **Concurrency**: two connections racing the first call (rework `test_simultaneous_first_calls_make_one_notebook`, keeping its `threading.Barrier` pattern) leave one notebook.
  - **Default deleted**: deleting the default row and calling again gives a new id, the same fields, and a link to "My kitchen" again.
  - **No alias**: 403 `alias_required`, and no `notebook` row.
- [ ] T019 [P] [US1] Add the BFF route `ui/app/api/notebooks/default/route.ts` (GET), copying the forwarding pattern of `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts`, and a case in `ui/app/api/notebooks.bff.test.ts`: it forwards to `/notebooks/default` with the `cookie` header and returns 502 `bad_gateway` when the api is unreachable (FR-017)

**Checkpoint**: User Story 1 works on its own.

---

## Phase 4: User Story 2 - A capture in a kitchen has a notebook to go into (Priority: P1)

**Goal**: `ResolveCaptureNotebookService`, which S-016's save will call, returns the member's notebook linked to a kitchen. It creates and links "{alias}'s Notebook ({kitchen name})" when the member has none, or creates the default notebook in their signup kitchen. It never runs from a route.

**Independent Test**: As a member of "Home" with no linked notebook, run the step twice: one "{alias}'s Notebook (Home)" exists, owned by the member and linked to "Home". A non-member gets `KitchenNotFoundError` and nothing is created.

- [ ] T020 [US2] Add `ResolveCaptureNotebookService` tests to `api/tests/test_notebooks_application.py`, first, and check that they fail. Cover each row of the contract table "In-process: the capture notebook step":
  - **Kitchen missing or caller not a member**: `KitchenNotFoundError`.
  - **One candidate, no pick**: that notebook.
  - **A pick among the candidates**: the pick.
  - **A pick that is not a candidate**: `NotebookNotFoundError`.
  - **Several candidates, no pick**: `NotebookChoiceRequiredError`.
  - **Archived kitchen**: `KitchenArchivedError` whether or not a candidate exists; nothing is created or returned.
  - **None, signup kitchen, no default yet**: the default notebook, created and linked, and no "(My kitchen)" notebook.
  - **None, otherwise**: a new "ana's Notebook (Home)" with Ana as owner, catalog seeded ("onion"), linked by Ana.
  - **Shared notebook**: Ben, a member of Ana's notebook linked to "Home", gets Ana's notebook.
  - **Lock order**: `lock_kitchen_membership` is called before `capture_candidates`.
- [ ] T021 [US2] Implement `ResolveCaptureNotebookCommand(actor_user_id, kitchen_id, picked_notebook_id=None)` and `ResolveCaptureNotebookService` in `api/application/notebooks.py` in the order of research R6:
  1. authorize with `read_kitchen` through `AuthorizeKitchenAccessService`, then refuse an archived kitchen with `KitchenArchivedError`;
  2. `lock_kitchen_membership`;
  3. `capture_candidates`;
  4. `choose_capture_notebook`;
  5. when it returns `None`: the signup kitchen and default notebook case (reusing the T016 helper), otherwise create, seed, add the owner and link with `kitchen_capture_notebook_name(alias, kitchen.name)`.

  It returns the `Notebook`. Commit a notebook it creates in its own transaction, so it stays if the caller's recipe save fails (FR-008, 2026-10-23). Do not add a route for it (FR-021).
- [ ] T022 [US2] Add integration tests for the capture step to `api/tests/test_notebook_integration.py`, calling the service with real adapters on a Compose session (SC-002, spec User Story 2):
  - **First call**: Ana's first call in "Home" creates "ana's Notebook (Home)", Ana owner, linked by Ana; the second call returns it.
  - **Two linked notebooks**: they raise `NotebookChoiceRequiredError`, a valid pick returns it, and a foreign pick raises `NotebookNotFoundError`.
  - **Shared notebook**: with Ben inserted as a `member` row in Ana's notebook, Ben's call returns Ana's notebook and creates nothing.
  - **Concurrency**: two connections racing Ana's first call in "Home" leave one notebook and one link.
  - **Non-member**: Carl gets `KitchenNotFoundError` and no rows.
  - **Archived kitchen**: `KitchenArchivedError` and no rows, also when Ana already has a notebook linked to it.
  - **Failed save**: a notebook created by the step stays after the caller's own transaction is rolled back.
  - **Signup kitchen**: Ana's first call in "My kitchen" with no default creates the default notebook and links it, with no "(My kitchen)" notebook.
- [ ] T023 [US2] Add a test to `api/tests/test_notebook_integration.py`: the app's routes under `/notebooks` are exactly the four GET routes of the contract, so the capture step is not reachable (FR-021)

**Checkpoint**: User Stories 1 and 2 work; S-016 can call the capture step from its save.

---

## Phase 5: User Story 3 - People and kitchen members read the notebooks they may see (Priority: P1)

**Goal**: `GET /notebooks`, `GET /notebooks/{notebook_id}` and `GET /notebooks/kitchens/{kitchen_id}` answer with the caller's access, and anyone without access gets the 404 for a missing resource.

**Independent Test**: Ana owns two notebooks, one linked to "Home", where Ben is also a member. Read Ana's list, each notebook, and Home's list as Ana, Ben and Carl, and check what each one sees.

- [ ] T024 [US3] Add tests for `ListMyNotebooksService`, `GetNotebookService` and `ListKitchenNotebooksService` to `api/tests/test_notebooks_application.py`, first, and check that they fail (spec User Story 3):
  - **My list**: holds only notebooks with a membership, `access` `"owner"` or `"member"`, never `"reader"`, oldest first, with `is_default` set only on the default.
  - **Get by id**:
    - `"reader"` for a member of a linked kitchen;
    - `"member"` for a kitchen notebook reached through its kitchen, with `name` the kitchen's current name and `owner_alias` `None`;
    - `NotebookNotFoundError` for no access and for a missing id.
  - **Kitchen list**: authorizes first (`KitchenNotFoundError` for a missing kitchen and a non-member), lists linked notebooks plus the kitchen notebook with each access, returns `[]` when nothing is linked, and still lists for an archived or hidden kitchen.
- [ ] T025 [US3] Implement `ListMyNotebooksService`, `GetNotebookService` and `ListKitchenNotebooksService` in `api/application/notebooks.py` so that T024 passes, building every answer with `notebook_view` (T011). The kitchen list authorizes with `read_kitchen` through `AuthorizeKitchenAccessService`
- [ ] T026 [US3] Add the routes to `api/api/routes/notebooks.py`:
  - `GET /notebooks` → `NotebooksResponse`;
  - `GET /notebooks/kitchens/{kitchen_id}` → `NotebooksResponse`, 404 `kitchen_not_found`;
  - `GET /notebooks/{notebook_id}` → `NotebookResponse`, 404 `notebook_not_found`.

  Declare the static segments (`/notebooks/default`, `/notebooks/kitchens/...`) before `/notebooks/{notebook_id}`.
- [ ] T027 [US3] Add the read-route integration tests to `api/tests/test_notebook_integration.py` (spec User Story 3 scenarios 1–7, SC-003, SC-004). Set the scene through the services and direct membership inserts:
  - **Ana's list**: Ana sees both her notebooks with `access "owner"`.
  - **Ben in "Home"**: Ben sees "ana's Notebook (Home)" in Home's list and by id with `access "reader"` and `owner_alias "ana"`, and never in `GET /notebooks`.
  - **Notebook 404s**: Ben gets 404 for "ana's Notebook" (linked only to Ana's "My kitchen"). Carl gets the same 404 body for that notebook and for a random UUID.
  - **Kitchen 404**: Carl gets 404 `kitchen_not_found` for Home's list, with the same body as for a missing kitchen.
  - **Empty kitchen**: an unlinked kitchen's list is `{"notebooks": []}`.
  - **Order**: lists are oldest first.
- [ ] T028 [P] [US3] Update the BFF routes and their test:
  - **New routes**: `ui/app/api/notebooks/route.ts` (GET `/notebooks`) and `ui/app/api/notebooks/[notebookId]/route.ts` (GET `/notebooks/{notebookId}`), with the pattern of `kitchens/[kitchenId]/route.ts`. That route is kept as is.
  - **Removed**: `ui/app/api/notebooks/members/`.
  - **`ui/app/api/notebooks.bff.test.ts`**: rework it so each of the four routes forwards to the right api path with the cookie and passes a 404 through, and remove the member-route cases (FR-017).

**Checkpoint**: All P1 stories work on their own.

---

## Phase 6: User Story 4 - The upgrade keeps existing data working (Priority: P2)

**Goal**: Revision `0003_notebooks_people` upgrades, downgrades and upgrades again on released data, without changing users or kitchens.

**Independent Test**: quickstart.md §2.

- [ ] T029 [US4] Run quickstart.md §2 on a scratch database at `0002` with invented users and kitchens: `upgrade head`, check that the four tables are empty, `users.default_notebook_id` is null for everyone and users and kitchens are unchanged; `downgrade 0002_pgvector_kitchen_lang`, check the tables and column are gone; `upgrade head` again. Then, on the upgraded database, check that an existing user's first `GET /notebooks/default` works (spec User Story 4). Record the result in `dev/memory/` with `dev/skills/save_to_memory.md` (SC-006)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T030 [P] Search the code for leftovers of the 2026-10-22 model: `InvalidNotebookOwnerError`, `IngredientCatalogReader`, `GetKitchenNotebookService`, `GetMemberNotebookService`, `KitchenNotebookResponse`, `MemberNotebookResponse`, `notebooks/members`, `NotebookModel.user_id`, `0003_notebooks_ingredients`. None may remain under `api/` or `ui/` (git history and `specs/` excepted)
- [ ] T031 Run `cd api && uv run ruff check .` and fix every finding in the touched files
- [ ] T032 Run the checks and report the pass counts:
  - **api suite in Compose with the dev overlay**: `docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.test.yml run --rm --build api`. The base file alone hangs (`dev/memory/221026.md`).
  - **ui**: `cd ui && npm test && npm run lint && npm run typecheck`.
- [ ] T033 Walk quickstart.md §3, §5 and §6 by hand on the running stack (`./scripts/compose-up.sh -d`) with two invented users (Ana and Ben). Covers the routes, the recreated default and kitchen deletion
- [ ] T034 [P] Add a dated re-sync note to `specs/016-capture-recipe-text/spec.md` and `plan.md` (plan "Build order" step 8):
  - **Save**: S-016's save calls `ResolveCaptureNotebookService` in the save transaction.
  - **Personal capture**: reads `GET /notebooks/default`.
  - **Kitchen draft with no notebook yet**: matched against `IngredientCatalog.names_for_person`.
  - **Errors**: S-016 maps `NotebookChoiceRequiredError` and `KitchenArchivedError` to HTTP.
  - **Superseded**: FR-001a and the old capture routes keyed by notebook owner.
- [ ] T035 [P] Ask the owner to approve adding the clarify Q3 rule ("the default notebook is linked to the person's signup kitchen when it is created") to PRD flow H and J1a in `dev/docs/prd.md` and to the domain rules in `AGENTS.md` (plan "Follow-ups"). Make the change only after approval
- [X] T036 Regenerate the requirements-quality checklist: after the owner confirms, delete the stale `specs/055-notebooks/checklists/requirements-quality.md` (2026-10-22 model, never committed), then run `/speckit-checklist`
- [ ] T037 Update the S-055 `verification` in `dev/docs/backlog.yaml` with the new pass counts and "reworked to the 2026-10-23 model", and append a memory line with `dev/skills/save_to_memory.md`. Do not push or deploy without review (AGENTS.md)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001)**: first, on any machine with an old dev database.
- **Foundational (T002–T014)**: blocks every story. Inside the phase:
  - T002 → T003 → T004.
  - T005 → T006.
  - T004 and T005 → T007 → T008 and T009 (parallel).
  - T010 and T011 after T007.
  - T012 after T004.
  - T013 after T007.
  - T014 after T008 and T009.
- **US1 (T015–T019)**: after Foundational.
- **US2 (T020–T023)**: after US1, because T021 reuses the default-notebook helper from T016.
- **US3 (T024–T028)**: after Foundational. Independent of US1 and US2: its tests set notebooks up through the repository and direct inserts.
- **US4 (T029)**: after T006. It is a run, not code.
- **Polish (T030–T037)**: after the stories it checks. T034 and T035 are docs and can start any time after Foundational.

### User story dependencies

- **US1 (P1)**: depends only on Foundational.
- **US2 (P1)**: depends on US1 (shared creation helper, signup kitchen case).
- **US3 (P1)**: depends only on Foundational.
- **US4 (P2)**: depends only on T006.

### Within each story

Tests first (they must fail), then the service, then the route, then the integration tests, then the BFF route.

### Parallel opportunities

- **Foundational**: T002 alongside T005 (domain tests vs models); T008 alongside T009 (two adapter files).
- **Stories**: US1 and US3 can be built side by side after Foundational (both touch `api/application/notebooks.py` and `api/api/routes/notebooks.py`, so merge carefully).
- **BFF routes**: T019 and T028 (ui) alongside the api work of their story.
- **Docs**: T030, T034 and T035 alongside each other.

## Parallel Example: Foundational

```text
Task: "T002 [P] Rewrite api/tests/test_notebook_domain.py (tests first)"
Task: "T005 Rework models in api/adapters/persistence/models.py"
# after T007
Task: "T008 [P] SqlAlchemyNotebookRepository in api/adapters/persistence/notebooks.py"
Task: "T009 [P] SqlAlchemyIngredientCatalog in api/adapters/persistence/ingredient_catalog.py"
```

## Parallel Example: User Story 3

```text
Task: "T024 [US3] Service tests in api/tests/test_notebooks_application.py"
Task: "T028 [P] [US3] BFF routes in ui/app/api/notebooks/ and notebooks.bff.test.ts"
```

## Implementation Strategy

- **MVP**: Phases 1–3 (Setup, Foundational, User Story 1). The Notebook tab can show the person's default notebook, and a personal capture has somewhere to go.
- **Next**: User Story 2. S-016's kitchen capture needs it.
- **Then**: User Story 3, which the kitchen Notebook tab and S-016's notebook picker need, and User Story 4, the migration check before merge.
- **Commits**: one per phase or smaller (domain, schema, adapters, each story, BFF, docs). The api suite must pass after each commit from the Foundational checkpoint on.
- **After merge**: S-016 re-syncs with T034 and builds on the capture step. S-056, S-034 and S-057 add members, manual links and the kitchen notebook.
