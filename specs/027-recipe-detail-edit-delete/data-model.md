# Data Model: Recipe Detail, Edit and Delete (S-027)

**No schema change and no migration.** Everything below already exists from spec 020.

## Stored entities (unchanged)

| Table | Used for | Notes |
|---|---|---|
| `recipe` | read, update, delete | `title`, `base_servings`, `servings_estimated`, `author_id` (nullable), `notebook_id`, `source_id` (nullable, `SET NULL`), `created_at`, `updated_at`. `updated_at` is the version token. |
| `recipe_ingredient` | read, replace, cascade delete | `recipe_id` (`CASCADE`), `position` unique per recipe, `name`, `quantity`, `unit`, `size`, `preparation`, `vague_note`. Existing check constraints enforce the line rules. |
| `step` | read, replace, cascade delete | `recipe_id` (`CASCADE`), `position` unique per recipe, `text`. |
| `source` | read (type, url), delete with the recipe | One row per saved recipe today (`type=text`, `raw_text`). |
| `ingredient` | read names, add names | Catalog of the recipe's notebook. Edit adds; nothing removes. |
| `users` | alias for the author | Left join; null reads "unknown". |

## Read model (application, not stored)

**RecipeDetail**
- `id`, `title`, `base_servings`, `servings_estimated`
- `author_alias` (null → "unknown")
- `notebook_id`, `notebook_name`, `notebook_kind`, `kitchen_id` (null for personal)
- `lines[]`: `name`, `vague` (derived: `vague_note` set), `quantity`, `unit`, `size`, `preparation`, `note` (the stored `vague_note`), in position order
- `steps[]`: `text`, in position order
- `source`: `{type, url}` or null (never `raw_text`)
- `created_at`, `version` (= `updated_at`)
- `can_write` (from the write rule, for the caller)

## Rules

| Rule | Where |
|---|---|
| May write recipes: personal owner or member; kitchen member of a non-archived kitchen | `domain/notebook.can_write_recipes` (new, pure) |
| Title required, servings ≥ 1, ≥ 1 line, ≥ 1 step, vague note excludes amount and unit, measured line needs quantity > 0 and unit, size only with `unit`, units from the allowed set, ≤ 100 lines, ≤ 100 steps | `check_edited_draft` + limits (reused) |
| A typed name is proposed a catalog entry when it is the same name under S-018 normalization, singular forms included | `domain/ingredient_catalog.propose_entry` (new, pure; built on `match_line`) |
| A name equal to a catalog entry by case/spacing takes the entry's spelling; other names are new and added to the catalog | `resolve_line_names` (reused) |

## State transitions

```text
saved ──(update, version matches)──▶ saved   (updated_at changes; author, notebook, source, created_at fixed)
saved ──(update, version differs)──▶ saved   (nothing written; caller told it changed)
saved ──(delete)───────────────────▶ gone    (recipe, lines, steps, source removed; catalog kept)
gone  ──(read | update | delete)───▶ gone    (404 recipe_not_found)
```

## Copies and snapshots

A copy or snapshot is a separate `recipe` row in another notebook (flow G/H, later stories). Edit and delete touch only the one row addressed, so copies never change (AC3.2, AC3.3).
