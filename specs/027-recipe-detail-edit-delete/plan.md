# Implementation Plan: Recipe Detail, Edit and Delete

**Branch**: `027-recipe-detail-edit-delete` (spec folder `027-recipe-detail-edit-delete`, story S-027) | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/027-recipe-detail-edit-delete/spec.md`

## Summary

Members can open a saved recipe, correct it and delete it. The api gains four recipe routes: read one recipe, check ingredient names against the notebook's catalog, replace a recipe's content, and delete it. The ui gains a detail page, an edit page and a delete confirmation, and the recipe cards of spec 021 become links.

Technical approach: **no new table, column or migration.** Access reuses spec 056 (`facts_for` + `notebook_access`) with one new pure rule, "may write recipes". Edit reuses the draft rules of spec 020 (`check_edited_draft`, `resolve_line_names`) and the S-018 name rule (`domain/ingredient_catalog`). A changed-since-opened save is refused using the recipe's existing `updated_at` as a version token. Delete removes the recipe (lines and steps cascade) and its source row in one transaction. The ui reuses the row components of the draft editor but not its capture store.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: SQLAlchemy, FastAPI, `NotebookRepository.facts_for`, `domain/recipe_draft.check_edited_draft`, `domain/recipe.resolve_line_names`, `domain/ingredient_catalog`. ui: `IngredientLineRow`, `RowControls`, `NameChangeNotice`, `LeaveDraftGuard`, `ActionDialog`, `RecipeCard`. **No new library.**

**Storage**: PostgreSQL 16. Existing `recipe`, `recipe_ingredient`, `step`, `source`, `ingredient` tables. Lines and steps cascade from `recipe` (`ondelete=CASCADE`). `recipe.updated_at` already exists and becomes the version token. **No Alembic migration.**

**Testing**: pytest + ruff (api): pure domain tests (write rule, name proposal), application tests against fake repositories, integration tests in the Compose test overlay against Postgres (read, edit, conflict, delete, access, copies untouched). vitest + eslint + typecheck (ui). Browser check of detail, edit and delete (constitution §6).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: Detail visible within 2 seconds for a recipe of up to 100 lines and 100 steps (SC-001); edit save well under 500 ms server side.

**Constraints**:
- `domain/` stays free of I/O and SDK imports (constitution §3).
- A person who cannot read the recipe's notebook gets the same 404 as for a missing recipe; read-without-write gets 403 (spec FR-006).
- No model call in edit: name matching is the deterministic S-018 rule.
- Limits as spec 020: at most 100 lines and 100 steps.
- Logs carry outcomes and counts only, never titles, names or pasted text (constitution §4).

**Scale/Scope**: One recipe per request. Four routes, one pure rule, four use cases, two repository methods more than today, three ui pages' worth of screens (detail, edit, delete dialog).

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. No new service, folder at the top level, or library. Reuses spec 020/021/056 code. |
| 2. Tech stack | Pass. No new dependency. |
| 3. Hexagonal | Pass. Rules in `domain/` (write rule, name proposal), use cases in `application/`, SQL in `adapters/persistence/`, HTTP in `api/routes/`. Access checked in `application/`, 404 for non-readers. |
| 4. Security and privacy | Pass. Read-only access still gated by notebook membership; the pasted source text is deleted with the recipe and never returned by the detail route; logs carry counts only. |
| 5. No AI shortcuts | Pass. No model involved. Edit is the member's own confirmed content. |
| 6. Testing | Pass. Domain → application (fakes) → integration (Compose) → ui; browser walk in quickstart. |
| 7. Deployment | Pass. Nothing added to compose or server config. |
| 8. Git discipline | Pass. No schema change, so no migration; small commits per layer. |
| 9. Scope | Pass. S-027 is Must (PRD Appendix C: recipe CRUD). PDF, copy and cart are out. |

Post-design re-check: unchanged. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/027-recipe-detail-edit-delete/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── recipe-api.md
│   └── recipe-ui.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── notebook.py              # + can_write_recipes(access, kitchen_is_archived)
│   └── ingredient_catalog.py    # + propose_entry(name, catalog)
├── application/
│   ├── ports.py                 # RecipeRepository: + get_detail, replace, delete; RecipeDetail, StaleRecipeError
│   └── recipe_manage.py         # NEW: GetRecipe, MatchRecipeNames, UpdateRecipe, DeleteRecipe
├── adapters/persistence/
│   └── recipes.py               # + get_detail, replace (version-checked), delete
├── api/
│   ├── deps.py                  # + four service providers
│   ├── routes/recipes.py        # + GET/PUT/DELETE /recipes/{id}, POST /recipes/{id}/name-matches
│   └── schemas/recipes.py       # + detail, update and match bodies
└── tests/                       # test_recipe_write_domain.py, test_recipe_manage_application.py,
                                 # test_recipe_manage_integration.py

ui/
├── app/
│   ├── recipes/[recipeId]/page.tsx            # detail
│   ├── recipes/[recipeId]/edit/page.tsx       # edit
│   └── api/recipes/[recipeId]/route.ts        # BFF GET/PUT/DELETE
│       api/recipes/[recipeId]/name-matches/route.ts
├── components/
│   ├── RecipeDetail/                          # NEW: detail view, actions, delete dialog
│   ├── RecipeEdit/                            # NEW: edit form reusing draft row components
│   └── RecipeCard/RecipeCard.tsx              # card becomes a link
└── lib/recipesClient.ts, lib/i18n/recipeDetail.ts
```

**Structure Decision**: Extends the existing hexagonal api and BFF ui. One new application module (`recipe_manage.py`) keeps the four use cases beside `recipe_save.py` and `recipe_lists.py`. The edit form is new, not a mode of `RecipeDraftEditor`, because the draft editor is bound to the client-only capture store; only its presentational rows are reused.

## Complexity Tracking

No violations to justify.
