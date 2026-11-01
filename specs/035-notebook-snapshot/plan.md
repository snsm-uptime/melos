# Implementation Plan: Add a personal notebook to a kitchen as a snapshot

**Branch**: `035-notebook-snapshot` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/035-notebook-snapshot/spec.md`

## Summary

A kitchen member picks a personal notebook they own, and the api makes a new kitchen notebook in one transaction: copies of every recipe (with lines, steps and its own source row), and the whole catalog, plus the origin label. One new column, `notebook.snapshot_key`, marks a notebook as a snapshot for good and makes a repeated request safe. The ui adds a kitchen notebooks view, opened from the chrome, that holds the cards and the action, and adds the origin label to the notebook page. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Tailwind 4. No new libraries.

**Storage**: PostgreSQL 16. One migration, `0011_notebook_snapshot_key`.

**Testing**: pytest (domain, application with fake ports, integration in the Compose test overlay), vitest (ui), browser walk ([quickstart.md](quickstart.md)).

**Target Platform**: The four existing Compose services. `mcp` and `db` images are unchanged.

**Project Type**: Web application (api plus BFF ui).

**Performance Goals**: A notebook of 100 recipes is added in under 5 seconds (SC-002).

**Constraints**: All or nothing (FR-006). No AI call (FR-014). No queue or worker, so the request runs in one transaction.

**Scale/Scope**: A home cookbook: tens to low hundreds of recipes per notebook, at most 100 lines and 100 steps per recipe.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| 1. Simplicity and reuse | Pass | No new service. Reuses `ActionDialog`, kitchen access checks and the kitchen lock. Auth is untouched. |
| 2. Tech stack | Pass | No new library. |
| 3. Hexagonal | Pass | The rule that picks a valid source lives in `application/`; SQL stays in `adapters/persistence/`, behind ports. |
| 4. Security and privacy | Pass | 404 for anything the caller can't see. The label carries a name only, and no route opens the original. Logs hold counts and outcomes only. |
| 5. No AI shortcuts | Pass | No AI step. |
| 6. Testing | Pass | All layers planned, including a browser walk. |
| 7. Deployment | Pass | Migration only. |
| 8. Git discipline | Pass | Schema change through Alembic. Work starts on branch `035-notebook-snapshot`; this plan was written on `main`. |
| 9. Scope | Pass | S-035 is a Must. |

Re-check after Phase 1: all pass. The amendments to spec 056 (FR-009, FR-013, SC-011) are listed in [research.md](research.md) R6 and need no constitution exception.

## Project Structure

### Documentation (this feature)

```text
specs/035-notebook-snapshot/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/snapshots-api.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── application/
│   ├── notebooks.py                 # AddNotebookSnapshotService; capture default
│   └── ports.py                     # new methods on the notebook, catalog and recipe ports
├── adapters/persistence/
│   ├── models.py                    # notebook.snapshot_key
│   ├── migrations/versions/0011_notebook_snapshot_key.py
│   ├── notebooks.py                 # snapshot lookups, origin name, own-notebook filter
│   ├── ingredient_catalog.py        # copy_names
│   ├── recipes.py                   # copy_all
│   └── side_panel.py                # count leaves snapshots out
├── api/routes/notebooks.py          # POST snapshots, POST capture-notebook
├── api/schemas/notebooks.py
└── tests/

ui/
├── app/api/notebooks/kitchens/[kitchenId]/{snapshots,capture-notebook}/route.ts
├── app/kitchens/KitchenDetailChrome.tsx        # the notebooks icon
├── app/kitchens/[kitchenId]/notebooks/page.tsx # the notebooks view
├── app/kitchens/KitchenNotebooksScreen.tsx     # cards and the action
├── app/kitchens/KitchenNotebooksSection.tsx    # capture default
├── app/kitchens/AddNotebookSnapshot.tsx        # choice and repeat warning
├── app/notebooks/[notebookId]/NotebookRecipesScreen.tsx   # origin label
├── components/AddRecipeCallToAction/           # capture default
├── lib/notebooksClient.ts
└── lib/i18n/notebooks.ts
```

**Structure Decision**: The existing `api/` and `ui/` layout. Snapshot code joins the notebook modules, since a snapshot is a notebook and not a new entity.

## Complexity Tracking

No violations.
