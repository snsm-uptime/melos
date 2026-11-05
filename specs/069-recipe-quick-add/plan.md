# Implementation Plan: Recipe quick add, and a recipe from another notebook

**Branch**: `069-recipe-quick-add` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/069-recipe-quick-add/spec.md`

## Summary

Add a quick add button to the app header (`ui/components/AppShell.tsx`) that opens the existing
add-recipe options dialog plus a new "Recipe from another notebook" option, and add the same option
to the kitchen's add dialog. The option opens a picker (personal notebook → recipe, searchable) and
posts to one new api endpoint that copies a single recipe into the caller's own kitchen notebook,
reusing the snapshot path's pieces (`ensure_member_kitchen_notebook`, the kitchen lock, the copy
code of `copy_all`, the embedding queue). A new nullable `recipes.copied_from_recipe_id` column
(hidden, `ON DELETE SET NULL`) detects a repeat; a repeat returns 409 and the ui offers Add another
copy, Overwrite or Cancel.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript / Next.js 16 / React 19 (ui)
**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic; Tailwind 4. No new dependency.
**Storage**: PostgreSQL 16; one migration (`0016_recipe_copied_from`).
**Testing**: pytest (domain, application with fake ports, Compose integration); vitest (ui).
**Target Platform**: Compose stack (db, api, ui, mcp); browsers at 360px and 1280px.
**Project Type**: Web application (api + ui BFF).
**Performance Goals**: One copy completes within a normal request (< 1s for a recipe of ≤ 100 lines).
**Constraints**: Hexagonal layering; membership checked in `application/`; 404 for non-members.
**Scale/Scope**: One recipe per request; picker pages through existing recipe-list endpoints.

## Constitution Check

| Principle | Status |
|---|---|
| 1 Simplicity and Reuse | Pass: reuses snapshot service pieces, capture dialog and sheets; no new service; auth untouched. |
| 2 Tech Stack | Pass: no new library. |
| 3 Hexagonal | Pass: new use case in `application/recipe_copy.py`; new port methods on `RecipeRepository` and `IngredientCatalog`; membership checked in the use case (404). |
| 4 Security | Pass: source readability and kitchen membership checked server-side (FR-008); no personal data in fixtures. |
| 5 No AI shortcuts | Pass: no AI; copy is user-confirmed. |
| 6 Testing | Pass: plan includes domain/app/integration/ui tests and a browser walk. |
| 7 Deployment | Pass: no infra change. |
| 8 Git | Pass: schema change via Alembic. |
| 9 Product scope | Pass: S-069 in backlog, spec exists. No MVP-era rule lifted. |

Post-design re-check: unchanged, all pass.

## Project Structure

### Documentation (this feature)

```text
specs/069-recipe-quick-add/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/recipe-copy-api.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
api/
├── application/recipe_copy.py               # CopyRecipeToKitchenService (new)
├── application/ports.py                     # RecipeRepository.copy_one / overwrite_from / latest_copy_in_kitchen; IngredientCatalog.add_names
├── adapters/persistence/recipes.py          # implementations; copy_all shares row-copy helpers
├── adapters/persistence/ingredient_catalog.py  # add_names
├── adapters/persistence/models.py           # RecipeModel.copied_from_recipe_id
├── adapters/persistence/migrations/versions/0016_recipe_copied_from.py
├── api/routes/notebooks.py                  # POST /notebooks/kitchens/{kitchen_id}/recipe-copies
├── api/schemas/                             # CopyRecipeRequest
└── tests/{domain,application,integration}/

ui/
├── components/AddRecipeCallToAction/AddRecipeOptionsDialog.tsx   # optional 4th option
├── components/AddRecipeCallToAction/RecipeFromNotebookSheet.tsx  # picker + repeat dialog (new)
├── components/QuickAddRecipe/QuickAddRecipe.tsx                   # header button (new)
├── components/AppShell.tsx                                        # mounts QuickAddRecipe
├── app/kitchens/KitchenNotebooksSection.tsx                       # enables the option with kitchenId
└── lib/i18n/                                                      # en/es strings
```

**Structure Decision**: Existing web-app layout; no new top-level folders.

## Complexity Tracking

No violations.
