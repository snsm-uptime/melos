# Data model: Recipe embeddings and search (spec 019)

One Alembic migration, `0014_recipe_embeddings` (after `0013_custom_units`). Upgrade, downgrade to
0013 and upgrade again must be tested. The `vector` extension already exists (migration 0002).

## recipe_embedding

| Column | Type | Rules |
|---|---|---|
| recipe_id | uuid | FK `recipe.id` ON DELETE CASCADE |
| model | text | not blank; the configured `GEMINI_EMBED_MODEL` |
| embedding | vector(768) | length checked in the adapter against `GEMINI_EMBED_DIM` (FR-025); L2-normalized |
| strategy_used | text | `toon` or `plain` (FR-021) |
| input_tokens | integer null | ≥ 0 when set (research R2) |
| input_truncated | boolean | default false; true when the service cut the input at 2,048 tokens (research R2a) |
| recipe_updated_at | timestamptz | the recipe's `updated_at` when its content was read (research R5) |
| updated_at | timestamptz | default `now()`; when this embedding was written |

- PK `(recipe_id, model)`: at most one per recipe and model (PRD 1.6).
- **Current** means `recipe_updated_at = recipe.updated_at` and `model` = the configured model. Only
  current rows are searched (FR-004, FR-018).
- At start-up the worker reads the column's dimension from `pg_attribute`. If it differs from
  `GEMINI_EMBED_DIM`, the worker logs an error once and does not run (edge case: dimension change).

## embedding_job

| Column | Type | Rules |
|---|---|---|
| recipe_id | uuid | PK; FK `recipe.id` ON DELETE CASCADE |
| due_at | timestamptz | default `now()`; indexed |
| attempts | integer | default 0, ≥ 0; unbounded |
| last_wait_s | double precision null | the wait used after the last failure (research R6) |
| claimed_until | timestamptz null | the lease of the process working on it (research R4) |
| last_failure | text null | result class name only (`Unavailable`, `LimitReached`, …), never a message (FR-023) |
| enqueued_at | timestamptz | default `now()`; used for "longest wait" (FR-009b) |

State transitions:

```text
(none) --enqueue: save, edit, snapshot, catch-up--> due
due --claim (SKIP LOCKED)--> claimed (claimed_until = now + 2 min)
claimed --success, version unchanged--> deleted (embedding written)
claimed --success, recipe changed--> due now (claimed_until cleared, attempts unchanged)
claimed --failure--> due at now + next_wait (attempts + 1, last_wait_s set)
claimed --lease expires (process died)--> due
any --recipe deleted--> gone (cascade)
enqueue on an existing row --> due now, attempts 0, last_wait_s null (upsert)
```

## search_event

| Column | Type | Rules |
|---|---|---|
| id | uuid | PK, default `gen_random_uuid()` |
| feature | text | `assistant`, `list_search`, `mcp`, `test` |
| scope_kind | text | `kitchen`, `my_notebooks`, `notebook` |
| result_count | smallint | 0 to 5 |
| model | text | |
| strategy | text | |
| min_closeness | double precision | the minimum in force when the marks were made |
| created_at | timestamptz | default `now()`; indexed, for the 180-day clean-up |

There is no person, no question text, and no kitchen or notebook id (FR-017b).

## search_result

| Column | Type | Rules |
|---|---|---|
| search_id | uuid | FK `search_event.id` ON DELETE CASCADE |
| recipe_id | uuid | FK `recipe.id` ON DELETE CASCADE |
| rank | smallint | 1 to 5 |
| score | double precision | `1 - cosine distance`, between -1 and 1 |
| mark | text | `close` or `weak` |
| used_at | timestamptz null | set by `MarkSearchResultUsed` (FR-017c) |

- PK `(search_id, recipe_id)`.

## Changes to existing code (no column changes)

- The schema guard `test_only_the_lines_and_steps_point_at_recipe_ids`
  (`api/tests/test_recipe_manage_integration.py:605`) gains `recipe_embedding`, `embedding_job` and
  `search_result`, all `CASCADE`. The `DeleteRecipeService` docstring
  (`api/application/recipe_manage.py:270`) says that search data now leaves by cascade (spec 027
  FR-016).
- Deleting a notebook or kitchen already cascades to `recipe`, and so to these three tables
  (FR-005).

## Domain values (pure, `domain/`)

- `RetryPolicy(first_s=60, growth=1.5, cap_s=7200)` and `next_wait(...)` in `domain/retry.py`.
- `SearchScope`: one of `Kitchen(kitchen_id)`, `MyNotebooks()`, `OneNotebook(notebook_id)`.
- `SearchFilters(author_id?, created_after?, created_before?, ingredient_names: tuple, exclude_recipe_ids: tuple)`.
  Ingredient names are passed through `normalize_name` and duplicates removed. `created_after`
  later than `created_before` is invalid and raises `InvalidSearchFiltersError`.
- `mark(score, minimum)` and `SEARCH_LIMIT = 5` in `domain/recipe_search.py`.
- `embed_text.toon(recipe)` and `embed_text.plain(recipe)` in `domain/embed_text.py`.
