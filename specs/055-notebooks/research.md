# Research: Personal and Kitchen Notebooks

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-24 (snapshot model; revised the same day, see below)

The Technical Context has no NEEDS CLARIFICATION items: every open point was decided on 2026-10-23 (`dev/memory/231026.md`, 13:52 to 14:08). This file records the design decisions for the snapshot model, how they change the code built for the 2026-10-22 model on `s55-notebooks`, and the alternatives that were rejected. It replaces the research for the kitchen-link model (R1 to R11 of commit `3ff1601`).

Revised 2026-10-24 (owner decisions on the checklist items): a kitchen notebook stores its owner, the member who created it (R1, R2, R10); a kitchen's first notebook is created on its first open or its first capture, not with the kitchen (R5, R14); the personal catalog keeps owned and joined notebooks (R9).

## R1. One `notebook` table for both kinds

- **Decision**: `notebook(id, name, kitchen_id?, source_notebook_id?, created_at)`.
  - `name` is `NOT NULL`, with a check that it is not blank. Kitchen notebooks now have names ("{alias}'s ({kitchen name}) Notebook").
  - `kitchen_id` is nullable, indexed, **not unique**, `ON DELETE CASCADE`. Set: a kitchen notebook. Null: a personal notebook.
  - `owner_user_id`: nullable, FK `users.id` `ON DELETE SET NULL`, indexed. It stores the owner of a kitchen notebook only, a check keeps it off personal notebooks, and personal notebooks keep their owner row (R2).
  - `notebook.user_id`, its index and `ck_notebook_one_owner` are removed.
- **Rationale**: PRD §1.6. A kitchen notebook has no membership rows (FR-002), but it needs one owner who can change: the member who created it, passed to the kitchen's owner when they leave. The owner is therefore a column, and S-057 passes it with one `UPDATE`. A kitchen can have several notebooks (made by first open, by capture, by snapshot, by S-058), so the 2026-10-22 `unique(kitchen_id)` goes. Deleting a kitchen deletes its notebooks through the cascade (FR-006, SC-008). One table keeps every recipe pointing at `notebook_id`, as AGENTS.md requires.
- **Alternatives considered**: two tables, `personal_notebook` and `kitchen_notebook` (recipes and ingredients would need two foreign keys or a polymorphic id); keep `name` nullable and show the kitchen's name (the 2026-10-22 rule, replaced by named kitchen notebooks); show the kitchen's owner as the notebook's owner with nothing stored (the 2026-10-23 model, withdrawn on 2026-10-24: the notebook belongs to the member who created it, and passes to the kitchen's owner only when they leave).

## R2. Personal notebook membership

- **Decision**: `notebook_membership(notebook_id, user_id, role, created_at)`, `pk(notebook_id, user_id)`, `role in ('owner', 'member')`, index on `user_id`, and a partial unique index `uq_notebook_one_owner` on `(notebook_id) WHERE role = 'owner'`. Both foreign keys `ON DELETE CASCADE`.
  - "Exactly one owner" (FR-002) is kept by the application: a personal notebook and its owner row are inserted in the same transaction, and the index stops a second owner.
  - "A kitchen notebook has no memberships" is an application rule: only the default-notebook path writes membership rows, and it writes them for a personal notebook it has just created. Tests check that kitchen creation, the first open (R14) and the capture step write none.
- **Rationale**: PRD §1.6 and flow H. Owner and members are one fact with two roles, so "the notebooks I own or belong to" is one query (FR-014), and S-056 adds members with no schema change. `created_at` orders "longest-standing member" for S-057.
- **Alternatives considered**: a trigger or a composite foreign key that checks the notebook's kind (no trigger exists in the schema; the only writer is this feature's application code); an owner column for personal notebooks too (their owner would be stored twice, in the column and in the owner row, and S-057 would update both).

## R3. The origin label column

- **Decision**: `notebook.source_notebook_id`, nullable, foreign key to `notebook.id` `ON DELETE SET NULL`, indexed. Two checks: `source_notebook_id IS NULL OR kitchen_id IS NOT NULL` (only a kitchen notebook has an origin), and `source_notebook_id <> id`. Nothing in S-055 sets it, and no answer shows it.
- **Rationale**: FR-003 and PRD §1.6. Adding the column now saves S-034 a migration on the same table, and the cascade rule ("cleared if the original is deleted") is part of the deletion behavior this feature tests. Leaving it out of the answers lets S-034 decide what kitchen members may see about a personal notebook they cannot read (spec Assumptions). Adding a field later does not break the contract.
- **Alternatives considered**: add the column in S-034 (a second migration on `notebook` a few days later); show `source_notebook_id` now (S-034 has not decided what the label shows).

## R4. The default personal notebook (FR-007)

- **Decision**: `GET /notebooks/default`, served by `GetDefaultNotebookService`, kept from the 2026-10-22 code with these changes:
  - the person comes from the session (no `user_id` in the path);
  - creation inserts the personal notebook "{alias}'s Notebook", its owner membership and the catalog seed (R9), then sets `users.default_notebook_id`;
  - no kitchen link (old FR-020 is withdrawn).
  The lock stays: if the stored default points at a notebook, return it; otherwise lock the user row (`SELECT … FOR UPDATE`), re-check, and create. The answer is always 200 with the same body.
- **Rationale**: The lock pattern is built and tested (T002, 2026-10-22): the loser of a race waits on the lock and then finds the default set, so it creates nothing (SC-001). A GET that creates data on first use was accepted on 2026-10-22: it is idempotent, so a cross-site navigation can at most create the notebook the person would get on their next visit anyway.
- **Alternatives considered**: create the default at signup (changes the auth routes, constitution §1); `POST /notebooks/default` (the Notebook tab would need two calls, for no gain given the idempotence).

## R5. Kitchen creation makes no notebook (FR-008, FR-008a)

- **Decision**: `CreateOwnedKitchenService` goes back to its pre-S-055 form: it creates the kitchen and the creator's kitchen membership, and no notebook. The branch's additions go with it: the notebook repository argument, the notebook insert and the seed. The kitchen's first notebook is created by R14, on the first open or the first capture.
  - **Atomicity**: `get_db` commits once at the end of the request and rolls back on any exception, so the kitchen, its membership and its notebook are committed together or not at all (SC-002).
  - **Dev seed** (`api/scripts/seed_dev_user.py`): the branch's notebook wiring is reverted. No alias skip is needed, because kitchen creation names no notebook.
  - **Signup**: `create_user_with_personal_kitchen` and the invite signup path are not touched. "My kitchen" starts with no notebook (spec US2 scenario 4).
- **Rationale**: Owner decision of 2026-10-24 (checklist item 9, option C): the system creates the kitchen's notebook at the one moment it is first needed, the same for every kitchen however it was made. This replaces the 2026-10-23 13:52 decision that kitchen creation makes it. Signup stays unchanged (FR-005), so "My kitchen" gets its notebook on its first open or first capture like any other kitchen.
- **Alternatives considered**: keep the notebook made with the kitchen (the 2026-10-23 13:52 decision, replaced); create it at signup for "My kitchen" (option B of 2026-10-24, rejected: it changes the auth routes); create the kitchen notebook on the kitchen's first read without the lock (two members could make two notebooks); name it after the kitchen only (decided against on 2026-10-23, Appendix D).

## R6. The capture notebook step in a kitchen (FR-009, FR-010, FR-013)

- **Decision**: `ResolveCaptureNotebookService` in `application/notebooks.py`, command `(actor_user_id, kitchen_id?, picked_notebook_id?)`, result `CaptureNotebook(notebook_id, created)`. No route calls it; S-019's save calls it first. With `kitchen_id` set:
  1. Authorize with `AuthorizeKitchenAccessService` (`read_kitchen`): a missing kitchen and a non-member get `KitchenNotFoundError`.
  2. Load the kitchen (`get_kitchen_with_grant`). If it is archived, raise `KitchenArchivedError` before reading anything else (FR-010, spec 016 FR-033).
  3. Load the kitchen's notebook ids, oldest first, and apply the pure rule `choose_capture_notebook(candidates, picked)`:
     - none → create (any pick ignored);
     - one candidate → use it (any pick ignored);
     - several, a pick → it must be a candidate, otherwise `NotebookNotFoundError`;
     - several, no pick → `NotebookChoiceRequiredError(candidates)`.
  4. To create: `ensure_kitchen_notebook` (R14) with the capturing member as the owner, then commit (R8).
- **Rationale**:
  - Any two members can make the first capture at the same moment (spec US3 scenario 4), so the lock must cover the kitchen, not one member. `FOR NO KEY UPDATE` serializes the capture steps for one kitchen without blocking the `FOR KEY SHARE` locks that foreign-key inserts elsewhere take (a new membership, a cart row), and without blocking reads.
  - The fast path takes no lock: once a kitchen has a notebook, every capture is a plain read.
  - A pick is checked only when there are several candidates (clarified 2026-10-23, CHK018/CHK019): with none or one there is nothing to choose, so a stale pick is ignored rather than failing the save.
  - The rule lives in `domain/notebook.py`, so its cases are plain unit tests.
- **Alternatives considered**: lock the caller's `kitchen_memberships` row (the kitchen-link plan's choice; it serializes one member, not the kitchen, so Ana and Ben could create two notebooks); a partial unique index "one capture-made notebook per kitchen" (a kitchen may legitimately have several notebooks, and nothing marks which one a capture made); `FOR UPDATE` on the kitchen row (it also blocks foreign-key inserts from other requests until the step commits).

## R7. The capture notebook step outside a kitchen (FR-011)

- **Decision**: The same service with `kitchen_id` null. Candidates are the personal notebooks the person owns or is a member of, oldest first, and the same `choose_capture_notebook` rule applies. With none, it runs the default-notebook creation from R4 (user-row lock and re-check) and returns that notebook with `created = True`.
- **Rationale**: One entry point for S-019, one rule for both contexts. Reusing R4's creation means two simultaneous first personal captures still make one default notebook. The two paths take different locks (user row here, kitchen row in R6) and neither takes the other's, so they cannot deadlock.
- **Alternatives considered**: always use the default notebook when there is no pick (it hides the choice FR-011 asks for; preselecting the default is S-016's UI choice, spec Assumptions); a separate service per context (two copies of the pick rule).

## R8. Keeping a created notebook when the save fails (FR-009, CHK024)

- **Decision**: A new port, `TransactionCommitter` (`commit() -> None`), implemented by `SqlAlchemyTransactionCommitter(session)`. `ResolveCaptureNotebookService` calls it right after it creates a notebook, in both contexts. S-019's save calls the step before it writes anything, so the commit carries only the new notebook, its catalog seed and (personal case) the default pointer. The commit also releases the kitchen-row lock early.
- **Rationale**: The request session commits only at the end (`get_db`), so without an explicit commit a failed recipe save would roll the new notebook back. Putting the commit behind a port keeps `application/` free of SQLAlchemy (constitution §3) and makes the behavior testable with a fake that records the call.
- **Alternatives considered**: a second session for the creation (two connections per request, and the save would not see the new row until the first commit); a savepoint (`begin_nested`) (a savepoint is undone by the outer rollback, so it does not keep the notebook); let S-019's route commit (the rule "created means committed" would live outside this feature and could be forgotten).

## R9. Catalogs: seeding and reading (FR-012, FR-018)

- **Decision**: The `ingredient` table is kept as built: `(id, notebook_id, name, created_at)`, `unique(notebook_id, name)`, `ON DELETE CASCADE`. The port `IngredientCatalogReader` is renamed `IngredientCatalog` and gains two methods:
  - `names_for_notebook(notebook_id)`, as built;
  - `names_for_person(user_id)`: the distinct names in every **personal** notebook the person owns or is a member of (a join through `notebook_membership`, so kitchen notebooks are never included);
  - `seed_from_person(notebook_id, user_id)`: one `INSERT … SELECT DISTINCT … ON CONFLICT DO NOTHING` from the same set.
  The seed runs right after the new notebook is inserted, before any owner membership exists, so the new (empty) notebook is never part of its own source.
- **Rationale**: PRD §1.6 design choices: "a person's catalog is every name in the personal notebooks they belong to"; a personal notebook starts from its owner's catalog; a kitchen notebook from its creator's. Names are already normalized and unique per notebook, so a set union needs no matcher. The matcher (S-017) is needed only when people's catalogs meet (S-056).
- **Alternatives considered**: include the person's kitchen notebooks in their catalog (the kitchen-link plan's rule; the PRD now says personal notebooks only, and it would copy one household's names into another kitchen); start every catalog empty (against flow H, and a first capture would propose every ingredient as new); owned notebooks only (option 2 of 2026-10-24: changes the PRD wording first, and a joined notebook's names stop helping the owner's captures); seed from the creator's default notebook only (option 3 of 2026-10-24: two rules, one for the seed and one for matching).
- **Decision on 2026-10-24** (checklist item 5, option 1): the set stays "owned or joined". Consequence, accepted: a kitchen notebook can carry names from a personal notebook its owner joined but the kitchen cannot see. The names are ingredient names, not recipes.

## R10. Access and the read model (FR-014 to FR-017)

- **Decision**:
  - **Facts from the repository**: for each notebook, its fields, the caller's membership role (if any), the owner's alias (for a kitchen notebook, the stored owner's, or the kitchen owner's when none is stored, joined through `notebook.owner_user_id` and `kitchens.owner_id`), whether it is the caller's default, and, for a kitchen notebook, whether the caller is a member of its kitchen. One query per route, with left joins.
  - **Rule in the domain**: `notebook_access(kind, role, in_kitchen)` returns `owner`, `member`, `kitchen_member` or `None`. A personal notebook gives its role, and kitchen membership never counts. A kitchen notebook gives `kitchen_member` when the caller belongs to its kitchen, and a membership row never counts. `None` becomes `NotebookNotFoundError` (404).
  - **Lists**: "my notebooks" reads only personal notebooks with the caller's membership, and creates nothing (FR-014). "A kitchen's notebooks" first authorizes the kitchen (`read_kitchen`, 404), then reads the notebooks with that `kitchen_id`. Archived kitchens are still readable by their members. Every list is ordered by `created_at, id`.
  - **Leaving**: access is computed from the kitchen membership on every request, so a member who leaves or is removed loses access at once and nothing is copied (FR-017, SC-006, AC1.3). No code runs on leave.
- **Rationale**: Constitution §3 and AGENTS.md: access is decided in `application/` and `domain/`, not in SQL filters, and the 404 body is the same for "missing" and "no access" (SC-004). Keeping the two kinds' rules apart in one pure function is what SC-005 tests.
- **Alternatives considered**: filter by access in SQL (the rule moves into the adapter, and only integration tests cover it); one "everything I can read" list (FR-014 keeps kitchen notebooks out of the person's own list).

## R11. Routes and wire shape

- **Decision**: Four GET routes in the `notebooks` router, which already sits behind `require_user_alias`:
  - `GET /notebooks`: my personal notebooks;
  - `GET /notebooks/default`: my default notebook, created on first use;
  - `GET /notebooks/kitchens/{kitchen_id}`: a kitchen's notebooks, creating the first one for a kitchen that has none (R14);
  - `GET /notebooks/{notebook_id}`: one notebook.

  One shape for every notebook: `{ id, name, kind, access, owner_alias, kitchen_id, is_default }`, with `kind: "personal" | "kitchen"` and `access: "owner" | "member" | "kitchen_member"`. Lists are `{ "notebooks": [...] }`, like `{ "kitchens": [...] }`. The routes `/notebooks/members/{user_id}[/{notebook_id}]` and their BFF routes are removed. The ui BFF routes mirror the paths under `/api/notebooks`. See [contracts/notebooks-api.md](./contracts/notebooks-api.md).
- **Rationale**: One response type for S-016 and the Notebook tabs. `default` and `kitchens` are static segments: FastAPI matches routes in order, so they are declared before `/{notebook_id}` (otherwise "default" fails UUID validation with 422), and Next.js prefers static folders over `[notebookId]`. `/notebooks/kitchens/{kitchen_id}` keeps the BFF folder that exists. No ui page reads these routes yet, so the old paths go without a transition. `kitchen_member` is the wire value of the spec's "kitchen member" label.
- **Alternatives considered**: `GET /kitchens/{kitchen_id}/notebooks` in the kitchens router (cleaner REST, but notebook rules would be split across two routers and the BFF folder would move); a separate response type per kind (more code for nearly the same fields).

## R12. The migration and the 2026-10-22 code

- **Decision**:
  - **Migration**: delete `0003_notebooks_ingredients` and add `0003_personal_kitchen_notebooks` (down revision `0002_pgvector_kitchen_lang`). It creates `notebook` (with `owner_user_id`), `notebook_membership` and `ingredient`, adds `users.default_notebook_id`, and backfills nothing. The downgrade drops them in reverse order.
  - **Dev databases** that ran the old `0003` must run `alembic downgrade 0002_pgvector_kitchen_lang` with the old file still present (any commit up to `3ff1601`), or be recreated (quickstart prerequisites). Production is at `0002`.
  - **Code**: rework in place (plan "Reuse"). `GetKitchenNotebookService`, `GetMemberNotebookService`, their responses and the `members` routes go.
- **Rationale**: The branch is not merged and production is at `0002` (backlog S-055 verification note). A new revision id makes a dev database at the old `0003` fail loudly ("can't locate revision") instead of believing it is current. Without a backfill, existing users get their default notebook on first use and existing kitchens on their first open or first capture (FR-023, spec US5).
- **Alternatives considered**: keep the old revision id and rewrite the file (a dev database at the old `0003` would silently keep the old schema); a `0004` that reshapes the old `0003` (a dead intermediate schema in history); backfill a kitchen notebook per existing kitchen (it would need a creator alias, and the capture step already covers kitchens with none).

## R13. Errors

- **Decision**:
  - **Kept**: `NotebookNotFoundError` (404 `notebook_not_found`), `KitchenNotFoundError` (404 `kitchen_not_found`), `AliasRequiredError` (the existing alias guard).
  - **Renamed**: `InvalidNotebookOwnerError` becomes `InvalidNotebookError`, raised by the `Notebook` dataclass for a blank name, an origin on a personal notebook, or an origin equal to the notebook's own id.
  - **New**: `KitchenArchivedError` (code `kitchen_archived`, message "This kitchen is archived, so recipes can't be added.", from spec 016 FR-033) and `NotebookChoiceRequiredError` (code `notebook_choice_required`, carries the candidate ids). Only the capture step raises them, and it has no route, so this feature adds no HTTP mapping; S-019 maps them when its save route lands.
- **Rationale**: Naming the step's errors now gives S-019 a stable contract, and the archived message is already fixed by spec 016.
- **Alternatives considered**: return a result union from the step (every other use case signals failure with domain errors).

## R14. A kitchen's first notebook: the first open and the first capture (FR-008a, FR-009, FR-012)

- **Decision**: One helper in `application/notebooks.py`, `ensure_kitchen_notebook(kitchen, actor_user_id, alias) -> tuple[UUID, bool]` (id, created), used by two callers:
  1. `ListKitchenNotebooksService` (`GET /notebooks/kitchens/{kitchen_id}`), for a member. It authorizes with `read_kitchen` (404 for a missing kitchen and for a non-member). If the kitchen has notebooks, it lists them. If it has none and is archived, it lists nothing and creates nothing. If it has none and is not archived, it calls the helper with the caller as owner, then lists the result.
  2. `ResolveCaptureNotebookService` in a kitchen with none (R6 step 4). It then commits (R8).
- **The helper**, when the kitchen has none: `lock_kitchen`, read the kitchen's notebooks again, and if still none insert `Notebook(name=kitchen_notebook_name(alias, kitchen.name), kitchen_id, owner_user_id=actor_user_id)` and call `seed_from_person(notebook_id, actor_user_id)`. It returns `(id, True)`. If another request created one under the lock, it returns `(id, False)` and creates nothing.
- **No commit in the helper.** The list answer is committed by `get_db` with the response, as for every read that writes. The capture step commits explicitly (R8).
- **Rationale**: The lock is the one from R6, so simultaneous first opens and captures by any members leave one notebook (SC-003, US2 scenario 3). The owner is the member who made the first open or capture, which is what the owner decision of 2026-10-24 asks for (FR-002). Keeping one helper means the open rule and the capture rule cannot drift apart.
- **A GET writes here, as in R4.** It is idempotent (the lock and re-check), and the owner does not treat the creation as a risk (2026-10-24).
- **Alternatives considered**: a separate "open" route (the Notebook tab would make two calls, and the list is already its first call); creating without the lock (two members could make two notebooks); creating the notebook for every kitchen at kitchen creation (the 2026-10-23 13:52 decision, replaced, R5).
