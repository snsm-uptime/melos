# Research: Notebooks That Belong to People and Are Linked to Kitchens

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-23

The Technical Context had no NEEDS CLARIFICATION items: the spec's three questions were answered on 2026-10-23. This file records the design decisions, how they change the code built for the 2026-10-22 model on `s55-notebooks`, and the alternatives that were rejected.

## R1. Who a notebook belongs to: a membership table, not an owner column

- **Decision**: `notebook(id, name?, kitchen_id?, created_at)` plus `notebook_membership(notebook_id, user_id, role, created_at)`, with `pk(notebook_id, user_id)`, `role in ('owner', 'member')` and a partial unique index allowing one `owner` row per notebook. `notebook.user_id` and the `ck_notebook_one_owner` check are removed.
- **Rationale**: PRD §1.6. Owner and members are the same kind of fact with a different role, so "the notebooks I own or am a member of" is one query (FR-011), and S-056 adds members without a schema change. The partial unique index enforces "at most one owner" in the database. The application creates the owner row in the same transaction as the notebook, so every notebook created here has exactly one owner (FR-002).
- **Alternatives considered**: keep `notebook.user_id` as the owner plus a members table (two places to check access, and ownership passing in S-057 would update both); a deferred constraint trigger for "at least one owner" (no trigger exists in the schema today; account deletion in S-057 briefly breaks the rule on purpose).

## R2. The kitchen notebook in the schema

- **Decision**: `notebook.kitchen_id` is nullable, unique, and `ON DELETE CASCADE`. A check `(kitchen_id IS NULL) = (name IS NOT NULL)` says a kitchen notebook has no name and every other notebook has one. Nothing in S-055 inserts a kitchen notebook. The read model treats the members of a kitchen notebook's kitchen as its members (access "member").
- **Rationale**: PRD §1.6 and FR-001. S-057 creates the kitchen notebook, and its members are always the kitchen's members, so deriving access from kitchen membership is correct before and after S-057. S-057 decides whether it also stores those rows for the person's catalog (PRD flow H).
- **Alternatives considered**: leave `kitchen_id` to S-057 (that would add a second migration on the same table a week later); store the kitchen's name on its notebook (two copies that drift).

## R3. Kitchen links

- **Decision**: `notebook_kitchen(notebook_id, kitchen_id, linked_by, created_at)` with `pk(notebook_id, kitchen_id)` and an index on `kitchen_id`. Both ids `ON DELETE CASCADE`; `linked_by` is a nullable foreign key to `users` with `ON DELETE SET NULL`. Inserts use `ON CONFLICT DO NOTHING`.
- **Rationale**: PRD §1.6 and FR-003, FR-006. Deleting a kitchen deletes its links but not the linked notebooks (SC-007). `linked_by` must not block account deletion, and the link itself ends through S-057 when that happens.
- **Alternatives considered**: `linked_by` not null with `CASCADE` (deleting a user would silently drop links before S-057 can keep copies).

## R4. Finding the signup kitchen without changing signup

- **Decision**: The signup kitchen is the oldest kitchen whose `owner_id` is the person (`ORDER BY created_at, id LIMIT 1`). It counts only while the person is still a member of it.
- **Rationale**: Signup creates "My kitchen" with `owner_id` set to the new user, in the user's own transaction, before any other kitchen can exist (`application/signup.py`). `kitchens.owner_id` never changes in the current code, which has no ownership transfer. So the rule is exact, with no flag column and no change to signup (FR-005, FR-020).
- **Alternatives considered**: match the name "My kitchen" (the kitchen can be renamed); add `kitchens.is_personal` and set it at signup (changes the auth signup path, constitution §1); the person's oldest membership (an invitee who signs up through a link may join the inviting kitchen in the same flow).

## R5. The default notebook (FR-007, FR-020)

- **Decision**: `GET /notebooks/default`. If `default_notebook_id` points at a notebook, return it. Otherwise lock the user row (`SELECT … FOR UPDATE`) and re-check. Then, in one transaction: insert the notebook named "{alias}'s Notebook", insert the owner membership, seed the catalog (R7), link the notebook to the signup kitchen if the person is still a member (R4), and set `default_notebook_id`. The answer is always 200 with the same body.
- **Rationale**: This keeps the locking pattern built and tested for the 2026-10-22 model (`GetDefaultNotebookService`, T002 note): the lock is taken before the insert, so a losing call creates nothing (SC-001). The person id comes from the session, so the path needs no `user_id`.
- **Alternatives considered**: keep `/notebooks/members/{user_id}` (the id can only ever be the caller, so it adds an always-404 branch and nothing else); link the default notebook again on every read (the link is made only at creation, per the spec's edge cases).

## R6. The capture notebook step (FR-008, FR-009, FR-020, FR-021)

- **Decision**: `ResolveCaptureNotebookService` in `application/notebooks.py`, with command `(actor_user_id, kitchen_id, picked_notebook_id?)`. No route calls it. S-016's save runs it before saving the recipe; a notebook it creates is committed on its own and kept if the save then fails (2026-10-23). The steps:
  1. Authorize with `read_kitchen`: a missing kitchen and a non-member get `KitchenNotFoundError` (404). An archived kitchen gets `KitchenArchivedError` before anything else is read: no capture happens in an archived kitchen (2026-10-23).
  2. Lock the caller's `kitchen_memberships` row for that kitchen (`FOR UPDATE`).
  3. Load the candidates: notebooks linked to the kitchen where the caller is owner or member, never the kitchen notebook.
  4. The pure rule `choose_capture_notebook(candidates, picked)` in `domain/notebook.py` decides:
     - one candidate and no pick → use it;
     - a pick → it must be a candidate, otherwise `NotebookNotFoundError`;
     - several candidates and no pick → `NotebookChoiceRequiredError`, carrying the candidate ids;
     - none → create.
  5. To create:
     - it is the caller's signup kitchen and they have no default notebook → run the default-notebook creation (R5), which links it to this kitchen, and use that notebook;
     - otherwise → create "{alias}'s Notebook ({kitchen name})" with its owner membership, seeded catalog and a link to the kitchen made by the caller.
- **Rationale**:
  - Locking the membership row serializes one member's first captures in one kitchen (SC-002) without a new unique constraint. A member may own several notebooks linked to the same kitchen, so a constraint would be wrong.
  - The lock order is always membership row, then user row. The default route takes only the user row, so the two cannot deadlock.
  - Putting the rule in `domain/` makes the four cases plain unit tests.
  - Nothing runs before the save, so a discarded capture creates nothing (SC-008).
- **Alternatives considered**: a `POST` route that S-016's page calls first (rejected by clarify Q1: it would create notebooks for discarded captures); an advisory lock keyed on `(kitchen, user)` (same effect, less visible); creating "{alias}'s Notebook (My kitchen)" even when the default notebook is missing (it gives a solo person two notebooks, which is what clarify Q3 rejected).

## R7. Catalogs: seeding and reading (FR-010, FR-014)

- **Decision**: The `ingredient` table is kept as built: `(id, notebook_id, name, created_at)` with `unique(notebook_id, name)`. `IngredientCatalog` (the port, renamed from `IngredientCatalogReader`) has three methods:
  - `names_for_notebook(notebook_id)`, as built;
  - `names_for_person(user_id)`: the distinct names in every notebook the person has a membership in, plus the kitchen notebooks of their kitchens;
  - `seed_from_person(notebook_id, user_id)`: one `INSERT … SELECT DISTINCT … ON CONFLICT DO NOTHING`.
  A new notebook is seeded before its owner membership is inserted, so its own (empty) catalog is not part of the source.
- **Rationale**: PRD flow H ("its catalog starts as the owner's catalog; a person's catalog is every name in the notebooks they own or are a member of"). Names are already normalized and unique per notebook, so a set union needs no matching. The S-017 matcher is only needed when catalogs from different people meet (S-056).
- **Alternatives considered**: start new catalogs empty (against flow H, and the first capture in a new kitchen would propose every ingredient as new); run the S-017 matcher when seeding (it does not exist yet, and one person's catalogs need no normalization against each other).

## R8. Access and the read model (FR-011 to FR-013)

- **Decision**:
  - **Repository facts**: the repository returns facts per notebook: the caller's role (if any), whether the caller can reach it through a kitchen (a link to a kitchen they belong to, or the kitchen notebook of one), the owner's alias, and whether it is the caller's default.
  - **Access rule**: the pure `notebook_access(role, via_kitchen, is_kitchen_notebook)` in `domain/notebook.py` returns `owner`, `member`, `reader` or `None`, strongest first. `None` → `NotebookNotFoundError` (404).
  - **Kitchen list**: the application authorizes the kitchen first (`read_kitchen`, 404), then lists the linked notebooks plus the kitchen notebook with each one's access.
  - **Order and visibility**: every list is ordered by `notebook.created_at, id`. Hidden and archived kitchen memberships still count as membership, as in `read_kitchen`.
- **Rationale**:
  - Constitution §3 and AGENTS.md: access is decided in `application/` and `domain/`, not in SQL.
  - Facts are cheap to fetch with joins in one query per route.
  - The same 404 body for "no access" and "does not exist" keeps SC-003.
- **Alternatives considered**: filter by access in SQL and return only visible rows (the rule moves into the adapter, and integration tests become the only tests of it); one combined "everything I can read" list (FR-011 says kitchen-only notebooks stay out of the person's own list).

## R9. Routes and wire shape

- **Decision**: These routes all sit in the `notebooks` router behind `require_user_alias`:
  - `GET /notebooks`
  - `GET /notebooks/default`
  - `GET /notebooks/{notebook_id}`
  - `GET /notebooks/kitchens/{kitchen_id}`

  Each notebook in an answer is `{ id, name, kind: "personal" | "kitchen", access: "owner" | "member" | "reader", owner_alias, is_default }`, and the lists are wrapped as `{ "notebooks": [...] }`, like `{ "kitchens": [...] }`. The routes `/notebooks/members/{user_id}[/{notebook_id}]` are removed. The ui BFF routes follow the same paths under `/api/notebooks`. See [contracts/notebooks-api.md](./contracts/notebooks-api.md).
- **Rationale**:
  - One shape for every answer means S-016 and the Notebook tabs use one type.
  - `/notebooks/kitchens/{kitchen_id}` keeps the BFF folder that already exists.
  - `default` and `kitchens` are static segments, declared before `/{notebook_id}` (FastAPI) and preferred over `[notebookId]` (Next.js).
  - Nothing reads these routes yet (no ui page uses them), so the old paths can go without a compatibility period.
- **Alternatives considered**: `GET /kitchens/{kitchen_id}/notebooks` in the kitchens router (cleaner REST, but it splits the notebook rules across two routers and moves the BFF folder); separate response types per route (more code for the same fields).

## R10. The 2026-10-22 code and migration

- **Decision**:
  - **Migration**: replace `0003_notebooks_ingredients` with a new revision `0003_notebooks_people` (down revision `0002_pgvector_kitchen_lang`). It creates `notebook`, `notebook_membership`, `notebook_kitchen` and `ingredient`, adds `users.default_notebook_id`, and backfills nothing.
  - **Kitchen creation**: remove the notebook insert from `CreateOwnedKitchenService` and its `NotebookRepository` dependency.
  - **Services**: remove `GetKitchenNotebookService` and `GetMemberNotebookService`.
  - **Tests**: rework the tests in place.
  - **Dev databases**: a dev database already at the old `0003` must be downgraded to `0002` with the old code, or recreated, before the new code runs (quickstart §1).
- **Rationale**: The branch is not merged, and production is at `0002` (backlog S-055 verification note). Stacking a `0004` that undoes `0003` would ship a schema nobody uses. With lazy creation, the default notebook covers existing users (spec Assumptions), and kitchens get notebooks only through captures and links.
- **Alternatives considered**: keep the revision id and rewrite the file (a dev database at the old `0003` would believe it is current while it has the old schema); a `0004` migration from the old `0003` (dead intermediate schema in history).

## R11. Errors

- **Decision**:
  - **Kept**: `NotebookNotFoundError` (404 `notebook_not_found`) and `KitchenNotFoundError` (404 `kitchen_not_found`).
  - **Renamed**: `InvalidNotebookOwnerError` becomes `InvalidNotebookError`, raised by the `Notebook` dataclass when the name and kitchen rule (R2) is broken.
  - **New, raised only by the capture step**: `NotebookChoiceRequiredError` (carries the candidate ids) and `KitchenArchivedError`. S-016 maps both to HTTP when its save route lands; this feature adds no HTTP mapping for them.
- **Rationale**: FR-021 keeps the capture step off the routes, so its errors have no wire form yet. Naming them now gives S-016 a stable contract.
- **Alternatives considered**: return a union result instead of raising (the codebase signals use-case failures with domain errors everywhere else).
