# Contract: `jobs` Compose service

The job exposes no network interface. Its contract is its Compose definition, its environment, its
healthcheck, and its exit behaviour.

## Compose definition

- Built from `./api` with the same Dockerfile as `api`.
- Command: `python -m jobs`.
- `depends_on: db` with `condition: service_healthy`.
- `networks: [internal]` only. No `ports:` entry (FR-008, FR-009).
- `restart: unless-stopped`.
- `logging`: the shared `json-file` anchor used by every service (R7).

## Environment

| Variable | Required | Default | Meaning |
|----------|----------|---------|---------|
| `DATABASE_URL` | yes | from `db` service | Same URL shape as `api`, pointing at `db` on the internal network. |
| `GEMINI_API_KEY` | yes | none | From `.env` only (FR-014). |
| `GEMINI_TRANSLATE_MODEL` | yes | none | Model name, from configuration (FR-015). No default in code. |
| `JOBS_INTERVAL_SECONDS` | no | `3600` | Time between runs. Fixed at hourly by default (spec assumption). |
| `JOBS_TRANSLATE_BATCH_SIZE` | no | `50` | Maximum model calls per run (R6). |
| `JOBS_RUN_ONCE` | no | `0` | `1` runs once and exits, for manual runs and tests (quickstart). |
| `JOBS_HEARTBEAT_PATH` | no | `/tmp/jobs-heartbeat` | Where the heartbeat file is written (R8). |
| `PYTHONUNBUFFERED` | no | `1` | So logs reach Compose at once. |

Startup waits for the database. It retries the connection with a fixed delay and logs each attempt,
and it does not exit on a failed first attempt (FR-011).

## Healthcheck

```text
test: heartbeat file exists and its mtime is less than 7200 seconds old
interval: 5m, timeout: 5s, retries: 3, start_period: 60s
```

The heartbeat is written at the start of every loop iteration, including iterations that find
nothing and skipped runs (R8).

## Exit behaviour

- Normal operation: never exits. Errors inside a run are caught, recorded on `job_run`, logged, and
  the loop continues.
- `JOBS_RUN_ONCE=1`: exits `0` after a succeeded or skipped run, and `1` after a failed run.
- Process-level failure (for example, an unreadable configuration): exits non-zero, and Compose
  restarts it.
