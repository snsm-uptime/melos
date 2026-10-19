# Finance-Dashboard Reuse Integration — Implementation Tasks

**Feature:** Finance-Dashboard Reuse Integration (spec-001)  
**Status:** Ready for implementation  
**Generated:** 2026-10-19  

**Document links:** [spec.md](spec.md) | [research.md](research.md) | [reuse-inventory.md](reuse-inventory.md) | [quickstart.md](quickstart.md)

---

## Overview & Scope

This bootstrap phase integrates Melos with proven patterns, components, and infrastructure from finance-dashboard. The scope is **reuse + minimal adaptation**, not new development. All feature work (recipes, cart, conversations, MCP) is deferred to separate feature specifications.

**Success Criteria:**
- All auth layer files copied without modification
- All UI shell components copied with documented minimal adaptations
- Docker Compose and scripts reused and tested
- All services run locally (db, api, ui, mcp)
- Health checks pass; auth flow validates end-to-end
- Setup completes in under 15 minutes for a developer

---

## Phase 1: Setup & Project Initialization

**Goal:** Prepare project structure and copy reused components from finance-dashboard.

**Independent Test:** Project structure matches finance-dashboard equivalent; all reused files present; no modifications to auth layer.

### Setup Tasks

- [x] T001 Create Git branches strategy and initial repo structure (if not already done)
- [x] T002 Copy `api/` directory structure from finance-dashboard (preserve hexagonal architecture: domain/, application/, adapters/, api/)
- [x] T003 Copy `ui/` directory structure from finance-dashboard (maintain App Router, components/, lib/, styles/)
- [x] T004 Copy `scripts/` directory with Compose management scripts (compose-up.sh, compose-down.sh, compose-restart.sh, compose-wipe-db.sh, compose-lib.sh)
- [x] T005 [P] Copy worktree management scripts to `scripts/worktree/` (for parallel Cursor development)
- [x] T006 [P] Copy `.github/workflows/ci.yml` from finance-dashboard (test, lint, build steps)
- [x] T007 [P] Copy `.cursor/worktrees.json` from finance-dashboard
- [x] T008 Copy `.gitignore` with Python and Node ignores (add: .env, node_modules/, .venv/)
- [x] T009 Adapt and create `.env.example` with new Melos environment variables (MELOS_* prefix; add GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIM; remove all finance-dashboard test credentials)
- [x] T009a Create data directory structure: `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata" && chmod 700 "${MELOS_DATA:-$HOME/melos}"`; verify Docker Compose can read/write

**Validation:**
```bash
./scripts/validate-bootstrap.sh  # From quickstart.md
```

---

## Phase 2: Foundational Components (Auth Layer, UI Shell, Compose)

**Goal:** Set up authentication, UI shell, and Docker Compose infrastructure.

**Blocker for all features:** Auth layer must be stable and tested before feature work begins.

**Independent Test:** Sign-up → sign-in → sign-out flow works end-to-end; all services healthy; migrations auto-run.

### Auth Layer (16 files, no customization)

**Reference:** [FR5.1 Auth Layer File Inventory](spec.md#fr51-auth-layer-file-inventory)

- [x] T010 Copy `api/routes/auth.py` as-is from finance-dashboard (endpoints: /auth/register, /auth/sign-in, /auth/sign-out, /auth/session, /auth/me, password reset, email verify)
- [x] T011 Copy `api/schemas/auth.py` as-is (Pydantic models: RegisterRequest, SignInRequest, SessionResponse, etc.)
- [x] T012 Copy `api/deps.py`, `api/settings.py`, `api/app.py` as-is (contains auth logic; config via environment variables)
- [x] T013 Copy auth application layer files as-is: `api/application/email_verification.py`, `api/application/password_reset.py`, `api/application/preferences.py`, `api/application/rate_limit.py`
- [x] T014 Copy entire `api/adapters/persistence/` directory as-is (Session, PasswordReset, EmailVerification models; repositories; password hasher)
- [x] T015 Copy entire `api/adapters/email/` directory as-is (SMTP adapter for password reset and verification emails)
- [x] T016 Verify NO modifications to any auth files (use `git diff` to confirm against finance-dashboard source)
- [x] T017 Verify `api/settings.py` loads all required environment variables (copied as-is from finance-dashboard): Confirm Settings class uses `os.getenv()` to load SESSION_SECRET, SESSION_COOKIE_*, AUTH_RATE_LIMIT_*, TRUSTED_PROXY_IPS, AUTH_CLIENT_IP_HEADER, GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIM; do NOT modify settings.py core auth logic

### Frontend Auth Components (Minimal Adaptations)

**Reference:** [FR5.2 Frontend Auth Components](spec.md#fr52-frontend-auth-components-to-copy)

- [x] T018 [P] Copy auth pages from finance-dashboard/ui/: `app/sign-in/`, `app/sign-up/`, `app/forgot-password/`, `app/reset-password/`, `app/verify/` (no modifications)
- [x] T019 [P] Copy BFF routes: `app/api/auth/sign-in/`, `app/api/auth/register/`, `app/api/auth/sign-out/`, `app/api/auth/session/`, `app/api/auth/me/`, `app/api/auth/verify/`, `app/api/auth/password-reset/` (proxy to FastAPI backend)
- [x] T020 [P] Copy session utilities: `ui/lib/session.ts`, `ui/lib/authBff.ts`, `ui/lib/authBff.test.ts` (no modifications)
- [ ] T021 Copy and adapt `ui/components/PreferencesProvider.tsx`: Rename localStorage keys (fh_theme_cache → melos_theme_cache, fh_lang_cache → melos_lang_cache); remove setLanguage() function; default locale to "en" (English-only)
- [ ] T022 Copy and adapt `ui/components/AccountMenu.tsx`: Remove language selector dropdown UI; keep theme toggle, profile link, sign-out button
- [ ] T023 Copy and adapt `ui/app/account/page.tsx`: Remove language selection UI section; keep alias, theme, photo management UI
- [x] T024 [P] Copy UI shell components: `ui/components/AppShell.tsx`, `ui/components/AppShell.test.tsx`, `ui/components/RedirectIfAuthenticated.tsx` (no modifications)
- [x] T025 [P] Copy reusable UI components: `ui/components/ActionDialog.tsx`, `ui/components/Chip.tsx`, `ui/components/ChipPicker.tsx`, `ui/components/IconButton.tsx`, `ui/components/Disclosure.tsx`, `ui/components/CopyButton.tsx` (no modifications)
- [x] T026 [P] Copy UI testing setup: update `ui/vitest.config.ts` (jsdom environment, test utils)

### Docker Compose & Services

- [x] T027 Copy base `docker-compose.yml` from finance-dashboard (db, api, ui services); **ADAPT db service**: change base image from `postgres:16` to `pgvector/pgvector:pg16` (for vector embeddings)
- [x] T028 Copy `docker-compose.dev.yml` from finance-dashboard; **ADAPT for Melos**: inject Gemini environment variables (GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIM); keep SEED_DEV_USER, SEED_DEV_USER_EMAIL, etc. for dev seeding
- [x] T028a Implement `api/scripts/seed_dev_user.py`: When `SEED_DEV_USER=1`, create test user (email, password, alias from `SEED_DEV_USER_*` env vars), sample kitchen (`SEED_DEV_USER_KITCHEN` env var), 3–5 recipes with ingredients, pre-populated cart (2 recipes, 1 meal each, 2 people), archived shopping list, 4–6 conversation messages per spec.md Development Seeding section
- [x] T029 Add MCP service to `docker-compose.yml`: FastAPI service on port 9000 (separate container for security); builds from `./mcp/` Dockerfile
- [x] T030 Copy `docker-compose.test.yml` from finance-dashboard (no modifications)
- [x] T031 Copy `docker-compose.prod.yml` from finance-dashboard (no modifications)
- [x] T032 [P] Copy worktree overlays: `docker-compose.worktree.yml`, `docker-compose.worktree-lite.yml` (Cursor parallel development; port isolation via API_HOST_PORT, UI_HOST_PORT, MELOS_COMPOSE_NAME)
- [x] T033 Verify Dockerfiles are reused as-is: `api/Dockerfile`, `ui/Dockerfile`, `ui/Dockerfile.dev` (build context, entrypoint commands unchanged)

### Python Tooling & Dependencies

- [x] T034 Create `api/pyproject.toml` (reuse structure from finance-dashboard; add new dependencies: google-genai, httpx, beautifulsoup4, weasyprint, psycopg[binary])
- [x] T035 Copy `api/uv.lock` structure (reused dependencies: FastAPI 0.141.1, SQLAlchemy 2.0.51, Alembic 1.18.5, pytest 9.1.1, ruff 0.14.7)
- [x] T036 Create `.python-version` file (Python 3.12)
- [x] T037 Create `api/Alembic` configuration (copy from finance-dashboard; migrations path: `api/alembic/versions/`)
- [x] T038 Update API entrypoint script (Dockerfile CMD or entrypoint.sh): auto-run `alembic upgrade head` before starting FastAPI (reused pattern from finance-dashboard)

### Node.js Tooling & Dependencies

- [x] T039 Create `ui/package.json` (reuse structure from finance-dashboard; specify versions: Next.js 16.2.12, React 19.2.4, Tailwind CSS 4.3.3, TypeScript 5, Vitest 4.1.10, ESLint 9)
- [x] T040 Create `.node-version` file (latest stable version or specified version)
- [x] T041 Copy `ui/tailwind.config.ts` and `ui/postcss.config.ts` from finance-dashboard (color palette, spacing, dark mode support)
- [x] T042 Copy global styles: `ui/styles/globals.css` (Tailwind directives, CSS variables for dark mode)
- [x] T043 Copy test configuration: `ui/vitest.config.ts`, `ui/jest.setup.ts` (if applicable)

---

## Phase 3: Integration & Infrastructure Validation

**Goal:** Ensure all services run together, migrations work, and the bootstrap is complete.

**Independent Test:** Docker Compose brings up all 4 services (db, api, ui, mcp); health checks pass; database migrations run automatically; auth flow works end-to-end.

### Database & Migrations

- [x] T044 Create initial Alembic migration: `api/alembic/versions/001_initial_schema.py` with all 21 tables per spec.md Key Entities (reused: user, session, password_reset_token, email_verification, preferences, kitchen, membership, invite; new: ingredient, category, recipe, recipe_ingredient, step, cart, cart_item, shopping_list, shopping_list_item, conversation, message, recipe_embedding, source); include all field definitions, constraints, and indices per spec.md Implementation Boundaries (line 413–453)
- [x] T045 Add pgvector migration extension to initial migration (IF NOT EXISTS pgvector; CREATE EXTENSION pgvector;)
- [x] T046 Verify Alembic is configured to auto-run on API container startup (entrypoint script)

### Service Health & Startup

- [x] T047 Create `api/routes/health.py` endpoint (GET /health returns 200 with status, timestamp, version)
- [x] T048 Create `ui/app/health/route.ts` health proxy (optional; for UI health check)
- [x] T049 Create MCP health endpoint (GET /health on port 9000)
- [ ] T050 Test Docker Compose startup: `./scripts/compose-up.sh -d` (all 4 services should be healthy within 30s)
- [ ] T051 Verify database auto-migrations: `docker compose exec api alembic current` should show head migration applied
- [ ] T052 Verify API health: `curl http://localhost:8000/health` returns 200
- [ ] T053 Verify UI loads: Open http://localhost:3000 in browser; should show sign-in page
- [ ] T054 Verify MCP health: `curl http://localhost:9000/health` returns 200

### End-to-End Auth Flow

- [ ] T055 Manual test sign-up: Create account, verify user row in DB, session cookie set
- [ ] T056 Manual test sign-in: Sign in with same credentials, verify session token, redirected to kitchen selector
- [ ] T057 Manual test sign-out: Sign out, verify session cookie cleared, redirected to sign-in
- [ ] T058 Manual test password reset request: Trigger password reset email (SMTP must be configured)
- [ ] T059 Manual test rate limiting: Attempt 6 sign-ups from same IP in 1 hour; verify 429 status on 6th attempt

### File Inventory Validation

- [x] T060 Validate all 16 auth files present (script from quickstart.md phase 7.1)
- [x] T061 Validate all frontend auth components present (script from quickstart.md phase 7.2)
- [x] T062 Validate environment prefix (no FH_ found in .env): `grep -E "^FH_" .env || echo "✓"`
- [x] T063 Validate pgvector image in docker-compose.yml: `grep -q "pgvector/pgvector:pg16"` confirms present
- [x] T064 Validate all Compose files present: `docker-compose.*.yml` overlays all exist

---

## Phase 4: Code Quality, Testing & Documentation

**Goal:** Ensure code quality standards are met; tests pass locally and in Compose; documentation is complete.

**Independent Test:** Linting, tests, and builds all pass; README is complete; no secrets in repo.

### Python Quality & Testing

- [ ] T065 Run Python linting: `cd api && uv run ruff check .` (E, F, I, UP, B rule sets; line length 100)
- [ ] T066 Run Python tests: `cd api && uv run pytest -q` (all tests pass; auth layer tests validate without modification)
- [ ] T066a Verify pytest integration tests use real PostgreSQL (per constitution Principle 6): Inspect `api/tests/` for real database connections (not mocks); ensure `-f docker-compose.yml -f docker-compose.test.yml` test overlay is used; no SQLAlchemy mock objects
- [ ] T067 Run Python tests in Compose: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`
- [ ] T068 Add type checking config (pyright or mypy if not present in finance-dashboard)
- [ ] T069 Verify no hardcoded secrets in Python code (grep for API keys, passwords, email creds)

### JavaScript Quality & Testing

- [ ] T070 Run JavaScript linting: `cd ui && npm run lint` (ESLint with Next.js config)
- [ ] T071 Run JavaScript type checking: `cd ui && npm run typecheck` (TypeScript, strict mode)
- [ ] T072 Run UI tests: `cd ui && npm test` (Vitest for component and client tests)
- [ ] T073 Test Turbopack in dev mode: `cd ui && npm run dev` (check hot-reload, no build errors)
- [ ] T074 Verify no hardcoded secrets in JavaScript code (grep for API keys, credentials)

### CI/CD Integration

- [ ] T075 Verify `.github/workflows/ci.yml` is present and configured (test, lint, build on push)
- [ ] T076 Test CI workflow locally: `gh workflow run ci.yml --ref spec-kit-per-story` (if available)
- [ ] T077 Ensure CI passes on main branch before merging

### Documentation

- [ ] T078 Create or update `README.md` (project overview, architecture, tech stack, setup instructions)
- [ ] T078a Add reuse origin documentation: All files copied from finance-dashboard must have header comment indicating source and any adaptations (format: `// Reused from finance-dashboard/<path>` or `// Adapted from finance-dashboard/<path>: <changes>`)
- [ ] T079 Document environment variables in README (POSTGRES_*, SESSION_*, AUTH_RATE_LIMIT_*, SMTP_*, GEMINI_*, MELOS_DATA)
- [ ] T080 Document setup steps in README (15-minute quickstart from quickstart.md)
- [ ] T081 Document how to run tests locally: Python (uv run pytest), JavaScript (npm test), both in Compose
- [ ] T082 Document git workflow (branching strategy, PR requirements, commit message style)
- [ ] T083 Document known issues and troubleshooting (port conflicts, SMTP config, Alembic migrations, etc.)
- [ ] T084 Create CONTRIBUTING.md (reference AGENTS.md, constitution.md, code review checklist)

### Final Validation

- [ ] T085 Run full validation script: `./scripts/validate-bootstrap.sh` (if created in Phase 1)
- [ ] T086 Verify `.env.example` has NO real credentials (only placeholders)
- [ ] T087 Verify `.gitignore` includes `.env`, `node_modules/`, `.venv/`, `pgdata/`, all secrets
- [ ] T088 Scan commit history for secrets: `git log --all --source --remotes --decorate -- .` (no credentials leaked)
- [ ] T089 Clean up any temporary files or debug code before final commit
- [ ] T089a Set up pre-commit hook for secret detection: Create `.git/hooks/pre-commit` (or use `pre-commit` framework with detect-secrets); reject commits containing API keys, passwords, database credentials (patterns: `[A-Z0-9]{32,}`, `password.*=`, `api.*key.*=`, `.env` files); per constitution Principle 4 & 8
- [ ] T089b Test worktree isolation: Create two worktrees; start both with `compose-up.sh`; verify: (1) port bindings differ (e.g., api:8001, api:8002), (2) container names differ (via `MELOS_COMPOSE_NAME`), (3) both health checks pass without conflicts

---

## Phase 5: Deployment Readiness & Handoff

**Goal:** Ensure the bootstrap is production-ready and documented for operators.

**Independent Test:** Services run on prod Compose overlay; health checks pass; no missing environment variables.

### Production Compose Setup

- [ ] T090 Document production deployment model (Docker Compose on owner's server; nginx reverse proxy + TLS managed outside repo)
- [ ] T091 Test `docker-compose.prod.yml` overlay locally: `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d`
- [ ] T092 Verify PostgreSQL data persists: Data directory at `$MELOS_DATA/pgdata` (outside repo, owned by user)
- [ ] T093 Document data backup and recovery procedures (pgdata backup/restore; no data in repo)

### Configuration & Secrets

- [ ] T094 Document production environment variables (POSTGRES_*, SESSION_*, GEMINI_*, MELOS_DATA, SMTP_*, etc.)
- [ ] T095 Document how operator should populate `.env` for production (secrets from environment, not repo)
- [ ] T096 Create example `.env.prod.example` (template with guidance for production values)
- [ ] T097 Document health check endpoints and monitoring (GET /health on api:8000, ui:3000, mcp:9000)

### Operator Handoff

- [ ] T098 Create DEPLOYMENT.md (step-by-step for server setup, Compose overlay configuration, TLS termination via nginx)
- [ ] T099 Document monitoring requirements (health checks, logging, error reporting)
- [ ] T100 Create runbook for common operations (restart services, view logs, reset database, migrate to new server)

---

## Task Summary & Metrics

| Phase | Task Count | Parallel Opportunities | Duration Estimate |
|-------|-----------|------------------------|-------------------|
| Phase 1: Setup | T001–T009a (10 tasks) | T005–T007 (3 parallel copy tasks) | 15–25 min |
| Phase 2: Foundational | T010–T043, T028a (35 tasks) | T018–T025 (8 parallel UI tasks); T034–T043 (10 parallel tool tasks) | 70–100 min |
| Phase 3: Integration | T044–T064 (21 tasks) | T047–T049 (3 parallel health endpoints); T051–T054 (4 parallel verification tests) | 30–45 min |
| Phase 4: Quality | T065–T089b (30 tasks) | T065–T067a (4 parallel Python quality); T070–T074 (5 parallel JavaScript quality); T089a–T089b (2 parallel final validation) | 60–75 min |
| Phase 5: Production | T090–T100 (11 tasks) | T091–T093 (3 parallel prod testing) | 30–45 min |
| **TOTAL** | **107 tasks** | **35+ parallelizable** | **205–290 min (3.5–4.8 hours)** |

---

## Parallel Execution Strategy

**For maximum throughput, execute these task groups in parallel within each phase:**

### Phase 1 Parallel Group
- T005, T006, T007 (copy scripts, CI/CD, cursor config in parallel)

### Phase 2 Parallel Groups
**Auth Layer (sequential, blocking):** T010–T017
**Frontend (parallel):** T018–T025 (8 auth component copy/adapt tasks)
**Tooling (parallel):** T034–T043 (Python and Node setup in parallel)

### Phase 3 Parallel Groups
- T047, T048, T049 (health endpoints)
- T051, T052, T053, T054 (service verification)

### Phase 4 Parallel Groups
- T065, T066, T067 (Python quality)
- T070, T071, T072, T073 (JavaScript quality)

### Phase 5 Parallel Groups
- T091, T092, T093 (prod Compose testing)

---

## Dependencies & Completion Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) — Auth MUST complete before Phase 3
    ├─ Auth Layer (blocking)
    └─ UI + Tooling (can parallelize)
        ↓
Phase 3 (Integration) — Cannot start until Phase 2 complete
    ├─ Migrations (requires API)
    └─ Health checks (requires all 4 services)
        ↓
Phase 4 (Quality) — Parallel within phase
    └─ Linting + Testing (can parallelize by language)
        ↓
Phase 5 (Production) — Final validation
    └─ Deploy readiness (requires Phase 4 pass)
```

---

## MVP Scope (Minimum Viable Bootstrap)

**To get Melos running locally with auth working:**

1. **Phase 1**: T001–T009 (Setup & env)
2. **Phase 2**: T010–T026 (Auth + UI components + Compose base)
3. **Phase 3**: T044–T059 (DB migrations + service health + auth flow)

**Estimated time: 90–120 minutes**

This gets you:
- ✓ All 4 services running locally
- ✓ Auth flow (sign-up, sign-in, sign-out) working
- ✓ Database migrations auto-running
- ✓ UI shell ready for feature work

**Then proceed to Phase 4 (quality) and Phase 5 (production) as needed.**

---

## Task Execution Checklist

**Before committing, ensure:**

- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 blocking tasks (T010–T017) complete before starting Phase 3
- [ ] All Phase 3 tasks complete (services healthy, auth validated)
- [ ] All Phase 4 quality tasks pass (linting, tests, no secrets)
- [ ] All Phase 5 tasks documented (for operator handoff)
- [ ] No modifications to auth layer files (compare with finance-dashboard source)
- [ ] No credentials in `.env.example`, README, or codebase
- [ ] CI/CD passes on branch before merging to main

---

## Notes for Implementers

1. **Auth Layer Immutability**: Tasks T010–T015 copy auth as-is. If you need to modify auth, get explicit written pre-approval first (see FR5.3 in spec.md).

2. **Environment Variables**: Task T017 is critical—it centralizes all environment loading in `settings.py`. Do NOT manually rename `FH_` → `MELOS_` in individual auth files.

3. **Parallelization**: Use branches and worktrees to parallelize work. For example, one developer does Phase 1 while another prepares Phase 2 tasks.

4. **Testing**: Each phase has validation criteria. Before moving to the next phase, ensure the current phase's tests pass.

5. **Documentation**: Keep README, CONTRIBUTING.md, and deployment docs in sync as you complete tasks.

---

**Status: Ready for implementation. All 100 tasks are independent, testable, and organized by dependency.**

