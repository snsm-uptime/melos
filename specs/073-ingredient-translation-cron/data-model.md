# Data Model: Scheduled Ingredient Translation Service

Additive changes only. The per-notebook and kitchen catalogs (`ingredient`, `ingredient_name`) and
`recipe_ingredient` are not changed (spec Q2, revised; research.md R4). One Alembic migration,
`0022_standard_ingredients`, creates the tables below (research.md R9).

## New: `standard_ingredient` (the standard catalog)

One row per real-world ingredient in the standard table. Separate from every notebook catalog.

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid, PK | |
| `normalized_name` | text, not null, **unique** | Trimmed, lower-case, singular (existing rule in `domain.ingredient_catalog`). Discovery key (R5). |
| `language` | varchar(2), not null | The language of the name that was discovered first: `en` or `es`. |
| `ai_checked_at` | timestamptz, nullable | Set once the model has answered, valid or invalid. Null means "not yet checked" (R3). |
| `created_at` | timestamptz, not null | |

Constraints:
- `UNIQUE (normalized_name)`.
- `CHECK (language IN ('en', 'es'))`.

## New: `standard_ingredient_name` (standard names per language)

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid, PK | |
| `standard_ingredient_id` | uuid, FK `standard_ingredient.id`, cascade | |
| `name` | text, not null | The standard name in `language`, trimmed, at most 80 characters, no newline. |
| `language` | varchar(2), not null | `en` or `es`. |
| `source` | text, not null | `discovery` (the first name, from a recipe), `ai` (the model's translation), or `admin` (an accepted custom value). |
| `model` | text, nullable | The model name that produced an `ai` row. |
| `created_at` | timestamptz, not null | |

Constraints:
- `UNIQUE (standard_ingredient_id, language)`: one standard name per language per ingredient.
- `CHECK (source IN ('discovery', 'ai', 'admin'))`.
- `CHECK (source <> 'ai' OR model IS NOT NULL)`.

Validation rules:
- A `source = 'ai'` row is written only by the translation use case, after a valid answer, in the
  same transaction that sets `standard_ingredient.ai_checked_at` (R3, data-model rule below).
- `source = 'admin'` is written only by accepting a review row (R11).
- No person writes this table directly (FR-021).

## New: `standard_ingredient_review` (admin validation of custom values)

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid, PK | |
| `standard_ingredient_id` | uuid, FK `standard_ingredient.id`, cascade | The ingredient whose AI-made name was replaced. |
| `replaces_name` | text, not null | The AI-made name being replaced. |
| `proposed_name` | text, not null | The person's custom value. |
| `proposed_language` | varchar(2), not null | `en` or `es`. |
| `proposed_by` | uuid, FK `users.id`, on delete set null | The person who entered it. Null if the account is deleted. |
| `status` | text, not null, default `pending` | `pending`, `accepted`, or `rejected`. |
| `decided_by` | uuid, FK `users.id`, nullable | The admin who decided. |
| `decided_at` | timestamptz, nullable | |
| `created_at` | timestamptz, not null | |

Constraints:
- `CHECK (status IN ('pending', 'accepted', 'rejected'))`.
- `CHECK ((status = 'pending') = (decided_by IS NULL))`.
- Index `ix_standard_review_status_created (status, created_at)`, for the admin list.

## New: `job_run`

One row per hourly run.

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid, PK | |
| `started_at` | timestamptz, not null | Taken before the scan. The next run's watermark (R5). |
| `finished_at` | timestamptz, nullable | Null while running. |
| `status` | text, not null | `running`, `succeeded`, `failed` or `skipped`. |
| `found` | integer, not null, default 0 | New standard ingredients created in this run. |
| `translated` | integer, not null, default 0 | Valid translations saved. |
| `rejected` | integer, not null, default 0 | Names the model marked invalid. |
| `failed` | integer, not null, default 0 | Calls that errored or returned unusable output. |
| `error` | text, nullable | A run-level error, if any. |

Constraints: `CHECK (status IN ('running', 'succeeded', 'failed', 'skipped'))`;
`CHECK (found >= 0 AND translated >= 0 AND rejected >= 0 AND failed >= 0)`.

Index: `ix_job_run_status_started (status, started_at)`, for "last successful run".

The advisory lock is held in Postgres, not stored (R2).

## Existing, used but not changed

- `recipe` (`updated_at`, `language`), used by discovery (R5). An index on `updated_at` is added:
  `ix_recipe_updated_at`.
- `recipe_ingredient` (`name`, `recipe_id`), read by discovery. No change.
- `ingredient`, `ingredient_name`: the notebook and kitchen catalogs. No change.
- `users` (`is_admin`), used by the review list and the accept/reject actions (spec 055).

## Relationships

```text
standard_ingredient 1 ──< standard_ingredient_name     (one per language)
standard_ingredient 1 ──< standard_ingredient_review   (custom values awaiting or decided)
job_run                                                (standalone)
recipe_ingredient ···· discovery reads its name ···· standard_ingredient (by normalized_name)
```

No table stores a list of recipe ids. Recipe lines carry no standard id (FR-018 and R4).

## Data model rule: AI result and check marker in one transaction

A translation and the `ai_checked_at` mark it records are written in one transaction. A crash never
leaves a translation saved but unmarked, or marked but not saved.
