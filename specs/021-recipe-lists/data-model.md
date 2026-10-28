# Data Model: Recipe Lists

No table or column is added. This feature reads the entities below.

## Read model: recipe card

| Field | Source | Notes |
|---|---|---|
| `id` | `recipe.id` | |
| `title` | `recipe.title` | |
| `author_alias` | `users.alias` via `recipe.author_id` | `null` when the author is gone → ui shows "unknown" |
| `ingredient_count` | count of `recipe_ingredient` rows of the recipe | 1 to 100 |
| `notebook_id`, `notebook_name` | `recipe.notebook_id`, `notebook.name` | name shown only on kitchen lists (FR-004) |
| `created_at` | `recipe.created_at` | order key, newest first |

## Read model: recipe page

`items` (up to 12 cards), `page` (the page returned), `page_size` (12), `total` (matching recipes), `total_pages` (at least 1).

## Scope of a list

| List | Notebooks included | Access check |
|---|---|---|
| Notebook | exactly one, personal or kitchen | `facts_for` + access rule (spec 056); none → not found |
| Kitchen | `kitchen_ids_for(kitchen_id)`; personal notebooks never | `read_kitchen`; non-member → not found; archived allowed |

## Filter rules (domain)

- `search_key(text)`: trim, drop accents, case-fold, collapse spaces. Empty key means no filter.
- A recipe matches when the key is a substring of the same transform of its title or of any of its ingredient names.
- `clamp_page(requested, total, page_size)` → `(page, total_pages)`: `total_pages = max(1, ceil(total / page_size))`, `page = min(requested, total_pages)`; `requested < 1` is invalid.

## Migration

`0006_unaccent` (revises `0005_recipes`): `upgrade` runs `CREATE EXTENSION IF NOT EXISTS unaccent`; `downgrade` is a no-op (other database objects may use the extension; dropping it is left to the owner). Tested for upgrade and re-run.

## Indexes

Existing `ix_recipe_notebook_id` and `ix_recipe_ingredient_recipe_id` serve the lists. No new index: one household, seq scan inside a notebook is fine. Revisit if a list passes a few thousand recipes.
