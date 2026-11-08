# Research: Scheduled Ingredient Translation Service

No NEEDS CLARIFICATION markers remain. Each decision lists what was chosen, why, and what else was
considered.

## R1. Where the job code lives

**Decision**: `api/jobs/` in the `api` package. It runs from the `api` image with
`python -m jobs` as the command. Compose defines it as its own service, `jobs`.

**Rationale**: The job needs the same normalization and the same Gemini adapter as the api. Sharing
them keeps one set of rules. The Compose service still gets its own environment, no port, and its
own restart policy.

**Alternatives considered**:
- A new `jobs/` package with its own dependencies. Rejected: it copies domain rules, and copies
  drift.
- A thread inside `api`, like the embedding worker (spec 019). Rejected: the user asked for a
  separate service, and job load would share the request process.

## R2. Hourly schedule and single run

**Decision**: An asyncio loop sleeps until the next full hour. Each run takes
`pg_try_advisory_lock(<fixed key>)` before doing anything. If the lock is busy, the run is logged as
`skipped` and nothing happens.

**Rationale**: No scheduler dependency. The lock works across restarts and replicas, which gives
FR-012 without a table.

**Alternatives considered**: APScheduler (a new dependency for one timer). Compose `restart` with a
cron loop in the shell (no run log, no lock).

## R3. One AI call per standard ingredient, shared by everyone

**Decision**: `standard_ingredient.ai_checked_at` is null until the model has answered. The job
calls the model only for standard ingredients where it is null. A valid answer saves the
other-language name (`source = ai`) and sets `ai_checked_at`. An invalid answer sets
`ai_checked_at` and saves nothing. A failed call (error, timeout, unusable output) leaves
`ai_checked_at` null, so the next run retries it.

**Rationale**: One field gives the reuse rule (FR-005a), the no-repeat rule (FR-005), and the retry
rule (FR-006), with no separate state table. Invalid names are not retried, so they cost nothing
after their first check.

**Alternatives considered**: A separate `translation_attempt` table with attempt counts and back-off.
Rejected for now: no retry cap is needed while batches are capped (R6).

## R4. Notebook catalogs and recipe lines stay as they are

**Decision**: The per-notebook and kitchen catalogs (`ingredient`, `ingredient_name`) keep their
current tables, columns and rules. `recipe_ingredient` keeps carrying the name. The standard table
is a separate set of tables (`standard_ingredient`, `standard_ingredient_name`). Nothing links a
notebook catalog row to a standard row, and no recipe line gets an id.

**Rationale**: The spec's revised Q2 keeps notebook catalogs unchanged. Adding a link would change
the catalog rules the spec keeps, and FR-016 and FR-017 were removed for that reason. A separate
table means the migration only adds tables and does not rewrite existing rows, so nothing is lost
and rollback is a drop.

**Alternatives considered**:
- Central id on every recipe line, with the notebook catalog pointing at it. Rejected: it changes
  the per-notebook rules and needs a backfill across every notebook.
- Replace the notebook catalogs with the central list (the earlier decision, Q2 option A).
  Superseded by the revised Q2.

## R5. Discovery of new names

**Decision**: Each run scans `recipe_ingredient` lines of recipes with `updated_at` at or after the
start of the last successful run (`job_run.started_at`). For each line, it normalizes the name
(trimmed, lower-case, singular) with the existing rule, and creates a `standard_ingredient` with
`ai_checked_at` null if no row has that `normalized_name`. The line's recipe language gives the
name's language. The first run has no watermark and scans every recipe once.

**Rationale**: `recipe.updated_at` is already stored, and the line table already has the names. The
watermark is one timestamp. The scan is idempotent, so an overlapping window costs nothing but a
re-check.

**Alternatives considered**: A change-data-capture trigger on recipe lines (more moving parts). A
full rescan every hour (fine at this scale, but the watermark is cheap and keeps the run fast as
data grows).

## R6. Cost cap and batching

**Decision**: `JOBS_TRANSLATE_BATCH_SIZE` (default 50) caps the model calls in one run. The rest
stay null and are picked up next hour. Each call is one standard ingredient.

**Rationale**: Keeps AI cost predictable even after a large import. One call per ingredient is the
smallest unit that shares the result.

**Alternatives considered**: Batching several ingredients per prompt. Rejected for now: a failure
would lose a whole batch, which FR-006 forbids. It can be revisited if cost requires it.

## R7. Logs: centralized output

**Decision**: The job writes JSON lines to stdout, like the other services. Compose's logging
configuration (`json-file` with rotation, set once in a shared anchor) applies to every service.
Each run writes a start line, one line per failure, and an end line with counts (contract
`run-log.md`). The `job_run` row keeps the same counts for queries.

**Rationale**: Docker already collects stdout from every service into one place (`docker compose
logs`). No extra log platform is added. The `job_run` table answers "what happened last night"
without parsing logs.

**Alternatives considered**: A log shipper (Loki, ELK). Out of scope per the spec assumptions.

## R8. Health

**Decision**: `jobs` writes the current time to a heartbeat file at the start of every loop
iteration. The Compose healthcheck fails if the file is older than two hours.

**Rationale**: No HTTP server to open. The probe checks the loop itself, not only that the process
exists.

**Alternatives considered**: An HTTP `/health` on an internal port. Rejected: an open port for one
probe, and it would not show a stuck loop.

## R9. Migration

**Decision**: One additive Alembic migration (`0022_standard_ingredients`):
1. Create `standard_ingredient`, `standard_ingredient_name`, `standard_ingredient_review` and
   `job_run`, with their constraints and indexes (data-model.md).
2. Create no rows and change no existing table. The first job run seeds the standard table from
   existing recipe lines (R5, no watermark).

**Rationale**: The notebook catalogs and recipes are untouched, so the migration cannot lose data
and the downgrade is a table drop. The seeding happens in the job, under its lock and with its
batch cap (R6), not in a long migration.

**Risks** (for tasks.md):
- The first run may need several hourly runs to clear a large backlog, since R6 caps calls per run.
  This is expected and matches SC-002's retry window; the run log shows the remaining count.
- Two notebooks spelling one ingredient differently still have separate notebook catalogs. That is
  the current behaviour under the revised Q2, and the standard table is where they meet.

## R10. Model prompt and output

**Decision**: One Gemini call per standard ingredient, with the name, its source language and the
target language, in a delimited block. The output is JSON with `valid` (boolean) and `translation`
(string or null). The adapter rejects any other shape as a failure (R3). Prompt text lives in a
file, like the existing pair suggester (spec 043 R9).

**Rationale**: One call gives both the validity check and the translation. A strict output shape
makes failures visible instead of saving bad text.

**Alternatives considered**: Two calls, one for validity and one for translation. Rejected: doubles
cost for the same information.

## R11. Admin review of custom values (FR-022)

**Decision**: When a person enters their own value for a name the AI produced (in their notebook,
as today), the system writes a `standard_ingredient_review` row: the standard ingredient, the AI
name it replaces, the proposed value, the proposing user, and a status (`pending`, `accepted`,
`rejected`). The admin dashboard (spec 055, `users.is_admin`) lists pending rows. Accepting a row
writes a `standard_ingredient_name` with `source = admin` and sets the review to `accepted`.
Rejecting sets `rejected` and changes nothing in the standard table.

**Rationale**: A separate review table keeps the standard table free of unvalidated text, and it
keeps the admin list as the only path into the standard names. It follows the existing admin
dashboard pattern rather than a new screen.

**Alternatives considered**: Writing the custom value straight into the standard table with a
`pending` flag. Rejected: every query on the standard table would need the flag, and a missed filter
would expose unvalidated names.

## Resolved by the revision

- Permissions for renaming a central ingredient (R9, earlier draft): resolved. Standard names change
  only through the job and admin acceptance (FR-021).
- Recipe-line ids and the ingredient-filtered vector search (R4, earlier draft, and FR-019): removed
  with the spec's id links. Vector rows stay as they are today (FR-018).
