# Contributing to Melos

Thank you for your interest in contributing to Melos! This document outlines our development workflow, governance principles, and expectations for all contributors.

## Before You Start

**Read the [Project Constitution](.specify/memory/constitution.md).** It establishes the engineering principles, architectural boundaries, and non-negotiable rules that all contributors must follow. If you need an exception to the constitution, ask for written approval.

Also read [AGENTS.md](AGENTS.md) for project structure, development environment setup, and the work states (Reflecting, Learning, Reasoning, Creating, Optimizing) that guide how we approach different types of work.

## Development Workflow

### Setting Up Your Environment

Prerequisites: Docker with Compose v2, `uv`, Node.js / npm

```bash
# 1. Clone the repository and check out the implementation branch
git clone <repo-url>
cd melos
git checkout implementation/001-bootstrap

# 2. Copy the environment template and fill in your values
cp .env.example .env
# Add real values for:
# - POSTGRES_PASSWORD (any secure string for dev)
# - SESSION_SECRET (any secure string for dev)
# - GEMINI_API_KEY (if testing AI features)
# - SMTP_* (if testing email features)

# 3. Create the data directory
mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"

# 4. Install dependencies
cd api && uv sync --group dev
cd ../ui && npm install
```

### Starting the Development Stack

```bash
# Start all services (db, api, ui, mcp) in the foreground
./scripts/compose-up.sh

# Or in the background
./scripts/compose-up.sh -d

# Stop services (keep data)
./scripts/compose-down.sh

# Restart services
./scripts/compose-restart.sh -d

# Wipe the database (careful!)
./scripts/compose-wipe-db.sh
```

Services will be available at:
- **UI (BFF):** http://localhost:3000
- **API:** http://localhost:8000 (health check: `/health`)
- **MCP:** http://localhost:9000 (health check: `/health`)

### Making Changes

1. **Create a feature branch** from `implementation/001-bootstrap`:
   ```bash
   git checkout -b feature/T###-your-feature-name
   ```

2. **Code according to the constitution** and AGENTS.md. Key rules:
   - No secrets in code, README or commit messages (use `.env` only)
   - Small changes: one per commit
   - Explain WHY in commit messages, not WHAT (the code shows the WHAT)
   - Auth layer is unchanged except for FR1.1 naming (see spec)
   - `domain/` imports nothing from `adapters/`, `api/`, FastAPI or SDK code
   - Every kitchen-scoped query checks membership (`application/kitchen_access.py`)
   - Schema changes go through Alembic migrations

3. **Run tests before committing**:
   ```bash
   # Python: linting and tests
   cd api && uv run ruff check .
   cd api && uv run pytest -q

   # JavaScript: linting, type checking, tests
   cd ui && npm run lint
   cd ui && npm run typecheck
   cd ui && npm test
   ```

4. **Run the full Compose test suite** before opening a PR:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
   ```

5. **Use git worktrees for parallel development**:
   ```bash
   ./scripts/worktree/worktree-add.sh <slug> <branch>
   ```
   This gives each worktree its own Compose stack with isolated ports and data.

## Code Review Process

### What to Include in Your PR

1. **Description:** What does this PR do? Why?
2. **Changes:** What files changed? Which spec tasks does it complete?
3. **Testing:** What did you test? How can a reviewer verify it works?
4. **Checklist:**
   - [ ] Linting passes (`ruff check`, `npm run lint`)
   - [ ] Tests pass (Python: `pytest`, JavaScript: `npm test`)
   - [ ] No secrets in code, comments or `.env.example`
   - [ ] Commit messages explain WHY, not WHAT
   - [ ] No breaking changes to existing APIs (unless spec-approved)

### Review Expectations

- All PRs require at least one review before merging to `main`
- Reviews focus on correctness, clarity, and adherence to the constitution
- If the constitution flags an issue, provide written context or ask for approval
- Ask questions if the intent is unclear — communication prevents rework

### Merging

- Squash commits for clarity (`git rebase -i`)
- Use descriptive commit messages (see format below)
- Ensure CI passes on the branch before merging
- Delete the feature branch after merging

## Commit Message Format

```
<type>(<scope>): <subject>

<body (optional)>
```

**Type:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`  
**Scope:** task ID (e.g., `T050`, `T078`) or module name (e.g., `auth`, `kitchens`, `health`)  
**Subject:** one line, imperative mood, ~50 characters  

**Example:**
```
feat(T050): Implement Docker Compose health checks for all services

Add /health endpoints for api, ui, and mcp services. Endpoints return
timezone-aware UTC timestamp and service name per contracts/health.md.
Updated docker-compose.yml healthcheck probes.

Fixes #50
```

## Architecture and Constraints

### Hexagonal Architecture (api/)

```
domain/          — Pure business rules, no I/O
  ├── kitchens, kitchen_access, kitchen_invite, signup, auth, email_verification, ...
application/     — Use cases and ports (interfaces)
  ├── services: CreateKitchenService, SignUpService, ...
  └── ports.py: LLMPort, EmailPort, ...
adapters/        — Implementations of ports
  ├── llm/       — Gemini API (when recipes feature exists)
  ├── email/     — SMTP
  └── persistence/ — PostgreSQL
api/              — HTTP layer
  ├── routes/    — FastAPI endpoints
  ├── schemas/   — Pydantic models
  └── deps.py, settings.py, app.py
```

### Key Rules

| Rule | Why | How to check |
|------|-----|-------------|
| `domain/` is pure | Testable without I/O | `grep -r "import.*fastapi\|import.*sqlalchemy" api/domain/` — should be empty |
| Auth layer unchanged | Stability | Only FR1.1 renames allowed (config via `.env` and `settings.py`) |
| No secrets in code | Security | `grep -r "password\|api.*key\|secret" --exclude-dir=.git` must not match real values |
| Membership checks in `application/` | Authorization | Non-members get 404 (not 403 or silent failure) |
| Schema via Alembic | Auditability | All database changes in `api/adapters/persistence/migrations/versions/` |

## Testing

### Python (api/)

```bash
# Linting
cd api && uv run ruff check .

# Unit and domain tests
cd api && uv run pytest -q tests/

# Integration tests (requires Postgres)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api

# Type checking (when available)
cd api && uv run mypy .
```

### JavaScript (ui/)

```bash
# Linting
cd ui && npm run lint

# Type checking
cd ui && npm run typecheck

# Unit tests
cd ui && npm test

# Development server (hot reload)
cd ui && npm run dev
```

### Manual Testing in the Browser

Before opening a PR, test the key user flows:

1. **Sign-up and verification**
   - Create a new account
   - Verify email arrives (if SMTP configured)
   - Sign in with the new credentials

2. **Kitchen management**
   - Create a kitchen
   - Invite a member by email
   - Accept invite in a new session
   - Check that member sees the kitchen and owner-only actions are not offered

3. **Health checks**
   - `curl http://localhost:8000/health` returns `"service":"api"`
   - `curl http://localhost:3000/health` returns `"service":"ui"`
   - `curl http://localhost:9000/health` returns `"service":"mcp"`

## Documentation

### What to Document

- **Code:** Only WHY, not WHAT. Use meaningful names instead of comments.
- **Features:** Update [specs/001-finance-dashboard-reuse/](specs/001-finance-dashboard-reuse/) if the feature has a spec.
- **APIs:** Document endpoint signatures in contracts (e.g., [contracts/kitchen-membership-api.md](specs/001-finance-dashboard-reuse/contracts/kitchen-membership-api.md)).
- **Operational:** Document deployment, monitoring, and troubleshooting in DEPLOYMENT.md or README.md.

### What NOT to Document

- Temporary debug code or work-in-progress notes (put them in `dev/` instead)
- Commit-specific details (those belong in commit messages)

## Common Issues and Troubleshooting

### Port Conflicts

If you get "Address already in use" when starting Compose:

```bash
# Check what's listening on port 3000, 8000, 9000
lsof -i :3000
lsof -i :8000
lsof -i :9000

# Kill the process or use a different port
API_HOST_PORT=8001 ./scripts/compose-up.sh -d
```

### SMTP Configuration for Dev

The bootstrap requires a real SMTP provider. Options:

1. **Gmail App Password** (recommended for testing)
   - Create an [App Password](https://myaccount.google.com/apppasswords)
   - Use in `.env`:
     ```
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USER=your-email@gmail.com
     SMTP_PASSWORD=your-app-password
     SMTP_FROM=Melos <noreply@your-domain.com>
     SMTP_STARTTLS=true
     ```

2. **MailHog** (for local testing, no real emails)
   - Already in `docker-compose.dev.yml` if configured
   - Visit http://localhost:1025 to see sent emails

### Alembic Migration Issues

If migrations fail:

```bash
# Check the current migration status
docker compose exec api uv run alembic current

# View migration history
docker compose exec api uv run alembic history

# If stuck, downgrade and re-upgrade
docker compose exec api uv run alembic downgrade -1
docker compose exec api uv run alembic upgrade head
```

### Database Connectivity

If the API container fails to start with "could not connect to database":

```bash
# Ensure the database container is healthy
docker compose ps

# Check database logs
docker compose logs db

# Verify the data directory is writable
ls -la "${MELOS_DATA:-$HOME/melos}/pgdata"
chmod 700 "${MELOS_DATA:-$HOME/melos}/pgdata"
```

## Governance

### When to Ask for Approval

- **Architecture changes:** Adding services, changing layer boundaries, or new dependencies
- **Security:** Anything involving secrets, authentication, or data access
- **Constitution violations:** If your change conflicts with any principle in `.specify/memory/constitution.md`
- **Breaking changes:** API changes, schema incompatibilities, or removal of features

### How to Ask

1. Open an issue or PR with a clear description of the change
2. Explain why you think it's necessary
3. Propose the solution and any trade-offs
4. Wait for explicit written approval before proceeding

## Resources

- **Specification:** [specs/001-finance-dashboard-reuse/spec.md](specs/001-finance-dashboard-reuse/spec.md)
- **Project Constitution:** [.specify/memory/constitution.md](.specify/memory/constitution.md)
- **Agent Instructions:** [AGENTS.md](AGENTS.md)
- **Error Handling:** [specs/001-finance-dashboard-reuse/contracts/error-responses.md](specs/001-finance-dashboard-reuse/contracts/error-responses.md)
- **API Contracts:** [specs/001-finance-dashboard-reuse/contracts/](specs/001-finance-dashboard-reuse/contracts/)

## Questions?

If something is unclear, ask! We'd rather clarify expectations upfront than debate them in code review.

Thank you for contributing to Melos! 🎉
