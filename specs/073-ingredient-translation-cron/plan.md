# Implementation Plan: Scheduled Ingredient Translation Service

**Branch**: `073-ingredient-translation-cron` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/073-ingredient-translation-cron/spec.md`

## Summary

Once an hour, a job finds ingredient names in recipe lines that the standard table has not yet
seen, adds them, and asks Gemini once per standard ingredient to validate the name and give its
translation into the other supported language. A valid translation is saved without confirmation,
marked AI-made. Each standard ingredient is checked by the AI once, so names that are already
standard never trigger a new call (FR-005a).

The per-notebook and kitchen catalogs keep their current rules and tables. The standard table is
added next to them. Recipe lines keep their names. A person's own value for an AI-made name goes to
an admin review list; accepted values join the standard table (FR-022). The `mcp` service is
removed and replaced by a `jobs` service in Compose.

Technical approach ([research.md](research.md)):

- The job is a separate Compose service built from the existing `api/` image with its own entry
  point, so it reuses the domain normalization and the Gemini adapter instead of copying them (R1).
- The hourly loop takes a Postgres advisory lock, so only one run is active at a time (R2).
- The standard table is separate: `standard_ingredient` and `standard_ingredient_name`. Discovery
  reads recipe line names and creates standard rows by normalized name (R4, R5).
- Each standard ingredient gets `ai_checked_at`. The job only calls the AI when it is null, and a
  failed call leaves it null so the next hourly run retries (R3).
- Custom values go to `standard_ingredient_review` and the existing admin dashboard (R11).

## Technical Context

**Language/Version**: Python 3.12 (api and jobs, managed with `uv`)

**Primary Dependencies**: FastAPI and SQLAlchemy (existing api), Alembic, `google-genai` (through
the `adapters/llm/` port only), lingua (existing language detection). No new dependency.

**Storage**: PostgreSQL 16 with pgvector (existing `db` service). Four new tables, one additive
Alembic migration (data-model.md, research.md R9).

**Testing**: pytest. Domain tests with no database; application tests against a fake translation
port; integration tests against Postgres in the Compose test overlay (constitution 6).

**Target Platform**: Docker Compose on the owner's Linux server (production) and on the developer's
machine (local).

**Project Type**: Web service (api, ui) plus a scheduled job service in the same Compose stack.

**Performance Goals**: Every ingredient added within 1 hour of being added is in the standard table
after the next run (SC-001). A run that finds nothing new finishes in under 10 seconds and makes no
AI calls (SC-003).

**Constraints**: No host port on the job service (FR-008). Secrets from environment only (FR-014).
Translation model name from configuration (FR-015). A failed AI call never blocks other ingredients
in the batch (FR-006). Standard names change only through the job and admin acceptance (FR-021).

**Scale/Scope**: A household app, so a few thousand recipes and a few thousand standard ingredients.
At most `JOBS_TRANSLATE_BATCH_SIZE` AI calls per run (default 50) to cap cost.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version 2.0.0. Gates checked against each principle:

| Principle | Status | Note |
|-----------|--------|------|
| 1. Simplicity and Reuse | **Violation — amendment required** | "Only four services: `db`, `api`, `ui`, `mcp`. No queue, no worker." The `jobs` service is a fifth service, and a scheduled worker. Justified in Complexity Tracking. Blocked until the project lead amends Principle 1. |
| 1. Auth layer immutable | Pass | No auth change. The admin review uses the existing `users.is_admin` gate. |
| 1. External calls through a port | Pass | Gemini only through a port in `application/` with a Gemini adapter in `adapters/llm/`. |
| 2. Tech stack stability | Pass | Python 3.12, `uv`, FastAPI and SQLAlchemy unchanged, Alembic migration, `google-genai`. |
| 2. Model names from settings | Pass | `GEMINI_TRANSLATE_MODEL` from environment (FR-015). |
| 3. Hexagonal architecture | Pass | Use case in `application/`, rules in `domain/`, I/O in `adapters/`. No SDK import in `domain/`. |
| 4. Security and privacy | Pass | Secrets only from `.env`. Tests use invented ingredient names only. Recipe text is never sent to the model, only one ingredient name. |
| 5. No AI shortcuts: AI draft confirmed first | **Violation — exception required** | AI-validated translations are saved without confirmation (Q1 option A, FR-020). Blocked until the project lead adds an explicit exception to Principle 5. Other parts pass: the model never answers from general knowledge; the prompt covers only ingredient names. |
| 5. No unit conversion | Pass | Not touched. |
| 6. Testing and quality | Pass | Layers listed in Technical Context. |
| 7. Deployment: compose only, no reverse proxy | Pass | `jobs` added to the existing Compose files. |
| 7. Health checks on `/health` for ui, api, mcp | **Needs amendment** | `mcp` is removed, so its check goes. `jobs` has no HTTP server, so it uses a heartbeat file. The list in Principle 7 must name `jobs` instead of `mcp`, and allow a heartbeat check. |
| 9. Product scope | Pass | Post-MVP, ranked by backlog priority. |

**Gate result**: ERROR on three items (Principles 1, 5 and 7). They are decisions the user has
already made (Q1, the `jobs` service, removing `mcp`). Implementation tasks must not start before
the project lead approves the amendment, under the Amendment Procedure, covering: the fifth service
and the scheduled job; the Principle 5 exception for AI-validated translations; and the Principle 7
health-check wording. Design and research can continue, since they are documents only.

The revised catalog model adds no new principle violation: notebook catalogs are unchanged, and
admin acceptance follows the existing admin dashboard.

## Project Structure

### Documentation (this feature)

```text
specs/073-ingredient-translation-cron/
├── plan.md                    # This file
├── research.md                # Phase 0 output
├── data-model.md              # Phase 1 output
├── quickstart.md              # Phase 1 output
├── contracts/
│   ├── job-service.md         # Compose service, config, health, exit behaviour
│   ├── translation-port.md    # AI validate-and-translate port: input and output
│   └── run-log.md             # Log lines and the job_run record
├── checklists/requirements.md
└── tasks.md                   # Not created by /speckit-plan; stale until regenerated
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── ingredient_catalog.py      # existing; normalization reused
│   └── ingredient_translation.py  # NEW: pure types, validation, language rule
├── application/
│   ├── ports.py                   # + IngredientTranslator port
│   ├── translate_ingredients.py   # NEW use case: discover, translate, record run
│   └── review_standard_names.py   # NEW use case: list, accept, reject custom values (admin)
├── adapters/
│   ├── llm/
│   │   ├── gemini_translator.py   # NEW Gemini adapter for the port
│   │   └── prompts/ingredient_translation.txt   # NEW
│   └── persistence/
│       ├── models.py              # + standard_ingredient*, job_run, review models
│       ├── job_lock.py            # NEW Postgres advisory lock
│       ├── standard_ingredients.py  # NEW discovery, save translation, reads
│       ├── job_runs.py            # NEW run record and watermark
│       └── migrations/versions/0022_standard_ingredients.py   # NEW, additive
├── jobs/
│   ├── __main__.py                # NEW entry point: hourly loop, or one run with JOBS_RUN_ONCE=1
│   ├── run_log.py                 # NEW JSON-line events
│   └── heartbeat.py               # NEW heartbeat file
└── tests/
    ├── test_ingredient_translation_domain.py
    ├── test_discovery_domain.py
    ├── test_translate_ingredients_application.py   # fake translator
    ├── test_review_standard_names_application.py
    └── test_*_integration.py                       # Postgres: discovery, reuse, failure, lock, review

docker-compose.yml                 # mcp removed; jobs added on the internal network, no ports
docker-compose.dev.yml             # jobs env overrides
docker-compose.prod.yml            # jobs env from server environment
mcp/                               # removed in the same change (FR-013)
ui/ (admin dashboard section)      # list of pending reviews with accept and reject (spec 055 pattern)
```

**Structure Decision**: The job lives in `api/jobs/` and runs from the `api` image with a different
entry point, so it shares the domain code and the Gemini adapter. It is still its own Compose
service, with no published port, its own environment, and its own restart policy. Putting it in a
separate package would copy the normalization rules, and a second copy would drift.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Fifth Compose service and a scheduled worker (Principle 1) | The user asked for a separate Python cron service on the private network with access to `db` | Running the job inside `api` on a thread would meet the "no worker" rule, but the user asked for a separate service, and an in-process timer would stop when `api` restarts and mix job load into the request path |
| AI translations saved without confirmation (Principle 5) | Q1 option A: the standard table grows automatically, and each name is checked once for everyone | Confirmation queue (Q1 B) keeps the rule but leaves translations unshared until a person acts, which defeats the reuse goal |
| No `/health` HTTP endpoint on `jobs` (Principle 7) | The job has no HTTP server, and adding one only for a probe is more surface | A heartbeat file read by the Compose healthcheck gives the same signal with no open port |
