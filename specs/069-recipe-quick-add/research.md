# Research: 069 recipe quick add

## R1 Copy a single recipe
- **Decision**: Add `RecipeRepository.copy_one(recipe_id, target_notebook_id, author_id, copied_from) -> UUID`, built from the same row-copy steps as `copy_all` (source row, recipe, lines, steps, preview image), refactored into shared helpers. Source row locked `FOR SHARE` as in `copy_all`.
- **Rationale**: Same content rules as snapshots (spec 035 R4/R5); one place to copy a recipe.
- **Alternatives**: Re-saving through `recipe_save` (would re-run validation and lose `created_at` semantics); waiting for S-048 (blocks this story).

## R2 Author and created_at
- **Decision**: Copy author = the caller (spec FR-005); `created_at` = now, so it shows as new in the kitchen list.
- **Rationale**: Differs from snapshots, which keep authors; the spec makes the member the author.

## R3 Target notebook
- **Decision**: `ensure_member_kitchen_notebook` under the kitchen lock, same as first capture.
- **Rationale**: Clarification Q1; existing naming rules (specs 056, 063).

## R4 Ingredient catalog
- **Decision**: New `IngredientCatalog.add_names(notebook_id, names)` inserting only the copied recipe's line names that are missing (no normalization, FR-010).
- **Alternatives**: `copy_names` (copies the whole personal catalog: too broad).

## R5 Repeat detection
- **Decision**: `recipes.copied_from_recipe_id UUID NULL REFERENCES recipes(id) ON DELETE SET NULL`, indexed. A repeat = any recipe in any notebook of the target kitchen with that value. Never returned by read endpoints.
- **Rationale**: Clarification Q3 needs a hidden link; SET NULL clears it when the source is deleted.
- **Alternatives**: Name match (false positives); a separate table (more code for one column).

## R6 Repeat protocol
- **Decision**: Request carries `on_repeat: "ask" | "add" | "overwrite"`. `ask` + repeat → 409 `recipe_already_in_kitchen` with the existing copy id and notebook name. `overwrite` replaces title, servings, image, source, lines and steps of the latest copy (by `created_at`) in place, sets author to the caller, re-enqueues its embedding. Takes the recipe edit lock path's row lock; if someone holds an edit lock (spec on recipe_locks) → 409 `recipe_locked`.
- **Rationale**: Mirrors the snapshot `confirm_repeat` pattern; overwrite keeps the recipe id so cart/list references survive.

## R7 Embeddings
- **Decision**: `embedding_jobs.enqueue([new_or_overwritten_id])` and `wake_embedding_worker` after commit.

## R8 Quick add placement and context
- **Decision**: An `IconButton` with `PlusIcon` in the AppShell header's trailing area, shown on every signed-in page with a header (mobile and desktop). Kitchen context comes from the path `/kitchens/[kitchenId]…`; there candidates come from `GET /api/notebooks/kitchens/{id}` and `capture-notebook`, elsewhere from `GET /api/notebooks` with the default notebook. Return path = current pathname.
- **Rationale**: Reuses `AddRecipeCallToAction`'s capture state and sheets; FR-001, Story 2 AS-2/AS-5.

## R9 Picker data
- **Decision**: Notebooks from `GET /api/notebooks` filtered to `kind === "personal"`; recipes from `GET /api/notebooks/{id}/recipes?q=` (existing search and paging). Target kitchen outside a kitchen: active kitchens from the existing membership store, archived excluded.
