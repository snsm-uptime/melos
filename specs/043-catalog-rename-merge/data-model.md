# Data Model: Catalog Management (rename and merge ingredient names)

Migration: `api/adapters/persistence/migrations/versions/0021_catalog_other_names.py`
(after `0020_ingredient_free_note`; numbered 0020 before main took that number). Decisions in [research.md](research.md).

## Changed: `recipe`

| Column | Type | Rule |
|---|---|---|
| `language` | `varchar(2)` NOT NULL | `en` or `es` (check). Set at capture from the extractor, editable in recipe edit. Migration fills it by the FR-005a fallback, then sets NOT NULL (R3) |
| `language_detected_at` | `timestamptz` NULL | Set by `scripts.recipe_languages detect` once the model has read the recipe; the command skips rows where it is set |
| `proposed_language` | `varchar(2)` NULL | Check `IN ('en','es')`. The model's proposal when it differs from `language`; cleared when a person applies or dismisses it (FR-005a, constitution 5) |

## Changed: `ingredient` (one catalog ingredient of one notebook)

| Column | Type | Rule |
|---|---|---|
| `name` | existing | The **kept name**. Every `recipe_ingredient.name` in the notebook equals the `name` of one ingredient (SC-005) |
| `language` | `varchar(2)` NULL | `en`, `es` or null: the kept name's language; null until a merge or the person sets it |

## New: `ingredient_name` (other names)

| Column | Type | Rule |
|---|---|---|
| `id` | uuid PK | |
| `ingredient_id` | uuid FK → `ingredient.id` ON DELETE CASCADE | The ingredient it belongs to |
| `notebook_id` | uuid FK → `notebook.id` ON DELETE CASCADE | Same notebook as the ingredient (kept for the unique index) |
| `name` | text NOT NULL | Normalized like catalog names (trimmed, lower-case, singular) |
| `kind` | text NOT NULL | `variant` or `spelling` |
| `language` | `varchar(2)` NULL | Required (`en`/`es`) when `kind = 'variant'`; null for `spelling` (check) |
| `created_at` | timestamptz | |

Indexes and checks:
- `unique(notebook_id, name)`.
- Partial unique `(ingredient_id, language) WHERE kind = 'variant'`: at most one variant per language.
- A name in `ingredient_name` is never also an `ingredient.name` of the same notebook, and a variant's
  language is never the ingredient's own `language`: held by the domain under the R6 locks.

## New: `ingredient_pair_dismissal`

| Column | Type | Rule |
|---|---|---|
| `notebook_id` | uuid FK → `notebook.id` ON DELETE CASCADE | PK part |
| `name_a`, `name_b` | text | PK parts; stored sorted (`name_a < name_b`, check) |
| `dismissed_by` | uuid FK → `users.id` ON DELETE SET NULL | |
| `created_at` | timestamptz | |

Rename rewrites the names (re-sorted). Merge deletes the notebook's rows that name the merged name,
since it is no longer a kept name. Split leaves the rows as they are.

## Changed: `shopping_list_item`

| Column | Type | Rule |
|---|---|---|
| `names` | JSONB NOT NULL default `{}` | `{"en": ..., "es": ...}` variants of the line's ingredient, set for cart-based lines at refresh (R7); `{}` for hand items and for lines saved before this story |

## Unchanged, but written by this story

- `recipe_ingredient.name`: rewritten from the old/merged name to the kept name (R1).
- `ingredient_place(user_id, name)`: moved from the old/merged name to the kept name (R8).
- `embedding_job`: affected recipes enqueued (R10).

## Snapshots and copies

- `copy_names` (snapshot, spec 035) copies `ingredient.language` and the `ingredient_name` rows.
  Dismissals are not copied.
- Recipe copy (spec 069/071, S-048) and notebook join (spec 057) do not copy other names; they match
  against the target's index (R4).

## State transitions of one name in one notebook

```text
kept name ──merge into X──▶ other name of X (variant if languages differ and X has none for it,
    │                                       else spelling); its recipe lines now carry X
    ├──rename to Y──▶ kept name Y (lines, places, dismissals follow)
    └──delete (unused only)──▶ gone, with its other names
other name ──split out──▶ kept name of a new ingredient; lines of recipes in its language that
                          showed it move to it (variant); spelling: no line moves
```

## Domain rules (`api/domain/ingredient_catalog.py`, pure)

- `CatalogIndex.build(ingredients)` → key of each name and its singular forms → kept name.
- `shown_name(ingredient, language)` → variant for the language, else kept name (FR-006, FR-007).
- `plan_merge(index, merged, kept, merged_language, kept_language)` → the rows to change: which
  other names become variants and which become spellings (spec edge case "A already has other
  names"), or an error (`same_ingredient`, `unknown_name`).
- `check_rename(index, old, new)` → normalized new name, or `exists(kept_name)` / `blank`.
- `split_plan(ingredient, other_name, recipe_languages)` → which recipe lines move.
- `filter_pairs(index, dismissed, proposed)` (R9).
