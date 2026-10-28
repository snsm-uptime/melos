# Data Model: Save a Confirmed Draft into Its Notebook

Migration `0005_recipes` (down revision `0004_drop_kitchen_hide`). Names follow PRD 1.6.

## source

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | `gen_random_uuid()` |
| user_id | uuid null | FK `users.id`, ON DELETE SET NULL |
| type | text | check in (`text`, `url`, `photo`); this feature writes `text` |
| url | text null | null for text |
| raw_text | text null | the pasted text |
| created_at | timestamptz | default now |

## recipe

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| notebook_id | uuid | FK `notebook.id`, ON DELETE CASCADE, indexed. Exactly one notebook |
| author_id | uuid null | FK `users.id`, ON DELETE SET NULL. Null reads "unknown" |
| source_id | uuid null | FK `source.id`, ON DELETE SET NULL |
| title | text | check `btrim(title) <> ''` |
| base_servings | integer | check `>= 1` |
| servings_estimated | boolean | default false |
| save_key | uuid null | client draft key (R5). Unique with `author_id` where not null |
| created_at, updated_at | timestamptz | default now |

## recipe_ingredient

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| recipe_id | uuid | FK `recipe.id`, ON DELETE CASCADE, indexed |
| position | integer | unique with `recipe_id`, starts at 0 |
| name | text | normalized name, same spelling as the catalog entry |
| quantity | numeric null | check `> 0` when set |
| unit | text null | check in the allowed set (`g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`) |
| size | text null | check in (`small`, `medium`, `large`) and `unit = 'unit'` |
| preparation | text null | |
| vague_note | text null | |

Line rules as table checks: vague (`vague_note` set) means `quantity` and `unit` are null; non-vague means both are set (PRD 1.6). The domain checks the same rules first; the checks are the last defence.

## step

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| recipe_id | uuid | FK `recipe.id`, ON DELETE CASCADE |
| position | integer | unique with `recipe_id` |
| text | text | check `btrim(text) <> ''` |

## ingredient (existing)

Unchanged. Save inserts missing `(notebook_id, name)` rows with `ON CONFLICT DO NOTHING` (unique `uq_ingredient_notebook_name`). It never updates or deletes entries.

## Domain values (no table)

- **NewRecipe**: title, base_servings, servings_estimated, lines (name, quantity, unit, size, preparation, vague_note), steps, source_text, author_id, notebook_id, save_key.
- **SavedRecipe** (use case result): recipe id, notebook id, `created` flag (false on replay).

## Relationships and lifecycle

- notebook 1—n recipe; recipe 1—n recipe_ingredient, step; recipe n—1 source.
- Created once by Save. This feature has no update or delete (S-027).
- Deleting a notebook cascades to its recipes, lines, steps and catalog; sources stay (orphaned sources are removed by S-027's recipe delete; out of scope here).
