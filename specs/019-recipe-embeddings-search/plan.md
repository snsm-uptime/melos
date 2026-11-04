# Implementation Plan: Recipe embeddings and search pre-filtered by kitchen

**Branch**: `worktree-kitchen-vectors` (feature id `019-recipe-embeddings-search`) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-recipe-embeddings-search/spec.md`

## Summary

Every recipe gets a 768-value `gemini-embedding-001` embedding, stored in `recipe_embedding`.
Embeddings are made by a worker thread inside the api, never inline. Save, edit and snapshot write
an `embedding_job` row in their own transaction. The worker claims jobs with `SKIP LOCKED`, calls
Gemini outside any transaction, one recipe per call, as Google's reference requires for this model, and writes the embedding only if the recipe's `updated_at` is
unchanged, so an embedding of old content can never be served. Failures retry forever with a wait
that grows by 50% up to 2 hours.

A catch-up queues every recipe that lacks an embedding, at start-up and by command. Search is an
in-process use case with three scopes: kitchen, my notebooks, one notebook. It checks access the
way the lists do, filters first, ranks by exact cosine distance, returns at most 5 hits marked
close or weak, and records each result for later tuning of the minimum closeness. No UI and no
route in this story.

## Technical Context

**Language/Version**: Python 3.12 (api only; no ui or mcp change)

**Primary Dependencies**: FastAPI 0.141, SQLAlchemy 2.0, Alembic, `google-genai` 2.32 (existing); **new: `python-toon`** (PRD Appendix D decision, `uv add python-toon`). No `pgvector` Python package; a small custom column type instead (research R9).

**Storage**: PostgreSQL 16 + pgvector (extension already enabled). Four new tables (data-model.md).

**Testing**: pytest. The domain is pure. Application tests use fakes (`api/tests/embedding_fakes.py`). Integration tests run against Postgres in the Compose test overlay. One live test of the model's dimension is skipped without a key.

**Target Platform**: Linux containers (Compose dev, test and prod overlays)

**Project Type**: web service (hexagonal api); the ui is untouched

**Performance Goals**: save, edit and snapshot within 10% of today (SC-002, SC-006); search under 1 s for 1,000 recipes, excluding the question's embedding (SC-007); new recipes searchable within 1 min at p95 (SC-001)

**Constraints**: one Gemini attempt per call (PRD 1.7); no Gemini call inside a DB transaction; logs carry counts and class names only; no new service and no queue (constitution 1, see Complexity Tracking)

**Scale/Scope**: a home deployment with tens of users and up to a few thousand recipes; exact vector scan with no ANN index (research R10)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| 1. Simplicity and reuse: four services, no queue, no worker | **Exception (owner-approved 2026-11-02)** | A worker thread inside `api` with state in Postgres; no fifth service and no queue system. See Complexity Tracking. Documented the way the constitution's Exceptions section allows, in a comment at the top of `api/api/worker.py` (task T023). Recording it in the constitution text itself is a separate change for the owner (T050). |
| 1. Every external call through a port, with errors mapped | Pass | `Embedder` port; Gemini error mapping shared with the extractor (research R11) |
| 2. Stack: uv, models from env | Pass | `GEMINI_EMBED_MODEL` and `GEMINI_EMBED_DIM` from env; `python-toon` added with `uv add` |
| 2. Model change needs approval | Pass | Owner approved `gemini-embedding-001` (spec Clarifications) |
| 3. Hexagonal: pure domain | Pass | Retry rule, marks, filters and embed text live in `domain/`; `python-toon` is a pure library |
| 3. Access in `application/`, 404 for non-members | Pass | Reuses `AuthorizeKitchenAccessService` and `facts_for` (research R13) |
| 4. Secrets and logs | Pass | No text, vectors or keys in logs; search records hold no person or question |
| 5. No AI shortcuts | Pass | No draft is affected; embeddings are internal only |
| 6. Tests: domain, fakes, integration | Pass | Plus the updated schema guard |
| 7. Deployment | Pass | No server config; env variables documented in `.env.example` |
| 8. Migrations | Pass | `0014_recipe_embeddings`, tested down and up |
| 9. Scope: Must | Pass | S-019 is Must |

Post-design re-check: unchanged. The only deviation is the approved worker exception.

## Project Structure

### Documentation (this feature)

```text
specs/019-recipe-embeddings-search/
├── spec.md
├── plan.md                         # this file
├── research.md                     # R1–R14
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── search-service.md
│   └── worker-and-commands.md
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── retry.py                    # new: RetryPolicy, next_wait (FR-009, FR-009a)
│   ├── embed_text.py               # new: toon and plain renderings (FR-022)
│   ├── recipe_search.py            # + SearchScope, SearchFilters, mark(), SEARCH_LIMIT
│   └── errors.py                   # + InvalidSearchQuestionError, InvalidSearchFiltersError
├── application/
│   ├── ports.py                    # + Embedder, EmbedTextStrategy, EmbeddingJobs, RecipeEmbeddings, SearchRecords
│   ├── recipe_search.py            # new: SearchRecipesService, MarkSearchResultUsed
│   ├── embedding_worker.py         # new: EmbedPendingRecipes (one pass), SearchRecordCleanup
│   ├── recipe_save.py              # + enqueue on create (not on replay)
│   ├── recipe_manage.py            # + enqueue on edit; DeleteRecipeService docstring
│   └── notebooks.py                # + enqueue_notebook after copy_all in AddNotebookSnapshotService
├── adapters/
│   ├── llm/gemini_embedder.py      # new: Embedder over google-genai (task types, normalize, length check)
│   ├── llm/gemini_errors.py        # new: shared classify(), moved from gemini_extractor.py
│   └── persistence/
│       ├── vector.py               # new: Vector(dim) UserDefinedType
│       ├── models.py               # + RecipeEmbeddingModel, EmbeddingJobModel, SearchEventModel, SearchResultModel
│       ├── embeddings.py           # new: SqlAlchemyEmbeddingJobs, SqlAlchemyRecipeEmbeddings
│       ├── search_records.py       # new: SqlAlchemySearchRecords
│       └── migrations/versions/0014_recipe_embeddings.py
├── api/
│   ├── app.py                      # + lifespan: start and stop the worker thread
│   ├── worker.py                   # new: thread loop, wake event, daily clean-up timer
│   ├── deps.py                     # + wiring for the new services; enqueue ports into save, edit, snapshot
│   ├── routes/recipes.py, recipe_capture.py, notebooks.py   # + wake after save, edit, snapshot
│   └── settings.py                 # + load_embedding_settings()
├── scripts/embeddings.py           # new: catch-up, status, score-report, cleanup
└── tests/
    ├── embedding_fakes.py
    ├── test_retry_domain.py, test_embed_text_domain.py, test_recipe_search_domain.py (+)
    ├── test_recipe_search_application.py, test_embedding_worker_application.py
    ├── test_gemini_embedder_adapter.py (fake client; one live test skipped without a key)
    ├── test_embeddings_integration.py, test_recipe_search_integration.py
    ├── test_recipe_embeddings_migration.py
    └── test_recipe_manage_integration.py   # schema guard updated
docker-compose.yml, docker-compose.test.yml, .env.example   # new variables, new embed model default
```

**Structure Decision**: Existing hexagonal api layout. No new folders: every new file goes in an
existing directory.

## Phase 0 and Phase 1 outputs

- [research.md](research.md): every unknown resolved. Model and dimension (R1, checked against
  Google's reference, with one live check left as the first task), token count (R2), one text per
  call and truncation (R2a), worker placement (R3), claiming (R4), staleness (R5),
  retry rule (R6), enqueueing and catch-up (R7), embed text (R8), vector type (R9), index (R10),
  errors (R11), records (R12), access (R13), no-config behaviour (R14).
- [data-model.md](data-model.md): four tables, the job state transitions and the domain values.
- [contracts/search-service.md](contracts/search-service.md): the use case consumers call, its
  errors and the ports.
- [contracts/worker-and-commands.md](contracts/worker-and-commands.md): the worker loop, settings
  and operator commands.
- [quickstart.md](quickstart.md): the validation walk.

## Follow-ups outside this plan

- Add the worker exception to `.specify/memory/constitution.md` (Exceptions) and update PRD §1.1
  ("No queue and no worker") and Appendix D (embedding model decided). Both need the owner's
  explicit approval as separate changes.
- S-044 must follow FR-015b (ingredient chips) and report result use (FR-017c). S-030 must report
  citations as use.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| A worker inside the api (constitution 1: "no worker") | Owner decision 2026-11-02: saving must never fail or wait on Gemini, and failed embeddings must heal on their own (spec FR-002, FR-008, FR-009) | Inline embedding blocks and fails saves during outages. Command-only catch-up leaves recipes unsearchable until someone acts. A separate worker service or queue would break the four-service rule even further. |
| New library `python-toon` | PRD Appendix D chose it for TOON. The same encoder serves the embed text now and the chat context in S-030 | A hand-written encoder duplicates a decided library and would need its own tests against the TOON spec |
