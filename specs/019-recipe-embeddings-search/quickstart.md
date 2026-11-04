# Quickstart: validate recipe embeddings and search (spec 019)

Validation guide only. See [data-model.md](data-model.md) for tables and
[contracts/](contracts/) for the use case, worker and commands.

## Prerequisites

- This worktree's stack: `./scripts/compose-up.sh -d` (project `melos-kitchen-vectors`, UI on
  port 3050). Never the primary stack's data directory.
- `GEMINI_API_KEY` set in this worktree's `.env`, needed for steps 1, 3, 4 and 6. Steps 2 and 5
  need no key.
- Migration 0014 applied (the api runs Alembic on start).
- A shell for the commands: `docker compose -p melos-kitchen-vectors exec api uv run python -m scripts.embeddings <sub>`.

## 0. Automated checks

- `./scripts/compose-test.sh`: all api tests, including the new domain, application (fakes) and
  integration tests. The integration tests cover claim with `SKIP LOCKED` across two sessions, the
  stale-version write, the cascades and the schema guard. Expect the same pre-existing failures
  only.
- `cd api && uv run ruff check .`
- Migration: upgrade, downgrade to `0013_custom_units`, upgrade again on a scratch database.

## 1. Model check (research R1). Do this first.

Run one embed call through the adapter (a test marked `live`, skipped without a key). Expect a
vector of 768 values with norm 1 after normalizing. If the length is not 768, stop and ask the
owner. Also record in `notes.md`:

- whether the Developer API fills `statistics.token_count` and `statistics.truncated` (research R2);
- whether a call with two texts succeeds for this model. If it does, `EMBED_BATCH_SIZE` may be
  raised (research R2a).

## 2. Saving never waits for or fails on the service (SC-002, US3)

1. Set `GEMINI_API_KEY` to an invalid value in the worktree `.env` and restart the api.
2. Save a captured recipe and edit another in the UI (port 3050). Both succeed, no error shows, and
   the timings are the same as with a valid key.
3. `… scripts.embeddings status` shows both recipes waiting, with failures of class
   `AIProviderError`.
4. Watch the api logs. Retries follow 60 s, 90 s, 135 s… (`last_wait_s` grows by 1.5).

## 3. Healing and catch-up (SC-001, SC-003, SC-005, US1)

1. Restore the valid key and restart the api. Its start-up queues every recipe without a current
   embedding, and `status` drops to 0 within a few minutes.
2. Run `… scripts.embeddings catch-up` again and expect `queued=0`.
3. Save a new recipe. Within 1 minute `status` is 0 again and the recipe has a row.

## 4. Search scope and filters (SC-004, US2)

Use the integration test helper or a Python shell in the api container to call
`SearchRecipesService` (contract: [search-service.md](contracts/search-service.md)) with invented
data: two kitchens, Ana's and Ben's personal notebooks, and a kitchen notebook.

- Kitchen scope for a member returns at most 5 hits, all from that kitchen.
- Kitchen scope for a non-member raises `KitchenNotFoundError`.
- `MyNotebooks` returns personal notebooks only, never kitchen ones.
- `OneNotebook` on a notebook the person doesn't belong to raises `NotebookNotFoundError`.
- An ingredient filter of `["chicken", "rice"]` returns only recipes with both.
- Every hit has a score and a `close` or `weak` mark, and a `search_event` row exists, including
  for a search with 0 hits.

## 5. Edit and delete (SC-008, FR-004, FR-005)

1. Edit a recipe's title. Until its job runs, a search never returns it (its embedding is not
   current).
2. Delete a recipe. Its `recipe_embedding`, `embedding_job` and `search_result` rows are gone.

## 6. Snapshot (SC-006, US4)

Add a snapshot of a personal notebook with several recipes. The snapshot takes no longer than
before. `status` shows the copies queued, and within 5 minutes a kitchen search finds them (SC-006).

## 7. Records and report (SC-009)

`… scripts.embeddings score-report` prints bands of 0.05 with shown and used counts.
`… scripts.embeddings cleanup` prints `deleted=N`. Rows older than 180 days in a scratch database
are removed.

Record what was walked and what was not in `specs/019-recipe-embeddings-search/notes.md`.
