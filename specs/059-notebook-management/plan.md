# Implementation Plan: Create, rename and delete notebooks

**Branch**: `worktree-059-notebook-rename` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/059-notebook-management/spec.md`

## Summary

Three actions finish notebook management: rename, delete, and add an empty kitchen notebook. No table changes: the foreign keys built with specs 056, 022 and 035 already carry a deletion to recipes, catalog, memberships, invites, cart entries and edit locks, clear snapshot labels and clear `users.default_notebook_id`. The work is three small services, one shared rule for who may manage a notebook, a lock order that makes the races end in a plain "not found", and the ui: an options menu on the notebook page, one name dialog shared by create and rename, and a delete confirmation.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Tailwind 4. No new libraries.

**Storage**: PostgreSQL 16. No migration.

**Testing**: pytest (domain, application with fakes, integration on Postgres), vitest

**Target Platform**: Compose stack, browser at phone and desktop width

**Project Type**: Web application (api plus Next.js BFF)

**Performance Goals**: SC-001 and SC-002, timed in the browser walk. No other target: a delete is one transaction of cascades, at household scale.

**Constraints**: All or nothing per request. 404 hides what a person may not see. UI text in English and Spanish.

**Scale/Scope**: A couple's household: tens of notebooks, hundreds of recipes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| §1 Simplicity and reuse | Pass | No new service. Reuses `delete_personal`, `lock_notebook`, `lock_kitchen`, `ActionDialog`, `IconButtonPopup`. Auth untouched. |
| §2 Stack | Pass | No new library. |
| §3 Hexagonal | Pass | The rule lives in `domain/notebook.py`, use cases in `application/notebooks.py`, access checked in `application/`, 404 for non-members. |
| §4 Security | Pass | No external calls. Notebook names are not logged. |
| §5 No AI shortcuts | Pass | No AI involved. |
| §6 Testing | Pass | Domain, fake-port and Postgres tests, including real concurrent requests for the races. |
| §7 Deployment | Pass | Nothing changes. |
| §8 Git discipline | Pass | No schema change. |
| §9 Scope | Pass | S-059 is Must. |

Re-checked after Phase 1: no change, no violations.

## Project Structure

### Documentation (this feature)

```text
specs/059-notebook-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── notebooks-api.md
│   └── notebooks-ui.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── domain/notebook.py                  # assert_can_manage
├── application/
│   ├── notebooks.py                    # Rename, Delete, CreateKitchenNotebook services; snapshot source lock
│   ├── notebook_ownership.py           # calls the renamed delete
│   └── ports.py                        # rename, delete
├── adapters/persistence/notebooks.py   # rename, delete (was delete_personal), lock_kitchen on a missing row
├── adapters/persistence/recipes.py     # add: a notebook gone at insert is NotebookNotFoundError
├── api/routes/notebooks.py             # PATCH and DELETE /{id}, POST /kitchens/{id}
├── api/schemas/notebooks.py            # name request
└── tests/                              # test_notebook_manage_{domain,application,integration}.py, fakes

ui/
├── app/api/notebooks/[notebookId]/route.ts            # PATCH, DELETE
├── app/api/notebooks/kitchens/[kitchenId]/route.ts    # POST
├── app/notebooks/NotebookNameDialog.tsx               # new, shared by create and rename
├── app/notebooks/NewNotebookCard.tsx                  # uses it, takes an optional kitchen
├── app/notebooks/[notebookId]/NotebookOptionsMenu.tsx # new
├── app/notebooks/[notebookId]/NotebookDeleteDialog.tsx # new
├── app/notebooks/[notebookId]/NotebookRecipesScreen.tsx
├── app/kitchens/KitchenNotebooksScreen.tsx
├── lib/notebooksClient.ts
└── lib/i18n/notebooks.ts
```

**Structure Decision**: the existing `api/` and `ui/` layout. No new folders.

## Complexity Tracking

No violations.
