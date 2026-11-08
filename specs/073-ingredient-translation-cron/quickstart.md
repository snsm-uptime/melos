# Quickstart: Validate the ingredient translation job

How to run the job by hand and check that it works end to end. Assumes the stack is set up per
`README.md`, and `GEMINI_API_KEY` and `GEMINI_TRANSLATE_MODEL` are set in `.env`.

## 1. Start the stack

```bash
./scripts/compose-up.sh -d
docker compose ps        # jobs is "running" and "healthy"; mcp is gone
```

Confirm the job has no published port:

```bash
docker compose port jobs 8000   # no output: no port is published
```

## 2. Add an ingredient in English

In the UI, add a recipe in English with an ingredient the catalog does not have yet, for example
"bell pepper". Note its time.

## 3. Run the job once

```bash
docker compose run --rm -e JOBS_RUN_ONCE=1 jobs
```

Expected: exit code `0`, and log lines `run.start`, `discovery.done` with `found >= 1`,
`translate.item` with `outcome: translated`, and `run.end` with `status: succeeded`.

## 4. Check the result in the database

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT s.normalized_name, n.language, n.name, n.source, n.model
     FROM standard_ingredient s JOIN standard_ingredient_name n ON n.standard_ingredient_id = s.id
    WHERE s.normalized_name = 'bell pepper';"
```

Expected: one `ai` row with `language = es` and a Spanish name, plus the `discovery` row in `en`.
The notebook catalogs are not changed by the job.

## 5. Check that nothing repeats

Run step 3 again. Expected: `found 0`, `translated 0`, and no `translate.item` lines. The model is
not called.

## 6. Check reuse across people

Add "bell pepper" to a recipe in a second notebook, then run step 3. Expected: no model call, since
`ai_checked_at` is already set (FR-005a).

## 7. Check the hourly schedule

```bash
docker compose logs -f jobs
```

Expected: a `run.start` at the top of each hour, and a heartbeat within two hours.

## 8. Check the standard lookup

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "EXPLAIN ANALYZE SELECT id FROM standard_ingredient WHERE normalized_name = 'bell pepper';"
```

Expected: an index scan on the unique `normalized_name` index, not a sequential scan.

## 9. Check the admin review list

Enter a custom value for "bell pepper" in a recipe, as a person would after reading the agent's
output. Sign in as the admin and open the admin dashboard. Expected: one `pending` review row with
the AI name it replaces and the custom value. Accepting it adds an `admin` name to the standard
table; rejecting it changes nothing in the standard table.

## Troubleshooting

- `jobs` unhealthy: the heartbeat is stale. Read `docker compose logs jobs` for a `db.wait` loop or
  a crash.
- `run.skipped` with `lock_busy`: another run is still active. Wait for it to end, or check
  `job_run` for a row stuck in `running`.
- `translate.failed` on every item: check `GEMINI_API_KEY` and `GEMINI_TRANSLATE_MODEL`.
