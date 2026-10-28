# Implementation Plan: Save a Confirmed Draft into Its Notebook

**Branch**: `020-save-confirmed-draft` (spec folder `020-save-confirmed-draft`, story S-020) | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-save-confirmed-draft/spec.md`

## Summary

The draft review screen gains a Save button. Save sends the member's edited draft to a new
`POST /recipes` route. The api checks access and the recipe rules again, then stores the
`source`, `recipe`, `recipe_ingredient` and `step` rows and the new catalog names in one
transaction, with the member as author. A client-made `save_key` makes a repeated Save return
the recipe already stored. On success the ui returns to the notebook page with a "Recipe
saved" notice; on a refusal the draft stays on screen.

Technical approach: a migration adds the four recipe tables (none exist yet). A pure domain
function re-checks an edited draft by reusing the rules of `domain/recipe_draft.py`, and
resolves each line name against the notebook's catalog with the shared spec 018 rule, so the
server decides which names are new and never trusts a client "matched" flag. A new
`SaveRecipeDraft` use case in `application/` runs the checks in the order below and talks to
two ports (`RecipeRepository`, and `IngredientCatalog.add_names`). The ui adds a save client,
a same-origin BFF route and the Save control.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: SQLAlchemy, Alembic, FastAPI, `domain/recipe_draft.py`, `domain/ingredient_catalog.py`, `ResolveCaptureNotebookService` (spec 056). ui: `captureStore`, `RecipeDraftEditor`, `LeaveDraftGuard`. **No new library.**

**Storage**: PostgreSQL 16. New tables `source`, `recipe`, `recipe_ingredient`, `step` through Alembic migration `0005_recipes` (constitution §8). The `ingredient` table is reused; no change.

**Testing**: pytest + ruff (api): pure domain tests, application tests against fake repositories, integration tests in the Compose test overlay against Postgres, plus a migration upgrade/downgrade check. vitest + eslint + typecheck (ui). Browser check of the Save flow (constitution §6).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: Save of a recipe with up to 100 lines and 100 steps completes within 1 second server side (SC-001 allows 3 s end to end).

**Constraints**:
- `domain/` stays free of I/O and SDK imports (constitution §3).
- No AI call in Save. The draft is stored only after the member confirms it (constitution §5).
- Nothing is written before every check passes (research R4), so a refused save leaves no row.
- Access is checked in `application/`; a caller without access gets the missing-notebook answer (constitution §3).
- The pasted text is stored as `source.raw_text` only because the member saved the recipe; it is never logged (constitution §4).
- Cuisines, main ingredients, preview image and cart count are not stored (S-061, S-047).

**Scale/Scope**: One household. 1 migration, 1 domain module, 1 use case, 1 route, 1 repository adapter, edits to the catalog port, plus ui client, BFF route and editor changes. Test files for each.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and reuse | No new service or library. Reuses the draft rules, the spec 018 rule and the spec 056 capture step. | Pass |
| 2. Tech stack stability | Alembic migration, SQLAlchemy, FastAPI as before. No model or SDK change. | Pass |
| 3. Hexagonal architecture | Rules in `domain/`; use case and ports in `application/`; SQL in `adapters/persistence/`; route only maps errors. Access checked in `application/`, 404 for no access. | Pass |
| 4. Security and privacy | Membership check before any write; same 404 body for missing and forbidden; pasted text not logged; no real data in fixtures. | Pass |
| 5. No AI shortcuts | Save only runs on the member's explicit action, on the member's edited values. | Pass |
| 6. Testing and quality | Domain tests first, application tests with fakes, integration on Postgres, vitest, browser check. | Pass |
| 7. Deployment | No deploy change. | Pass (n/a) |
| 8. Git discipline | Schema change through Alembic migration `0005_recipes` with a tested downgrade. | Pass |
| 9. Product scope | Save is a Must (PRD Appendix C: recipe CRUD). Categories stay out (S-061). | Pass |

**Re-check after design (Phase 1)**: unchanged, all Pass. The only new surface is `POST /recipes`, which follows the same auth, access and error pattern as the capture route.

## Project Structure

### Documentation (this feature)

```text
specs/020-save-confirmed-draft/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── save-api.md
│   └── save-ui.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── recipe_draft.py                 # edit: public check for an edited draft (no matching)
│   └── recipe.py                       # new: NewRecipe, resolve_line_names
├── application/
│   ├── ports.py                        # edit: RecipeRepository; IngredientCatalog.add_names
│   └── recipe_save.py                  # new: SaveRecipeDraft use case
├── adapters/persistence/
│   ├── models.py                       # edit: SourceModel, RecipeModel, RecipeIngredientModel, StepModel
│   ├── recipes.py                      # new: SqlAlchemyRecipeRepository
│   ├── ingredient_catalog.py           # edit: add_names
│   └── migrations/versions/0005_recipes.py   # new
├── api/
│   ├── routes/recipes.py               # new: POST /recipes
│   ├── schemas/recipes.py              # new: request body
│   └── deps.py                         # edit: get_save_recipe_draft
└── tests/                              # domain, application, integration, migration
ui/
├── app/api/recipes/route.ts            # new: BFF pass-through
├── lib/capture/saveClient.ts           # new: submitSave
├── lib/capture/captureStore.ts         # edit: saveKey, saving, savedNotice
├── lib/i18n/capture.ts                 # edit: save messages
├── components/RecipeDraft/RecipeDraftEditor.tsx   # edit: Save control
└── app/notebooks/NotebookTabScreen.tsx # edit: show the notice
```

**Structure Decision**: Existing web-application layout; the new files follow the names used by specs 016 and 056.

## Complexity Tracking

No constitution violations. No entries.
