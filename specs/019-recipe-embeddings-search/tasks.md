---
description: "Task list for spec 019: recipe embeddings and search pre-filtered by kitchen"
---

# Tasks: Recipe embeddings and search pre-filtered by kitchen

**Input**: Design documents from `specs/019-recipe-embeddings-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/search-service.md, contracts/worker-and-commands.md, quickstart.md

**Tests**: Included. The constitution (principle 6) requires domain tests, application tests against fake ports, and integration tests against Postgres. Write each story's tests first and see them fail.

**Organization**: Grouped by user story (spec.md US1–US5). All paths are from the repository root. Run Python with `cd api && uv run …`. The canonical full run is `./scripts/compose-test.sh`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

**Purpose**: confirm the model, add the one library, and add the settings.

- [X] T001 Run the live model check of research R1/R2a before anything else. Write a throwaway script under the session scratchpad (not in the repo) that calls `google.genai.Client(api_key=…).models.embed_content(model="gemini-embedding-001", contents=["arroz con tomate"], config={"task_type": "RETRIEVAL_DOCUMENT", "title": "arroz", "output_dimensionality": 768})`, and once more with two texts. Record in `specs/019-recipe-embeddings-search/notes.md`: the vector length (must be 768), whether `statistics.token_count` and `statistics.truncated` are filled, and whether two texts in one call succeed. **If the length is not 768, stop and ask the owner** (spec Assumptions). Never print or write the key.
- [X] T002 Add the TOON library: `cd api && uv add python-toon`. The owner chose this library in PRD Appendix D ("✓ TOON encoder: Use python-toon"), which counts as the approval AGENTS.md asks for; name the added library in the final report. then check `from toon import encode` works in `uv run python -c`.
- [X] T003 [P] Add `EmbeddingSettings` and `load_embedding_settings()` to `api/api/settings.py`, with every variable and default from contracts/worker-and-commands.md "Settings": `GEMINI_EMBED_MODEL` (default `gemini-embedding-001`), `GEMINI_EMBED_DIM` (768), `EMBED_TEXT_STRATEGY` (`toon`|`plain`, default `toon`), `EMBEDDING_WORKER_ENABLED` (default true), `EMBED_WORKER_POLL_S` (5), `EMBED_BATCH_SIZE` (1), `EMBED_RETRY_FIRST_WAIT_S` (60), `EMBED_RETRY_GROWTH` (1.5), `EMBED_RETRY_CAP_S` (7200), `SEARCH_MIN_CLOSENESS` (0.65), `SEARCH_RECORD_RETENTION_DAYS` (180). Reuse `_env_float` and `_env_int`. The key stays `repr=False`. Reject an unknown strategy name, growth ≤ 1, a cap below the first wait, and a closeness outside -1..1, with a `ValueError` naming the variable.
- [X] T004 [P] Update `.env.example` (no real values) and `docker-compose.yml` (`api.environment`, pass each variable through with the defaults above; change the `GEMINI_EMBED_MODEL` default from `text-embedding-004` to `gemini-embedding-001`), and set `EMBEDDING_WORKER_ENABLED: "false"` in `docker-compose.test.yml`. Also set it to false in `api/tests/conftest.py` for host test runs.

---

## Phase 2: Foundational (blocking all stories)

**Purpose**: tables, ports, the vector type and the Gemini embedder. Nothing user-visible yet.

- [X] T005 Create `api/adapters/persistence/vector.py`: a SQLAlchemy `UserDefinedType` `Vector(dim)` whose `get_col_spec()` is `vector(dim)`. Its bind processor turns a sequence of floats into the text `"[v1,v2,…]"` and its result processor parses it back into a tuple of floats. Raise `ValueError` on a wrong length (research R9). No `pgvector` package.
- [X] T006 Add the four models to `api/adapters/persistence/models.py`, exactly as in data-model.md:
  - `RecipeEmbeddingModel` (`recipe_embedding`): PK `(recipe_id, model)`; `recipe_id` FK `recipe.id` ON DELETE CASCADE; `embedding Vector(768)` not null; `strategy_used` text not null; `input_tokens` integer null with a check "≥ 0 when set"; `input_truncated` boolean "default false"; `recipe_updated_at` timestamptz not null; `updated_at` timestamptz default `now()`.
  - `EmbeddingJobModel` (`embedding_job`): `recipe_id` PK FK ON DELETE CASCADE; `due_at` default `now()`, indexed; `attempts` integer "default 0, ≥ 0"; `last_wait_s` double precision null; `claimed_until` timestamptz null; `last_failure` text null ("result class name only … never a message"); `enqueued_at` default `now()`.
  - `SearchEventModel` (`search_event`): `id` uuid PK default `gen_random_uuid()`; `feature` check in (`assistant`,`list_search`,`mcp`,`test`); `scope_kind` check in (`kitchen`,`my_notebooks`,`notebook`); `result_count` smallint check 0–5; `model`, `strategy` text; `min_closeness` double precision; `created_at` default `now()`, indexed.
  - `SearchResultModel` (`search_result`): PK `(search_id, recipe_id)`; `search_id` FK `search_event.id` ON DELETE CASCADE; `recipe_id` FK `recipe.id` ON DELETE CASCADE; `rank` smallint check 1–5; `score` double precision; `mark` check in (`close`,`weak`); `used_at` timestamptz null.
- [X] T007 Write migration `api/adapters/persistence/migrations/versions/0014_recipe_embeddings.py` (down_revision `0013_custom_units`) creating the four tables, constraints and indexes from T006. The downgrade drops them in reverse order and leaves the `vector` extension alone (it belongs to 0002).
- [X] T008 [P] Write `api/tests/test_recipe_embeddings_migration.py`, following `api/tests/test_shopping_lists_migration.py`: upgrade to head, downgrade to `0013_custom_units`, upgrade again; check the tables, the `vector(768)` column type and the CASCADE options.
- [X] T009 Update the schema guard in `api/tests/test_recipe_manage_integration.py` (`test_only_the_lines_and_steps_point_at_recipe_ids`) so its expected dict adds `"recipe_embedding": "CASCADE"`, `"embedding_job": "CASCADE"` and `"search_result": "CASCADE"`. Update the docstring of `DeleteRecipeService` in `api/application/recipe_manage.py` to say that search data (S-019) now leaves by cascade (spec 027 FR-016).
- [X] T010 Add the ports to `api/application/ports.py`, exactly as listed in contracts/search-service.md "Ports": `Embedder` (with `embed_documents(texts, titles, timeout_s)`, `embed_query`, `count_tokens`, `model`, `dimension`), `EmbedTextStrategy`, `EmbeddingJobs`, `RecipeEmbeddings`, `SearchRecords`. Also add the frozen dataclasses `Embedded(vectors, token_counts, truncated)`, `Backlog(count, oldest_enqueued_at)`, `RawHit(recipe_id, notebook_id, title, score)` and `Band(low, high, shown, used)`. The result classes `LimitReached`, `Unavailable`, `InvalidOutput` and `AIProviderError` are reused from `application/recipe_extraction.py`.
- [X] T011 Move the SDK error classification out of `api/adapters/llm/gemini_extractor.py` (`_classify`, `_retry_after_seconds`, `_find_retry_delay`, `RETRY_DELAY_PATTERN`) into a new `api/adapters/llm/gemini_errors.py` with a public `classify(exc)`. Import it back in the extractor with no behaviour change, so `api/tests/test_gemini_extractor_adapter.py` passes unchanged (research R11).
- [X] T012 Create `api/adapters/llm/gemini_embedder.py` (`GeminiEmbedder`), implementing `Embedder`:
  - The key and model come only from settings. One attempt per call (`HttpRetryOptions(attempts=1)`), with the timeout from `GEMINI_TEXT_TIMEOUT_S`.
  - Documents: `task_type="RETRIEVAL_DOCUMENT"`, `title` = the recipe title, `output_dimensionality=dimension`, one text per call when `EMBED_BATCH_SIZE` is 1. Queries: `task_type="RETRIEVAL_QUERY"`.
  - Each vector's length must equal `dimension`, else return `InvalidOutput` (FR-025). L2-normalize each vector.
  - Read `statistics.token_count` and `statistics.truncated` when present.
  - Errors go through `gemini_errors.classify`. An empty key or model returns `AIProviderError` without calling.
  - Logs: class name and request ref only, never text, vectors or messages (FR-023).
- [X] T013 [P] Write `api/tests/test_gemini_embedder_adapter.py`, following `test_gemini_extractor_adapter.py` with a fake client: task types and title passed, 768 asked for, a wrong length becomes `InvalidOutput`, vectors are normalized to norm 1, 429 becomes `LimitReached` with retry-after, 5xx and transport errors become `Unavailable`, 401 becomes `AIProviderError`, and no text appears in captured logs. Add one test marked `@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), …)` that makes a real call and checks length 768.
- [X] T014 [P] Create `api/tests/embedding_fakes.py` with `FakeEmbedder` (deterministic vectors from a hash of the text, normalized; can be set to return a given failure class; counts calls), `FakeEmbeddingJobs`, `FakeRecipeEmbeddings` and `FakeSearchRecords`, all in memory, matching the port signatures from T010.

**Checkpoint**: migration applied, ports and embedder in place, `./scripts/compose-test.sh` green apart from the known failures.

---

## Phase 3: User Story 1 - Every recipe becomes findable (P1) 🎯 MVP

**Goal**: new, edited and pre-existing recipes get one current embedding without the member doing anything, and saving is unchanged.

**Independent test**: save a recipe, edit another, start the api against a database with older recipes, and see each end with exactly one current embedding (quickstart step 3). Spec US1 scenarios 1–4.

### Tests for US1

- [X] T015 [P] [US1] Write `api/tests/test_embed_text_domain.py` for `domain/embed_text.py`:
  - `toon` renders the B.3 shape without `id` (title, base_servings, the ingredients table with name, quantity, unit, size, preparation and vague_note, then the steps) using `toon.encode`.
  - `plain` renders title, servings, one line per ingredient and the steps.
  - Both put title and ingredients before the steps (research R2a).
  - A recipe with no steps or a vague-only line renders without error.
- [X] T016 [P] [US1] Write `api/tests/test_embedding_worker_application.py` with the fakes from T014:
  - One pass of `EmbedPendingRecipes` claims, renders, embeds and writes.
  - A job whose recipe changed between read and write is released as due now, not written (FR-004).
  - A deleted recipe is dropped.
  - A missing token count calls `count_tokens` once, and a failing `count_tokens` stores `None`.
  - An empty key makes the pass do nothing and log once (FR-014).
- [X] T017 [P] [US1] Write `api/tests/test_embeddings_integration.py` against Postgres:
  - `enqueue` is an upsert that resets `attempts` and `last_wait_s`.
  - `enqueue_missing` queues only recipes without a current embedding for the model, and a second run queues 0 (SC-005).
  - Two sessions claiming at once with `FOR UPDATE SKIP LOCKED` never get the same recipe (FR-012).
  - An expired `claimed_until` makes a job claimable again.
  - `write_if_current` writes when `updated_at` is unchanged, writes nothing after an edit, and writes nothing for a deleted recipe.
  - Deleting a recipe, a notebook or a kitchen removes its `recipe_embedding` and `embedding_job` rows (FR-005).
- [X] T018 [P] [US1] Extend `api/tests/test_recipe_save_application.py` and `api/tests/test_recipe_manage_application.py`: a created save enqueues its recipe id once; a replayed save (same save key) enqueues nothing (FR-007); an edit enqueues; a refused save or edit enqueues nothing.

### Implementation for US1

- [X] T019 [P] [US1] Create `api/domain/embed_text.py` with `toon(recipe) -> str` and `plain(recipe) -> str` over the domain's recipe detail values (research R8). Add `STRATEGIES = {"toon": toon, "plain": plain}`. Pure: imports only `toon` and the domain.
- [X] T020 [US1] Create `api/adapters/persistence/embeddings.py` with `SqlAlchemyEmbeddingJobs` (enqueue upsert, `enqueue_notebook`, `enqueue_missing` with `ON CONFLICT DO NOTHING`, `claim` using `FOR UPDATE SKIP LOCKED` with a lease, `fail`, `release_changed`, `backlog`) and `SqlAlchemyRecipeEmbeddings.content_for` / `write_if_current`. `write_if_current` is `INSERT … SELECT … FROM recipe WHERE id = :id AND updated_at = :read_version ON CONFLICT (recipe_id, model) DO UPDATE`; it deletes the job when a row was written and returns whether it was (research R4, R5).
- [X] T021 [US1] Create `api/application/embedding_worker.py` with `EmbedPendingRecipes.run_once() -> int`: claim `EMBED_BATCH_SIZE` jobs, read content and version, render with the configured `EmbedTextStrategy`, call `embed_documents` once, then write each with `write_if_current`, or `release_changed` when it changed. The failure branch calls `EmbeddingJobs.fail` with a placeholder wait of `EMBED_RETRY_FIRST_WAIT_S`; US3 replaces it with the growing rule. Logs carry counts only.
- [X] T022 [US1] Enqueue in the write paths. In `SaveRecipeDraft.execute` (`api/application/recipe_save.py`), take an `EmbeddingJobs` constructor argument and call `enqueue([stored.id])` after `add` succeeds, not in `_replay`. In `UpdateRecipeService.execute` (`api/application/recipe_manage.py`), call `enqueue([command.recipe_id])` after `replace`. Wire `SqlAlchemyEmbeddingJobs(db)` into both in `api/api/deps.py` (`get_save_recipe_draft`, `get_update_recipe`).
- [X] T023 [US1] Create `api/api/worker.py`. Begin the file with the constitution exception comment (constitution "Exceptions": documented "in a comment at the top of the relevant code file"): `# Constitution exception (principle 1, "No queue, no worker"): approved in writing by the project lead on 2026-11-02 (specs/019-recipe-embeddings-search/spec.md, Clarifications). Scope: background jobs running inside the api process, with their state in Postgres. No new service and no queue system.` Then add an `EmbeddingWorker` daemon thread with a `threading.Event` for waking, a stop flag and a session factory from `adapters/persistence/db.py`. On start it checks that the column dimension (`pg_attribute` for `recipe_embedding.embedding`) equals `GEMINI_EMBED_DIM`; if not it logs an error once and does not run. Then it runs `enqueue_missing(model)` as the catch-up (FR-010), and loops `run_once` while jobs are due, waiting `EMBED_WORKER_POLL_S` or until woken. Each pass uses its own session and commits. Add `wake_embedding_worker(app)`.
- [X] T024 [US1] Add a FastAPI `lifespan` to `create_app` in `api/api/app.py` that starts the worker when `EMBEDDING_WORKER_ENABLED` is true and stops it on exit (join up to 5 s). Call `wake_embedding_worker(request.app)` in `api/api/routes/recipes.py`, after a created save in `save_recipe` (`POST /recipes`) and after a successful edit.
- [X] T025 [US1] Create `api/scripts/embeddings.py` with `argparse` subcommands `catch-up` (prints `queued=N`) and `status` (backlog count, oldest wait in seconds, failures by `last_failure` class). Exit 0, or 1 on a database error. Run as `uv run python -m scripts.embeddings …` (contracts/worker-and-commands.md).

**Checkpoint**: US1 independently testable. Quickstart step 3 with a valid key.

---

## Phase 4: User Story 2 - Search returns only what the person may read (P1)

**Goal**: the in-process search with three scopes, filters, close or weak marks, and result records.

**Independent test**: spec US2 scenarios 1–7 and SC-004 with invented people, kitchens and notebooks (quickstart step 4).

### Tests for US2

- [X] T026 [P] [US2] Extend `api/tests/test_recipe_search_domain.py`:
  - `mark(score, minimum)` returns `close` at or above the minimum and `weak` below it.
  - `SearchFilters` normalizes and de-duplicates ingredient names with `normalize_name`.
  - `created_after` later than `created_before` raises `InvalidSearchFiltersError`.
  - An empty or blank question raises `InvalidSearchQuestionError`.
  - `SEARCH_LIMIT == 5`.
- [X] T027 [P] [US2] Write `api/tests/test_recipe_search_application.py` with the fakes:
  - Each scope resolves its notebook ids (kitchen through `kitchen_ids_for`, my notebooks through `personal_ids_for`, one notebook through `facts_for`).
  - Non-members get `KitchenNotFoundError` or `NotebookNotFoundError`, and no embedder call is made.
  - An empty scope returns no hits, makes no embedder call and records nothing.
  - An embedder failure raises `SearchQuestionNotEmbedded` carrying the embedder's result unchanged, and records nothing.
  - Hits are marked against the minimum. One event is recorded even with 0 hits (FR-017b). `MarkSearchResultUsed` sets `used_at` once and returns `False` for unknown pairs.
- [X] T028 [P] [US2] Write `api/tests/test_recipe_search_integration.py` against Postgres with invented data (two kitchens; Ana's two personal notebooks and one shared with Ben; a kitchen notebook), with embeddings written directly through `write_if_current` from `FakeEmbedder` vectors:
  - Kitchen scope returns only that kitchen's notebooks.
  - My notebooks returns only personal notebooks (US2 3a). One notebook returns only it (US2 3b).
  - The ingredient filter `["chicken", "rice"]` returns only recipes with both (FR-015a).
  - The author, date and exclude filters work.
  - Stale embeddings (after `replace`) and other models are never returned (FR-004, FR-018).
  - At most 5 hits, closest first.
  - The cross-person matrix of SC-004 returns zero foreign hits.
  - A 1,000-recipe kitchen search runs in under 1 s in the test harness (SC-007).
  - Records are deleted with their recipe.
  - An archived kitchen stays searchable for its members.
  - A member removed from a kitchen gets `KitchenNotFoundError` on their next search.

### Implementation for US2

- [X] T029 [P] [US2] In `api/domain/recipe_search.py` add `SEARCH_LIMIT = 5`, `SearchScope` (`Kitchen`, `MyNotebooks`, `OneNotebook`), `SearchFilters` and `mark()`. In `api/domain/errors.py` add `InvalidSearchQuestionError` and `InvalidSearchFiltersError`. No new AI error types: Gemini failures keep the existing result classes (next task).
- [X] T030 [US2] Add `SqlAlchemyRecipeEmbeddings.search(notebook_ids, filters, model, query_vector, limit)` in `api/adapters/persistence/embeddings.py`, as in research R10:
  - Join `recipe` to `recipe_embedding` on `recipe_id`, `model = :model` and `recipe_updated_at = recipe.updated_at`.
  - Filter `notebook_id = ANY(:ids)`, the optional author, `created_at` bounds and the exclude list.
  - For the ingredient "all" rule: `(SELECT count(DISTINCT name) FROM recipe_ingredient WHERE recipe_id = r.id AND name = ANY(:names)) = :n`.
  - `ORDER BY embedding <=> CAST(:q AS vector)`, `LIMIT :limit`.
  - Return `RawHit` with `score = 1 - distance`.
- [X] T031 [P] [US2] Create `api/adapters/persistence/search_records.py` with `SqlAlchemySearchRecords.record(event, hits) -> UUID`, `mark_used` (sets `used_at` only when null), `delete_older_than(cutoff) -> int` and `score_bands(width) -> list[Band]` (FR-017b–e). It never stores a person, question, kitchen or notebook id.
- [X] T032 [US2] Create `api/application/recipe_search.py` with `SearchRecipesCommand`, `SearchAnswer`, `SearchHit`, `SearchRecipesService` and `MarkSearchResultUsed`, following the order of steps and errors in contracts/search-service.md. Access reuses `AuthorizeKitchenAccessService(action="read_kitchen")` + `kitchen_ids_for`, `personal_ids_for` and `facts_for`, as `ListKitchenRecipesService` does (research R13). When the question cannot be embedded, raise `SearchQuestionNotEmbedded(outcome)` (defined in this module), which carries the embedder's result unchanged (`LimitReached`, `Unavailable`, `InvalidOutput` or `AIProviderError` from `application/recipe_extraction.py`). Consumers map `outcome` the way `api/api/routes/recipe_capture.py:176-200` already does (422, 429 with Retry-After, 503).
- [X] T033 [US2] Add `get_search_recipes` and `get_mark_search_result_used` factories in `api/api/deps.py`. The `Embedder` (`GeminiEmbedder`) is cached on `app.state` like `get_recipe_extraction`. No route; consumers S-030, S-044 and S-032 add them.
- [X] T034 [US2] Add `score-report [--width 0.05]` (table `low high shown used share`) and `cleanup` (prints `deleted=N`) to `api/scripts/embeddings.py`. Add the daily clean-up to `api/api/worker.py`: on the first pass after 03:00 local time, or at start if a day was missed, delete records older than `SEARCH_RECORD_RETENTION_DAYS` (FR-017e).

**Checkpoint**: US1 + US2 make a complete search the later stories can call.

---

## Phase 5: User Story 3 - An outage never blocks saving, and heals on its own (P2)

**Goal**: the growing retry rule, shared by background jobs, and an operator view of the backlog.

**Independent test**: with a failing embedder, saves and edits succeed in the same time; when it recovers, everything is embedded with no one acting (quickstart step 2, SC-002, SC-003).

### Tests for US3

- [X] T035 [P] [US3] Write `api/tests/test_retry_domain.py` for `next_wait`:
  - First failure gives 60 s, then 90, 135, 202.5 … and never above 7200.
  - A service wait longer than the computed one wins, and a shorter one does not.
  - Custom `first_s`, `growth` and `cap_s` are respected.
  - Invalid policies (growth ≤ 1, cap < first) raise `ValueError`.
- [X] T036 [P] [US3] Extend `api/tests/test_embedding_worker_application.py`:
  - After repeated `Unavailable` results each job's `due_at` follows the 1.5× rule up to the cap, with `attempts` growing without limit.
  - `LimitReached(retry_after_seconds=300)` gives a wait of at least 300 s.
  - A later success deletes the job, so the next enqueue starts from the first wait again.
  - Only class names are stored in `last_failure`.
- [X] T037 [P] [US3] Add to `api/tests/test_recipe_save_integration.py` and `api/tests/test_recipe_manage_integration.py`: with the worker off and no Gemini key, save and edit return their usual status and body, write one `embedding_job` row, and make no embedder call (FR-002, FR-003, SC-002).

### Implementation for US3

- [X] T038 [P] [US3] Create `api/domain/retry.py` with a frozen `RetryPolicy(first_s=60.0, growth=1.5, cap_s=7200.0)` that validates itself, and `next_wait(previous_s, policy, service_wait_s=None) -> float` (research R6, FR-009a). It is pure, and documented as the default for every background job.
- [X] T039 [US3] Replace the placeholder wait in `EmbedPendingRecipes` (`api/application/embedding_worker.py`) with `next_wait(job.last_wait_s, policy, result.retry_after_seconds)`. Build the policy from `EMBED_RETRY_FIRST_WAIT_S`, `EMBED_RETRY_GROWTH` and `EMBED_RETRY_CAP_S`.
- [X] T040 [US3] In `api/api/worker.py`, log `embedding backlog count=%d oldest_s=%d` on each pass with a backlog (FR-009b). Retry a failed daily clean-up with the same `RetryPolicy` (defaults), held in memory. When no key or model is configured, log once at INFO and re-check every 60 s without error logs (FR-014).

**Checkpoint**: quickstart step 2 passes.

---

## Phase 6: User Story 4 - Snapshot copies are searchable (P2)

**Goal**: copies made by a snapshot are queued without slowing the snapshot.

**Independent test**: a 50-recipe snapshot takes the same time as before and its copies become searchable (quickstart step 6, SC-006).

- [X] T041 [P] [US4] Extend `api/tests/test_notebook_snapshots_application.py`: a created snapshot calls `enqueue_notebook(new_notebook_id)` once; a replayed one (same snapshot key) does not.
- [X] T042 [P] [US4] Extend `api/tests/test_notebook_snapshots_integration.py`:
  - After a snapshot of a notebook with embedded recipes, each copy has an `embedding_job` row and no embedding yet.
  - The originals' embeddings are untouched.
  - A 50-recipe snapshot takes at most 5 statements more than before.
- [X] T043 [US4] In `AddNotebookSnapshotService.execute` (`api/application/notebooks.py:634`), take an `EmbeddingJobs` argument and call `enqueue_notebook(notebook.id)` right after `copy_all`, not on the replay path. Wire it in `api/api/deps.py`, and call `wake_embedding_worker` after a created snapshot in `api/api/routes/notebooks.py`. `copy_all` (`api/adapters/persistence/recipes.py:177`) is not changed.

**Checkpoint**: spec 035 FR-013 is met.

---

## Phase 7: User Story 5 - Embedding strategies can be compared (P3)

**Goal**: each embedding names its strategy, model, token count and time, and the operator can re-embed with another strategy.

**Independent test**: spec US5 scenarios 1–2.

- [X] T044 [P] [US5] Extend `api/tests/test_embeddings_integration.py`:
  - Written rows carry `model`, `strategy_used`, `input_tokens` (or null), `input_truncated` and `updated_at`.
  - `enqueue_missing(model)` does not queue recipes embedded with another strategy.
  - `enqueue_missing(model, other_strategy_of="toon")` queues those embedded with `plain`.
- [X] T045 [US5] Add `--reembed-other-strategy` to `catch-up` in `api/scripts/embeddings.py`, passing the configured strategy name to `enqueue_missing` (FR-013). Add the `other_strategy_of` branch to `SqlAlchemyEmbeddingJobs.enqueue_missing` in `api/adapters/persistence/embeddings.py`.

---

## Phase 8: Polish and cross-cutting

- [X] T046 [P] Check the logs: grep the new modules for `logger.` calls and confirm none takes recipe text, question text, vectors or keys (FR-023). Add a captured-log assertion to `test_embedding_worker_application.py`.
- [X] T047 Run `cd api && uv run ruff check .` and `./scripts/compose-test.sh`. Compare failures with the baseline on HEAD before this story, and record both counts in `specs/019-recipe-embeddings-search/notes.md`.
- [X] T048 Walk quickstart.md steps 2–7 on this worktree's stack (project `melos-kitchen-vectors`, UI port 3050) with invented data. For SC-001, save 20 recipes and compute each one's time from `recipe.created_at` to its `recipe_embedding.updated_at`; report the 95th percentile and the maximum. Record each step as passed or not walked in `specs/019-recipe-embeddings-search/notes.md`.
- [X] T049 [P] Update `README.md`, the operator section only (ask before any rewrite): the new variables, the worker, and the `scripts.embeddings` commands.
- [X] T050 Prepare (do not apply without the owner's approval) the wording for the constitution exception (`.specify/memory/constitution.md`, Exceptions: in-api worker, approved 2026-11-02, scope: background jobs inside the api process) and for PRD §1.1 and Appendix D (embedding model decided). Put the drafts in `specs/019-recipe-embeddings-search/notes.md` and ask the owner.
- [X] T051 Update `dev/docs/backlog.yaml` S-019: status `in_progress` while building, and a `verification` entry with the results of T047 and T048.

---

## Dependencies and execution order

- **Setup (T001–T004)**: T001 first; if it fails the 768 check, stop. T002–T004 can follow in any order.
- **Foundational (T005–T014)**: needs Setup. T005 → T006 → T007 → T008; T009 needs T007; T010 before T012 and T014; T011 before T012.
- **US1 (T015–T025)**: needs Foundational. This is the MVP.
- **US2 (T026–T034)**: needs Foundational, and real data needs US1's embeddings. Its integration tests write embeddings directly, so they can be built alongside US1 after T020.
- **US3 (T035–T040)**: needs US1 (the worker exists). T038 can be written at any time.
- **US4 (T041–T043)**: needs US1's `SqlAlchemyEmbeddingJobs`.
- **US5 (T044–T045)**: needs US1.
- **Polish (T046–T051)**: needs the stories that are in scope.

Within each story, write the tests first and see them fail, then build models and adapters, then services, then wiring.

## Parallel examples

- Setup: T003 and T004 together.
- Foundational: T008, T013 and T014 together, once their inputs exist.
- US1: T015, T016, T017 and T018 together, then T019 alongside T020.
- US2: T026, T027 and T028 together; T029 and T031 together.
- US3: T035, T036 and T037 together; T038 alongside them.
- US4 and US5 can run alongside each other after US1.

## Implementation strategy

1. **MVP**: Setup, Foundational and US1. Every recipe gets embedded and kept current. Stop and validate with quickstart step 3.
2. **US2**: the search that S-030 and S-044 call. Validate with step 4.
3. **US3**: the healing retry rule. Validate with step 2.
4. **US4**, then **US5**.
5. **Polish**: full test run, browser-free walk, README, and the drafts for the constitution and PRD for the owner.

## Notes

- Nothing is pushed or committed without the owner's request. Stage only this story's files (other agents share the repository).
- Use invented data only, in tests and in the walk.
- Never read or print `.env` contents or the key.
