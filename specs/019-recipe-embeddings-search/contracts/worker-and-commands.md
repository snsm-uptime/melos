# Contract: embedding worker, clean-up and operator commands

## Worker (`application/embedding_worker.py`, started in `api/app.py` lifespan)

One daemon thread per api process. Runs only when `EMBEDDING_WORKER_ENABLED` is true (default
`true`; `false` in the test overlay and in pytest).

```text
on start:
  check column dimension == GEMINI_EMBED_DIM, else log error once and stop
  if key or model missing: log INFO once, then sleep and re-check every 60 s
  catch-up: EmbeddingJobs.enqueue_missing(model)          (FR-010, never blocks start-up)
loop:
  wait up to EMBED_WORKER_POLL_S (5 s) or until woken
  repeat while jobs are due:
  ids = claim(batch=EMBED_BATCH_SIZE (1), lease_s=120)
  rows = content_for(ids); texts = strategy.render(each); titles = recipe titles
  result = embedder.embed_documents(texts, titles)        (one call, one attempt;
                                                           RETRIEVAL_DOCUMENT, title, 768)
  success → for each: write_if_current(...)
              written → job deleted
              not written (edited meanwhile) → release_changed (due now)
            missing token counts → count_tokens per text, failure → NULL
  failure → for each id: fail(id, next_wait(last_wait_s, policy, retry_after), class name)
  every pass with backlog > 0: log "embedding backlog count=%d oldest_s=%d" (FR-009b)
  once a day (first pass after 03:00 local, or at start if missed): delete search records
    older than SEARCH_RECORD_RETENTION_DAYS; failure retries by the same RetryPolicy (FR-017e)
on stop (lifespan exit): set stop flag, join up to 5 s
```

Logs carry only counts, class names and request ids. They never include text, vectors, keys or
service messages (FR-023).

## Waking the worker

Routes that save, edit or snapshot call `wake_embedding_worker(request.app)` after their service
returns. Waking only shortens the wait. Correctness relies on the job row, which was written in the
same transaction.

## Settings (`api/settings.py`, `load_embedding_settings()`)

| Variable | Default | Meaning |
|---|---|---|
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` | model id (was `text-embedding-004`) |
| `GEMINI_EMBED_DIM` | `768` | must equal the column dimension |
| `GEMINI_TEXT_TIMEOUT_S` | `10` | timeout per embed call (existing) |
| `EMBED_TEXT_STRATEGY` | `toon` | `toon` or `plain` |
| `EMBEDDING_WORKER_ENABLED` | `true` | `false` turns the thread off |
| `EMBED_WORKER_POLL_S` | `5` | longest idle wait |
| `EMBED_BATCH_SIZE` | `1` | recipes per call; raise only if the live check shows several texts per call work (research R2a) |
| `EMBED_RETRY_FIRST_WAIT_S` | `60` | first wait after a failure |
| `EMBED_RETRY_GROWTH` | `1.5` | each wait is this times the last |
| `EMBED_RETRY_CAP_S` | `7200` | longest wait |
| `SEARCH_MIN_CLOSENESS` | `0.65` | close or weak (provisional, research R12) |
| `SEARCH_RECORD_RETENTION_DAYS` | `180` | clean-up age |

Every variable is added to `.env.example` (no real values), `docker-compose.yml` (`api.environment`)
and, for `EMBEDDING_WORKER_ENABLED=false`, to `docker-compose.test.yml`.

## Operator command (`api/scripts/embeddings.py`)

Run inside the api container: `docker compose exec api uv run python -m scripts.embeddings <sub>`.

| Subcommand | Does | Output |
|---|---|---|
| `catch-up` | `enqueue_missing(model)` and exits; the worker does the calls | `queued=N` |
| `catch-up --reembed-other-strategy` | also queues recipes embedded with another strategy (FR-013) | `queued=N` |
| `status` | backlog count, oldest wait, failures by class | one line per figure |
| `score-report [--width 0.05]` | used share per score band (FR-017d) | table `low high shown used share` |
| `cleanup` | runs the 180-day clean-up now | `deleted=N` |

Exit code 0 on success and 1 on a database error. Every subcommand is safe to repeat.
