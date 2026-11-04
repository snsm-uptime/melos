# Research: Recipe embeddings and search (spec 019)

Each item: **Decision**, **Rationale**, **Alternatives considered**. Code references are to the
repo at `worktree-kitchen-vectors` (2026-11-02).

## R1. Embedding model and dimension

- **Decision**: `GEMINI_EMBED_MODEL=gemini-embedding-001`, `GEMINI_EMBED_DIM=768`, passed as
  `EmbedContentConfig(output_dimensionality=768)`. Vectors are L2-normalized in the adapter before
  storing. Recipes use `task_type="RETRIEVAL_DOCUMENT"`, questions `task_type="RETRIEVAL_QUERY"`.
  The first task of implementation is one live call that checks the length is 768; if not, stop and
  reopen the dimension with the owner (spec Assumptions).
- **Rationale**: Owner decision (spec Clarifications). Google's reference
  ([Text embeddings API](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/text-embeddings-api),
  read 2026-11-02) lists `gemini-embedding-001` with output "up to 3072" dimensions, a 2,048-token
  input limit, and Spanish and English among its languages. `outputDimensionality` "truncates" the
  output to the size given. The page does not say outright that 768 is allowed, and it does not
  say whether truncated vectors must be normalized. Hence the live check, and normalizing anyway:
  it is harmless for cosine distance.
  `text-embedding-004` is no longer listed. The page says `gemini-embedding-001` "unifies" the
  older `text-embedding-005` and `text-multilingual-embedding-002`. The installed SDK
  (`google-genai` 2.32.0) has `EmbedContentConfig.task_type`, `title` and
  `output_dimensionality`.
- **Task types and title**: `RETRIEVAL_DOCUMENT` with `title` set to the recipe's title, which the
  page says is "only valid with `task_type=RETRIEVAL_DOCUMENT`" and helps quality. Questions use
  `RETRIEVAL_QUERY`, which is also the default when no task type is given.
- **Alternatives**: keep `text-embedding-004` (not listed any more); 3072 dimensions (larger rows,
  and the PRD fixes 768); `gemini-embedding-2` (8,192-token inputs and images, listed on the same
  page; a model change that needs the owner's approval, so not taken).

## R2. Input token count (FR-021)

- **Decision**: Store `ContentEmbedding.statistics.token_count` when the response carries it. When
  it does not (the Gemini API may leave it empty), call `models.count_tokens` once for that text in
  the same job. If that call fails, store `NULL` and do not retry for it.
- **Rationale**: Google's reference shows `statistics.token_count` and `statistics.truncated` in
  every prediction, and the SDK has both fields. That page documents the Vertex AI endpoint
  (project, region, OAuth). This app calls the Gemini Developer API with an API key, so whether
  those fields are filled there is not confirmed; the live check (quickstart step 1) records it. The token count is used only for comparing
  strategies (US5), so a missing count must never block an embedding.
- **Alternatives**: always call `count_tokens` (one more call per recipe); estimate from character
  count (not a token count).

## R2a. One text per call, and long recipes

- **Decision**: `EMBED_BATCH_SIZE` defaults to **1**: the worker sends one recipe per call and
  claims one job at a time per pass, looping while jobs are due. The value is configurable, and
  may be raised only after the live check shows the Developer API accepts several texts for this
  model. Inputs longer than 2,048 tokens are truncated by the service (`autoTruncate` defaults to
  true), and the embedding records `input_truncated` when `statistics.truncated` says so. A
  truncated recipe stays searchable by its first 2,048 tokens: title, ingredients and the first
  steps, since that is the order the text is built in.
- **Rationale**: Google's reference says "For gemini-embedding-001, each request can only include
  a single input text", and its Go, Java and Node samples loop one text per request. Its Python
  sample passes three texts, so the page contradicts itself. One per call is safe on both APIs. A
  home deployment has at most a few thousand recipes, so the extra calls are affordable, and the
  retry rule handles quota answers.
- **Alternatives**: batches of 20 (may be rejected for this model); failing over-long recipes
  (they would retry forever, since the content does not change).

## R3. Where the worker runs (constitution principle 1)

- **Decision**: One daemon thread per api process, started and stopped in a FastAPI `lifespan`
  handler (`api/app.py`). It polls the job table every `EMBED_WORKER_POLL_S` (5 s), and is woken
  early by an in-process event after a save, edit or snapshot. It is off when
  `EMBEDDING_WORKER_ENABLED=false` (test overlay, test runs).
- **Rationale**: The owner chose a worker inside the api. A thread fits the code base, which uses
  sync SQLAlchemy sessions (`adapters/persistence/db.py`) and the sync Gemini client
  (`gemini_extractor.py`), and adds no service or queue. Its state lives in Postgres, so a restart
  loses nothing (FR-012).
- **Alternatives**: FastAPI `BackgroundTasks` (lost on restart, no retries); an asyncio task
  (would need async DB and SDK calls); a fifth Compose service (ruled out by the constitution).

## R4. Job table, claiming and several processes

- **Decision**: An `embedding_job` row per recipe that needs an embedding (`recipe_id` PK, FK
  `ON DELETE CASCADE`). The worker claims a batch with
  `SELECT … WHERE due_at <= now() AND (claimed_until IS NULL OR claimed_until < now())
  ORDER BY due_at LIMIT :batch FOR UPDATE SKIP LOCKED`, sets `claimed_until = now() + lease`
  (lease 2 min), and commits before calling Gemini. Results are written in a second transaction.
- **Rationale**: `SKIP LOCKED` means two processes never take the same row (FR-012), and the lease
  means a process that dies mid-call releases its rows. No Gemini call runs inside an open
  transaction.
- **Alternatives**: advisory locks (harder to inspect); a `status` column state machine (more
  states, same effect).

## R5. Never serving a stale embedding (FR-003, FR-004, edge cases)

- **Decision**: Each embedding stores `recipe_updated_at`, the recipe's `updated_at` at the moment
  its content was read. Search joins only rows where `recipe_embedding.recipe_updated_at =
  recipe.updated_at`. The worker writes with `INSERT … SELECT … FROM recipe WHERE id = :id AND
  updated_at = :read_version ON CONFLICT (recipe_id, model) DO UPDATE`. If no row is written, the
  recipe changed or was deleted. Its job stays due now, or has already gone by cascade.
- **Rationale**: `updated_at` is already the edit version token. It is bumped with
  `clock_timestamp()` in `SqlAlchemyRecipeRepository.replace` (`adapters/persistence/recipes.py:171`),
  and no other code writes it. An edit therefore takes the old embedding out of search in the same
  transaction, with no extra delete. A worker reading the old content can never overwrite the new.
- **Alternatives**: delete the embedding on edit (a worker could still write the old content
  afterwards); a content hash (needs the text rebuilt on every search).

## R6. Retry rule (FR-009, FR-009a)

- **Decision**: A pure function in `domain/retry.py`:
  `next_wait(previous_s, *, first_s, growth, cap_s, service_wait_s) -> float`. The first wait is
  `first_s`, then `min(previous_s * growth, cap_s)`, and never less than the service's
  `Retry-After`. Defaults: `first_s=60`, `growth=1.5`, `cap_s=7200`. A `RetryPolicy` dataclass holds
  them, and each job loads its own values from settings with these defaults (`EMBED_RETRY_*`). The
  attempts count is unbounded. A success deletes the job, which resets the wait.
- **Rationale**: Owner decision (spec Clarifications), kept pure so it can be reused and tested
  without I/O.
- **Alternatives**: a library such as tenacity (it retries inside one call, which PRD §1.7
  forbids, and adds a dependency).

## R7. Enqueueing and catch-up (FR-002, FR-006, FR-010, FR-011, FR-013)

- **Decision**:
  - Save (`SaveRecipeDraft`) and edit (`UpdateRecipeService`) call a new port
    `EmbeddingJobs.enqueue(recipe_ids)` in the request's transaction. It is an upsert, so
    `due_at = now()`, `attempts = 0`. A replayed save does not enqueue (FR-007).
  - Snapshot: `AddNotebookSnapshotService` calls `EmbeddingJobs.enqueue_notebook(notebook_id)`
    after `copy_all`. It is one `INSERT … SELECT id FROM recipe WHERE notebook_id = :id`.
  - Catch-up: `EmbeddingJobs.enqueue_missing(model, strategy=None)`.
    `INSERT … SELECT r.id FROM recipe r WHERE NOT EXISTS (current embedding for model) ON
    CONFLICT DO NOTHING`. With `--reembed-other-strategy` it also includes rows whose
    `strategy_used` differs. It runs as the worker thread's first step, so it never delays
    start-up, and as `uv run python -m scripts.embeddings catch-up`.
  - After the request's commit the route sets the worker's wake event.
- **Rationale**: Enqueueing in the same transaction means a saved recipe can never miss its job.
  The insert is one indexed row, so save time is unchanged (SC-002). The snapshot stays one
  statement (SC-006).
- **Alternatives**: embed inline with a timeout (slows saves and fails them during outages,
  against the owner's decision); detect missing embeddings only by scanning (no per-recipe retry
  state).

## R8. Text that is embedded (FR-022)

- **Decision**: Port `EmbedTextStrategy` (`name: str`, `render(recipe: RecipeDetail) -> str`).
  Two implementations live in `domain/embed_text.py`, selected by `EMBED_TEXT_STRATEGY`:
  - `toon` (default): the PRD B.3 shape with the `id` field left out, because an id adds noise to
    a meaning fingerprint. It is encoded with the `python-toon` library (`from toon import encode`),
    as PRD Appendix D decided.
  - `plain`: title, servings, one line per ingredient and the steps as sentences.

  The same TOON encoder becomes the assistant's context encoder in S-030.
- **Rationale**: PRD §1.5 E and B.3, and the owner's A/B intent (`dev/memory/171026.md`).
- **Library**: `uv add python-toon`, which the PRD Appendix D decided. Say so at implementation.
  It is pure Python, so `domain/` may import it (constitution 3 forbids only adapters, api,
  FastAPI, SQLAlchemy and the SDK).
- **Alternatives**: a hand-written TOON encoder (`domain/toon.py` from PRD 1.4). Appendix D
  replaced that with the library.

## R9. Vector column without a new library

- **Decision**: A small SQLAlchemy `UserDefinedType` `Vector(dim)` in
  `adapters/persistence/vector.py` that binds `"[v1,v2,…]"` text and reads it back. Search uses
  `embedding <=> CAST(:q AS vector)` (cosine distance), and score = `1 - distance`.
- **Rationale**: Avoids adding the `pgvector` Python package, since AGENTS.md says to ask before
  adding libraries, and only two operations are needed. The extension is already installed by
  migration `0002_pgvector_kitchen_lang`.
- **Alternatives**: the `pgvector` package (cleaner, but a new dependency that needs approval).

## R10. Index and filters (FR-017, SC-007)

- **Decision**: No approximate index (HNSW or IVFFlat) in this story. Search filters first with
  plain indexed predicates: `notebook_id = ANY(:ids)`, `author_id`, `created_at` range,
  `NOT (id = ANY(:exclude))`, and ingredient "all" through
  `(SELECT count(DISTINCT name) FROM recipe_ingredient WHERE recipe_id = r.id AND name = ANY(:names)) = :n`.
  It then orders by exact cosine distance and takes `LIMIT 5`.
- **Rationale**: A kitchen holds hundreds to a few thousand recipes. An exact scan of 1,000 vectors
  of 768 values takes milliseconds (SC-007), and it is always correct with filters. An approximate
  index filters after ranking and can return fewer than five matches.
- **Alternatives**: HNSW with iterative scan. Revisit if a single scope passes about 50,000 recipes.

## R11. Search errors (FR-019)

- **Decision**: The `Embedder` port returns the same result classes as the extractor
  (`application/recipe_extraction.py`: `LimitReached`, `Unavailable`, `InvalidOutput`,
  `AIProviderError`), mapped by the same `_classify` logic, moved to a shared
  `adapters/llm/gemini_errors.py`. When the question cannot be embedded, the search use case
  raises `SearchQuestionNotEmbedded(outcome)`, which carries that result unchanged; no new AI
  error types are added. Consumers that add routes (S-030, S-044) map `outcome` exactly as
  `api/api/routes/recipe_capture.py` does: 429 with `Retry-After`, 503, 422.
- **Rationale**: One mapping for every Gemini call (constitution 3).

## R12. Closeness mark and records (FR-017 to FR-017e)

- **Decision**: `SEARCH_MIN_CLOSENESS` defaults to **0.65**, a provisional value: typical
  related-text cosine scores for Gemini embeddings sit around 0.6 to 0.8, and the records will
  replace this guess. `domain/recipe_search.py` gains `mark(score, minimum) -> "close" | "weak"`.
  Each search writes one `search_event` row (feature, scope kind, result count, model, strategy,
  time) and one `search_result` row per result. `MarkSearchResultUsed(search_id, recipe_id)` sets
  `used_at`. A daily clean-up job in the same worker thread deletes events older than
  `SEARCH_RECORD_RETENTION_DAYS` (180), and its results cascade. The report command prints the used
  share per 0.05 band.
- **Rationale**: Spec FR-017b keeps no question and no person, so the records are not personal
  data. The cascade from recipe deletion keeps FR-005 true for records too.

## R13. Access per scope (FR-015, FR-016)

- **Decision**:
  - `kitchen`: uses `AuthorizeKitchenAccessService(action="read_kitchen")` and
    `NotebookRepository.kitchen_ids_for`, like `ListKitchenRecipesService`
    (`application/recipe_lists.py:86`). Archived kitchens are allowed.
  - `my_notebooks`: uses `NotebookRepository.personal_ids_for(user_id)`, computed at search time.
  - `notebook`: uses `NotebookRepository.facts_for(user_id, notebook_id)`, and `None` raises
    `NotebookNotFoundError`.
  - An empty notebook set returns an empty result without an embedding call.
- **Rationale**: Reuses the checks every list already uses, so the 404 rules stay identical.

## R14. No configuration (FR-014)

- **Decision**: With an empty key or model, the worker logs once at INFO ("embeddings not
  configured") and sleeps. Jobs keep accumulating and are processed once the key is set. Search
  raises the `AIProviderError` mapping ("unavailable").
