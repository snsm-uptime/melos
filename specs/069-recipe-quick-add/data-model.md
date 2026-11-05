# Data Model: 069 recipe quick add

## recipes (changed)
| Column | Type | Notes |
|---|---|---|
| copied_from_recipe_id | UUID NULL | FK `recipes.id` ON DELETE SET NULL; index `ix_recipes_copied_from_recipe_id`. Set only by recipe copies of this story. Never exposed in responses. |

Migration `0016_recipe_copied_from` (Alembic), reversible.

## Rules
- A copy lives in the caller's own kitchen notebook of the target kitchen (created if missing).
- Copy author = caller; content = source's title, base_servings, servings_estimated, preview image, a new source row (type/url/raw_text copied), lines, steps.
- Repeat = exists recipe R with `R.copied_from_recipe_id = source.id` and `R.notebook.kitchen_id = target kitchen`.
- Overwrite targets the most recent such R; it keeps R.id and R.notebook_id, replaces content, sets author = caller, keeps `copied_from_recipe_id`.
- Deleting the source sets every copy's `copied_from_recipe_id` to NULL; deleting a copy has no effect on the source.
- Ingredient names of the copy are added to the target notebook's catalog if missing.

## States
`new copy` → (edited freely) → `overwritten` (content replaced) | `deleted`.
