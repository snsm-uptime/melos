# Health Contract (api, ui, mcp)

**Status:** Bootstrap contract (D6). It supersedes the "Health Check Endpoint" section of [error-responses.md](error-responses.md).
**Used by:** Compose healthchecks, `quickstart.md` §3, grading-day checks (constitution §7).

## GET /health

| Service | URL (dev) | Served by |
|---------|-----------|-----------|
| api | `http://localhost:${API_HOST_PORT:-8000}/health` | `api/api/routes/health.py` |
| ui | `http://localhost:${UI_HOST_PORT:-3000}/health` | `ui/app/health/route.ts` (does not proxy to the api) |
| mcp | `http://localhost:${MCP_HOST_PORT:-9000}/health` | `mcp/server/main.py` |

**Auth:** none. It must answer before sign-in and without an API key.

**Response `200 OK`** (`Content-Type: application/json`):

```json
{
  "status": "healthy",
  "service": "api",
  "timestamp": "2026-10-19T12:00:00+00:00"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `status` | string | always `"healthy"` when the process is up |
| `service` | string | `"api"`, `"ui"` or `"mcp"` |
| `timestamp` | string | ISO-8601, timezone-aware UTC (no naive `utcnow()`) |

**Semantics:** liveness only. The endpoint does not check the database, Gemini or SMTP. A readiness check with a `503` body is out of scope for the bootstrap.

**Must not:** expose versions of dependencies, environment values or secrets.

## Compose healthchecks

| Service | Probe | Notes |
|---------|-------|-------|
| db | `pg_isready` | existing |
| api | python `urllib` → `http://127.0.0.1:8000/health` | the slim image has no curl |
| ui | `node -e fetch('http://127.0.0.1:3000/health')` | existing |
| mcp | python `urllib` → `http://127.0.0.1:9000/health` | existing |

All four report `healthy` within about 30 s of `./scripts/compose-up.sh -d` on a warm image cache.

## Tests

- `api/tests/test_health.py`: asserts `200`, `status == "healthy"`, `service == "api"`, and a parseable timestamp.
- mcp: one equivalent test against `server.main:app`.
- ui: covered by the Compose healthcheck. A vitest on the route handler is optional.
