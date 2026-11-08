# Implementation Plan: Ingredients Table Layout (user and admin)

**Branch**: `074-ingredients-table` (not created yet) | **Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/074-ingredients-table/spec.md`

## Summary

Make the admin Ingredients table show the same first columns as the user's catalog views, add three read-only admin columns (Standard status, Source, Notebooks) and an admin review-list section (spec 073 FR-022). Apply the owner's decisions: custom places first in the Place picker, Language always shown in the catalog view, and the review list as its own section. The work reads existing tables only: no schema change, no migration, no new endpoint. The admin API gains three fields per name, and the UI reuses the shared `DataTable` (spec 066).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with React 19 and Next.js 16 (ui)

**Primary Dependencies**: FastAPI and SQLAlchemy (api); the shared `DataTable` component in `ui/components/DataTable`; `vitest` for ui tests

**Storage**: PostgreSQL 16. No new tables or columns. Reads: `ingredient`, `ingredient_name`, `ingredient_place`, `recipe_ingredient`, `recipe`, `standard_ingredient`, `standard_ingredient_name`, `standard_ingredient_review`.

**Testing**: pytest (domain, application with fake ports, integration against Postgres); vitest (components); browser check at 360 px and 1280 px in en and es (constitution 6).

**Target Platform**: Compose stack (`db`, `api`, `ui`, `jobs`); browsers at phone and desktop widths.

**Project Type**: web application (Next.js BFF over FastAPI).

**Performance Goals**: sort and search stay in the browser with no server call (spec 066 SC-005). Admin ingredients query returns in under 1 s for the seeded data set.

**Constraints**: no change to data returned for the user's places and catalog; admin sees names and counts only (constitution 4); the auth layer is untouched (constitution 1).

**Scale/Scope**: a household app. Hundreds of ingredient names per person, low thousands across all accounts. No paging exists (spec 066 Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| 1. Simplicity and reuse | Uses the shared `DataTable` and existing admin and catalog endpoints. No new service, no new dependency. | Pass |
| 2. Tech stack | Python with `uv`, FastAPI, SQLAlchemy, Next.js and React already in use. No new library. | Pass |
| 3. Hexagonal architecture | The admin count and status query lives in `adapters/persistence/admin.py`, behind the existing `AdminReports` port in `application/ports.py`. The name-key mapping uses the existing pure function `discovery_key` in `domain/ingredient_catalog.py`. | Pass |
| 4. Security and privacy | The admin sees names and counts, as now. The Notebooks count reveals no notebook names or members. Admin endpoints keep `_require_admin`. | Pass |
| 5. No AI shortcuts | Read-only. Status and Source show what the job wrote. The review list only lists items for the admin to decide; it saves nothing. | Pass |
| 6. Testing | Domain test for the name-key mapping (pure). Application test with a fake reports port for the admin rule. Integration test for the admin query on Postgres. vitest for the table columns, order and the review section. Browser check. | Pass |
| 7. Deployment | No compose or proxy change. | Pass |
| 8. Git discipline | No schema change, so no Alembic migration. One commit per layer: API, then UI, then docs. | Pass |
| 9. Product scope | A `should` story (S-074) in the backlog. The spec exists. Owner confirms the ID and priority before build. | Pass, pending owner confirmation of the ID |

**Result**: all gates pass. No violations to justify, so Complexity Tracking stays empty.

**Post-design re-check**: after Phase 1, still all pass. The contract adds fields and a section; no new principle is touched.

## Project Structure

### Documentation (this feature)

```text
specs/074-ingredients-table/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (read model, no schema change)
├── quickstart.md        # Phase 1 output (validation guide)
├── contracts/
│   └── admin-ingredients.md   # Phase 1 output (admin API fields)
└── tasks.md             # Created by /speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── ingredient_catalog.py          # discovery_key reused (no change expected)
├── application/
│   ├── admin.py                       # AdminReports use case: passes new fields through
│   └── ports.py                       # AdminIngredientRow gains status, source, notebooks
├── adapters/persistence/
│   └── admin.py                       # _INGREDIENTS query gains the three columns
├── api/
│   ├── schemas/admin.py               # AdminIngredient gains the three fields
│   └── routes/admin.py                # /api/admin/ingredients response unchanged in shape otherwise
└── tests/
    ├── test_ingredient_catalog_domain.py          # key mapping cases
    ├── test_admin_ingredients_application.py      # new: fake reports port
    └── test_admin_ingredients_integration.py      # new: Postgres query

ui/
├── app/admin/
│   ├── adminTables.tsx                # ingredientsTable: new columns, order, sort defaults
│   ├── AdminDashboard.tsx             # new review-list section (spec 073 FR-022)
│   └── AdminDashboard.test.tsx        # column and section tests
├── components/Ingredients/
│   ├── IngredientsScreen.tsx          # Place picker: custom first; name in viewer language
│   └── IngredientsScreen.test.tsx     # picker order and name rule tests
├── components/CatalogManager/
│   └── CatalogManager.tsx             # Language column always shown (verify, no change expected)
└── lib/i18n/
    ├── admin.ts                       # labels for new columns and review section (en, es)
    └── places.ts                      # any new labels (en, es)
```

**Structure Decision**: web application layout already in the repo. Changes stay in the existing admin and ingredients modules. No new directories except the spec folder and the new test files.

## Phase 0: Research

See [research.md](./research.md). Key findings:

1. The `standard_ingredient.normalized_name` key is `discovery_key` (singular form), not `normalize_name`. The admin join must map each admin name through `discovery_key` first.
2. Current admin ingredients rows come from the union of `recipe_ingredient` and `ingredient` names, grouped by raw name. Notebooks count is `COUNT(DISTINCT ingredient.notebook_id)` on that name.
3. The review list needs its own query over `standard_ingredient_review` with `status = 'pending'`. The data is already written by the spec 073 flow.

## Phase 1: Design and Contracts

- [data-model.md](./data-model.md): read model for the admin row and the review item. No table changes.
- [contracts/admin-ingredients.md](./contracts/admin-ingredients.md): the new fields on `GET /api/admin/ingredients` and the review list endpoint.
- [quickstart.md](./quickstart.md): how to seed data, run the checks, and verify both views in a browser.

## Complexity Tracking

No violations. Nothing to justify.
