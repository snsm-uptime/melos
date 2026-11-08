# Data Model: Ingredients Table Layout (spec 074)

No tables, columns or migrations are added. This file lists the read models the feature uses.

## Admin ingredient row (one per name, across all notebooks)

Built by `_INGREDIENTS` in `api/adapters/persistence/admin.py`, then enriched in the application layer (R1, R3).

| Field | Source | Notes |
|---|---|---|
| `name` | `recipe_ingredient.name` union `ingredient.name` | Raw name; grouping key of the row. |
| `recipes` | `COUNT(DISTINCT recipe_ingredient.recipe_id)` | Existing. |
| `people` | `COUNT(DISTINCT recipe.author_id)` | Existing. Distinct authors (spec 055). |
| `notebooks` | `COUNT(DISTINCT ingredient.notebook_id)` where `ingredient.name = name` | New (R2). |
| `standard_status` | `standard_ingredient` via `discovery_key(name)` | New. One of `checked`, `pending`, `rejected` (R3). |
| `sources` | `standard_ingredient_name.source` for the matched standard row | New. Set of `discovery`, `ai`, `admin`. |

**Validation rules**
- `standard_status` is `pending` when no standard row matches the key.
- `sources` is empty when no standard row matches.

## Admin review item (one per flagged value)

Read from `standard_ingredient_review` (spec 073 data model), filtered to `status = 'pending'`.

| Field | Source |
|---|---|
| `id` | `standard_ingredient_review.id` |
| `replaces_name` | `standard_ingredient_review.replaces_name` |
| `proposed_name` | `standard_ingredient_review.proposed_name` |
| `proposed_language` | `standard_ingredient_review.proposed_language` |
| `proposed_by` alias | `users.alias` via `proposed_by` (admin only) |
| `created_at` | `standard_ingredient_review.created_at` |

**Ordering**: `created_at` descending. The spec 073 index `ix_standard_review_status_created (status, created_at)` serves this query.

## User views (no change to data)

- **Catalog view**: `ingredient`, `ingredient_name` (other names), `recipe_count` and actions as today. Language column always shown (R6).
- **Places view**: `ingredient_place` and `recipe_ingredient` as today. Name follows the viewer's language (R7).

## Relationships used

```text
ingredient (notebook_id, name) ──< ingredient_name (kind, language)
recipe_ingredient (name) ──> recipe (id, author_id, notebook)
standard_ingredient (normalized_name = discovery_key) ──< standard_ingredient_name (source)
standard_ingredient ──< standard_ingredient_review (status = pending)
```
