# Implementation Plan: Personal and Kitchen Notebooks

**Branch**: `s55-notebooks` (spec folder `056-notebooks`) | **Date**: 2026-10-24 (snapshot model; stored kitchen-notebook owner; first-open creation) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/056-notebooks/spec.md` (re-specified 2026-10-23 for the snapshot model; replaces the kitchen-link plan of commit `3ff1601`)

**Note**: The branch holds code for the 2026-10-22 model, in which a notebook was owned by a kitchen or a member (commits `b17f5a5`, `187ff14`). This plan reworks that code in place. What carries over is listed under "Reuse".

## Summary

There are two kinds of notebook. A personal notebook belongs to people: one owner and any number of members, recorded in `notebook_membership`. A kitchen notebook has a `kitchen_id`, one stored owner (`owner_user_id`, the member who created it), no membership rows, and is readable by every member of that kitchen. This feature:

- adds the `notebook`, `notebook_membership` and `ingredient` tables and `users.default_notebook_id`, with `notebook.owner_user_id` for kitchen notebooks and room for a snapshot's origin label (`notebook.source_notebook_id`, unset until S-035);
- creates a person's default personal notebook on first use;
- gives a kitchen its named kitchen notebook the first time a member opens its notebooks or saves a first capture, not when the kitchen is made;
- adds the in-process capture notebook step that S-020's save calls, for a kitchen (use, pick, or create one) and outside a kitchen (use, pick, or create the default);
- exposes four read routes and their ui BFF routes: my notebooks, my default notebook, one notebook, and a kitchen's notebooks.

Technical approach:

- **Domain**: pure rules in `domain/notebook.py` (the `Notebook` invariants, names, the access rule, the capture choice).
- **Application**: services in `application/notebooks.py` over the `NotebookRepository`, `IngredientCatalog`, `UserDefaultNotebook`, `TransactionCommitter`, `PreferencesRepository` and `KitchenRepository` ports. `ensure_kitchen_notebook` creates a kitchen's first notebook for the first open and the first capture (R14). `CreateOwnedKitchenService` creates no notebook (R5).
- **Persistence**: SQLAlchemy adapters. A row lock on `users` serializes the first default notebook; a `FOR NO KEY UPDATE` lock on the `kitchens` row serializes the first capture in a kitchen.
- **Migration**: a fresh Alembic revision `0003_personal_kitchen_notebooks` replaces the unmerged `0003_notebooks_ingredients`, with no backfill.
- **Unchanged**: signup and the auth routes.

## Technical Context

**Language/Version**: Python 3.12 (api, uv); TypeScript with Next.js 16 and React 19 (ui BFF routes only)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic (api); Next.js route handlers (ui). No new library.

**Storage**: PostgreSQL 16 (pgvector image). Three new tables (`notebook`, `notebook_membership`, `ingredient`) and two new columns (`users.default_notebook_id`, `notebook.owner_user_id`). See [data-model.md](./data-model.md).

**Testing**: pytest (domain pure, application against fake ports, integration in the Compose test overlay against Postgres); vitest for the BFF routes

**Target Platform**: Linux containers via Docker Compose (`db`, `api`, `ui`, `mcp`)

**Project Type**: Web application (hexagonal api + Next.js BFF ui)

**Performance Goals**: One query per read route (joins on indexed keys). Creating a notebook adds at most one row lock and four statements (notebook, catalog seed, owner membership, default pointer). No target beyond the app's normal page loads.

**Constraints**:

- Auth layer and signup unchanged (FR-005, constitution §1).
- A caller with no access gets the same 404 as for something that does not exist, never 403 (constitution §3, SC-004).
- No env var added.
- The capture step has no route (FR-013).

**Scale/Scope**: A household: a few people, kitchens and notebooks each.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| §1 Simplicity and reuse: auth layer immutable | Signup, sign-in, alias claim and session code unchanged. "My kitchen" gets its notebook from its first open or first capture, not from signup. The only change to the user is the nullable `default_notebook_id`, approved 2026-10-22 (spec Clarifications). | Pass (approved exception, Complexity Tracking) |
| §1 Four services, external calls through ports | No service added. No external call. | Pass |
| §2 Stack stability | No library, no env var. Schema change through Alembic. | Pass |
| §3 Hexagonal | `domain/notebook.py` imports only `domain.errors`. Access is decided by `notebook_access` (domain) in `application/notebooks.py`; repositories return facts (research R10). Kitchen access goes through `AuthorizeKitchenAccessService` (`read_kitchen`). The early commit goes through the `TransactionCommitter` port (R8). | Pass |
| §3 404 for non-members | `notebook_not_found` and `kitchen_not_found` bodies are identical for "missing" and "no access" (contract). | Pass |
| §4 Security and privacy | A personal notebook is visible only to its owner and members, a kitchen notebook only to its kitchen's members (AGENTS.md). The origin label is not shown until S-035 decides what kitchen members may see. Test data is invented. | Pass |
| §5 No AI shortcuts | No AI call. Nothing is saved from a draft here. | Pass (n/a) |
| §6 Testing layers | Domain (pure), application (fakes), integration (Compose, including concurrency and cascades), vitest BFF. | Pass |
| §8 Git discipline | Migration with a working downgrade. One concern per commit. Not pushed without review. | Pass |
| §9 Scope | S-056 is a Must prerequisite for S-016 (backlog). Invites, snapshots, ownership passing and notebook management stay in S-057, S-035, S-058 and S-059. | Pass |

**Post-design re-check (after Phase 1)**: unchanged, all pass. Points checked:

- The kitchen-row lock (`FOR NO KEY UPDATE`) is a new query in the notebook adapter. It does not change kitchen or auth code paths, and it does not block foreign-key inserts that reference the kitchen (research R6).
- `CreateOwnedKitchenService` gains no ports: kitchen creation goes back to its pre-S-056 form (R5). Kitchens are not part of the auth layer.
- The `TransactionCommitter` port is the first explicit commit outside `get_db`. It runs only when the capture step has created a notebook, before the save writes anything (R8).

## Project Structure

### Documentation (this feature)

```text
specs/056-notebooks/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R13 and rejected alternatives
├── data-model.md        # Phase 1: tables, cascades, domain rules, read model
├── quickstart.md        # Phase 1: how to check it works
├── contracts/
│   └── notebooks-api.md # Phase 1: four routes, BFF routes, in-process capture step and catalog readers
├── checklists/
│   ├── requirements.md          # spec quality (passes)
│   └── requirements-quality.md  # PR review gate (36 items)
└── tasks.md             # Phase 2: task list (/speckit-tasks)
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── notebook.py                      # REWORK: Notebook(id, name, kitchen_id?, source_notebook_id?, owner_user_id?),
│   │                                    #   kind; default_notebook_name, kitchen_notebook_name,
│   │                                    #   notebook_access, choose_capture_notebook
│   └── errors.py                        # InvalidNotebookOwnerError → InvalidNotebookError;
│                                        #   + KitchenArchivedError, NotebookChoiceRequiredError
├── application/
│   ├── ports.py                         # REWORK: NotebookRepository (facts, create_personal,
│   │                                    #   create_kitchen_notebook, personal_ids_for, kitchen_ids_for,
│   │                                    #   lock_kitchen); IngredientCatalogReader → IngredientCatalog
│   │                                    #   (+ names_for_person, seed_from_person); UserDefaultNotebook
│   │                                    #   kept; + TransactionCommitter
│   ├── notebooks.py                     # REWORK: ListMyNotebooks, GetDefaultNotebook, GetNotebook,
│   │                                    #   ListKitchenNotebooks, ResolveCaptureNotebook; NotebookView
│   └── kitchens.py                      # CreateOwnedKitchenService: kitchen and membership only (R5)
├── adapters/persistence/
│   ├── models.py                        # NotebookModel (drop user_id, kitchen_id not unique, name not null, + owner_user_id,
│   │                                    #   + source_notebook_id, new checks), + NotebookMembershipModel;
│   │                                    #   IngredientModel and users.default_notebook_id kept
│   ├── notebooks.py                     # REWORK: SqlAlchemyNotebookRepository; SqlAlchemyUserDefaultNotebook
│   │                                    #   kept; + SqlAlchemyTransactionCommitter
│   ├── ingredient_catalog.py            # SqlAlchemyIngredientCatalog (+ names_for_person, seed_from_person)
│   └── migrations/versions/
│       ├── 0003_notebooks_ingredients.py       # DELETE
│       └── 0003_personal_kitchen_notebooks.py  # NEW, down_revision 0002_pgvector_kitchen_lang, no backfill
├── api/
│   ├── routes/notebooks.py              # REWORK: GET /notebooks, /notebooks/default,
│   │                                    #   /notebooks/kitchens/{kitchen_id}, /notebooks/{notebook_id}
│   ├── routes/kitchens.py               # unchanged (R5)
│   ├── schemas/notebooks.py             # NotebookResponse, NotebooksResponse
│   └── app.py                           # unchanged (router already behind require_user_alias)
├── scripts/seed_dev_user.py             # revert the notebook wiring of the kitchen service (R5)
└── tests/
    ├── test_notebook_domain.py          # REWORK
    ├── test_notebooks_application.py    # REWORK (fake ports)
    ├── test_notebook_integration.py     # REWORK (routes, capture step, cascades, concurrency, leaving)
    ├── test_kitchens_domain.py          # kitchen creation makes no notebook
    └── test_kitchens_integration.py     # a new kitchen has no notebook; a failed creation leaves neither

ui/app/api/notebooks/
├── route.ts                             # NEW  GET /api/notebooks
├── default/route.ts                     # NEW  GET /api/notebooks/default
├── [notebookId]/route.ts                # NEW  GET /api/notebooks/{notebookId}
├── kitchens/[kitchenId]/route.ts        # kept (forwards as is; body is now a list)
└── members/                             # DELETE (both routes)
ui/app/api/notebooks.bff.test.ts         # REWORK
```

**Structure Decision**: The existing hexagonal api and Next.js BFF layout (AGENTS.md "Project structure"). No new folder.

## Reuse (from the 2026-10-22 code on this branch)

- **Kept as is**:
  - the `ingredient` table and model;
  - `users.default_notebook_id` with `ON DELETE SET NULL` and `use_alter`;
  - `SqlAlchemyUserDefaultNotebook` (`get_for_update`, `set`);
  - the `require_user_alias` wiring in `app.py`;
  - the 404 helpers in `routes/notebooks.py`;
  - the BFF forwarding pattern (copy `kitchens/[kitchenId]/route.ts` for the three new BFF routes).
- **Kept with changes**:
  - `GetDefaultNotebookService`: the lock and re-check stay. It adds the owner membership and the catalog seed, and loses the `user_id` path argument and the owner-only branch.
  - `CreateOwnedKitchenService`: reverted to create no notebook (R5). The branch's notebook insert and its extra argument go.
  - `ensure_kitchen_notebook` (R14) is new. `ResolveCaptureNotebookService` and the kitchen list service both use it.
  - `default_notebook_name`, `NotebookNotFoundError`, `names_for_notebook`.
- **Removed**:
  - `notebook.user_id`, its index and `ck_notebook_one_owner`; `unique(kitchen_id)`;
  - `GetKitchenNotebookService` (and its lazy notebook creation on read) and `GetMemberNotebookService`;
  - `KitchenNotebookResponse` and `MemberNotebookResponse`;
  - the backfill.

## Build order (for /speckit-tasks)

1. **Domain**: rework `domain/notebook.py` and the errors, with domain tests first.
2. **Schema**: models plus migration `0003_personal_kitchen_notebooks`, checked as quickstart §2 (upgrade, downgrade, upgrade).
3. **Ports and adapters**: repository facts queries, personal and kitchen candidate ids, the kitchen-row lock, the committer, the catalog seed and readers.
4. **Application services**, tested against fakes. `ResolveCaptureNotebookService` reuses the default-notebook creation for the personal case (R7) and `ensure_kitchen_notebook` for a kitchen (R14).
5. **Kitchen creation**: revert the notebook creation in `CreateOwnedKitchenService`, `seed_dev_user.py` and the kitchen tests (R5). Then the first open: `ListKitchenNotebooksService` with `ensure_kitchen_notebook` (R14).
6. **Routes and schemas**, then integration tests: simultaneous first calls (SC-001), simultaneous first opens and first captures (SC-003), kitchen deletion (SC-008), leaving (SC-006), failed save (FR-009).
7. **UI BFF routes** and vitest.
8. **Docs**:
   - backlog S-056 verification note;
   - spec 016 re-sync (FR-001a still says a kitchen capture is "also saved into the member's notebook" and names "a kitchen's shared notebook"): a capture outside a kitchen targets a picked personal notebook, a capture in a kitchen one of its notebooks; the draft reads `names_for_notebook`, or `names_for_person` in a kitchen with none;
   - S-020 note: its save calls `ResolveCaptureNotebookService` first and maps `KitchenArchivedError`, `NotebookChoiceRequiredError`, `NotebookNotFoundError` and `KitchenNotFoundError`.

## Follow-ups outside this feature

- **Spec 016** (S-016): FR-001a and the capture routes must be re-synced to the snapshot model before S-016 is built (backlog S-016 note already says so).
- **S-058**: passes a kitchen notebook's owner (`owner_user_id`) to the kitchen's owner when the owner leaves or is deleted. Built with the leave and user-deletion routes (S-054).
- **S-035**: sets `source_notebook_id` and adds it to the notebook answer.
- **S-059**: creating more notebooks, renaming and deleting them. A deleted personal notebook clears `users.default_notebook_id` through the existing cascade.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New column `users.default_notebook_id` on an auth table (constitution §1: auth layer immutable) | The Notebook tab, S-016 and the personal capture step need one stable default notebook per person, among several. Owner approval 2026-10-22, still valid after both re-specifications. | "Oldest notebook I own" has no stable default once the person creates more (S-059), or once the default is deleted and recreated. A preferences row still changes auth-owned data and adds a join. Creating the notebook at signup changes the auth routes. |
| An explicit commit inside a use case (`TransactionCommitter`), where every other use case relies on `get_db`'s single commit | FR-009: a notebook made by the capture step must stay when the save that called it fails (CHK024, 2026-10-23). | A savepoint is undone by the outer rollback; a second session cannot be seen by the save until it commits; leaving the commit to S-020's route puts this feature's rule in another story's code. |
