# Tasks: Personal and Kitchen Notebooks

**Input**: Design documents from `specs/055-notebooks/` (spec.md re-specified 2026-10-23 for the snapshot model, plan.md, research.md R1–R13, data-model.md, contracts/notebooks-api.md, quickstart.md). Prerequisite for `specs/016-capture-recipe-text`.

**Prerequisites**: plan.md, spec.md (both required); research.md, data-model.md, contracts/ (used below)

**Tests**: Included. The constitution (§6) requires them: domain tests are pure, use-case tests use fake ports, integration tests run in the Compose overlay with Postgres. Within each story, write the tests first and check that they fail.

**Organization**: Tasks are grouped by user story (US1–US5 of spec.md). This list replaces the kitchen-link task list (T001–T037 of commit `3ff1601`) and the 2026-10-22 list (commit `064d344`). The branch holds the 2026-10-22 code; the plan's "Reuse" section says what carries over, and the tasks below rework it in place.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1–US5, spec.md)
- Paths are relative to the repo root (`api/`, `ui/`, per plan.md)

## Notes

- Signup, sign-in, alias claim and sessions are not changed (FR-005, constitution §1). The only change to the user is `users.default_notebook_id`, which already exists on the branch. `notebook.owner_user_id` is the only other new column (kitchen notebooks, T005 and T006).
- No task writes recipe, step, category, source, invite or cart rows, adds notebook members through the app, or sets `source_notebook_id` (FR-022). Integration tests may insert membership rows, or a notebook with `source_notebook_id`, directly to set up a scenario.
- A caller with no access gets the same 404 body as for something that does not exist, never 403 (SC-004).
- Commit one task or one small group at a time. Do not push (AGENTS.md).

---

## Phase 1: Setup

- [X] T001 Bring the local dev and test databases off the old revision before the rework lands: a database that ran `api/adapters/persistence/migrations/versions/0003_notebooks_ingredients.py` must go back to `0002_pgvector_kitchen_lang`. Run `docker compose exec api uv run alembic downgrade 0002_pgvector_kitchen_lang` while the old file still exists (any commit up to `3ff1601`), or recreate the dev database (quickstart.md, Prerequisites; research R12). Production is at `0002` and needs nothing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain rules, schema, ports, adapters, the shared read model, and the removal of the 2026-10-22 code. Every story depends on this phase.

- [X] T002 [P] Rewrite `api/tests/test_notebook_domain.py` first and check that it fails (data-model.md "Domain"). Cases:
  - **`Notebook`**: `Notebook(id, name="ana's Notebook")` is valid with `kind == "personal"`; with `kitchen_id` set, `kind == "kitchen"`. `InvalidNotebookError` for a blank name (`""`, `"  "`), for `source_notebook_id` on a notebook with no `kitchen_id`, for `source_notebook_id == id`, and for `owner_user_id` on a notebook with no `kitchen_id`.
  - **Names**: `default_notebook_name("ana") == "ana's Notebook"`; `kitchen_notebook_name("ana", "Home") == "ana's (Home) Notebook"`.
  - **`notebook_access(kind, role, in_kitchen)`**: personal with role `"owner"` → `"owner"`, with `"member"` → `"member"`, with no role and `in_kitchen=True` → `None`; kitchen with `in_kitchen=True` → `"kitchen_member"`, with role `"owner"` and `in_kitchen=False` → `None`.
  - **`choose_capture_notebook(candidates, picked)`**: no candidates, no pick → `None`; one candidate, no pick → it; a pick among the candidates → the pick; a pick not among them, also with no candidates → `NotebookNotFoundError`; several and no pick → `NotebookChoiceRequiredError` whose `candidate_ids` equal the candidates in order.
  - **Errors**: `NotebookNotFoundError.CODE == "notebook_not_found"`, `KitchenArchivedError.CODE == "kitchen_archived"`, `NotebookChoiceRequiredError.CODE == "notebook_choice_required"`.
- [X] T003 In `api/domain/errors.py`, following the `MESSAGE` and `CODE` style of the existing errors (research R13):
  - rename `InvalidNotebookOwnerError` to `InvalidNotebookError` (message: "A notebook needs a name, and only a kitchen notebook has an origin or an owner.");
  - add `KitchenArchivedError` (code `kitchen_archived`, message "This kitchen is archived, so recipes can't be added.");
  - add `NotebookChoiceRequiredError` (code `notebook_choice_required`, carries `candidate_ids: list[UUID]`).
  Add no HTTP mapping for the two new errors: S-019 maps them
- [X] T004 Rework `api/domain/notebook.py` so that T002 passes:
  - `Notebook(id, name: str, kitchen_id: UUID | None = None, source_notebook_id: UUID | None = None, owner_user_id: UUID | None = None)`, frozen, with the four invariants (the three above, and an owner only on a kitchen notebook) and `kind` `"personal" | "kitchen"` (drop `user_id`);
  - keep `default_notebook_name`; add `kitchen_notebook_name(alias, kitchen_name)`;
  - add `NotebookKind`, `NotebookRole = Literal["owner", "member"]`, `NotebookAccess = Literal["owner", "member", "kitchen_member"]`, `notebook_access(...)` and `choose_capture_notebook(...)`.
  Pure: import only from `domain.errors` and the standard library. Update the module docstring to the two kinds
- [X] T005 [P] Rework `api/adapters/persistence/models.py` (data-model.md "Tables"):
  - **`NotebookModel`**: drop `user_id` and its index, and `ck_notebook_one_owner`. `name` is text, not null, with `CheckConstraint("btrim(name) <> ''", name="ck_notebook_name_not_blank")`. `kitchen_id` is nullable, **not unique**, FK `kitchens.id` `ON DELETE CASCADE`, index `ix_notebook_kitchen_id`. Add `source_notebook_id`, nullable, FK `notebook.id` `ON DELETE SET NULL`, index `ix_notebook_source_notebook_id`, with `CheckConstraint("source_notebook_id IS NULL OR kitchen_id IS NOT NULL", name="ck_notebook_source_is_kitchen")` and `CheckConstraint("source_notebook_id <> id", name="ck_notebook_source_not_self")`. Add `owner_user_id`, nullable, FK `users.id` `ON DELETE SET NULL`, index `ix_notebook_owner_user_id`, with `CheckConstraint("owner_user_id IS NULL OR kitchen_id IS NOT NULL", name="ck_notebook_owner_is_kitchen")`.
  - **Add `NotebookMembershipModel`** (`notebook_membership`): `notebook_id` FK `notebook.id` `ON DELETE CASCADE`; `user_id` FK `users.id` `ON DELETE CASCADE`, index `ix_notebook_membership_user_id`; `role` text with `CheckConstraint("role IN ('owner', 'member')", name="ck_notebook_membership_role")`; `created_at` default `now()`; primary key `(notebook_id, user_id)`; partial unique index `uq_notebook_one_owner` on `(notebook_id) WHERE role = 'owner'`.
  - **Keep** `IngredientModel` (`uq_ingredient_notebook_name` on `(notebook_id, name)`) and `UserModel.default_notebook_id` (FK `notebook.id` `ON DELETE SET NULL`, `use_alter`) as they are.
- [X] T006 Delete `api/adapters/persistence/migrations/versions/0003_notebooks_ingredients.py` and add `api/adapters/persistence/migrations/versions/0003_personal_kitchen_notebooks.py` (revision `0003_personal_kitchen_notebooks`, down revision `0002_pgvector_kitchen_lang`):
  - **Upgrade**: create `notebook`, `notebook_membership` and `ingredient` with the constraints, indexes and names of T005, then add `users.default_notebook_id` with its foreign key `users_default_notebook_id_fkey`. No backfill (FR-023).
  - **Downgrade**: drop the foreign key and column, then `ingredient`, `notebook_membership` and `notebook`.
- [X] T007 Rework `api/application/ports.py` (research R6–R10):
  - **Add a frozen `NotebookFacts`**: `notebook: Notebook`, `role: NotebookRole | None`, `in_kitchen: bool`, `owner_alias: str | None` (for a kitchen notebook, the stored owner's alias, or the kitchen owner's when none is stored, read through `notebook.owner_user_id` and `kitchens.owner_id`), `kitchen_is_archived: bool | None`, `is_default: bool`.
  - **`NotebookRepository` becomes**:
    - `get(notebook_id) -> Notebook | None`;
    - `facts_for(user_id, notebook_id) -> NotebookFacts | None`;
    - `personal_facts_for(user_id) -> list[NotebookFacts]` (personal notebooks where the user has a membership);
    - `kitchen_notebooks(kitchen_id) -> list[Notebook]`;
    - `personal_ids_for(user_id) -> list[UUID]` and `kitchen_ids_for(kitchen_id) -> list[UUID]` (capture candidates);
    - `create(notebook: Notebook) -> None`;
    - `add_owner(notebook_id, user_id) -> None`;
    - `lock_kitchen(kitchen_id) -> None`.
  - **Rename `IngredientCatalogReader` to `IngredientCatalog`**: keep `names_for_notebook(notebook_id) -> list[str]`; add `names_for_person(user_id) -> list[str]` and `seed_from_person(notebook_id, user_id) -> None`.
  - **Keep `UserDefaultNotebook`** (`get_for_update`, `set`) as it is.
  - **Add `TransactionCommitter`** with `commit() -> None` (research R8).
  - **Order**: every list and id list is ordered by `notebook.created_at, notebook.id` (FR-019).
- [X] T008 [P] Rework `api/adapters/persistence/notebooks.py`:
  - **`SqlAlchemyNotebookRepository`** implementing T007. One query per method. `facts_for` and `personal_facts_for` left-join the caller's `notebook_membership` row (role), the owner's row and `users.alias` (owner alias; for a kitchen notebook, the stored owner's, else the kitchen owner's, R10), the caller's `users.default_notebook_id` (`is_default`) and, for a kitchen notebook, the caller's `kitchen_memberships` row (`in_kitchen`; archived kitchens count, as in `read_kitchen`). `personal_ids_for` reads only notebooks with `kitchen_id IS NULL`. `lock_kitchen` runs `SELECT id FROM kitchens WHERE id = :id FOR NO KEY UPDATE` (`with_for_update(key_share=True)`). The repository returns facts and never decides access (research R10).
  - **Keep `SqlAlchemyUserDefaultNotebook`** unchanged.
  - **Add `SqlAlchemyTransactionCommitter(session)`**, whose `commit()` calls `session.commit()`.
- [X] T009 [P] Rework `api/adapters/persistence/ingredient_catalog.py` into `SqlAlchemyIngredientCatalog` (research R9):
  - `names_for_notebook`: kept as built.
  - `names_for_person(user_id)`: the sorted distinct names in every notebook the user has a `notebook_membership` row in (so personal notebooks only).
  - `seed_from_person(notebook_id, user_id)`: one `INSERT INTO ingredient (notebook_id, name) SELECT DISTINCT … ON CONFLICT DO NOTHING` over the same source.
- [X] T010 Remove the 2026-10-22 read code:
  - `GetKitchenNotebookService` (with its lazy notebook creation), `GetMemberNotebookService`, `KitchenNotebookView` and their commands in `api/application/notebooks.py`;
  - `KitchenNotebookResponse` and `MemberNotebookResponse` in `api/api/schemas/notebooks.py`;
  - the three handlers in `api/api/routes/notebooks.py`.
  Keep the `_kitchen_not_found` and `_notebook_not_found` helpers, and keep the router included behind `require_user_alias` in `api/api/app.py`. `CreateOwnedKitchenService` is reworked in US2 (T020)
- [X] T011 Add the shared read model:
  - **In `api/application/notebooks.py`**: a frozen `NotebookView(id, name, kind, access, owner_alias, kitchen_id, kitchen_is_archived, is_default)` and `notebook_view(facts) -> NotebookView`, which applies `notebook_access` and raises `NotebookNotFoundError` when it is `None`. A kitchen notebook's view has `owner_alias` the stored owner's alias, or the kitchen owner's when none is stored (None when neither exists), and `is_default False` (data-model.md "Read model").
  - **In `api/api/schemas/notebooks.py`**: `NotebookResponse` with `id`, `name`, `kind: Literal["personal", "kitchen"]`, `access: Literal["owner", "member", "kitchen_member"]`, `owner_alias: str | None`, `kitchen_id: UUID | None`, `kitchen_is_archived: bool | None`, `is_default: bool`; `NotebooksResponse` with `notebooks: list[NotebookResponse]`.
- [X] T012 Rewrite the fakes at the top of `api/tests/test_notebooks_application.py` and delete the tests written for the 2026-10-22 services:
  - an in-memory `FakeNotebookRepo` implementing T007 (notebooks with creation order, memberships, a call log for `lock_kitchen`);
  - `FakeIngredientCatalog` (names per notebook; `seed_from_person` copies the union of the person's personal notebooks);
  - `FakeUserDefaultNotebook`, `FakePrefs` and `FakeCommitter` (counts `commit()` calls);
  - keep `FakeKitchenRepo` for kitchen authorization, with an `is_archived` flag.
- [X] T013 Rewrite the schema part of `api/tests/test_notebook_integration.py` (Compose Postgres) and delete its 2026-10-22 tests. New tests (FR-001 to FR-006):
  - **Rejected writes**: a second `owner` row for one notebook; the same person twice in one notebook; a blank name; `source_notebook_id` on a personal notebook; `source_notebook_id` equal to `id`.
  - **Allowed**: two kitchen notebooks for one kitchen.
  - **Deleting a kitchen**: removes its kitchen notebooks and their `ingredient` rows, clears `source_notebook_id` on a notebook that came from one of them, and keeps every personal notebook of its members (SC-008).
  - **Deleting a personal notebook**: removes its memberships and catalog, sets `users.default_notebook_id` to null where it pointed at it, and clears `source_notebook_id` on a kitchen notebook inserted as its snapshot, which stays.
  - **Deleting a user**: removes their memberships, sets `owner_user_id` to null on the kitchen notebooks they owned, and leaves every notebook.
  - **Catalog adapter**: `names_for_notebook` returns only that notebook's names, sorted; `names_for_person` returns each name once across the person's personal notebooks and never a kitchen notebook's names; `seed_from_person` copies that set into a new notebook.

**Checkpoint**: The schema migrates, the domain and adapters pass their tests, and no 2026-10-22 read code remains. Kitchen creation still makes a notebook with the branch's wiring until T020 reverts it, so commit this phase together with US2, or do US2 next; from then on the api suite passes after every commit.

---

## Phase 3: User Story 1 - Every person has a default personal notebook on first use (Priority: P1) 🎯 MVP

**Goal**: The first `GET /notebooks/default` creates the personal notebook "{alias}'s Notebook" with the caller as owner and a seeded catalog, and records it as their default. Later calls return the same notebook.

**Independent Test**: As a person with no default notebook, ask for it twice. One notebook exists, named after the alias, personal, owned by the person and recorded as their default.

- [X] T014 [US1] Add `GetDefaultNotebookService` tests to `api/tests/test_notebooks_application.py` (fakes from T012), first, and check that they fail (spec US1 scenarios 1–5):
  - **First call**: creates a notebook named "ana's Notebook" with no `kitchen_id`, an owner membership for Ana and a catalog seed, sets the default, and returns `access "owner"`, `is_default True`.
  - **Second call**: returns the same id and creates nothing.
  - **Default set by another call under the lock**: a call that finds it after `get_for_update` creates nothing.
  - **Default deleted**: the next call creates a new one.
  - **Seed**: with personal notebooks holding "onion" and "garlic", the new catalog has both.
  - **No alias**: raises `AliasRequiredError` and creates nothing.
- [X] T015 [US1] Rework `GetDefaultNotebookService` in `api/application/notebooks.py` so that T014 passes (research R4):
  - **Command**: `GetDefaultNotebookCommand(actor_user_id)`; drop the `user_id` argument and the owner-only branch.
  - **Order**: read the default; if unset or gone, `get_for_update` and re-check. To create: `create(Notebook(name=default_notebook_name(alias)))`, `seed_from_person`, `add_owner`, then `set` the default.
  - **Return**: a `NotebookView` built with `facts_for`.
  - **Helper**: put the lock, re-check and creation in one function, `ensure_default_notebook(...) -> tuple[UUID, bool]` (id, created), that `ResolveCaptureNotebookService` reuses (research R7).
- [X] T016 [US1] Add `GET /notebooks/default` to `api/api/routes/notebooks.py`, answering `NotebookResponse`, always 200, the same body whether or not the notebook was just created (contract). Declare it before `/notebooks/{notebook_id}`
- [X] T017 [US1] Add integration tests to `api/tests/test_notebook_integration.py` (SC-001, SC-007):
  - **First calls**: a signed-up user's first `GET /notebooks/default` returns 200 with `name "{alias}'s Notebook"`, `kind "personal"`, `access "owner"`, `owner_alias` the alias, `kitchen_id null` and `is_default true`. The second call returns an identical body.
  - **Rows**: one owner membership; `users.default_notebook_id` points at the notebook; `kitchen_id` is null.
  - **Concurrency**: two connections racing the first call (rework `test_simultaneous_first_calls_make_one_notebook`, keeping its `threading.Barrier` pattern) leave one notebook.
  - **Default deleted**: deleting the default row and calling again gives a new id and the same fields.
  - **No alias**: 403 `alias_required`, and no `notebook` row.
- [X] T018 [P] [US1] Add the BFF route `ui/app/api/notebooks/default/route.ts` (GET), copying the forwarding pattern of `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts`, and a case in `ui/app/api/notebooks.bff.test.ts`: it forwards to `/notebooks/default` with the `cookie` header and returns 502 `bad_gateway` when the api is unreachable (FR-021)

**Checkpoint**: User Story 1 works on its own.

---

## Phase 4: User Story 2 - A kitchen gets its kitchen notebook the first time a member opens it (Priority: P1)

**Goal**: Kitchen creation makes no notebook (R5). The first time a member opens a kitchen's notebooks while it has none, and the kitchen is not archived, the kitchen gets "{alias}'s ({kitchen name}) Notebook", owned by that member and seeded from their personal catalog (R14). Signup is not changed.

**Independent Test**: As Ana, create "Home": it has no notebook. Ana opens its notebooks: exactly one exists, named "ana's (Home) Notebook", owned by Ana, with no membership rows and Ana's personal catalog.

- [X] T019 [US2] Rework the kitchen-creation tests in `api/tests/test_kitchens_domain.py` first, and check that they fail (spec US2 scenario 1, R5):
  - creating "Home" as "ana" makes no notebook and calls neither the notebook repository nor the catalog;
  - an invalid kitchen name raises `InvalidKitchenNameError` and creates nothing.
- [X] T020 [US2] Revert `CreateOwnedKitchenService` in `api/application/kitchens.py` to its pre-S-055 form so that T019 passes (research R5): the kitchen and the creator's membership only, with its original constructor. Its docstring says kitchen creation makes no notebook (spec 055 FR-008). No commit here: `get_db` commits the kitchen and its membership together.
- [X] T021 [US2] Revert the notebook wiring in `api/scripts/seed_dev_user.py` (the `SqlAlchemyNotebookRepository` import and argument). No alias skip is needed, because kitchen creation names no notebook. `api/api/routes/kitchens.py` needs no change.
- [X] T021a [US2] Write the first-open tests first in `api/tests/test_notebooks_application.py`, and check that they fail (spec US2 scenarios 2, 3, 7; R14). Cases for `ListKitchenNotebooksService`:
  - a member opens "Home" with no notebook: one notebook "ben's (Home) Notebook" is created with `kitchen_id` Home and `owner_user_id` Ben, is seeded from Ben's personal catalog ("onion"), and is listed with `access "kitchen_member"`;
  - a second open returns the same notebook and creates nothing;
  - the kitchen's lock is taken before the second read (`lock_kitchen` in the call log);
  - an archived kitchen with no notebook lists `[]` and creates nothing; an archived kitchen with a notebook still lists it;
  - a non-member, or a missing kitchen, gets `KitchenNotFoundError`;
  - no `commit()` is called.
- [X] T021b [US2] Implement `ensure_kitchen_notebook(kitchen, actor_user_id, alias)` and `ListKitchenNotebooksService` in `api/application/notebooks.py` so that T021a passes (research R14). Authorize with `read_kitchen` through `AuthorizeKitchenAccessService`. List the kitchen's notebooks. When there are none and the kitchen is not archived, call the helper (lock, re-check, create owned by the caller, seed), then list. Build views with `notebook_view(facts)` and `in_kitchen=True`. No commit.
- [X] T022 [US2] Integration tests in `api/tests/test_kitchens_integration.py` and `api/tests/test_notebook_integration.py` (SC-002, SC-003, spec US2):
  - `POST /kitchens` "Home" as "ana" leaves no `notebook` row for Home;
  - Ana's first `GET /notebooks/kitchens/{Home}` creates one `notebook` row named "ana's (Home) Notebook" with `owner_user_id` Ana and no `notebook_membership` row, and lists it; the second call returns the same id;
  - with Ana's default notebook holding "onion", Home's notebook catalog holds "onion";
  - Ana and Ben racing their first open on two connections (`threading.Barrier`) leave one notebook;
  - with `SqlAlchemyIngredientCatalog.seed_from_person` patched to raise, the first open fails and no notebook exists;
  - a failure after the kitchen row (the membership insert patched to raise) leaves neither the kitchen nor a notebook (scenario 4);
  - a new signup's "My kitchen" has no notebook until its first open (scenario 5);
  - renaming "Home" to "Casa" leaves the notebook named "ana's (Home) Notebook" (scenario 6);
  - an archived kitchen with no notebook lists `{"notebooks": []}` and creates nothing (scenario 7).

**Checkpoint**: User Stories 1 and 2 work; the api suite is green again.

---

## Phase 5: User Story 3 - A capture has a notebook to go into (Priority: P1)

**Goal**: `ResolveCaptureNotebookService`, which S-019's save will call, returns the notebook a capture goes into: in a kitchen, its only notebook, the picked one, or a new "{alias}'s ({kitchen name}) Notebook"; outside a kitchen, the only personal notebook, the picked one, or the default. It never runs from a route.

**Independent Test**: As a member of "My kitchen" with no notebook, run the step twice: one "{alias}'s (My kitchen) Notebook" exists and is used both times. A non-member gets `KitchenNotFoundError`, and an archived kitchen `KitchenArchivedError`, with nothing created.

- [X] T023 [US3] Add `ResolveCaptureNotebookService` tests to `api/tests/test_notebooks_application.py`, first, and check that they fail. Cover each row of the contract table "In-process: the capture notebook step":
  - **Kitchen missing or caller not a member**: `KitchenNotFoundError`, nothing created.
  - **Archived kitchen**: `KitchenArchivedError` with and without notebooks; the candidates are not read.
  - **Kitchen, none**: creates "ana's (My kitchen) Notebook" with `kitchen_id` set and `owner_user_id` Ana, no membership, seeds it from Ana's personal catalog ("onion"), calls `lock_kitchen` before the second candidate read and `commit()` once, and returns `created True`.
  - **Kitchen, none, but another call created one under the lock**: uses it, creates nothing, no commit.
  - **Kitchen, one**: Ben gets it with `created False`, no lock, no commit.
  - **Kitchen, two**: no pick → `NotebookChoiceRequiredError` with both ids; a pick from another kitchen → `NotebookNotFoundError`; a valid pick → it.
  - **Personal, none**: runs `ensure_default_notebook`, commits, returns the default with `created True`.
  - **Personal, two** (Ana's own and Ben's "Family", where Ana is a member): no pick → `NotebookChoiceRequiredError`; a pick of a kitchen notebook → `NotebookNotFoundError`; a valid pick → it.
- [X] T024 [US3] Implement `ResolveCaptureNotebookCommand(actor_user_id, kitchen_id=None, picked_notebook_id=None)`, `CaptureNotebook(notebook_id, created)` and `ResolveCaptureNotebookService` in `api/application/notebooks.py` so that T023 passes, in the order of research R6 (kitchen) and R7 (personal): authorize with `read_kitchen` through `AuthorizeKitchenAccessService`; load the kitchen with `get_kitchen_with_grant` and raise `KitchenArchivedError` if archived; read the candidates; `choose_capture_notebook`; on `None`, `ensure_kitchen_notebook` (T021b, R14) with the actor as owner, which locks, re-reads and creates; then `TransactionCommitter.commit()` when it created one. The personal path reuses `ensure_default_notebook` (T015) and commits when it created. Add no route (FR-013)
- [X] T025 [US3] Add integration tests for the capture step to `api/tests/test_notebook_integration.py`, calling the service with real adapters on Compose sessions (SC-003, SC-009, spec US3):
  - **First capture in "My kitchen"**: creates "ana's (My kitchen) Notebook" owned by Ana, with no membership rows; a second call returns it with `created False`.
  - **Concurrency**: Ana and Ben racing the first capture in a kitchen with none, on two connections with a `threading.Barrier`, leave one notebook, and both calls return its id.
  - **Several notebooks**: `NotebookChoiceRequiredError`; a pick from another kitchen → `NotebookNotFoundError`; a valid pick → it.
  - **Non-member**: Carl gets `KitchenNotFoundError` and no rows.
  - **Archived kitchen**: `KitchenArchivedError` and no new rows, also when the kitchen has notebooks.
  - **Failed save**: after the step creates a notebook, the test rolls back the caller's session (as a failed save would); the notebook is still there.
  - **Discarded capture**: a kitchen where the step was never called has no notebook.
  - **Personal, none**: a person with no notebook gets their default notebook created and returned.
- [X] T026 [US3] Add a test to `api/tests/test_notebook_integration.py`: every app route under `/notebooks` is a GET and one of the four paths of the contract, so the capture step is not reachable (FR-013). It holds before and after US4 adds the other read routes

**Checkpoint**: User Stories 1–3 work; S-019 can call the capture step from its save.

---

## Phase 6: User Story 4 - People and kitchen members read the notebooks they may see (Priority: P1)

**Goal**: `GET /notebooks`, `GET /notebooks/{notebook_id}` and `GET /notebooks/kitchens/{kitchen_id}` answer with the caller's access, and anyone without access gets the 404 for a missing resource.

**Independent Test**: Give Ana a default notebook and make her and Ben members of "Home", which has one notebook. Read Ana's list, each notebook, and Home's list as Ana, Ben and Carl, and check what each one sees.

- [X] T027 [US4] Add tests for `ListMyNotebooksService`, `GetNotebookService` and `ListKitchenNotebooksService` to `api/tests/test_notebooks_application.py`, first, and check that they fail (spec US4):
  - **My list**: only personal notebooks with a membership, `access` `"owner"` or `"member"`, oldest first, `is_default` only on the default; never a kitchen notebook; creates nothing.
  - **Get by id**: a personal notebook for its owner and members; a kitchen notebook with `access "kitchen_member"`, `owner_alias` the stored owner's alias (the kitchen owner's when none is stored) and `kitchen_id` set for a member of its kitchen; `NotebookNotFoundError` for a personal notebook whose owner shares a kitchen with the caller, for a kitchen notebook of another kitchen, and for a missing id.
  - **Kitchen list**: the first-open cases are in T021a. Here: lists only that kitchen's notebooks, with `access "kitchen_member"` for a member, and still lists them for an archived kitchen.
- [X] T028 [US4] Implement `ListMyNotebooksService` and `GetNotebookService` in `api/application/notebooks.py` so that T027 passes, building every answer with `notebook_view` (T011). `ListKitchenNotebooksService` is from T021b
- [X] T029 [US4] Add the routes to `api/api/routes/notebooks.py`:
  - `GET /notebooks` → `NotebooksResponse`;
  - `GET /notebooks/kitchens/{kitchen_id}` → `NotebooksResponse` (it creates the first notebook of a kitchen that has none, T021b), 404 `kitchen_not_found`;
  - `GET /notebooks/{notebook_id}` → `NotebookResponse`, 404 `notebook_not_found`.

  Declare the static segments (`/notebooks/default`, `/notebooks/kitchens/...`) before `/notebooks/{notebook_id}`.
- [X] T030 [US4] Add the read-route integration tests to `api/tests/test_notebook_integration.py` (spec US4 scenarios 1–8, US1 scenario 6, SC-004 to SC-006). Set the scene through the services and direct membership inserts:
  - **Ana's list**: her default with `access "owner"` and Ben's "Family" with `access "member"`, oldest first.
  - **Home's list**: Ana and Ben both see "ana's (Home) Notebook" with `kind "kitchen"` and `access "kitchen_member"`, and by id; it is never in `GET /notebooks`, and Ana's personal notebooks are never in Home's list.
  - **Notebook 404s**: Ben gets 404 for Ana's default although they share "Home"; Carl gets the same body for a Home notebook and for a random UUID.
  - **Kitchen 404**: Carl gets 404 `kitchen_not_found` for Home's list, with the same body as for a missing kitchen.
  - **Archived empty kitchen**: an archived kitchen with no notebook lists `{"notebooks": []}` and creates no row.
  - **Leaving**: after Ben's `kitchen_memberships` row for "Home" is deleted, his next reads of Home's list and of its notebook by id get the 404s, and the notebook row is unchanged.
- [X] T031 [P] [US4] Update the BFF routes and their test:
  - **New routes**: `ui/app/api/notebooks/route.ts` (GET `/notebooks`) and `ui/app/api/notebooks/[notebookId]/route.ts` (GET `/notebooks/{notebookId}`), with the pattern of `kitchens/[kitchenId]/route.ts`, which is kept as is.
  - **Removed**: `ui/app/api/notebooks/members/`.
  - **`ui/app/api/notebooks.bff.test.ts`**: each of the four routes forwards to the right api path with the cookie and passes a 404 through; remove the member-route cases (FR-021).

**Checkpoint**: All P1 stories work on their own.

---

## Phase 7: User Story 5 - The upgrade keeps existing data working (Priority: P2)

**Goal**: Revision `0003_personal_kitchen_notebooks` upgrades, downgrades and upgrades again on released data, without changing users or kitchens.

**Independent Test**: quickstart.md §2.

- [X] T032 [US5] Run `specs/055-notebooks/quickstart.md` §2 on a scratch database at `0002` with invented users and kitchens: `upgrade head`, check that the three tables are empty, `users.default_notebook_id` is null for everyone and users and kitchens are unchanged; `downgrade 0002_pgvector_kitchen_lang`, check the tables and column are gone; `upgrade head` again. Then check that an existing user's first `GET /notebooks/default` works and an existing kitchen's first `GET /notebooks/kitchens/{id}` creates its notebook (spec US5). Record the result in `dev/memory/` with `dev/skills/save_to_memory.md` (SC-010)

---

## Phase 7b: Remove the per-member kitchen hide (FR-024)

**Goal**: Archive is the only way to put a kitchen away. Hide, added in S-009 at bootstrap (`7722f27`), is removed end to end.

**Independent Test**: `POST /kitchens/{id}/hide` and `/unhide` return 404 (no route); a non-owner member's kitchen list shows a kitchen as archived only when `kitchens.is_archived` is true; `kitchen_memberships` has no `is_hidden` column at head and gets it back (all `false`) on downgrade.

- [X] T041 [P] Write failing tests first: in `api/tests/test_kitchens_integration.py` replace the hide/unhide cases with (a) the two routes are gone (404/405) and (b) `kitchens_for_user(archived=True)` for a non-owner member follows `kitchens.is_archived` alone; delete the hide cases in `api/tests/test_kitchens_domain.py`; in `ui/app/kitchens/KitchensPanel.test.tsx` replace the hide cases with "no Hide control is shown"
- [X] T042 Remove hide from the api: `HideKitchenCommand`, `UnhideKitchenCommand`, `HideKitchenService`, `UnhideKitchenService`, the guard raising `CannotHideOwnedKitchenError` and the port methods `hide_kitchen_for_member` / `unhide_kitchen_for_member` in `api/application/kitchens.py` (update its module docstring); `CannotHideOwnedKitchenError` in `api/domain/errors.py`; the two routes and their imports in `api/api/routes/kitchens.py` (update its docstring); the two repository methods in `api/adapters/persistence/repositories.py`, and replace the `effective_archived` `case(...)` in `kitchens_for_user` with `KitchenModel.is_archived` (drop the comment that explains the OR); `KitchenMembershipModel.is_hidden` in `api/adapters/persistence/models.py`
- [X] T043 Add revision `api/adapters/persistence/migrations/versions/0004_drop_kitchen_hide.py` (down revision `0003_personal_kitchen_notebooks`): upgrade drops `kitchen_memberships.is_hidden`; downgrade adds it back `NOT NULL DEFAULT false`. Extend T032's run to cover `0004` (upgrade, downgrade to `0002`, upgrade again)
- [X] T044 [P] Remove hide from the ui: delete `ui/app/api/kitchens/[kitchenId]/hide/` and `ui/app/api/kitchens/[kitchenId]/unhide/` (routes and tests), `hideKitchen` / `unhideKitchen` in `ui/app/kitchens/kitchensClient.ts`, and `onHide`, the unhide handler and their buttons and imports in `ui/app/kitchens/KitchensPanel.tsx`
- [X] T045 [P] Update the docs: S-009's title and `notes` in `dev/docs/backlog.yaml` ("hide removed by S-055, 2026-10-23, archive covers it"); add a dated "superseded: hide removed (S-055 FR-024)" note to the hide sections of `specs/001-finance-dashboard-reuse/contracts/kitchen-membership-api.md` and `specs/001-finance-dashboard-reuse/data-model.md`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T033 [P] Search `api/` and `ui/` for leftovers of the replaced models: `InvalidNotebookOwnerError`, `IngredientCatalogReader`, `GetKitchenNotebookService`, `GetMemberNotebookService`, `KitchenNotebookResponse`, `MemberNotebookResponse`, `notebooks/members`, `NotebookModel.user_id`, `0003_notebooks_ingredients`, `notebook_kitchen`, `kitchen_capture_notebook_name`, `"reader"`, `is_hidden`, `hide_kitchen`, `unhide`, `HideKitchen`, `CannotHideOwnedKitchenError`, `cannot_hide_owned_kitchen`, `onHide`. None may remain (git history and `specs/` excepted)
- [X] T034 Run `cd api && uv run ruff check .` and fix every finding in the touched files under `api/domain/`, `api/application/`, `api/adapters/persistence/`, `api/api/` and `api/tests/`
- [X] T035 Run the checks and report the pass counts:
  - **api suite in Compose with the dev overlay**: `docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.test.yml run --rm --build api`. The base file alone hangs (`dev/memory/221026.md`).
  - **ui**: `cd ui && npm test && npm run lint && npm run typecheck`.
- [ ] T036 Walk `specs/055-notebooks/quickstart.md` §3, §5 and §6 by hand on the running stack (`./scripts/compose-up.sh -d`) with two invented users (Ana and Ben). Covers the routes, the recreated default and kitchen deletion
- [X] T037 [P] Add a dated re-sync note to `specs/016-capture-recipe-text/spec.md` and `specs/016-capture-recipe-text/plan.md` (plan "Build order" step 8): FR-001a's "also saved into the member's notebook" and "a kitchen's shared notebook" are superseded; a capture outside a kitchen targets a picked personal notebook (the picker preselects the default) and a capture in a kitchen one of its notebooks; the draft reads `IngredientCatalog.names_for_notebook`, or `names_for_person` in a kitchen with no notebook yet
- [X] T038 [P] Extend the S-019 `notes` in `dev/docs/backlog.yaml`: its save calls `ResolveCaptureNotebookService` before writing anything and maps `KitchenArchivedError`, `NotebookChoiceRequiredError`, `NotebookNotFoundError` and `KitchenNotFoundError` to HTTP (contract, research R13)
- [X] T039 Regenerate the requirements-quality checklist `specs/055-notebooks/checklists/requirements-quality.md` for the snapshot-model spec with `/speckit-checklist` (it replaces the kitchen-link checklist of commit `3ff1601`)
- [X] T040 Update the S-055 `verification` in `dev/docs/backlog.yaml` with the new pass counts and "reworked to the snapshot model", and append a memory line with `dev/skills/save_to_memory.md`. Do not push or deploy without review (AGENTS.md)
- [X] T046 Close SC-011 in `api/tests/test_notebook_integration.py`, reusing T026 (FR-013) and the BFF cases of T018 and T031 (FR-021) rather than repeating them:
  - **Catalog readers (FR-018)**: `names_for_notebook` returns one notebook's names, sorted, and none from another notebook; `names_for_person` returns the distinct names of the personal notebooks the person owns or is a member of, and none from their kitchen notebooks.
  - **Writes nothing else (FR-022)**: count the rows of the recipe, step, category, source, invite and cart tables that exist, and of `notebook_membership` for kitchen notebooks, before and after the default request, a kitchen creation, a first open and both capture-step paths; every count is unchanged, and `source_notebook_id` stays null on every notebook.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001)**: first, on any machine with an old dev database.
- **Foundational (T002–T013)**: blocks every story. Inside the phase:
  - T002 → T003 → T004.
  - T005 → T006.
  - T004 and T005 → T007 → T008 and T009 (parallel).
  - T010 and T011 after T007.
  - T012 after T007.
  - T013 after T008 and T009.
- **US1 (T014–T018)**: after Foundational.
- **US2 (T019–T022, T021a, T021b)**: after Foundational; commit with Foundational or right after it (Foundational checkpoint).
- **US3 (T023–T026)**: after US1 and US2, because T024 reuses `ensure_default_notebook` (T015) and `ensure_kitchen_notebook` (T021b).
- **US4 (T027–T031)**: after Foundational. Its tests set notebooks up through the repository and direct inserts, and use the kitchen service (US2) for Home's notebook.
- **US5 (T032)**: after T006 and T043. It is a run, not code.
- **Remove hide (T041–T045)**: after Foundational (T043 needs the `0003` revision from T006). T041 before T042 and T044; T042 → T043. Independent of US1–US4.
- **Polish (T033–T040, T046)**: after the stories they check and T041–T045. T046 after T026, T030 and T031. T037 and T038 are docs and can start any time after Foundational.

### User story dependencies

- **US1 (P1)**: Foundational only.
- **US2 (P1)**: Foundational only.
- **US3 (P1)**: US1 (shared default creation) and US2 (`ensure_kitchen_notebook`).
- **US4 (P1)**: Foundational; US2 for the integration scenario that creates "Home" through the API.
- **US5 (P2)**: T006 only.

### Within each story

Tests first (they must fail), then the service, then the route, then the integration tests, then the BFF route.

### Parallel opportunities

- **Foundational**: T002 alongside T005 (domain tests vs models); T008 alongside T009 (two adapter files).
- **Stories**: US1 and US2 side by side after Foundational (`application/notebooks.py` vs `application/kitchens.py`). US4 alongside US3 once US1 is in, merging carefully in `api/application/notebooks.py` and `api/api/routes/notebooks.py`.
- **BFF routes**: T018 and T031 (ui) alongside the api work of their story.
- **Docs**: T033, T037 and T038 alongside each other.

## Parallel Example: Foundational

```text
Task: "T002 [P] Rewrite api/tests/test_notebook_domain.py (tests first)"
Task: "T005 [P] Rework models in api/adapters/persistence/models.py"
# after T007
Task: "T008 [P] SqlAlchemyNotebookRepository and committer in api/adapters/persistence/notebooks.py"
Task: "T009 [P] SqlAlchemyIngredientCatalog in api/adapters/persistence/ingredient_catalog.py"
```

## Parallel Example: User Stories 1 and 2

```text
Task: "T014 [US1] GetDefaultNotebookService tests in api/tests/test_notebooks_application.py"
Task: "T019 [US2] Kitchen-creation tests in api/tests/test_kitchens_domain.py"
Task: "T018 [P] [US1] BFF default route in ui/app/api/notebooks/default/route.ts"
```

## Implementation Strategy

- **MVP**: Phases 1–4 (Setup, Foundational, US1, US2). The Notebook tab shows the person's default notebook, and a kitchen gets its notebook when a member first opens it. US2 belongs in the MVP because kitchen creation has to be reverted with the Foundational phase.
- **Next**: US3. S-019's save needs it, and, with the first open of a kitchen's notebooks, it is how signup's "My kitchen" and older kitchens get one.
- **Then**: US4, which the Notebook tabs and S-016's notebook picker need, and US5, the migration check before merge.
- **Commits**: one per phase or smaller (domain, schema, adapters, each story, BFF, docs). The api suite must pass after each commit from the US2 checkpoint on.
- **After merge**: S-016 re-syncs with T037, S-019 builds on the capture step, and S-056, S-034, S-057 and S-058 add members, snapshots, ownership passing and notebook management.
