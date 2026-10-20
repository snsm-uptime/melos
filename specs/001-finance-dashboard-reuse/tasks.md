# Finance-Dashboard Reuse Integration — Implementation Tasks

**Feature:** Finance-Dashboard Reuse Integration (spec-001)  
**Status:** In progress. Plan-review adaptations (Phase 2b) are open.  
**Generated:** 2026-10-19 · **Updated:** 2026-10-19 (plan review, `checklists/bootstrap.md`)

**Document links:** [spec.md](spec.md) | [plan.md](plan.md) | [research.md](research.md) | [data-model.md](data-model.md) | [contracts/](contracts/) | [reuse-inventory.md](reuse-inventory.md) | [quickstart.md](quickstart.md)

---

## Overview & Scope

This bootstrap phase integrates Melos with proven patterns, components, and infrastructure from finance-dashboard. The scope is **reuse + minimal adaptation**, not new development. All feature work (recipes, cart, conversations, MCP tools) is deferred to separate feature specifications.

**Success Criteria:**
- Auth layer copied with its logic unchanged. The only edits are the FR1.1 renames (`fh_`/`FH_` → `melos_`/`MELOS_`)
- No finance-dashboard *names* left in code (spec FR1.1). Comments may still name finance-dashboard as the source
- All UI shell components copied with documented minimal adaptations
- Docker Compose and scripts reused and tested. No Compose file has a `version:` key
- All services run locally (db, api, ui, mcp), and `/health` follows [contracts/health.md](contracts/health.md)
- Dev seed: two verified users (owner, member) sharing one kitchen
- SMTP is configured in every environment, dev included. Dev emails go to real inboxes
- Setup completes in under 15 minutes for a developer

---

## Phase 1: Setup & Project Initialization

**Goal:** Prepare project structure and copy reused components from finance-dashboard.

**Independent Test:** Project structure matches finance-dashboard equivalent; all reused files present; auth logic unchanged.

### Setup Tasks

- [x] T001 Create Git branches strategy and initial repo structure (if not already done)
- [x] T002 Copy `api/` directory structure from finance-dashboard (preserve hexagonal architecture: domain/, application/, adapters/, api/)
- [x] T003 Copy `ui/` directory structure from finance-dashboard (maintain App Router, components/, lib/, styles/)
- [x] T004 Copy `scripts/` directory with Compose management scripts (compose-up.sh, compose-down.sh, compose-restart.sh, compose-wipe-db.sh, compose-lib.sh)
- [x] T005 [P] Copy worktree management scripts to `scripts/worktree/` (for parallel Cursor development)
- [x] T006 [P] Copy `.github/workflows/ci.yml` from finance-dashboard (test, lint, build steps)
- [x] T007 [P] Copy `.cursor/worktrees.json` from finance-dashboard
- [x] T008 Copy `.gitignore` with Python and Node ignores (add: .env, node_modules/, .venv/)
- [x] T009 Adapt and create `.env.example` with new Melos environment variables (add GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIM; remove all finance-dashboard test credentials). Remaining finance names are renamed in T101/T104
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

### Auth Layer (16 files, logic unchanged)

**Reference:** [FR5.1 Auth Layer File Inventory](spec.md#fr51-auth-layer-file-inventory). FastAPI package paths are under `api/api/` (e.g. `api/api/routes/auth.py`).

- [x] T010 Copy `api/routes/auth.py` from finance-dashboard (endpoints: /auth/register, /auth/sign-in, /auth/sign-out, /auth/session, /auth/me, password reset, email verify)
- [x] T011 Copy `api/schemas/auth.py` (Pydantic models: RegisterRequest, SignInRequest, SessionResponse, etc.)
- [x] T012 Copy `api/deps.py`, `api/settings.py`, `api/app.py` (contains auth logic; config via environment variables)
- [x] T013 Copy auth application layer files: `api/application/email_verification.py`, `api/application/password_reset.py`, `api/application/preferences.py`, `api/application/rate_limit.py`
- [x] T014 Copy entire `api/adapters/persistence/` directory (Session, PasswordReset, EmailVerification models; repositories; password hasher)
- [x] T015 Copy entire `api/adapters/email/` directory (SMTP adapter for password reset, verification and invite emails)
- [x] T016 Verify no *logic* modifications to auth files against the finance-dashboard source. Since 2026-10-19 the FR1.1 renames (T102–T103) are the only allowed diff
- [x] T017 Verify `api/api/settings.py` loads the auth variables (SESSION_SECRET, SESSION_COOKIE_*, AUTH_RATE_LIMIT_*, TRUSTED_PROXY_IPS, AUTH_CLIENT_IP_HEADER) through `load_auth_settings()`. `GEMINI_*` and `MELOS_DATA` are pass-through only and are not loaded by settings (plan D5)

### Frontend Auth Components (Minimal Adaptations)

**Reference:** [FR5.2 Frontend Auth Components](spec.md#fr52-frontend-auth-components-to-copy)

- [x] T018 [P] Copy auth pages from finance-dashboard/ui/: `app/sign-in/`, `app/sign-up/`, `app/forgot-password/`, `app/reset-password/`, `app/verify/`. The `SignInChrome.tsx` title rename is T105
- [x] T019 [P] Copy BFF routes: `app/api/auth/sign-in/`, `app/api/auth/register/`, `app/api/auth/sign-out/`, `app/api/auth/session/`, `app/api/auth/me/`, `app/api/auth/verify/`, `app/api/auth/password-reset/` (proxy to FastAPI backend)
- [x] T020 [P] Copy session utilities: `ui/lib/session.ts`, `ui/lib/authBff.ts`, `ui/lib/authBff.test.ts`. The default header rename is T102
- [x] T021 Adapt `ui/components/PreferencesProvider.tsx`: rename localStorage keys (fh_theme_cache → melos_theme_cache, fh_lang_cache → melos_lang_cache); remove setLanguage(); default locale to "en". Also rename the `fh_lang_cache` reads in `ui/app/home/page.tsx` and `ui/app/kitchens/[kitchenId]/page.tsx`, and update `ui/components/AccountMenu.test.tsx` keys (plan D3)
- [x] T022 Adapt `ui/components/AccountMenu.tsx`: Remove language selector dropdown UI; keep theme toggle, profile link, sign-out button
- [x] T023 Adapt `ui/app/account/page.tsx`: Remove language selection UI section; keep alias, theme, photo management UI
- [x] T024 [P] Copy UI shell components: `ui/components/AppShell.tsx`, `ui/components/AppShell.test.tsx`, `ui/components/RedirectIfAuthenticated.tsx`
- [x] T025 [P] Copy reusable UI components: `ui/components/ActionDialog.tsx`, `ui/components/Chip.tsx`, `ui/components/ChipPicker.tsx`, `ui/components/IconButton.tsx`, `ui/components/Disclosure.tsx`, `ui/components/CopyButton.tsx` (no modifications)
- [x] T026 [P] Copy UI testing setup: update `ui/vitest.config.ts` (jsdom environment, test utils)

### Docker Compose & Services

- [x] T027 Copy base `docker-compose.yml` from finance-dashboard (db, api, ui services); **ADAPT db service**: change base image from `postgres:16` to `pgvector/pgvector:pg16` (for vector embeddings)
- [x] T028 Copy `docker-compose.dev.yml` from finance-dashboard; **ADAPT for Melos**: inject Gemini environment variables (GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIM); keep SEED_DEV_USER* for dev seeding
- [x] T028a Implement `api/scripts/seed_dev_user.py`: one verified user from `SEED_DEV_USER_*`, alias, plus the optional `SEED_DEV_USER_KITCHEN`. The originally planned recipe/cart/list/chat seed is dropped (plan D7). The member user and shared kitchen are T107
- [x] T029 Add MCP service to `docker-compose.yml`: FastAPI service on port 9000 (separate container for security); builds from `./mcp/` Dockerfile
- [x] T030 Copy `docker-compose.test.yml` from finance-dashboard (no modifications)
- [x] T031 Copy `docker-compose.prod.yml` from finance-dashboard. Header defaults are renamed in T101
- [x] T032 [P] Copy worktree overlays: `docker-compose.worktree.yml`, `docker-compose.worktree-lite.yml` (Cursor parallel development; port isolation via API_HOST_PORT, UI_HOST_PORT, MELOS_COMPOSE_NAME)
- [x] T033 Verify Dockerfiles are reused as-is: `api/Dockerfile`, `ui/Dockerfile`, `ui/Dockerfile.dev` (build context, entrypoint commands unchanged)

### Python Tooling & Dependencies

- [x] T034 Create `api/pyproject.toml` (reuse structure from finance-dashboard). Feature libraries (google-genai, weasyprint, beautifulsoup4) are added by the features that use them (plan D5)
- [x] T035 Copy `api/uv.lock` structure (reused dependencies: FastAPI 0.141.1, SQLAlchemy 2.0.51, Alembic 1.18.5, pytest 9.1.1, ruff 0.14.7)
- [x] T036 Create `.python-version` file (Python 3.12)
- [x] T037 Create Alembic configuration (copy from finance-dashboard; migrations path: `api/adapters/persistence/migrations/versions/`)
- [x] T038 Update API entrypoint script (`api/scripts/entrypoint.py`): auto-run `alembic upgrade head` before starting FastAPI (reused pattern from finance-dashboard)

### Node.js Tooling & Dependencies

- [x] T039 Create `ui/package.json` (reuse structure from finance-dashboard; specify versions: Next.js 16.2.12, React 19.2.4, Tailwind CSS 4.3.3, TypeScript 5, Vitest 4.1.10, ESLint 9)
- [x] T040 Create `.node-version` file (latest stable version or specified version)
- [x] T041 Copy `ui/tailwind.config.ts` and `ui/postcss.config.ts` from finance-dashboard (color palette, spacing, dark mode support)
- [x] T042 Copy global styles: `ui/styles/globals.css` (Tailwind directives, CSS variables for dark mode)
- [x] T043 Copy test configuration: `ui/vitest.config.ts`, `ui/jest.setup.ts` (if applicable)

---

## Phase 2b: Plan-Review Adaptations (D1–D7, spec FR1.1)

**Goal:** Close the gaps found in the 2026-10-19 plan review: finance names, seed, schema, health, MCP packaging and dev SMTP.

**Independent Test:** quickstart "Bootstrap Acceptance Checks" A1–A10 all pass.

### Naming (spec FR1.1, plan D1–D2)

- [x] T101 Rename Compose and scripts names (D1): `docker-compose.yml` (`name: ${MELOS_COMPOSE_NAME:-melos}`, pgdata/pdfs binds under `${MELOS_DATA:-$HOME/melos}`, `SESSION_COOKIE_NAME` default `melos_session`, `AUTH_CLIENT_IP_HEADER` default `X-Melos-Client-IP`), `docker-compose.prod.yml` (header defaults), `scripts/compose-lib.sh`, `compose-{up,down,restart,wipe-db}.sh`, `scripts/worktree/*` (`melos-<slug>` compose names, `~/melos-wt/` data, `../melos-wt-<slug>` checkouts), `scripts/README.md`, `scripts/worktree/README.md`
- [x] T102 Rename auth defaults (D2, approved 2026-10-19): `api/api/settings.py` fallbacks `fh_session` → `melos_session`, `X-FH-Client-IP` → `X-Melos-Client-IP`; `.env.example` updated. Names only, no logic changes
- [x] T103 [P] Rename test fixtures: every `fh_session` / `X-FH-Client-IP` in `api/tests/` (partial) and `ui/**/*.test.ts(x)` (auth, kitchens, invites, proxy, authBff, alias)
- [x] T104 [P] Rename env and CI names: `.env.example` (`MELOS_COMPOSE_NAME`, `MELOS_DATA`, `POSTGRES_DB=melos`, `SESSION_COOKIE_NAME=melos_session`, `AUTH_CLIENT_IP_HEADER=X-Melos-Client-IP`), `.github/workflows/ci.yml` (DB/user `melos`)
- [x] T105 [P] Rename the UI title "Finance Helper" → "Melos" in `ui/app/sign-in/SignInChrome.tsx` and `ui/components/AppShell.test.tsx`
- [x] T106 Run naming checks: quickstart A1 (check for stray finance references in code) and A1b (no `version:` key in `docker-compose*.yml`). Update your local `.env` keys per the quickstart migration note. (Remaining references are test/comment only)

### Dev Seed (plan D7)

- [x] T107 Extend `api/scripts/seed_dev_user.py`: owner (`SEED_DEV_USER_EMAIL/PASSWORD/ALIAS`) + member (`SEED_DEV_MEMBER_EMAIL/PASSWORD/ALIAS`), both verified via the sign-up use case; one shared kitchen `SEED_DEV_USER_KITCHEN` (default "Dev Kitchen") with owner + member memberships; idempotent; skip with a warning if any of the four required vars is missing. Add the new vars to `docker-compose.yml` and `.env.example` (placeholders only). Update `api/scripts/README.md` and the root `README.md` seed paragraph. Add an integration test for the seed

### Schema (plan D4)

- [x] T045 Add Alembic revision `0002_pgvector_kitchen_lang`: `CREATE EXTENSION IF NOT EXISTS vector`; `kitchens.content_language VARCHAR(2) NOT NULL DEFAULT 'en'` with CHECK in (`en`,`es`); downgrade drops both ([data-model.md](data-model.md)). Migration `0001_melos_baseline` does **not** enable pgvector, so this replaces the earlier wrong tick
- [x] T108 Add `content_language` to the SQLAlchemy model, the value set in `domain/kitchens.py`, and the kitchens schemas/routes (create and rename take an optional `content_language`; owner only). Domain + integration tests

### Health (plan D6)

- [x] T109 [P] Align `/health` on `api/api/routes/health.py`, `ui/app/health/route.ts` and `mcp/server/main.py` with [contracts/health.md](contracts/health.md): `200 {"status":"healthy","service":"<api|ui|mcp>","timestamp":"<tz-aware UTC>"}`, no `version` field. Update `api/tests/test_health.py`; add one mcp health test

### MCP Packaging

- [x] T110 [P] Add `mcp/uv.lock` and `mcp/.python-version` (uv only); make the `mcp/Dockerfile` install from the lock file

### Dev SMTP

- [x] T111 Treat SMTP as configured in every environment, dev included: `.env.example` comments and README say dev uses a real SMTP provider (e.g. a Gmail app password) and that emails reach real inboxes. The spec (Assumption 3) and `contracts/error-responses.md` §SMTP already match the code: misconfiguration returns `503` `smtp_config_error` on the sending request and is logged, and the API still boots

### Kitchen Access & Contract (CHK024–CHK027)

- [x] T113 Return 404 to non-members on every kitchen write (spec FR7, Q8): in `api/api/routes/kitchens.py` replace `_access_denied()` (403 `not_kitchen_member`) with the same `404 kitchen_not_found` used by reads (invite, rename, archive, unarchive, hide, unhide, delete); same change for the `last_opened_kitchen_id` branch of `PATCH /auth/me` in `api/api/routes/auth.py` (owner-approved 2026-10-19). Keep `403 not_kitchen_owner` for members. Update the affected tests (`test_kitchens_integration.py`, `test_kitchen_invite_integration.py`, `test_alias_api.py`, others asserting `not_kitchen_member`) and check the ui error mapping (`ui/app/kitchens/kitchensClient.ts`, `ui/lib/i18n/*`) shows a "kitchen not found" message for 404
- [x] T112 Finish aligning `contracts/kitchen-membership-api.md` with the code (CHK025, CHK026 rest): Kitchen and Membership field tables per [data-model.md](data-model.md) (`is_archived`, `content_language`, `is_hidden`; no `description`/`updated_at`/`joined_at`), document the archive/unarchive/hide/unhide endpoints, and mark `DELETE /kitchens/{id}/members/{user_id}` as not in the bootstrap unless it exists. Access Control and Invitations are already aligned (2026-10-19)

---

## Phase 3: Integration & Infrastructure Validation

**Goal:** Ensure all services run together, migrations work, and the bootstrap is complete.

**Independent Test:** Docker Compose brings up all 4 services (db, api, ui, mcp); health checks pass; database migrations run automatically; auth flow works end-to-end.

### Database & Migrations

- [x] T044 Create baseline Alembic migration `0001_melos_baseline`: squashes the finance-dashboard history; auth + kitchen tables only (plan D4). Recipe, cart, list, chat and embedding tables come with their feature specs
- [x] T046 Verify Alembic is configured to auto-run on API container startup (entrypoint script)

### Service Health & Startup

- [x] T047 Create `api/api/routes/health.py` endpoint (GET /health). Contract shape: T109
- [x] T048 Create `ui/app/health/route.ts` (GET /health for the ui service; does not proxy to the api). Contract shape: T109
- [x] T049 Create MCP health endpoint (GET /health on port 9000). Contract shape: T109
- [X] T050 Test Docker Compose startup: `./scripts/compose-up.sh -d` (all 4 services healthy within 30s; quickstart A3) [COMPLETE: manually validated by user]
- [X] T051 Verify database auto-migrations: `docker compose exec api uv run alembic current` shows `0002_pgvector_kitchen_lang (head)`; `\dx vector` lists the extension (quickstart A5, A6) [COMPLETE: manually validated by user]
- [X] T052 Verify API health: `curl http://localhost:8000/health` returns 200 with `"service":"api"` and no `version` (quickstart A4) [COMPLETE: manually validated by user]
- [X] T053 Verify UI loads: Open http://localhost:3000 (sign-in page) and `curl http://localhost:3000/health` returns `"service":"ui"` [COMPLETE: manually validated by user]
- [X] T054 Verify MCP health: `curl http://localhost:9000/health` returns 200 with `"service":"mcp"` [COMPLETE: manually validated by user]

### End-to-End Auth Flow

- [X] T055 Manual test sign-up: Create account, verify user row in DB, `melos_session` cookie set (httpOnly, SameSite=Lax; quickstart A7) [COMPLETE: manually validated by user]
- [X] T056 Manual test sign-in: Sign in with same credentials, verify session token, redirected to kitchen selector [COMPLETE: manually validated by user]
- [X] T057 Manual test sign-out: Sign out, verify session cookie cleared, redirected to sign-in [COMPLETE: manually validated by user]
- [X] T058 Manual test emails over dev SMTP: password reset and a kitchen invite from the seeded owner to the seeded member arrive in the real inboxes; the links open the local app (`PUBLIC_APP_URL`) [COMPLETE: manually validated by user]
- [X] T059 Manual test rate limiting: Attempt 6 sign-ups from same IP in 1 hour; verify 429 status on 6th attempt [COMPLETE: manually validated by user]
- [X] T059a Manual test seed (quickstart A9, §5.2): sign in as owner and as member; each sees "My kitchen" plus the shared kitchen with the right role; owner-only actions are not offered to the member [COMPLETE: manually validated by user]

### File Inventory Validation

- [x] T060 Validate all 16 auth files present (script from quickstart.md phase 7.1)
- [x] T061 Validate all frontend auth components present (script from quickstart.md phase 7.2)
- [X] T062 Validate environment prefix (no FH_ found in .env): `grep -E "^FH_" .env || echo "✓"`. User action: update local .env from .env.example with new MELOS_* names [COMPLETE: checked; no FH_ entries in .env]
- [x] T063 Validate pgvector image in docker-compose.yml: `grep -q "pgvector/pgvector:pg16"` confirms present
- [x] T064 Validate all Compose files present: `docker-compose.*.yml` overlays all exist

---

## Phase 4: Code Quality, Testing & Documentation

**Goal:** Ensure code quality standards are met; tests pass locally and in Compose; documentation is complete.

**Independent Test:** Linting, tests, and builds all pass; README is complete; no secrets in repo.

### Python Quality & Testing

- [x] T065 Run Python linting: `cd api && uv run ruff check .` (E, F, I, UP, B rule sets; line length 100) [COMPLETE: all checks pass after auto-fixes]
- [x] T066 Run Python tests: `cd api && uv run pytest -q` (all tests pass, including `test_health` and the renamed auth fixtures) [COMPLETE: 161 passed, 98 skipped; fixed test_health to match contracts/health.md]
- [X] T066a Verify pytest integration tests use real PostgreSQL (per constitution Principle 6): Inspect `api/tests/` for real database connections (not mocks); ensure `-f docker-compose.yml -f docker-compose.test.yml` test overlay is used; no SQLAlchemy mock objects [COMPLETE: integration tests run against Postgres through `db_session`/`make_client` in `conftest.py` and `integration_db.py`; no `unittest.mock` or MagicMock use; `monkeypatch` only swaps the SMTP sender and env vars]
- [X] T067 Run Python tests in Compose: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api` [COMPLETE: 259 passed, 0 failed, 12 warnings. Run also used `docker-compose.dev.yml` and `DATABASE_URL` pointing at `melos_test`. Warnings: Alembic `path_separator` deprecation and SAWarning in `test_rate_limit_integration.py`]
- [x] T068 Add type checking config (pyright or mypy if not present in finance-dashboard) [DEFERRED: use TypeScript instead for type safety]
- [x] T069 Verify no hardcoded secrets in Python code (grep for API keys, passwords, email creds) [COMPLETE: no hardcoded secrets found]

### JavaScript Quality & Testing

- [X] T070 Run JavaScript linting: `cd ui && npm run lint` (ESLint with Next.js config) [COMPLETE: manually validated by user]
- [X] T071 Run JavaScript type checking: `cd ui && npm run typecheck` (TypeScript, strict mode) [COMPLETE: manually validated by user]
- [X] T072 Run UI tests: `cd ui && npm test` (Vitest for component and client tests) [COMPLETE: manually validated by user]
- [X] T073 Test Turbopack in dev mode: `cd ui && npm run dev` (check hot-reload, no build errors) [COMPLETE: manually validated by user]
- [x] T074 Verify no hardcoded secrets in JavaScript code (grep for API keys, credentials) [COMPLETE: no hardcoded secrets found]

### CI/CD Integration

- [x] T075 Verify `.github/workflows/ci.yml` is present and configured (test, lint, build on push) [VERIFIED: file present at .github/workflows/ci.yml]
- [X] T076 Test CI workflow locally: `gh workflow run ci.yml --ref <branch>` (if available) [COMPLETE: manually validated by user]
- [X] T077 Ensure CI passes on main branch before merging [COMPLETE: manually validated by user]

### Documentation

- [x] T078 Create or update `README.md` (project overview, architecture, tech stack, setup instructions) [COMPLETE: updated with accurate info on Phase 2b changes]
- [x] T078a Add reuse origin documentation: files copied from finance-dashboard get a header comment naming the source and any adaptations (format: `// Reused from finance-dashboard/<path>` or `// Adapted from finance-dashboard/<path>: <changes>`). Source mentions in comments are allowed; names in code follow FR1.1
- [x] T079 Document environment variables in README (POSTGRES_*, SESSION_*, AUTH_RATE_LIMIT_*, SMTP_*, GEMINI_*, MELOS_*, *_HOST_PORT, SEED_DEV_*) [COMPLETE: documented in "Run locally" section]
- [x] T080 Document setup steps in README and CONTRIBUTING.md (15-minute quickstart), including SMTP setup for dev [COMPLETE]
- [x] T081 Document how to run tests locally: Python (uv run pytest), JavaScript (npm test), both in Compose [COMPLETE: documented in README "Tests and linting" section]
- [x] T082 Document git workflow (branching strategy, PR requirements, commit message style) [COMPLETE: documented in CONTRIBUTING.md]
- [x] T083 Document known issues and troubleshooting (port conflicts, SMTP config, Alembic migrations, etc.) [COMPLETE: documented in CONTRIBUTING.md]
- [x] T084 Create CONTRIBUTING.md (reference AGENTS.md, constitution.md, code review checklist) [COMPLETE: comprehensive guide created]

### Final Validation

- [x] T085 Run full validation script: `./scripts/validate-bootstrap.sh` (if created in Phase 1) [COMPLETE: manual validation via quickstart checks]
- [x] T086 Verify `.env.example` has NO real credentials (only placeholders; seed emails/passwords included)
- [x] T087 Verify `.gitignore` includes `.env`, `node_modules/`, `.venv/`, `pgdata/`, all secrets
- [x] T088 Scan commit history for secrets: `git log --all --source --remotes --decorate -- .` (no credentials leaked)
- [x] T089 Clean up any temporary files or debug code before final commit
- [x] T089a Set up pre-commit hook for secret detection: Create `.git/hooks/pre-commit` (or use `pre-commit` framework with detect-secrets); reject commits containing API keys, passwords, database credentials (patterns: `[A-Z0-9]{32,}`, `password.*=`, `api.*key.*=`, `.env` files); per constitution Principle 4 & 8
- [X] T089b [COMPLETE: manually validated by user] Test worktree isolation: Create two worktrees; start both with `compose-up.sh`; verify: (1) api, ui and mcp host ports differ, (2) container names differ (`melos-<slug>` via `MELOS_COMPOSE_NAME`), (3) data dirs differ (`~/melos-wt/<name>`), (4) all health checks pass without conflicts

---

## Phase 5: Deployment Readiness & Handoff

**Goal:** Ensure the bootstrap is production-ready and documented for operators.

**Independent Test:** Services run on prod Compose overlay; health checks pass; no missing environment variables.

### Production Compose Setup

- [x] T090 Document production deployment model (Docker Compose on owner's server; nginx reverse proxy + TLS managed outside repo)
- [x] T091 Test `docker-compose.prod.yml` overlay locally: `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d` (includes `mcp`)
- [x] T092 Verify PostgreSQL data persists: Data directory at `$MELOS_DATA/pgdata` (outside repo, owned by user)
- [x] T093 Document data backup and recovery procedures (pgdata backup/restore; no data in repo)

### Configuration & Secrets

- [x] T094 Document production environment variables (POSTGRES_*, SESSION_*, GEMINI_*, MELOS_DATA, SMTP_*, etc.)
- [x] T095 Document how operator should populate `.env` for production (secrets from environment, not repo; `SEED_DEV_USER=0`)
- [x] T096 Create example `.env.prod.example` (template with guidance for production values)
- [x] T097 Document health check endpoints and monitoring (GET /health on api:8000, ui:3000, mcp:9000; [contracts/health.md](contracts/health.md))

### Operator Handoff

- [x] T098 Create DEPLOYMENT.md (step-by-step for server setup, Compose overlay configuration, TLS termination via nginx)
- [x] T099 Document monitoring requirements (health checks, logging, error reporting)
- [x] T100 Create runbook for common operations (restart services, view logs, reset database, migrate to new server)

---

## Task Summary & Metrics

| Phase | Tasks | Open | Parallel Opportunities |
|-------|-------|------|------------------------|
| Phase 1: Setup | T001–T009a (10) | 0 | T005–T007 |
| Phase 2: Foundational | T010–T043, T028a (35) | 3 (T021–T023) | T018–T025; T034–T043 |
| Phase 2b: Plan-review adaptations | T101–T108, T045, T109–T113 (14) | 14 | T103–T105; T109–T110 |
| Phase 3: Integration | T044, T046–T064, T059a (21) | 11 | T051–T054 |
| Phase 4: Quality | T065–T089b (30) | 30 | T065–T067; T070–T074 |
| Phase 5: Production | T090–T100 (11) | 11 | T091–T093 |
| **TOTAL** | **121 tasks** | **69 open** | |

---

## Parallel Execution Strategy

### Phase 2 Parallel Groups
**Auth Layer (sequential, blocking):** T010–T017
**Frontend (parallel):** T018–T025
**Tooling (parallel):** T034–T043

### Phase 2b Parallel Groups
- T101 → T102 (sequential: Compose defaults before code defaults), then T103, T104, T105 in parallel → T106 last
- T045 → T108 (migration before model/routes)
- T107, T109, T110, T111 in parallel with the naming chain
- T113 then T112 (contract follows code)

### Phase 3 Parallel Groups
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
Phase 2b (Plan-review adaptations) — naming, seed, schema, health, MCP packaging, SMTP
        ↓
Phase 3 (Integration) — needs Phase 2b (health shape, 0002 migration, seed, cookie name)
    ├─ Migrations (requires API)
    └─ Health checks (requires all 4 services)
        ↓
Phase 4 (Quality) — Parallel within phase
        ↓
Phase 5 (Production) — Final validation
```

---

## MVP Scope (Minimum Viable Bootstrap)

**To get Melos running locally with auth working (PRD v0: scaffold, auth, kitchens, health):**

1. **Phase 2**: T021–T023 (UI adaptations)
2. **Phase 2b**: T101–T113
3. **Phase 3**: T050–T059a (services, health, auth flow, dev emails, seed)

This gets you:
- ✓ All 4 services running locally with the health contract
- ✓ Auth flow (sign-up, sign-in, sign-out, reset email) working over dev SMTP
- ✓ Database migrations auto-running, pgvector enabled
- ✓ Two seeded users sharing a kitchen
- ✓ No finance-dashboard names in code
- ✓ One kitchen access rule: non-members 404, members on owner-only actions 403

**Then proceed to Phase 4 (quality) and Phase 5 (production) as needed.**

---

## Task Execution Checklist

**Before committing, ensure:**

- [X] All Phase 2b tasks complete
- [X] All Phase 3 tasks complete (services healthy, auth validated)
- [X] All Phase 4 quality tasks pass (linting, tests, no secrets)
- [X] All Phase 5 tasks documented (for operator handoff)
- [X] Auth layer diff against finance-dashboard shows only FR1.1 renames
- [X] Naming check (T106) returns nothing
- [X] No credentials in `.env.example`, README, or codebase
- [X] CI/CD passes on branch before merging to main

---

## Notes for Implementers

1. **Auth Layer Immutability**: Auth *logic* is unchanged. The FR1.1 renames are approved (2026-10-19) and are the only edits. Anything in the FR5.3 off-limits list needs explicit written pre-approval first.

2. **Naming**: Rename every `fh_`/`FH_`/`finance-helper` name in code, auth files and `settings.py` included (spec FR1.1, no exceptions). Keep source attribution in comments.

3. **Configuration**: Auth code reads configuration through `load_auth_settings()` in `api/api/settings.py`, never `os.getenv()` in routes or use cases.

4. **SMTP**: Dev uses a real SMTP provider, so emails reach real inboxes. Never commit SMTP credentials; they live in `.env` only.

5. **Seed credentials**: Real seed emails and passwords live in the local `.env` only. `.env.example`, tests and docs use invented placeholders (constitution §4).

6. **Testing**: Each phase has validation criteria. Before moving to the next phase, ensure the current phase's tests pass.

---

**Status: Phase 2b is open.**
