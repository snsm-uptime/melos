# M.E.L.O.S (Menus Everyone Loves to Share)

**App link:** melos.sebassoto.info
**Author:** Sebastian Soto Madrigal

## Pitch

M.E.L.O.S helps couples and small groups capture recipes they love, scale
ingredients for meals they cook, and shop together. It turns recipes from URLs
or photos into structured ingredients and steps using Gemini AI. The AI also
powers kitchen conversations: ask your recipes questions and get answers with
citations from what you've saved.

## The problem

Many couples and small groups collect recipes from different sources but struggle
to organize them, scale ingredients for varying amounts, and shop without
duplication. Today, they use spreadsheets, notes, or just remember what to buy.
Melos solves this by creating a shared space where everyone can contribute
recipes and plan meals together.

## What the app does

Melos is organized around **kitchens**: shared spaces where members collect
recipes, plan meals and shop together.

1. Sign up (or get invited by email) and join a kitchen as owner or member.
2. Capture recipes from a URL, an upload or by hand; the AI extracts title,
   servings, ingredients and steps into a draft you review.
3. Browse recipes with a normalized ingredient catalog and categories.
4. Add recipes to a cart with a number of meals and people; ingredients are
   scaled and consolidated.
5. Turn the cart into a shopping list, then archive it when you are done.
6. Chat with your kitchen: ask questions answered from your own recipes (with
   citations) and from past shopping lists.
7. Export recipes and lists to PDF or Markdown.

## The AI part

- **What it uses:** Gemini API via the `google-genai` SDK (chat model and
  embedding model, configured with `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`,
  `GEMINI_EMBED_DIM`), plus a RAG over the kitchen's recipes stored as vectors
  in PostgreSQL with `pgvector`. An MCP service (separate container, port 9000)
  exposes Melos to external AI clients.
- **Why this option:** [one or two sentences]
- **What happens if it fails:** every external call (Gemini, web fetch, SMTP)
  goes through a port in `application/ports.py` and maps errors to domain errors
  (e.g. `AIUnavailable`, `PageFetchFailed`). Raw SDK exceptions never reach the
  user; the app reports that the AI is unavailable and manual entry keeps
  working.

## How I built it

Melos bootstraps from my earlier **finance-dashboard** project, reusing its
proven auth, architecture, tooling and deployment patterns
(see [specs/001-finance-dashboard-reuse/spec.md](specs/001-finance-dashboard-reuse/spec.md)).

| | What | Notes |
|---|---|---|
| **Reused as-is** | Hexagonal `api/` layout, `ui/` shell, `scripts/` compose helpers, CI workflow, Dockerfiles, auth layer (sessions, argon2, password reset, email verification, rate limiting) | Auth layer is not modified without explicit approval |
| **Adapted** | Docker Compose (`pgvector/pgvector:pg16`, new `mcp` service), env prefix `FH_` → `MELOS_`, data dir `~/melos`, list → kitchen, UI English-only (language toggle removed) | Config changes go through `.env` and `api/settings.py`, never per-file renames |
| **New** | Gemini integration, recipe capture, cart/shopping list, conversations, embeddings, PDF export, MCP service | |
| **Not reused** | All finance domain code (cards, statements, budgets, FX, bank adapters) and finance seed credentials | |

**Stack:** Python 3.12 + `uv`, FastAPI, SQLAlchemy + Alembic, PostgreSQL 16 +
pgvector, pytest, ruff · Next.js 16 (App Router, Turbopack), React 19,
Tailwind CSS 4, TypeScript 5, Vitest, ESLint · Docker Compose (db, api, ui, mcp).

- **Tools:** Claude Code, Cursor, GitHub, Gemini API via google-genai SDK
- **Agent context file:** [AGENTS.md](AGENTS.md) (project governance and work instructions)
- **Specification:** [specs/001-finance-dashboard-reuse/spec.md](specs/001-finance-dashboard-reuse/spec.md) (bootstrap phase)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, code review process,
and governance. The project is governed by the [Project Constitution](.specify/memory/constitution.md).

## Run locally

Prerequisites: Docker, `uv`, Node.js / npm.

```bash
# 1. Configure secrets (never commit .env)
cp .env.example .env
#    fill in POSTGRES_PASSWORD, SESSION_SECRET, GEMINI_API_KEY, SMTP_*
#    SMTP is required for email verification, password reset, and kitchen invites.
#    Use a real provider (e.g., Gmail app password) — misconfigured SMTP returns 503
#    on the sending request and is logged. For dev: SMTP_HOST, SMTP_USER, SMTP_PASSWORD,
#    SMTP_FROM (RFC5322 format like "Melos <noreply@example.com>"), SMTP_STARTTLS=true

# 2. Create the data directory outside the repo
mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"

# 3. Install dependencies
(cd api && uv sync --group dev)
(cd ui && npm install)

# 4. Start db, api, ui and mcp (migrations run automatically on api start)
./scripts/compose-up.sh        # add -d to run in the background
```

Then check:

- UI: http://localhost:3000 (login page)
- API: http://localhost:8000/health
- MCP: http://localhost:9000/health

With `SEED_DEV_USER=1` (dev only) the API seeds two verified users (owner and
member) sharing one kitchen, ready for testing auth and kitchen membership.

**Tests and linting**

```bash
cd api && uv run ruff check . && uv run pytest -q
cd ui && npm run lint && npm run typecheck && npm test
```

Parallel work: `./scripts/worktree/worktree-add.sh <slug> <branch>` gives each
worktree its own Compose stack (`MELOS_COMPOSE_NAME`, `API_HOST_PORT`,
`UI_HOST_PORT`).

## Screenshots

[The app running, the app facing an edge case, a moment of your work with the AI
and the testing. Without any key in view.]
