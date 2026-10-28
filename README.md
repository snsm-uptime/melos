# M.E.L.O.S (Menus Everyone Loves to Share)

**App link:** melos.sebassoto.info
**Author:** Sebastian Soto Madrigal

## Pitch

M.E.L.O.S helps couples and small groups capture recipes they love, scale
ingredients for meals they cook, and shop together. It turns recipes from text,
URLs or photos into structured ingredients and steps using Gemini AI. The AI also
powers kitchen conversations: ask your recipes questions and get answers with
citations from what you've saved.

## The problem

Many couples and small groups collect recipes from different sources but struggle
to organize them, scale ingredients for varying amounts, and shop without
duplication. Today, they use spreadsheets, notes, or just remember what to buy.
Melos solves this by creating a shared space where everyone can contribute
recipes and plan meals together.

## What the app does

Melos is organized around **kitchens** and **notebooks**. A kitchen is a shared
space where members plan meals and shop together. Recipes live in notebooks:

- A **personal notebook** belongs to one owner; others join it by email invite.
  It is private and never shown in a kitchen.
- A **kitchen notebook** belongs to a kitchen; every member reads and writes it
  while they belong to the kitchen. A personal notebook reaches a kitchen only
  as a **snapshot**, an independent copy.

The flow:

1. Sign up (or get invited by email) and join a kitchen as owner or member.
   Everyone gets a default personal notebook and "My kitchen".
2. Capture a recipe from pasted text (URL and photo come later); Gemini
   extracts title, servings, ingredients and steps into a draft you review,
   matching ingredient names to the notebook's catalog ("onions" → "onion").
3. Save the draft into a notebook; browse, filter, edit and delete recipes, and
   scale a recipe's servings on its detail page.
4. Add recipes to the kitchen's cart with a number of people and meals;
   ingredients are scaled and consolidated into a shopping list.
5. Export the list as PDF or Markdown and finalize it as a snapshot.
6. Chat with your kitchen: questions answered from your own recipes (with
   citations) and from past shopping lists.

The interface is in Spanish by default, with English or Spanish chosen in the
account.

## Progress

Tracked in [dev/docs/backlog.yaml](dev/docs/backlog.yaml); the product spec is
[dev/docs/prd.md](dev/docs/prd.md). Delivery: 02/11/2026.

| Area | Status |
|---|---|
| Bootstrap: scaffold, auth, health checks, kitchens, invites, kitchen switcher (S-001 to S-014) | Done |
| Gemini extraction adapter (S-015) | Done |
| Personal and kitchen notebooks, notebook lists in the UI (S-056, S-060) | Done |
| Capture from text, clear error messages, catalog matching (S-016, S-017, S-018) | Done |
| Save a draft, recipe lists, detail, edit and delete (S-020, S-021, S-027) | Done |
| Servings scaling on the recipe detail (S-062) | Done |
| Spanish as the default language, every screen translated (S-063) | Done |
| Cart, shopping list, export and finalize (S-022 to S-025) | Next |
| Notebook snapshots, invites, ownership passing, notebook CRUD (S-035, S-057, S-058, S-059) | Backlog |
| Embeddings, conversations, the kitchen assistant (S-019, S-029 to S-031) | Backlog |
| Capture from a URL, recipe PDF (S-026, S-028) | Backlog |
| MCP tools with API keys, deployment, AI evaluation set (S-032 to S-034) | Backlog |

Main ingredients and cuisines were moved out of the MVP on 2026-10-27 (S-061,
PRD Appendix E); ingredient catalog matching stays.

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
| **Adapted** | Docker Compose (`pgvector/pgvector:pg16`, new `mcp` service), env prefix `FH_` → `MELOS_`, data dir `~/melos`, list → kitchen, UI in Spanish (default) and English, chosen in the account | Config changes go through `.env` and `api/settings.py`, never per-file renames |
| **New** | Gemini integration, notebooks, recipe capture, cart/shopping list, conversations, embeddings, PDF export, MCP service | |
| **Not reused** | All finance domain code (cards, statements, budgets, FX, bank adapters) and finance seed credentials | |

**Stack:** Python 3.12 + `uv`, FastAPI, SQLAlchemy + Alembic, PostgreSQL 16 +
pgvector, pytest, ruff · Next.js 16 (App Router, Turbopack), React 19,
Tailwind CSS 4, TypeScript 5, Vitest, ESLint · Docker Compose (db, api, ui, mcp).

- **Tools:** Claude Code, Cursor, GitHub, Gemini API via google-genai SDK
- **Agent context file:** [AGENTS.md](AGENTS.md) (project governance and work instructions)
- **Specification:** [specs/001-finance-dashboard-reuse/spec.md](specs/001-finance-dashboard-reuse/spec.md) (bootstrap phase)

## Development harness: agents and Spec Kit

Melos is built with AI coding agents (Claude Code, Cursor, Gemini) working
inside a fixed harness, so every agent gets the same context and follows the
same rules.

**Agent context**

| File or folder | Role |
|---|---|
| [AGENTS.md](AGENTS.md) | The single instruction file: architecture, domain rules, dev commands, checks and what not to do. `CLAUDE.md` and `GEMINI.md` only point to it |
| [.specify/memory/constitution.md](.specify/memory/constitution.md) | Non-negotiable engineering principles; changed only with approval (`/speckit-constitution`) |
| [dev/docs/prd.md](dev/docs/prd.md) | Product spec: architecture, flows, data model, journeys and acceptance criteria |
| [dev/docs/backlog.yaml](dev/docs/backlog.yaml) | Stories (`S-NNN`) with priority, status (`backlog`, `in_design`, `in_progress`, `done`), source and verification notes |
| `dev/skills/` | Work states (Creating, Logic, Learning, Optimizing, Reflecting) the agent picks per request, plus procedures such as TOON encoding and saving memory |
| `dev/memory/` | Append-only daily log (`ddMMYY.md`) of decisions and finished changes, read at the start of each session |

**Spec Kit workflow.** Each backlog story becomes a spec folder
`specs/NNN-short-name/`, where `NNN` is the story number (S-016 →
`specs/016-capture-recipe-text/`). The bootstrap spec
`specs/001-finance-dashboard-reuse/` covers S-001 to S-014. The commands live
as skills in `.claude/skills/`:

1. `/speckit-specify`: write `spec.md` from the story (created with
   `.specify/scripts/bash/create-new-feature.sh --number <story>` so the folder
   number is the story's).
2. `/speckit-clarify`: ask up to five targeted questions and record the answers
   in the spec.
3. `/speckit-plan`: produce `plan.md`, research, data model, contracts and a
   quickstart.
4. `/speckit-tasks`: produce a dependency-ordered `tasks.md`.
5. `/speckit-analyze` and `/speckit-checklist`: check spec, plan and tasks
   against each other and the constitution before building.
6. `/speckit-implement`: work through the tasks with tests;
   `/speckit-converge` appends tasks for anything still unbuilt.

When a story is done, its backlog entry moves to `done` with a verification
note (tests run, migrations checked, manual walks still open). Each story goes
on its own branch and is merged by pull request after review; agents do not
push or deploy without it.

**Checks.** api tests run in Compose
(`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`)
with ruff; ui runs vitest, ESLint and the TypeScript check. CI
(`.github/workflows/ci.yml`) runs the api and ui checks on every push and
pull request. Worktrees (`scripts/worktree/`) give parallel agents
their own Compose stack.

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
