# Contract: Run log

Each run writes JSON lines to stdout. Compose collects them with the other services' logs
(`docker compose logs jobs`). Each line has the same keys so the output can be filtered.

## Line shape

```json
{"ts": "2026-11-07T14:00:00Z", "service": "jobs", "run_id": "<uuid>", "event": "<event>", "...": "..."}
```

## Events

| Event | When | Extra keys |
|-------|------|------------|
| `run.start` | Lock acquired, run begins | `started_at` |
| `run.skipped` | Lock busy, another run active | `reason: "lock_busy"` |
| `discovery.done` | Recipe scan finished | `recipes_scanned`, `found` |
| `translate.item` | One standard ingredient handled | `standard_ingredient_id`, `outcome` (`translated`, `rejected`, `failed`) |
| `translate.failed` | One call failed | `standard_ingredient_id`, `error_kind` (see translation-port.md) |
| `run.end` | Run finished | `status`, `found`, `translated`, `rejected`, `failed`, `duration_ms` |
| `db.wait` | Database not ready at startup | `attempt`, `retry_in_s` |

Logged values never include the full recipe text, the author's name, or the API key. Ingredient
names are logged by id, not by name, so the log holds no recipe content.

## Stored record

The same counts go to `job_run` (data-model.md), so the last successful run can be found with a
query. The `job_run.started_at` of the last `succeeded` row is the discovery watermark (R5).
