# Implementation Plan: Notebooks That Belong to People and Are Linked to Kitchens

**Branch**: `s55-notebooks` (spec folder `055-notebooks`) | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/055-notebooks/spec.md` (re-specified 2026-10-23, clarify Q1 A, Q2 A, Q3 B)

**Note**: The branch already holds code for the replaced 2026-10-22 model, in which a notebook was owned by a kitchen or a member (commits `b17f5a5`, `187ff14`). This plan reworks that code in place. The pieces that carry over are listed under "Reuse" below.

## Summary

A notebook belongs to people: one owner and any number of members, recorded in `notebook_membership`. A kitchen sees a notebook only through a `notebook_kitchen` link. This feature does the following:

- adds those two tables, the `notebook` and `ingredient` tables, and `users.default_notebook_id`;
- creates a person's default notebook on first use, linked to their signup kitchen;
- adds the in-process capture notebook step that S-016's save calls (find, or create and link, the member's notebook in a kitchen);
- exposes four read routes and their ui BFF routes: my notebooks, my default notebook, one notebook, and a kitchen's notebooks.

Technical approach:

- **Domain**: pure rules in `domain/notebook.py` (names, the access rule, the capture choice).
- **Application**: services in `application/notebooks.py`, working through the `NotebookRepository`, `IngredientCatalog`, `UserDefaultNotebook` and `KitchenRepository` ports.
- **Persistence**: SQLAlchemy adapters. A row lock on `users` serializes the first default request, and a row lock on the caller's `kitchen_memberships` row serializes first captures.
- **Migration**: a fresh Alembic revision `0003_notebooks_people` replaces the unmerged `0003_notebooks_ingredients`, with no backfill.
- **Unchanged**: signup and the auth routes. Kitchen creation stops creating a notebook.

## Technical Context

**Language/Version**: Python 3.12 (api, uv); TypeScript with Next.js 16 and React 19 (ui BFF routes only)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic (api); Next.js route handlers (ui). No new library.

**Storage**: PostgreSQL 16 (pgvector image). Four new tables (`notebook`, `notebook_membership`, `notebook_kitchen`, `ingredient`) and one new column (`users.default_notebook_id`). See [data-model.md](./data-model.md).

**Testing**: pytest (domain pure, application against fake ports, integration in the Compose test overlay against Postgres); vitest for the BFF routes

**Target Platform**: Linux containers via Docker Compose (`db`, `api`, `ui`, `mcp`)

**Project Type**: Web application (hexagonal api + Next.js BFF ui)

**Performance Goals**: One query per read route (joins on indexed keys). A first default request or first capture adds one row lock and at most five inserts: notebook, membership, catalog seed, link, and the default update. No target beyond the app's normal page loads.

**Constraints**:

- Auth layer and signup unchanged (FR-005, constitution §1).
- A caller with no access gets the same 404 as for something that does not exist, never 403 (constitution §3, SC-003).
- No env var added.
- The capture step has no route (FR-021).

**Scale/Scope**: A household: a few people, kitchens and notebooks each. A person may own several notebooks linked to one kitchen.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| §1 Simplicity and reuse: auth layer immutable | Signup, sign-in, alias claim and session code unchanged. The only change to the user is the nullable `default_notebook_id`, approved 2026-10-22 (spec Clarifications). The signup kitchen is found from existing data (`kitchens.owner_id`, research R4), so signup gains no flag. | Pass (approved exception, Complexity Tracking) |
| §1 Four services, external calls through ports | No service added. No external call. | Pass |
| §2 Stack stability | No library, no env var. Schema change through Alembic. | Pass |
| §3 Hexagonal | `domain/notebook.py` imports only `domain.errors`. Access is decided by `notebook_access` (domain) in `application/notebooks.py`; repositories return facts, not decisions (R8). Kitchen access goes through `AuthorizeKitchenAccessService` (`read_kitchen`). | Pass |
| §3 404 for non-members | `notebook_not_found` and `kitchen_not_found` bodies are identical for "missing" and "no access" (contract). | Pass |
| §4 Security and privacy | A notebook is visible only to its owner, its members and the members of linked kitchens (AGENTS.md recipe-access rule). Test data is invented. | Pass |
| §5 No AI shortcuts | No AI call. Nothing is saved from a draft here. | Pass (n/a) |
| §6 Testing layers | Domain (pure), application (fakes), integration (Compose, including concurrency), vitest BFF. | Pass |
| §8 Git discipline | Migration with a working downgrade. One concern per commit. Not pushed without review. | Pass |
| §9 Scope | S-055 is a Must prerequisite for S-016 (backlog). Invites, manual links and kept copies stay in S-056, S-034 and S-057. | Pass |

**Post-design re-check (after Phase 1)**: unchanged, all pass. Two points checked:

- The design reads `kitchens.owner_id` and locks `kitchen_memberships` rows. Neither changes kitchen or auth code paths: both are new queries in the notebook adapter.
- `CreateOwnedKitchenService` loses its notebook dependency, which takes it back to its pre-055 form.

## Project Structure

### Documentation (this feature)

```text
specs/055-notebooks/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R11 and rejected alternatives
├── data-model.md        # Phase 1: tables, cascades, domain rules, read model
├── quickstart.md        # Phase 1: how to check it works
├── contracts/
│   └── notebooks-api.md # Phase 1: four routes, BFF routes, in-process capture step and catalog readers
├── checklists/
│   ├── requirements.md          # spec quality (passes)
│   └── requirements-quality.md  # 2026-10-22 model: stale, regenerate with /speckit-checklist
└── tasks.md             # 2026-10-22 model: stale, regenerate with /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── notebook.py                      # REWORK: Notebook(id, name?, kitchen_id?), kind personal|kitchen,
│   │                                    #   default_notebook_name, kitchen_capture_notebook_name,
│   │                                    #   notebook_access, choose_capture_notebook
│   └── errors.py                        # InvalidNotebookOwnerError → InvalidNotebookError;
│                                        #   + NotebookChoiceRequiredError, KitchenArchivedError
├── application/
│   ├── ports.py                         # REWORK: NotebookRepository (facts, create_personal, link,
│   │                                    #   capture_candidates, lock_kitchen_membership, signup_kitchen_for);
│   │                                    #   IngredientCatalogReader → IngredientCatalog (+ names_for_person,
│   │                                    #   seed_from_person); UserDefaultNotebook kept
│   ├── notebooks.py                     # REWORK: ListMyNotebooks, GetDefaultNotebook, GetNotebook,
│   │                                    #   ListKitchenNotebooks, ResolveCaptureNotebook services; NotebookView
│   └── kitchens.py                      # CreateOwnedKitchenService no longer creates a notebook
├── adapters/persistence/
│   ├── models.py                        # NotebookModel (drop user_id, new check), + NotebookMembershipModel,
│   │                                    #   NotebookKitchenModel; IngredientModel and users.default_notebook_id kept
│   ├── notebooks.py                     # REWORK: SqlAlchemyNotebookRepository; SqlAlchemyUserDefaultNotebook kept
│   ├── ingredient_catalog.py            # SqlAlchemyIngredientCatalog (+ names_for_person, seed_from_person)
│   └── migrations/versions/
│       ├── 0003_notebooks_ingredients.py  # DELETE
│       └── 0003_notebooks_people.py       # NEW, down_revision 0002_pgvector_kitchen_lang, no backfill
├── api/
│   ├── routes/notebooks.py              # REWORK: GET /notebooks, /notebooks/default, /notebooks/{id},
│   │                                    #   /notebooks/kitchens/{kitchen_id}
│   ├── routes/kitchens.py               # drop SqlAlchemyNotebookRepository from kitchen creation
│   ├── schemas/notebooks.py             # NotebookResponse, NotebooksResponse
│   └── app.py                           # unchanged (router already behind require_user_alias)
├── scripts/seed_dev_user.py             # drop the notebook repository from CreateOwnedKitchenService
└── tests/
    ├── test_notebook_domain.py          # REWORK
    ├── test_notebooks_application.py    # REWORK (fake ports)
    ├── test_notebook_integration.py     # REWORK (routes, capture step, cascades, concurrency)
    ├── test_kitchens_domain.py          # drop the notebook fake from kitchen creation
    └── test_kitchens_integration.py     # kitchen creation now leaves no notebook

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
  - `ingredient` table and model;
  - `users.default_notebook_id` with `ON DELETE SET NULL` and `use_alter`;
  - `SqlAlchemyUserDefaultNotebook` (`get_for_update`, `set`);
  - the `require_user_alias` wiring in `app.py`;
  - the 404 helpers in `routes/notebooks.py`;
  - the BFF forwarding pattern (copy `kitchens/[kitchenId]/route.ts` for the three new BFF routes).
- **Kept with changes**:
  - `GetDefaultNotebookService`: the lock and re-check stay. It adds the owner membership, the catalog seed and the signup kitchen link, and loses the `user_id` path argument.
  - `default_notebook_name`.
  - `NotebookNotFoundError`.
- **Removed**:
  - `notebook.user_id` and its check;
  - `GetKitchenNotebookService` and `GetMemberNotebookService`;
  - `KitchenNotebookResponse` and `MemberNotebookResponse`;
  - the notebook created with a kitchen;
  - the backfill.

## Build order (for /speckit-tasks)

1. **Domain**: rework `domain/notebook.py` and the errors, with domain tests first.
2. **Schema**: models plus migration `0003_notebooks_people`, checked as quickstart §2 (upgrade, downgrade, upgrade).
3. **Ports and adapters**: repository facts queries, membership lock, signup kitchen lookup, catalog seed and readers.
4. **Application services**, tested against fakes. `ResolveCaptureNotebookService` reuses the default-notebook creation for the signup kitchen case (R6).
5. **Routes and schemas**, then integration tests. The tests include simultaneous first calls (SC-001, SC-002) and kitchen deletion (SC-007).
6. **Kitchen creation clean-up**: `CreateOwnedKitchenService`, `routes/kitchens.py`, `seed_dev_user.py` and the kitchen tests.
7. **UI BFF routes** and vitest.
8. **Docs**:
  - un-stale `tasks.md` and the requirements-quality checklist;
  - backlog S-055 verification note;
  - spec 016 FR-001a re-sync (S-016 note): it calls `ResolveCaptureNotebookService` at save, `GET /notebooks/default` for a personal capture, and `IngredientCatalog.names_for_person` for a kitchen draft with no notebook yet.

## Follow-ups outside this feature

- **PRD and AGENTS.md**: clarify Q3 added a rule, "the default notebook is linked to the person's signup kitchen when it is created". It is not yet in the PRD (flow H, J1a) or AGENTS.md's domain rules. Add it there before merge, with approval, so the spec and the PRD agree.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New column `users.default_notebook_id` on an auth table (constitution §1: auth layer immutable) | The Notebook tab, S-016 and the signup kitchen link need one stable default notebook per person, among several. Owner approval 2026-10-22, still valid after the re-specification. | "Oldest notebook I own" has no stable default once the person creates more, or once the default is deleted and recreated. A preferences row still changes auth-owned data and adds a join. Creating the notebook at signup changes the auth routes. |
