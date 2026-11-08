# Tasks: Scheduled Ingredient Translation Service

**Input**: Design documents from `specs/073-ingredient-translation-cron/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution Principle 6 requires domain tests (pure pytest), application tests
(fake ports), and integration tests (Postgres). They are not optional for this feature.

**Organization**: Tasks are grouped by user story (spec.md priorities: US1 P1, US2 P1, US3 P2, US4 P2).

**Gate**: Phase 1 (T001) records the constitution amendment. No task after T001 may start until
T001 is merged, because the plan's constitution gate fails without it. T001 needs the project lead's
approval; it is not something to implement.

**Model**: Notebook and kitchen catalogs (`ingredient`, `ingredient_name`) and `recipe_ingredient`
are not changed. The standard table is new and separate (spec Q2, revised; research.md R4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 to US4, from spec.md

---

## Phase 1: Setup

**Purpose**: Record the approved amendment and create the package skeleton

- [X] T001 Record the approved constitution amendment in `.specify/memory/constitution.md`: redefine Principle 1 (five services, one scheduled job service, no queue), add the Principle 5 exception for AI-validated translations saved without confirmation (marked AI-made), and replace `mcp` with `jobs` in the Principle 7 health-check list (heartbeat for jobs). Bump version to 3.0.0, add an amendment-log entry dated 2026-11-07 that cites spec 073, and commit it on its own (Amendment Procedure step 4). Requires the project lead's approval first.
- [X] T002 Create the package skeleton `api/jobs/__init__.py` (empty package marker) for the job entry point.
- [X] T003 [P] Add job and translation settings to `api/api/settings.py`: `GEMINI_TRANSLATE_MODEL` (required, no default, read from environment), `JOBS_INTERVAL_SECONDS` (default 3600), `JOBS_TRANSLATE_BATCH_SIZE` (default 50), `JOBS_RUN_ONCE` (default 0), `JOBS_HEARTBEAT_PATH` (default `/tmp/jobs-heartbeat`). Names and defaults exactly as in `contracts/job-service.md`.

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: Schema, domain types, ports, and the adapter every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Write the additive Alembic migration `api/adapters/persistence/migrations/versions/0022_standard_ingredients.py`: create `standard_ingredient`, `standard_ingredient_name`, `standard_ingredient_review` and `job_run` per data-model.md, with the constraints quoted in T005. Add index `ix_recipe_updated_at` on `recipe(updated_at)`, `ix_standard_review_status_created` on `standard_ingredient_review(status, created_at)`, and `ix_job_run_status_started` on `job_run(status, started_at)`. Change no existing table. The migration docstring says downgrade drops the four tables.
- [X] T005 Quote these constraints verbatim in the migration `0022_standard_ingredients.py`: `standard_ingredient.normalized_name` NOT NULL UNIQUE; `standard_ingredient.language` CHECK `language IN ('en', 'es')`; `standard_ingredient_name` UNIQUE `(standard_ingredient_id, language)`; `standard_ingredient_name.source` CHECK `source IN ('discovery', 'ai', 'admin')`; `standard_ingredient_name` CHECK `source <> 'ai' OR model IS NOT NULL`; `standard_ingredient_review.status` CHECK `status IN ('pending', 'accepted', 'rejected')`; `standard_ingredient_review` CHECK `(status = 'pending') = (decided_by IS NULL)`; `job_run.status` CHECK `status IN ('running', 'succeeded', 'failed', 'skipped')`; `job_run` CHECK `found >= 0 AND translated >= 0 AND rejected >= 0 AND failed >= 0`; `job_run.started_at` NOT NULL.
- [X] T006 Update SQLAlchemy models in `api/adapters/persistence/models.py` to match data-model.md: `StandardIngredientModel`, `StandardIngredientNameModel`, `StandardIngredientReviewModel`, `JobRunModel`, and the `updated_at` index on `RecipeModel`. Existing `IngredientModel`, `IngredientNameModel` and `RecipeIngredientModel` are not changed.
- [X] T007 [P] Confirm the normalization in `api/domain/ingredient_catalog.py` is the one used for `normalized_name` (trimmed, lower-case, singular). Add a `discovery_key(name: str) -> str` only if no function with that rule exists; reuse it otherwise. Extend `api/tests/test_ingredient_catalog_domain.py` with cases for plurals, case and surrounding spaces.
- [X] T008 [P] Create `api/domain/ingredient_translation.py`: pure dataclasses `IngredientTranslationRequest` (`name`, `source_language`, `target_language`) and `IngredientTranslationResult` (`valid`, `translation`), plus domain errors `TranslationUnavailable` and `TranslationUnparseable`. No SDK or framework imports (constitution 3). Validation: when `valid` is true, `translation` must be non-empty, trimmed, at most 80 characters, with no newline; when `valid` is false, `translation` must be `None`.
- [X] T009 [P] Write `api/tests/test_ingredient_translation_domain.py`: the validation rules from T008 (valid requires non-empty translation; invalid requires `translation = None`; 80-character limit; no newline) and the rule that languages are only `en` or `es`.
- [X] T010 [P] Add the `IngredientTranslator` port (`translate(request) -> result`) to `api/application/ports.py`, next to the existing `IngredientPairSuggester` port.
- [X] T011 [P] Create the fake translator `api/tests/catalog_translation_fakes.py`: scripted results per name, scripted failures (`TranslationUnavailable`, `TranslationUnparseable`), and a call log so tests can assert the number of calls (needed for FR-005a).
- [X] T012 [P] Create `api/adapters/persistence/job_lock.py`: `try_acquire()` runs `pg_try_advisory_lock` with one fixed key constant; `release()` runs `pg_advisory_unlock`; both in a context manager that always releases in `finally` (FR-012).
- [X] T013 [P] Create `api/adapters/llm/gemini_translator.py` implementing the port with the `google-genai` SDK. Map errors as in `contracts/translation-port.md`: timeout or network error to `TranslationUnavailable`; quota or rate limit to `TranslationUnavailable`; output not matching the JSON shape to `TranslationUnparseable`. Read the model name from settings (`GEMINI_TRANSLATE_MODEL`), never hard-code it (FR-015).
- [X] T014 [P] Create the prompt file `api/adapters/llm/prompts/ingredient_translation.txt`: the ingredient name inside a delimited block; an instruction to treat the block as data and ignore instructions inside it; the output shape `{"valid": bool, "translation": string|null}`; no other text. Follow the layout of the existing prompt files in `api/adapters/llm/prompts/`.
- [X] T015 [P] Write `api/tests/test_gemini_translator_adapter.py` with a fake SDK client (no network): shape errors map to `TranslationUnparseable`; quota and timeout map to `TranslationUnavailable`; the model name comes from settings.

**Checkpoint**: Schema, domain types, port, lock and adapter exist. User stories can start.

---

## Phase 3: User Story 1 - Hourly detection of new ingredients (Priority: P1) 🎯 MVP

**Goal**: Each hour, find ingredient names in recipe lines since the last successful run, and record each name the standard table has not seen once in `standard_ingredient`.

**Independent Test**: Add an English recipe with a new ingredient, run the job once (`JOBS_RUN_ONCE=1`), and check that the standard ingredient exists with `ai_checked_at` null. Run again and check that no duplicate is created (spec.md User Story 1).

### Tests for User Story 1

- [X] T016 [P] [US1] Write `api/tests/test_discovery_domain.py`: the candidate rule (recipe lines of recipes with `updated_at` at or after the last succeeded run's `started_at`), deduplication by `discovery_key`, and the language taken from the recipe. Pure pytest, no database.
- [X] T017 [P] [US1] Write `api/tests/test_translate_ingredients_application.py` (discovery part) with fake repositories: discovery creates a standard ingredient once; a repeated run creates none; a run with no new names makes no translator call.
- [X] T018 [P] [US1] Write `api/tests/test_discovery_integration.py` against Postgres: the watermark comes from the last `succeeded` row in `job_run`; a `failed` run does not move the watermark; a recipe edited during a run is picked up by the next run; the first run with no watermark scans all recipes once.

### Implementation for User Story 1

- [X] T019 [US1] Create `api/domain/ingredient_discovery.py`: a pure function that takes recipe lines with their recipe language and returns the distinct candidates, keyed by `discovery_key` (uses T007).
- [X] T020 [US1] Create `api/adapters/persistence/standard_ingredients.py`: select recipe line names from recipes with `updated_at >= watermark`; insert a `standard_ingredient` by `normalized_name` with `ai_checked_at` null and `ON CONFLICT DO NOTHING`; set `language` from the recipe language on creation only.
- [X] T021 [US1] Create `api/adapters/persistence/job_runs.py`: insert a `running` row with `started_at` taken before the scan; finish it with `status` and counts; read the last `succeeded` `started_at` as the watermark.
- [X] T022 [US1] Create `api/application/translate_ingredients.py` with the run lifecycle: acquire the lock (record `skipped` with `reason: lock_busy` if busy), read the watermark, run discovery, record counts on `job_run`, release the lock in `finally`. The translation step is added in US2.
- [X] T023 [US1] Create `api/jobs/run_log.py`: write JSON-line events `run.start`, `run.skipped`, `discovery.done`, `run.end` with the keys in `contracts/run-log.md`. Log standard ingredient ids, never names or recipe text.

**Checkpoint**: The job detects new names and records each once in the standard table. Translation is not yet called.

---

## Phase 4: User Story 2 - AI translation into the other language (Priority: P1)

**Goal**: Each standard ingredient gets one AI validation and translation into the other supported language. The result is shared, and a failed call is retried on the next run.

**Independent Test**: Add an English recipe with "onion". After one run, a Spanish `standard_ingredient_name` exists with `source = ai` and `model` set. A second run calls the model zero times (spec.md User Story 2).

### Tests for User Story 2

- [X] T024 [P] [US2] Write `api/tests/test_translate_ingredients_ai_application.py` with the fake translator: one call per standard ingredient; a valid answer saves the other-language name with `source = ai` and `model`, then sets `ai_checked_at`; an invalid answer sets `ai_checked_at` and saves nothing; a failure leaves `ai_checked_at` null; a quota error stops the run early.
- [X] T025 [P] [US2] Write `api/tests/test_translate_ingredients_ai_integration.py` against Postgres: a second recipe in another notebook using the same name causes no call (FR-005a); `JOBS_TRANSLATE_BATCH_SIZE` caps the calls per run; one failing item does not stop the rest; the name and `ai_checked_at` are written in one transaction.
- [X] T026 [P] [US2] Extend `api/tests/test_ingredient_translation_domain.py`: the target language is the other of the discovered language; a standard ingredient with no language is rejected.

### Implementation for User Story 2

- [X] T027 [US2] Add the target rule to `api/domain/ingredient_translation.py` (extends T008): target is the other of `en` and `es` from the discovered language; raise a domain error when the language is missing.
- [X] T028 [US2] Create `api/adapters/persistence/standard_translations.py`: select `standard_ingredient` rows with `ai_checked_at IS NULL`, ordered by `created_at`, limited to `JOBS_TRANSLATE_BATCH_SIZE`; save a `standard_ingredient_name` with `source = 'ai'` and `model`, and set `ai_checked_at`, in one transaction.
- [X] T029 [US2] In `api/application/translate_ingredients.py`, add the translation step: skip an ingredient whose name in the target language already exists (FR-005a); call the port once per remaining ingredient; count `translated`, `rejected` and `failed`; stop the run early on a quota error.
- [X] T030 [US2] In `api/jobs/run_log.py`, add the events `translate.item` (with `outcome`) and `translate.failed` (with `error_kind`) from `contracts/run-log.md`.

**Checkpoint**: The job validates and translates each new ingredient once, and shares the result.

---

## Phase 5: User Story 3 - Standard table and admin review of custom values (Priority: P2)

**Goal**: The standard table holds one entry per real-world ingredient with validated names. The notebook and kitchen catalogs keep their current logic. A person's own value for an AI-made name goes to an admin review list, and only accepted values join the standard table (FR-021, FR-022).

**Independent Test**: Two notebooks add "tomatoes" and "tomato". After the job runs, the standard table holds one entry for tomato, and each notebook's own catalog is unchanged. A custom value entered for "bell pepper" appears as a pending review; accepting it adds an `admin` name, and rejecting it changes nothing in the standard table (spec.md User Story 3).

### Tests for User Story 3

- [ ] T031 [P] [US3] Write `api/tests/test_standard_catalog_integration.py` against Postgres: two notebooks adding "tomatoes" and "tomato" resolve to one standard ingredient; each notebook's `ingredient` and `ingredient_name` rows are unchanged by the job; `standard_ingredient_name` allows one name per language per ingredient.
- [ ] T032 [P] [US3] Write `api/tests/test_review_standard_names_application.py`: a custom value for an AI-made standard name creates a `pending` review; accept writes a `standard_ingredient_name` with `source = 'admin'` and sets the review `accepted`; reject sets `rejected` and changes nothing in the standard table; a non-admin cannot decide.
- [ ] T033 [P] [US3] Write `api/tests/test_review_standard_names_integration.py` against Postgres: the pending list returns only `pending` rows, ordered by `created_at`; the status and decided-by CHECK rejects a `pending` row with `decided_by` set; deleting a standard ingredient cascades to its reviews.

### Implementation for User Story 3

- [ ] T034 [US3] Create `api/domain/standard_review.py`: pure rules for a review: it can be decided only once, and the decision keeps the proposed value unchanged.
- [ ] T035 [US3] Create `api/application/review_standard_names.py`: create a review when a person enters a value that differs from an AI-made standard name; list pending reviews; accept (writes `source = 'admin'`) and reject. Admin checks use the existing `users.is_admin` guard (spec 055).
- [ ] T036 [US3] Create `api/adapters/persistence/standard_reviews.py`: persistence for `standard_ingredient_review` and the admin-accepted `standard_ingredient_name` write.
- [ ] T037 [US3] Update the recipe save path (the module used by `api/tests/test_recipe_save_application.py`) so a value entered for a name that has an AI-made standard entry calls T035 to create a review. The notebook catalog write is unchanged. Add a test case to `api/tests/test_recipe_save_application.py`.
- [ ] T038 [US3] Add admin routes under `api/routes/` for the review list, accept and reject, following the spec 055 admin API. Extend `api/tests/test_admin_integration.py` with: a non-admin gets the same answer as an unknown path (spec 055 SC-006); a pending review is listed; accept and reject respond as in T032.
- [ ] T039 [US3] Add the review list to the admin dashboard in `ui/` (spec 055 pattern): the AI name, the proposed value, the proposer's alias, and accept and reject actions.
- [ ] T040 [P] [US3] Add a test `api/tests/test_standard_write_guard.py`: the only code paths that write `standard_ingredient_name` are the translation use case (`source = 'ai'`, `discovery`) and the accept use case (`source = 'admin'`). Assert this against the persistence module names (FR-021).

**Checkpoint**: Notebook catalogs are unchanged, the standard table is shared, and custom values are validated by the admin.

---

## Phase 6: User Story 4 - Operations: private service with centralized logs (Priority: P2)

**Goal**: The job runs as a `jobs` Compose service on the internal network, with no published port, a heartbeat, shared logs, and `mcp` removed.

**Independent Test**: Start the stack. `jobs` is healthy, has no published port, reaches `db`, and its log lines appear with the other services' logs. `mcp` is gone (spec.md User Story 4).

### Tests for User Story 4

- [X] T041 [P] [US4] Write `api/tests/test_jobs_entrypoint_integration.py` against Postgres: `JOBS_RUN_ONCE=1` exits `0` after a succeeded or skipped run and `1` after a failed run; a busy lock records `skipped`; a missing `GEMINI_TRANSLATE_MODEL` fails at startup with a clear message.
- [X] T042 [P] [US4] Write `api/tests/test_jobs_heartbeat.py`: the heartbeat is written at the start of each loop iteration, and a file older than 7200 seconds is reported stale.

### Implementation for User Story 4

- [X] T043 [US4] Create `api/jobs/heartbeat.py`: write the current time to `JOBS_HEARTBEAT_PATH`; provide the staleness check used by the Compose healthcheck (research R8).
- [X] T044 [US4] Create `api/jobs/__main__.py`: read settings (T003) and fail fast if `GEMINI_TRANSLATE_MODEL` is missing; wait for the database with a fixed retry delay and log `db.wait` each attempt, without exiting (FR-011); run the hourly loop with `JOBS_INTERVAL_SECONDS`, calling the use case from T022, and write the heartbeat each iteration; honour `JOBS_RUN_ONCE` with the exit codes in `contracts/job-service.md`.
- [X] T045 [US4] In `docker-compose.yml`, remove the `mcp` service and every `MCP_HOST_PORT` reference.
- [X] T046 [US4] In `docker-compose.yml`, add the `jobs` service exactly as `contracts/job-service.md` specifies: build from `./api` with the same Dockerfile; command `python -m jobs`; `depends_on` `db` with `service_healthy`; `networks: [internal]` only; no `ports`; `restart: unless-stopped`; the heartbeat healthcheck (interval 5m, timeout 5s, retries 3, start_period 60s); and the environment table.
- [X] T047 [US4] In `docker-compose.yml`, add one shared `json-file` logging anchor (with `max-size` and `max-file`) and apply it to every service (research R7).
- [X] T048 [P] [US4] Update `docker-compose.dev.yml` with `jobs` overrides (local env passthrough) and remove any `mcp` overrides.
- [X] T049 [P] [US4] Update `docker-compose.prod.yml`: `jobs` reads its environment from the server environment, and `mcp` is removed.
- [X] T050 [P] [US4] Update `docker-compose.test.yml` to include `jobs` in the test overlay, so the integration tests in T018, T025, T031, T033 and T041 run in Compose (constitution 6).
- [X] T051 [US4] Remove the `mcp/` directory (`mcp/Dockerfile`, `mcp/pyproject.toml`, `mcp/uv.lock`, `mcp/server/`, `mcp/tools/`) and every reference to it. Grep the repo for `mcp` and `9000` and fix each hit in `scripts/`, `.github/workflows/`, `docker-compose.worktree.yml`, `README.md` and `DEPLOYMENT.md` (FR-013).
- [X] T052 [US4] Update the health-check and compose scripts in `scripts/` (for example `scripts/compose-up.sh`) so they no longer probe `mcp` `/health` and instead check the `jobs` healthcheck status.
- [X] T053 [P] [US4] Add `GEMINI_TRANSLATE_MODEL` and the `JOBS_*` variables with their defaults to `.env.example` and `.env.prod.example`. No secret values.
- [X] T054 [P] [US4] Update `AGENTS.md`: the service list (`db`, `api`, `ui`, `jobs`); the standard table and the translation rule (AI-validated translations saved without confirmation, FR-020; custom values reviewed by the admin, FR-022). The per-notebook catalog rule stays. Update `README.md` with the `jobs` service and how to run it once.

**Checkpoint**: The stack runs with `jobs` and without `mcp`. Logs are collected in one place.

---

## Phase 7: Polish & cross-cutting concerns

**Purpose**: Checks that span stories

- [ ] T055 [P] Run `specs/073-ingredient-translation-cron/quickstart.md` end to end on a worktree stack and record each expected result in `specs/073-ingredient-translation-cron/notes.md`.
- [ ] T056 Run `EXPLAIN ANALYZE` on the standard lookup by `normalized_name` on realistic data, and record in `specs/073-ingredient-translation-cron/notes.md` that the index scan is used.
- [X] T057 [P] Verify FR-018 with a test: no table outside the vector tables stores lists of related ids next to a vector. Put it in `api/tests/test_no_id_lists_domain.py`.
- [X] T058 Run `ruff check` and the `pytest` suite from `api/` (`uv run ruff check`, `uv run pytest`) and fix any failures in the files this feature touched.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: T001 first (constitution gate, needs project lead approval). T002 and T003 can run after it.
- **Foundational (Phase 2)**: depends on Setup. Blocks all user stories. T004 to T006 are sequential (one migration and one model file). T007 to T015 are parallel.
- **User Stories (Phase 3+)**: depend on Foundational.
  - US1 (P1) is the MVP and comes first.
  - US2 (P1) depends on US1's discovery step (T022).
  - US3 (P2) depends on the schema (T004 to T006) and on the translation step for the AI-made names it reviews (T029). It can otherwise run in parallel with US1 and US2.
  - US4 (P2) depends on T022 and T044 (the entry point), and on US1 and US2 for the end-to-end checks.
- **Polish (Phase 7)**: depends on the stories it checks.

### Within each story

- Tests are written first and must fail before implementation.
- Domain before application, application before persistence adapters, persistence before compose.

### Parallel opportunities

- Foundational: T007 to T015 touch different files.
- US1 tests: T016, T017, T018 touch different files.
- US2 tests: T024, T025, T026 touch different files.
- US3 tests: T031, T032, T033 touch different files; T040 is parallel to them.
- US4: T048, T049, T050, T053, T054 touch different files.

---

## Parallel Example: User Story 1 tests

```bash
Task: "Write api/tests/test_discovery_domain.py (T016)"
Task: "Write api/tests/test_translate_ingredients_application.py (T017)"
Task: "Write api/tests/test_discovery_integration.py (T018)"
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 (T001 to T003), including the amendment commit.
2. Phase 2 (T004 to T015).
3. Phase 3 (T016 to T023).
4. **Stop and validate**: run the quickstart steps 2 to 5 (detection and no repeats).

### Incremental delivery

1. Setup and Foundational: foundation ready.
2. US1: detection works. Demo: new names appear in the standard table.
3. US2: translation works. Demo: a Spanish name appears for an English ingredient.
4. US3: admin review of custom values.
5. US4: the `jobs` service runs in Compose, `mcp` is removed.

---

## Notes

- Every task names its file path. Paths that are existing modules but not named in the plan (the recipe save path, the admin routes, the `ui/` admin section) are identified by the test that imports them, so the implementer can find them with a search.
- Task numbering changed from the earlier draft: FR-016, FR-017 and FR-019 are removed from the spec, so the id-link and ingredient-filtered search tasks are gone. The old T044 (rename and merge rights) is replaced by T040 (write guard), since FR-021 settles who may write standard names.
