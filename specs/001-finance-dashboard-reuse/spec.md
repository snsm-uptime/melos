# Finance-Dashboard Reuse Integration

## Overview

Establish a clear, reusable integration with the finance-dashboard codebase to accelerate Melos development by leveraging proven architecture, infrastructure patterns, and shared components. This specification defines what will be reused as-is, what will be adapted, and what will remain independent.

## User Scenarios & Flows

**Scenario 1: Developer Setting Up Melos for the First Time**

As a developer, I want to understand what parts of the codebase I can use without modification from finance-dashboard, so that I don't waste time reimplementing proven solutions.

- Recognize which folders, patterns and configurations come from finance-dashboard
- Understand which parts are identical and which need customization
- Know which new code needs to be written specific to Melos
- Quickly bootstrap the codebase with confidence

**Scenario 2: Implementing a New Feature**

As a developer building a Melos feature, I want to follow established architectural patterns so that my code is consistent with the rest of the codebase.

- Reuse existing patterns for authentication, API structure, UI shell and testing
- Adapt existing patterns (e.g., list → kitchen, membership checks) where appropriate
- Know the boundaries where new custom logic is required
- Implement faster using proven patterns from finance-dashboard

**Scenario 3: Reviewing and Auditing Code Quality**

As a code reviewer, I want to know which patterns come from finance-dashboard so I can understand what is stable, proven code versus what is new or adapted.

- Recognize reused patterns and why they are safe
- Identify adapted patterns and review them carefully
- Distinguish new code specific to Melos that needs thorough review
- Maintain consistency with proven patterns

## Functional Requirements

### FR1: Repository Layout Reuse
- `api/` folder structure and hexagonal architecture are copied and reused as-is
- `ui/` folder structure is copied and reused as-is
- `scripts/` folder with compose management scripts is copied and reused as-is
- `.github/workflows/ci.yml` is copied and reused as-is
- `.cursor/worktrees.json` is copied and reused as-is
- Every finance-dashboard name in code becomes a Melos name (FR1.1)
- Data directory path changes from `~/finance-helper` to `~/melos`

#### FR1.1: Naming Rule

Code, configuration, tests and scripts use Melos names only. No identifier, environment variable, cookie or storage key, HTTP header, Compose project or container name, database name, data path or UI label keeps a finance-dashboard name.

| Finance-dashboard name | Melos name |
|---|---|
| `FH_*` env vars (e.g. `FH_COMPOSE_NAME`) | `MELOS_*` (e.g. `MELOS_COMPOSE_NAME`) |
| `FINANCE_HELPER_DATA` (default `~/finance-helper`) | `MELOS_DATA` (default `~/melos`) |
| cookie `fh_session` | `melos_session` |
| storage keys `fh_theme_cache`, `fh_lang_cache` | `melos_theme_cache`, `melos_lang_cache` |
| header `X-FH-Client-IP` | `X-Melos-Client-IP` |
| Compose project `finance-helper`, worktree names `fh-<slug>` | `melos`, `melos-<slug>` |
| worktree data `~/finance-helper-wt/`, checkouts `../finance-dashboard-wt-<slug>` | `~/melos-wt/`, `../melos-wt-<slug>` |
| database `finance_helper` (`.env.example`, CI) | `melos` |
| UI title "Finance Helper" | "Melos" |

- The rule covers the auth layer too (FR5.1–FR5.3). Renaming is the only edit made to those files, and their logic stays the same.
- There are no exceptions. The `fh_session` and `X-FH-Client-IP` fallback defaults in `api/api/settings.py` become `melos_session` and `X-Melos-Client-IP`.
- The rule covers names, not attribution. Comments, docstrings and docs **may** name finance-dashboard as the source of reused code (SC-1).
- **Pass condition:** `git grep -nE 'FH_|fh_|fh-|X-FH-|FINANCE_HELPER|finance[-_]helper|Finance Helper'` outside `specs/` and `dev/` returns nothing. Mentions of `finance-dashboard` in comments and docs are allowed.

### FR2: Docker Compose Configuration Reuse
- Base `docker-compose.yml` is copied and reused with these services:
  - **db**: PostgreSQL 16 (base image in finance-dashboard; upgraded to `pgvector/pgvector:pg16` for vector embeddings in Melos)
  - **api**: FastAPI service (Dockerfile builds from `./api`, port 8000; Dockerfile reused as-is)
  - **ui**: Next.js service (Dockerfile builds from `./ui`, port 3000; Dockerfile reused as-is)
  - **mcp** (new for Melos): FastAPI MCP service (separate container for security, port 9000)
- **Overlay files:**
  - `docker-compose.dev.yml` (reused from finance with adaptations: Gemini/pgvector environment variables injected; Compose project named by `MELOS_COMPOSE_NAME`; host ports set by `API_HOST_PORT`, `UI_HOST_PORT` and `MCP_HOST_PORT`)
  - `docker-compose.prod.yml` (reused; `mcp` is defined in the base file, so it runs in every overlay, prod included)
  - `docker-compose.test.yml` (reused as-is)
  - `docker-compose.worktree.yml`, `docker-compose.worktree-lite.yml` (reused for parallel Cursor development)
- **No `version` field:** No Compose file declares or depends on a top-level `version:` key (Compose v2 ignores it). No healthcheck, health response or other Docker configuration requires a version field either (see FR6.5 step 7).
- Environment variables reused from finance-dashboard:
  - `POSTGRES_*` (database credentials)
  - `SESSION_SECRET`, `SESSION_COOKIE_*` (auth)
  - `SMTP_*` (email delivery)
  - `AUTH_RATE_LIMIT_*` (rate limiting thresholds)
  - `TRUSTED_PROXY_IPS`, `AUTH_CLIENT_IP_HEADER` (IP trust)
  - `PDF_STORAGE_PATH` (file storage)
- **Melos additions (environment):**
  - `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`, `GEMINI_EMBED_DIM` (AI/LLM integration; injected into all environments including dev)
  - `MELOS_COMPOSE_NAME`, `MELOS_DATA` (namespace and data location, replacing `FINANCE_HELPER_*`)
  - `API_HOST_PORT`, `UI_HOST_PORT`, `MCP_HOST_PORT` (host ports; worktrees give each stack its own)
  - All finance-dashboard names change per FR1.1 (e.g., session cookie `melos_session`, client IP header `X-Melos-Client-IP`). Standard response headers such as `Retry-After` keep their names.
  - **Dev-specific additions** (docker-compose.dev.yml): `SEED_DEV_USER`, `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD`, `SEED_DEV_USER_ALIAS`, `SEED_DEV_MEMBER_EMAIL`, `SEED_DEV_MEMBER_PASSWORD`, `SEED_DEV_MEMBER_ALIAS`, `SEED_DEV_USER_KITCHEN` for the dev seed (see "Development Seeding")

### FR3: Scripts and Build Tools Reuse
- Compose management scripts (`compose-up.sh`, `compose-down.sh`, `compose-restart.sh`, `compose-wipe-db.sh`) are copied and reused
- `compose-lib.sh` helper library is reused
- Worktree helper scripts are reused with names adapted to Melos
- Default ports may be changed but patterns remain the same

### FR4: Python and Node Tooling & Dependencies
- **Python:** 3.12+ with `uv` package manager (not pip or venv)
- **Key Python dependencies (api/):**
  - FastAPI 0.141.1 (web framework)
  - Uvicorn 0.52.1 (ASGI server)
  - SQLAlchemy 2.0.51 (ORM)
  - Alembic 1.18.5 (migrations)
  - psycopg 3.3.4 (PostgreSQL driver)
  - Pydantic 2.13.4 (data validation)
  - argon2-cffi 25.1.0 (password hashing)
  - aiosmtplib 5.1.2 (email delivery)
  - pytest 9.1.1 (testing framework)
  - ruff 0.14.7 (linting and formatting)
  - httpx 0.28.1 (HTTP client for tests)
- **Database:** PostgreSQL 16 (base); pgvector extension added for Melos embeddings
- **Node.js:** Latest stable (version specified in `.node-version` if present)
- **Key JavaScript/React dependencies (ui/):**
  - Next.js 16.2.12 (framework)
  - React 19.2.4 + React DOM 19.2.4 (UI library)
  - Tailwind CSS 4.3.3 + PostCSS 8.5.26 (styling)
  - TypeScript 5 (type safety)
  - Vitest 4.1.10 (testing framework)
  - ESLint 9 (linting)
  - Turbopack (Next.js bundler, enabled in dev mode)
- **Testing Strategy:**
  - API: pytest for unit and integration tests
  - UI: vitest for component and client tests
  - Both use Compose test overlay (`docker-compose.test.yml`)
- **Code Quality:** ruff for Python (linting + formatting), eslint for JavaScript

### FR5: Authentication Layer Reuse
- Session-based authentication with httpOnly cookie is reused unchanged
- Password hashing with argon2 (`argon2-cffi`) is reused
- Password reset flow (email with single-use token, 1-hour expiry) is reused
- Email verification feature (gated by `EMAIL_VERIFICATION_REQUIRED` setting) is reused
- Rate limiting (per IP and per user) is reused with same status codes and headers
- Profile management (alias, photo, theme) is reused
- API endpoints remain: `/auth/register`, `/auth/sign-in`, `/auth/sign-out`, `/auth/session`, `/auth/me`, password reset and verification endpoints
- The auth layer's logic is **not modified** without explicit approval. The FR1.1 renames are approved (2026-10-19) and are the only edits.

#### FR5.1: Auth Layer File Inventory

All auth files listed below are copied from `finance-dashboard/api/` to `melos/api/` with their logic unchanged. The only file-level edits are the FR1.1 renames (for example the `fh_session` and `X-FH-Client-IP` fallback defaults in `api/api/settings.py`).

Paths are relative to `api/`. The FastAPI package is `api/api/`, so `api/routes/auth.py` lives at `api/api/routes/auth.py`. Alembic revisions live in `api/adapters/persistence/migrations/versions/`.

| File Path | Module Purpose | Handles |
|-----------|---|---|
| `api/routes/auth.py` | HTTP endpoints | POST /auth/register, /auth/sign-in, /auth/sign-out, /auth/session, /auth/me, password reset, email verification endpoints |
| `api/schemas/auth.py` | Request/response models | Pydantic models: RegisterRequest, SignInRequest, SessionResponse, PasswordResetRequest, etc. |
| `api/deps.py` | Dependency injection | `get_current_user()`, `get_session()`, rate limit middleware, authenticated request guards |
| `api/settings.py` | Config loading | Environment variables: `SESSION_*`, `AUTH_RATE_LIMIT_*`, `TRUSTED_PROXY_IPS`, `AUTH_CLIENT_IP_HEADER` |
| `api/app.py` | FastAPI setup | Rate limit middleware registration, session middleware setup |
| `application/email_verification.py` | Email verification logic | Request, confirm, and validate email verification tokens (1-hour expiry) |
| `application/password_reset.py` | Password reset logic | Request and complete password reset flows (email with token, 1-hour expiry) |
| `application/preferences.py` | Profile management | Get/set user alias, theme, locale; user preferences CRUD |
| `application/rate_limit.py` | Rate limiting service | Rate limit checks per IP and per user; status code 429 on exceeded limits |
| `adapters/persistence/sessions.py` | Session storage | SQLAlchemy session table, httpOnly cookie creation, session validation |
| `adapters/persistence/password_hasher.py` | Password hashing | Argon2-cffi wrapper for password hashing and verification |
| `adapters/persistence/password_reset.py` | Password reset storage | SQLAlchemy table and queries for password reset tokens |
| `adapters/persistence/email_verification.py` | Email verification storage | SQLAlchemy table and queries for email verification tokens |
| `adapters/persistence/repositories.py` | Data access | `SqlAlchemyAuthUserRepository`, `SqlAlchemySignupRepository` (user CRUD, credential lookup) |
| `adapters/persistence/models.py` | Database models | SQLAlchemy models for `users`, `sessions`, `password_reset_tokens`, `email_verification_tokens` (preferences are columns on `users`) |
| `adapters/email/smtp.py` | Email sending | SMTP adapter for password reset and verification emails |
| `adapters/email/settings.py` | Email config | Environment variables: `SMTP_*`, `PUBLIC_APP_URL`, email template defaults |

**Copy Instructions:**
1. Copy entire `api/routes/auth.py` as-is
2. Copy entire `api/schemas/auth.py` as-is
3. Copy `api/deps.py`, `api/settings.py`, and `api/app.py` as-is (they contain auth logic mixed with other setup)
4. Copy all files under `application/` that relate to auth (email_verification.py, password_reset.py, preferences.py, rate_limit.py)
5. Copy entire `adapters/persistence/` directory as-is (includes all auth models and repositories)
6. Copy entire `adapters/email/` directory as-is
7. **Do not change the core auth logic in any of these files.** The only edits are the FR1.1 renames (`fh_`/`FH_` → `melos_`/`MELOS_`, `X-FH-Client-IP` → `X-Melos-Client-IP`), including in the auth tests. Values come from `.env` and are read through `load_auth_settings()` in `api/api/settings.py`.
   - `settings.py` does not load `GEMINI_*` or `MELOS_DATA` in the bootstrap. Compose passes those through only (plan D5). The feature that first uses them adds them to the settings.
8. **Do not remove or rename any of these files**, as they are a dependency of other layers.

#### FR5.2: Frontend Auth Components to Copy

All frontend auth files listed below are copied from `finance-dashboard/ui/` to `melos/ui/` with minimal adaptations. Adaptations are file-level only (localStorage key renaming, language toggle removal); no route or logic structure changes.

| File Path | Type | Purpose | Adaptations for Melos |
|-----------|------|---------|-----|
| `app/sign-in/page.tsx` | Page | Sign-in page entry point | None |
| `app/sign-in/SignInForm.tsx` | Component | Login form with email/password fields | None |
| `app/sign-in/SignInChrome.tsx` | Component | Sign-in layout wrapper | Header title "Finance Helper" → "Melos" |
| `app/sign-in/signInClient.ts` | Utility | Client-side sign-in logic | None |
| `app/sign-up/page.tsx` | Page | Sign-up page entry point | None |
| `app/forgot-password/page.tsx` | Page | Forgot password entry point | None |
| `app/forgot-password/ForgotPasswordForm.tsx` | Component | Forgot password form | None |
| `app/reset-password/page.tsx` | Page | Reset password entry point | None |
| `app/reset-password/ResetPasswordForm.tsx` | Component | Reset password form (token validation) | None |
| `app/verify/page.tsx` | Page | Email verification entry point | None |
| `app/verify/VerifyForm.tsx` | Component | Email verification form | None |
| `app/account/page.tsx` | Page | User profile/account management page | Remove language toggle UI; keep theme/alias/photo |
| `components/AppShell.tsx` | Component | Main layout wrapper, session initialization | None |
| `components/AppShell.test.tsx` | Test | AppShell tests | None |
| `components/PreferencesProvider.tsx` | Context | User preferences, theme, locale, photo | Rename localStorage keys: `fh_theme_cache` → `melos_theme_cache`, `fh_lang_cache` → `melos_lang_cache`; remove `setLanguage()` function; default locale to English |
| `components/AccountMenu.tsx` | Component | User dropdown menu in header | Remove language selector dropdown; keep theme, logout, account link |
| `components/AccountMenu.test.tsx` | Test | AccountMenu tests | Update snapshot if language selector removed |
| `components/RedirectIfAuthenticated.tsx` | Component | Route guard redirecting authenticated users | None |
| `lib/session.ts` | Utility | Session utilities and types | None |
| `lib/authBff.ts` | Utility | BFF auth proxy (cookie forwarding, IP header validation) | Default header `X-FH-Client-IP` → `X-Melos-Client-IP` |
| `lib/authBff.test.ts` | Test | BFF auth tests | None |
| `app/api/auth/sign-in/route.ts` | BFF Route | Proxy to POST /auth/sign-in backend | None |
| `app/api/auth/sign-in/route.test.ts` | Test | Sign-in route tests | None |
| `app/api/auth/register/route.ts` | BFF Route | Proxy to POST /auth/register backend | None |
| `app/api/auth/register/route.test.ts` | Test | Register route tests | None |
| `app/api/auth/sign-out/route.ts` | BFF Route | Proxy to POST /auth/sign-out backend | Default cookie name `fh_session` → `melos_session` |
| `app/api/auth/sign-out/route.test.ts` | Test | Sign-out route tests | None |
| `app/api/auth/session/route.ts` | BFF Route | Proxy to GET /auth/session backend | None |
| `app/api/auth/session/route.test.ts` | Test | Session route tests | None |
| `app/api/auth/me/route.ts` | BFF Route | Proxy to GET /auth/me backend (current user) | None |
| `app/api/auth/me/route.test.ts` | Test | Me route tests | None |
| `app/api/auth/verify/request/route.ts` | BFF Route | Proxy to POST /auth/verify/request backend | None |
| `app/api/auth/verify/confirm/route.ts` | BFF Route | Proxy to POST /auth/verify/confirm backend | None |
| `app/api/auth/verify/route.test.ts` | Test | Verify route tests | None |
| `app/api/auth/password-reset/route.ts` | BFF Route | Proxy to POST /auth/password-reset backend | None |
| `app/api/auth/password-reset/route.test.ts` | Test | Password reset route tests | None |

**Copy Instructions:**
1. Copy all files listed above from finance-dashboard/ui/ to melos/ui/ maintaining directory structure
2. Edit `components/PreferencesProvider.tsx`:
   - Line 20: `const THEME_CACHE_KEY = "fh_theme_cache"` → `const THEME_CACHE_KEY = "melos_theme_cache"`
   - Line 21: `const LANG_CACHE_KEY = "fh_lang_cache"` → `const LANG_CACHE_KEY = "melos_lang_cache"`
   - Remove or stub out `setLanguage()` function (keep function signature but make it a no-op or remove the UI call)
   - Default `locale` to `"en"` only
3. Edit `components/AccountMenu.tsx`:
   - Remove language selector dropdown/toggle UI
   - Keep theme toggle, profile link, sign-out button
4. Edit `app/account/page.tsx`:
   - Remove language selection UI section
   - Keep alias, theme, photo management UI
5. Apply the FR1.1 renames everywhere in `ui/`, tests included:
   - `fh_session` default in `app/api/auth/sign-out/route.ts` and `proxy.ts`
   - `X-FH-Client-IP` default in `lib/authBff.ts`
   - `fh_lang_cache` reads in `app/home/page.tsx` and `app/kitchens/[kitchenId]/page.tsx`
   - "Finance Helper" title in `app/sign-in/SignInChrome.tsx`
6. **Do not customize BFF route logic.** The routes proxy directly to the FastAPI backend, and configuration lives in the backend's `api/api/settings.py`. FR1.1 renames are the only edits.

#### FR5.3: Minimal Customization Scope

The auth layer is copied as-is from finance-dashboard and is **not modified** without explicit written approval from Sebastián. This section defines the strict boundaries for what may be changed without approval and how developers should handle the manual copy process.

**Off-Limits (Require Pre-Approval):**
- Session cookie behavior: httpOnly flag, Secure flag, SameSite policy, cookie lifetime. The cookie name is fixed as `melos_session` (approved 2026-10-19).
- Password hashing algorithm and configuration: argon2-cffi parameters, salt rounds, memory/time cost settings
- Rate limit policy thresholds: limits per IP, limits per user, window duration, status codes returned
- Database schema for auth tables: `users`, `sessions`, `password_reset_tokens`, `email_verification_tokens` table structure, column types, constraints (preferences are columns on `users`)
- API endpoint signatures: `/auth/*` paths, HTTP method, parameter names, response structure

**Permitted Without Pre-Approval (Code Review Sufficient):**
- Configuration via `.env` and `api/settings.py`: loading environment variables, choosing between optional features (e.g., `EMAIL_VERIFICATION_REQUIRED`), selecting SMTP provider
- Test changes: adding tests, updating test data, refactoring test structure
- Documentation: comments, docstrings, README updates explaining auth patterns
- Code formatting: linting, import reorganization, style compliance (must pass ruff)
- Non-critical bug fixes: typos, logic bugs that do not alter intended behavior, missing error handling for edge cases
- Type hints and type safety improvements: adding or fixing type annotations without changing logic

**Approval Process:**
- Changes to **permitted areas** require standard code review approval via pull request
- Changes to **off-limits areas** require explicit written pre-approval from Sebastián **before** opening a pull request
- If a developer is unsure whether a change is permitted, they should ask in a GitHub issue or discussion before implementing

**Common Mistakes to Avoid:**

1. **Leaving finance-dashboard names behind.** FR1.1 renames are required in auth files as well: `fh_`/`FH_` become `melos_`/`MELOS_`, and `X-FH-Client-IP` becomes `X-Melos-Client-IP`. Rename the names and defaults only, not the logic around them.
2. **Changing behaviour while renaming.** A rename must not touch cookie flags or lifetime, hashing parameters, rate limit thresholds or endpoint signatures. Those stay off-limits.
3. **Reading configuration outside the settings loader.** Auth code reads configuration from `load_auth_settings()` in `api/api/settings.py`, never with `os.environ`/`os.getenv()` in routes or use cases.
4. **Changing the schema outside Alembic.** Any column or table rename goes through a new Alembic revision and needs pre-approval for auth tables.

**Example:**
```python
# ❌ WRONG: bypasses the settings loader and keeps the finance-dashboard name
cookie_name = os.getenv("SESSION_COOKIE_NAME", "fh_session")

# ✅ RIGHT: the settings loader reads the value; its fallback uses the Melos name
settings = load_auth_settings()
cookie_name = settings.session_cookie_name  # "melos_session" unless .env overrides it
```

### FR6: UI Shell and Component Reuse
- **Framework**: Next.js 16.2.12 with App Router (not Pages Router), Turbopack bundler in dev
- **Styling**: Tailwind CSS 4.3.3 with PostCSS, dark mode support via CSS variables
- **Reused components from finance-dashboard**:
  - `AppShell` (main layout wrapper)
  - `AccountMenu` (user profile dropdown)
  - `ActionDialog` (confirmation modals)
  - `Chip`, `ChipPicker` (tag-like components)
  - `IconButton`, `Disclosure` (reusable UI primitives)
  - `CopyButton` (copy-to-clipboard)
- **Tailwind theme**: Color palette, spacing scale, typography, responsive breakpoints all reused
- **Language toggle**: **Removed** for Melos (UI is English-only, unlike finance which has multi-language support)
- **React 19.2.4** with React DOM 19.2.4
- **TypeScript 5** for type safety across UI
- **Testing**: Vitest 4.1.10 for component and client tests (jsdom environment)
- **BFF pattern**: UI acts as backend-for-frontend
  - All routes under `app/api/*` proxy to FastAPI `/api` backend
  - UI handles session cookie forwarding via `Set-Cookie` header (api is the cookie issuer)
  - Client browser only communicates with localhost:3000, never directly with api
- **Accessibility & Patterns**: Same component patterns as finance-dashboard (semantic HTML, WCAG compliance, icon buttons with labels)

### FR6.5: Development Workflow Patterns (Reused with Adaptations)

**Initial Developer Setup (One-Time)**
1. Clone the repository and navigate to the project root
2. Copy `.env.example` to `.env` and fill in required values:
   - `POSTGRES_PASSWORD` (generate a secure password)
   - `SESSION_SECRET` (generate a random string)
   - `GEMINI_API_KEY` (obtain from Google AI Studio)
   - `SMTP_*` (required in dev too: use a real SMTP provider, e.g. a Gmail app password, so reset, verification and invite emails reach real inboxes)
3. Create the data directory outside the repo:
   - `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"` (PostgreSQL data persists here)
4. Install Python dependencies:
   - `cd api && uv sync --group dev` (installs from uv.lock, never use pip)
5. Install Node.js dependencies:
   - `cd ui && npm install` (installs from package-lock.json)
6. Start all services (4 containers total):
   - `./scripts/compose-up.sh` (or `./scripts/compose-up.sh -d` for background)
   - Starts: **db** (PostgreSQL + pgvector), **api** (FastAPI), **ui** (Next.js), **mcp** (MCP service)
   - **API entrypoint auto-runs `alembic upgrade head`** before starting FastAPI (reused from finance-dashboard)
   - Developers do NOT need to run migrations manually
7. Verify all services are healthy:
   - UI: http://localhost:3000 (should show login page) and http://localhost:3000/health
   - API: http://localhost:8000/health
   - MCP: http://localhost:9000/health
   - Each `/health` returns `200 {"status":"healthy","service":"<api|ui|mcp>","timestamp":"<ISO-8601 UTC>"}` ([contracts/health.md](contracts/health.md)). There is no `version` field.
   - All services run locally for end-to-end testing of external AI integrations before deployment

**Ongoing Python workflow** (from api/ directory):
- Run locally: `uv run <command>` (never `python` or `pip`)
- Add libraries: `uv add <package>` or `uv add --group dev <package>` (updates uv.lock automatically)
- Linting: `uv run ruff check .` (E, F, I, UP, B rule sets, line length 100)
- Tests: `uv run pytest -q` (pytest with pythonpath=["."], testpaths=["tests"])
- In Compose: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`

**Ongoing Node.js workflow** (from ui/ directory):
- Add libraries: `npm install <package>` (updates package-lock.json automatically)
- Dev server: `npm run dev` (uses Turbopack; auto-reload on file changes)
- Build: `npm run build` (production build)
- Linting: `npm run lint` (eslint with next config)
- Type checking: `npm run typecheck` (tsc, strict mode)
- Tests: `npm test` (vitest in watch mode)
- Coverage: `npm run test:coverage` (vitest with coverage)

**Git and branches (parallel work with Cursor worktrees)**:
- Create isolated worktree: `./scripts/worktree/worktree-add.sh <slug> <branch>`
- Each worktree gets its own Compose stack via environment variables:
  - `MELOS_COMPOSE_NAME` isolates container names (prevents collisions)
  - `API_HOST_PORT` assigns a different port per worktree (e.g., 8001, 8002)
  - `UI_HOST_PORT` assigns a different UI port (e.g., 3001, 3002)
  - `MCP_HOST_PORT` assigns a different MCP port (e.g., 9001, 9002)
  - `MELOS_DATA` points at `~/melos-wt/<compose-name>` so each worktree has its own Postgres data
- This allows multiple developers to run isolated instances simultaneously

**CI/CD** (GitHub Actions):
- `.github/workflows/ci.yml` runs the same commands (lint, test, build) on push
- Must pass locally before pushing

### FR7: List/Kitchen Conceptual Reuse
- Membership model (kitchen_id, user_id, role as owner|member) is reused
- Access control: one rule for every kitchen-scoped endpoint, reads and writes alike. No session → `401`. Kitchen missing or caller not a member → `404 kitchen_not_found` (same body, so kitchen existence is never revealed). Member but the action is owner-only → `403 not_kitchen_owner`. Non-members never get `403`. Full table in [contracts/kitchen-membership-api.md](contracts/kitchen-membership-api.md) §Access Control
- Invite-by-email flow is reused: the owner invites an email. Existing accounts get a `join` link (`/invites/accept?token=`, sign in, then `POST /invites/accept`). New people get a `signup` link (`/signup?invite=`, then `POST /auth/register` with `invite_token`). `GET /invites/preview` is public. Invalid, expired or used tokens return `410`. Tokens are single-use, email-bound and last 7 days. The API never redirects; routing is the UI's job
- Kitchen replaces "list" concept in code, database and UI

### FR8: What Is NOT Reused
- Finance-dashboard `.env.example` seed credentials are **not copied** (invent new examples for Melos)
- Finance domain code is **not reused**: no cards, statements, budgets, splits, FX, bank adapters
- Any finance-specific routes, use cases or adapters are excluded
- Architecture changes are not made without approval

## Clarifications

### Session 2026-10-19

Clarifications made during specification refinement phase:

- **Q1: Dev Compose Adaptation** → **A:** Environment names change (FH_ → MELOS_), Gemini/pgvector configs added to dev overlay, Dockerfiles and scripts reused as-is
- **Q2: Developer Setup Steps** → **A:** Explicit step-by-step procedure (copy .env, create data dir, uv sync, npm install, compose-up) with health check verification
- **Q3: Development Seeding** → **A:** Seed test user + sample kitchen + 3–5 recipes + ingredient catalog + populated cart + conversation history + archived shopping list for comprehensive local testing
- **Q4: Database Migrations** → **A:** API entrypoint auto-runs `alembic upgrade head` on startup (reused from finance-dashboard); developers do not run migrations manually
- **Q5: MCP in Development** → **A:** MCP service runs in dev Compose (all 4 services: db, api, ui, mcp) for end-to-end testing of external AI integrations locally
- **Q6: Auth Layer File Inventory** → **A:** Add enumerated file inventory (FR5.1) listing exact paths, modules, and what each handles; no file-level customizations needed (config via .env and api/settings.py)
- **Q7: Frontend Auth Components to Copy** → **A:** Exact file paths from finance-dashboard/ui/ for auth pages (sign-in, sign-up, forgot-password, reset-password, verify, account), session utilities (AppShell, PreferencesProvider, AccountMenu, session.ts, authBff.ts), and BFF proxy routes. Adaptations needed: rename localStorage keys (fh_ → melos_), remove language toggle from AccountMenu (English-only for Melos), default locale to "en".

### Session 2026-10-19 (FR5.3 Clarifications)

Clarifications made during minimal customization scope definition:

- **Q1: FR5.3 Section Formalization** → **A:** Add FR5.3 as formal requirement section with explicit permit/prohibit lists for auth layer changes
- **Q2: Off-Limits Areas** → **A:** Session cookie behavior, password hashing algorithm, rate limit thresholds (policy), auth database schema, and API endpoint signatures are off-limits. Permitted: configuration via .env/settings.py, tests, comments, formatting, non-critical bug fixes.
- **Q3: Automatic Transformations** → **A:** No automatic file transformations. All copies are manual, one-time operations. Configuration happens via .env and api/settings.py, not via file-level find-replace or build scripts. Document for developers the specific places where env var prefixes appear (and why they should NOT be manually changed).
- **Q4: Developer Guidance** → **A:** Add "Common Mistakes" subsection to FR5.3 showing examples of what NOT to do (e.g., naive find-replace of FH_ → MELOS_ in auth files), with corrected examples and explanation of how settings.py handles config.
- **Q5: Approval Process** → **A:** Code review approval sufficient for permitted changes (tests, docs, formatting, non-critical fixes). Explicit pre-approval from Sebastián required only for off-limits areas before opening a PR.

### Session 2026-10-19 (Plan review, checklist `checklists/bootstrap.md`)

Decisions by the owner after `/speckit-plan`. They supersede earlier answers where they differ.

- **Q1: Finance-dashboard names in code** → **A:** None remain. Every `fh_`/`FH_`/`finance-helper` name becomes `melos_`/`MELOS_`/`melos`, auth files included (FR1.1). This supersedes the earlier "no file-level find-replace" guidance (FR5.3 Clarification Q3/Q4).
- **Q2: `fh_session` fallback in `settings.py`** → **A:** Not allowed. It becomes `melos_session`. The plan's proposed exception is withdrawn.
- **Q3: Source attribution** → **A:** Comments and docs keep naming finance-dashboard as the source (SC-1). Only names in code change.
- **Q4: Dev seed** → **A:** Seed only users and one kitchen: two verified users, an owner and a member, sharing one kitchen. No recipe, cart, shopping-list or conversation data. Credentials come from `.env` only.
- **Q5: Version fields** → **A:** No Docker configuration ever requires a `version` field: no top-level `version:` in Compose files, and no `version` in `/health` responses.
- **Q7: SMTP in dev** → **A:** Dev has SMTP configured with a real provider. That is how emails are tested (reset, verification, invites to the seeded users).
- **Q8: 404 vs 403 for kitchens** → **A:** 404 everywhere for non-members, writes included. 403 only for a member attempting an owner-only action. This changes the reused write routes (today they return `403 not_kitchen_member`), including the `last_opened_kitchen_id` check in `PATCH /auth/me`. The owner approved that auth-route status change on 2026-10-19 (FR5.3).
- **Q9: Invite acceptance when signed out** → **A:** The contract documents the code's flow: public preview, then accept with a session or register with `invite_token`. `410` for bad tokens. Redirects belong to the UI. Checked: new invitees get a `/signup?invite=` link, so they are offered sign-up. No change needed.
- **Q6: Spec vs plan** → **A:** The plan (D1–D7) is authoritative for bootstrap scope. The spec is updated to match: staged seed, bootstrap-only tables, real source paths.

## Success Criteria

1. **Codebase Consistency**: All reused code from finance-dashboard is clearly documented with comments indicating origin and any adaptations. Comments may name finance-dashboard, but identifiers follow FR1.1.
2. **Bootstrap Speed**: A developer can set up the Melos codebase for the first time in under 15 minutes using the reused patterns
3. **Pattern Adherence**: All new features follow the established patterns (hexagonal architecture, port/adapter, naming conventions) with no deviations without approval
4. **No Secrets Exposure**: No finance-dashboard credentials or Melos secrets appear in code, the repo, .env.example or documentation
5. **Test Suite Parity**: Test structure, tooling and patterns match those of finance-dashboard (pytest, vitest, same directory layout)
6. **Documentation Clarity**: The spec and README clearly explain which parts come from finance and which are Melos-specific

## Key Entities & Data Structures

Full definitions are in [data-model.md](data-model.md).

**Tables this feature owns (bootstrap):**
- `users` (auth; preferences such as alias, theme and photo are columns here)
- `sessions` (auth)
- `password_reset_tokens` (auth)
- `email_verification_tokens` (auth)
- `kitchens` (replaces "list"; gains `content_language`, `en`/`es`, default `en`, in revision `0002`)
- `kitchen_memberships` (kitchen_id, user_id, role)
- `kitchen_invite_tokens` (kitchen_id, email, token_hash)
- The `vector` (pgvector) extension, enabled in revision `0002`. No vector columns yet.

**Melos-specific entities (deferred, not created by this feature):**
Each is created by an Alembic revision in the feature spec that owns it (plan D4):
- `ingredient`, `category`, `source`, `recipe`, `recipe_ingredient`, `recipe_category`, `step`, `recipe_embedding` (capture + recipes)
- `cart`, `cart_item` (plan)
- `shopping_list`, `shopping_list_item` (shop)
- `conversation`, `message` (ask)
- `api_key` (MCP service)

## Implementation Boundaries

### API Layer Separation (Hexagonal Architecture)

This is the target v1 layout. The bootstrap builds only auth, kitchens, invites and `/health`. Items marked *(later)* arrive with their own feature specs.

- **domain/**: Pure business logic (no I/O, no framework dependencies)
  - `recipe.py` (Unit, Size, Dimension, validation rules) *(later)*
  - `cart.py` (scaling, consolidation) *(later)*
  - `ingredient_catalog.py` (name normalization) *(later)*
  - `toon.py` (object encoding for LLM prompts) *(later)*
  - `render.py` (Markdown/embed text generation) *(later)*
  - `kitchens.py`, `kitchen_access.py`, `kitchen_invite.py` (reused from finance-dashboard; `kitchens.py` validates `content_language`)
- **application/**: Use cases and port definitions
  - `ports.py`: repositories now; RecipeExtractor, Embedder, ChatModel, PageFetcher, PdfRenderer *(later)*
  - Use cases: `kitchens`, `kitchen_access`, `kitchen_invite`, `kitchen_invite_accept` + reused auth; `capture_recipe`, `recipes`, `ingredients`, `categories`, `carts`, `shopping_list`, `conversations`, `exports` *(later)*
  - All kitchen-scoped queries enforce membership checks here (`kitchen_access.py`, non-members get 404)
- **adapters/**: Concrete implementations of ports
  - `llm/gemini.py` (Gemini API via google-genai SDK) *(later)*
  - `web/page_fetcher.py`, `web/jsonld.py` (URL fetching with SSRF protection) *(later)*
  - `pdf/weasyprint.py` + `templates/`, `fonts/` (PDF generation with Unicode fonts) *(later)*
  - `persistence/` (SQLAlchemy, Alembic migrations, pgvector)
  - `email/` (aiosmtplib — reused from finance)
- **api/api/**: FastAPI application layer
  - `app.py` (FastAPI app entry point)
  - `routes/` (HTTP endpoints):
    - `auth.py` (reused from finance-dashboard)
    - `kitchens.py`, `invites.py` (kitchen and member management)
    - `health.py` (health check endpoint)
    - `recipes.py`, `drafts.py`, `ingredients.py`, `categories.py`, `carts.py`, `shopping_list.py`, `conversations.py`, `messages.py`, `exports.py` *(later)*
  - `schemas/` (Pydantic request/response models)
  - `deps.py` (dependency injection: auth, session, kitchen access)
  - `settings.py` (environment configuration)
- **tests/**: pytest test suite (domain, application, integration tests)
- **scripts/**: Data seeding, migrations, CLI utilities

### External Call Handling
All external calls (Gemini, web fetch, SMTP) must:
- Go through a port in `application/ports.py`
- Map errors to domain errors (e.g., `AIUnavailable`, `PageFetchFailed`)
- Never expose raw SDK exceptions to the user

## Repository Structure (Reused with Adaptations)

```
melos/
├── .github/workflows/ci.yml         # Reused from finance-dashboard (test, lint, build steps)
├── .cursor/worktrees.json          # Reused for Cursor worktree management
├── .gitignore                       # Standard Python/Node ignores (added: .env, node_modules/, .venv/)
├── docker-compose.yml              # Reused (db, api, ui, mcp; adapted: db image → pgvector, names per FR1.1; no `version:` key)
├── docker-compose.{dev,prod,test,worktree,worktree-lite}.yml  # All overlays reused
├── .env.example                    # Adapted: new Gemini vars, MELOS_ names, invented placeholder values only
├── .env                            # LOCAL ONLY (never committed) — copy from .env.example
├── api/
│   ├── pyproject.toml             # Reused structure; feature libs (google-genai, weasyprint) arrive with their features
│   ├── uv.lock                    # Locked dependencies (commit this, never edit by hand)
│   ├── Dockerfile, alembic.ini    # Reused
│   ├── domain/                    # Pure business logic (reused structure, Melos rules)
│   │   ├── kitchens.py, kitchen_access.py, kitchen_invite.py  # From finance-dashboard ("lists" renamed)
│   │   └── recipe.py, cart.py, …  # (later features)
│   ├── application/               # Use cases + ports (reused pattern)
│   │   ├── ports.py
│   │   └── kitchens.py, kitchen_access.py, signup.py, …
│   ├── adapters/
│   │   ├── persistence/           # Reused: SQLAlchemy models, repositories, sessions
│   │   │   └── migrations/versions/  # 0001_melos_baseline, 0002_pgvector_and_kitchen_language
│   │   ├── email/                 # Reused from finance: aiosmtplib
│   │   └── llm/, web/, pdf/       # (later features: Gemini, page fetcher, WeasyPrint)
│   ├── api/
│   │   ├── app.py                # FastAPI app setup
│   │   ├── routes/               # auth.py (reused), kitchens.py, invites.py, health.py
│   │   ├── schemas/              # Pydantic models (reused pattern)
│   │   ├── deps.py               # Dependency injection
│   │   └── settings.py           # Environment config
│   ├── tests/                    # pytest suite (reused structure)
│   └── scripts/                  # entrypoint.py (migrate → seed → uvicorn), seed_dev_user.py
├── mcp/
│   ├── Dockerfile, pyproject.toml, uv.lock, .python-version
│   ├── server/main.py            # FastAPI app: /health only in the bootstrap
│   └── tools/                    # Empty; tools arrive with the MCP feature spec
├── ui/
│   ├── package.json              # Reused; dependencies locked (npm install)
│   ├── Dockerfile, Dockerfile.dev # Reused
│   ├── app/                      # Next.js App Router structure (reused)
│   │   ├── layout.tsx            # Root layout (AppShell)
│   │   ├── api/                  # BFF routes (proxy to FastAPI)
│   │   ├── health/route.ts       # /health for the ui service
│   │   └── kitchens/[kitchenId]/ # Kitchen-scoped pages
│   ├── components/               # Reusable React components (reused + Melos-specific)
│   ├── styles/                   # Global styles (Tailwind)
│   ├── lib/                      # Utilities, API client wrappers
│   └── vitest.config.ts          # Test configuration
├── scripts/
│   ├── compose-up.sh, compose-down.sh, compose-restart.sh, compose-wipe-db.sh  # Reused
│   ├── compose-lib.sh            # Reused helper library
│   └── worktree/                 # Reused for parallel work
├── dev/                          # Support material (not part of app)
│   ├── docs/prd.md              # Product specification
│   ├── skills/                  # Procedures and work states
│   └── memory/                  # Decision history
├── specs/                        # Feature specifications (planning & tracking)
└── .specify/                     # Spec Kit configuration (planning)
    ├── memory/constitution.md   # Project constitution (principles, boundaries)
    └── templates/               # Spec templates
```

## Configuration and Secrets (Reused Pattern)

**Environment Variables** (from finance-dashboard pattern, adapted for Melos):

| Category | Variables | Purpose |
|----------|-----------|---------|
| **Database** | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL credentials |
| **Compose** | `MELOS_COMPOSE_NAME`, `API_HOST_PORT`, `UI_HOST_PORT`, `MCP_HOST_PORT` | Project name (default `melos`) and host ports (defaults 8000/3000/9000) |
| **Session** | `SESSION_SECRET`, `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` | Session cookie config (name `melos_session`, httpOnly, Secure in prod, SameSite=Lax) |
| **Auth Rate Limits** | `AUTH_RATE_LIMIT_REGISTER_MAX`, `AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_SIGN_IN_MAX`, `AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_MAX`, `AUTH_RATE_LIMIT_VERIFY_REQUEST_MAX` | Rate limiting per IP and per user |
| **Email** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_STARTTLS`, `SMTP_TIMEOUT_SECONDS` | Outbound email via SMTP (fail loudly if misconfigured) |
| **App URLs** | `PUBLIC_APP_URL` | Where the app is reachable (for reset links, invites) |
| **Network** | `TRUSTED_PROXY_IPS`, `AUTH_CLIENT_IP_HEADER` | IP headers trusted from BFF (Compose: 172.16.0.0/12, localhost); header default `X-Melos-Client-IP` |
| **Auth** | `EMAIL_VERIFICATION_REQUIRED` | Gate email verification on sign-up (default false) |
| **Storage** | `PDF_STORAGE_PATH`, `MELOS_DATA` | File storage locations (outside repo) |
| **Dev Seeds** | `SEED_DEV_USER`, `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD`, `SEED_DEV_USER_ALIAS`, `SEED_DEV_MEMBER_EMAIL`, `SEED_DEV_MEMBER_PASSWORD`, `SEED_DEV_MEMBER_ALIAS`, `SEED_DEV_USER_KITCHEN` | Two pre-verified users (owner, member) sharing one kitchen (dev/worktree only) |
| **Gemini (Melos)** | `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`, `GEMINI_EMBED_DIM` | LLM configuration |

**Secrets Management** (strict reuse):
- `.env` file is **never committed** (in `.gitignore`)
- `.env.example` documents all variables with NO real values (e.g., `GEMINI_API_KEY=` empty)
- Local development: copy `.env.example` to `.env` and fill in actual values
- Production: secrets come from the server environment (e.g., systemd, Docker Compose secret files), never from the repo
- SMTP misconfiguration fails loudly (no silent email loss)

## Development Seeding (Test Data)

When `SEED_DEV_USER=1`, the API bootstrap script (`api/scripts/seed_dev_user.py`) creates **exactly two users and one shared kitchen**. Nothing else is seeded.

**Users** (both go through the normal sign-up use case, with the email marked verified):

| Role | Email | Password | Alias |
|------|-------|----------|-------|
| Owner | `$SEED_DEV_USER_EMAIL` | `$SEED_DEV_USER_PASSWORD` | `$SEED_DEV_USER_ALIAS` (optional) |
| Member | `$SEED_DEV_MEMBER_EMAIL` | `$SEED_DEV_MEMBER_PASSWORD` | `$SEED_DEV_MEMBER_ALIAS` (optional) |

- The four email and password variables are required when `SEED_DEV_USER=1`. If any is missing, the seed logs a warning and creates nothing.
- The real values live only in the local `.env`. `.env.example`, the spec, tests and docs show invented placeholders only (constitution §4).

**Shared kitchen:**
- Name: `$SEED_DEV_USER_KITCHEN`, default "Dev Kitchen"
- Content language: `en`
- The owner user has role `owner`. The member user has role `member`.
- Sign-up still gives each user their personal "My kitchen", the same as for any real user. The seed adds no other kitchens.

**Idempotency:** If the owner's email already exists, the seed does nothing. Re-running never duplicates users, kitchens or memberships.

**Purpose:** Developers can sign in as either user straight away and check membership behaviour (owner-only actions, member access, non-member 404) without manual setup.

**Later features:** Recipes, cart, shopping-list and conversation sample data are **not** part of this feature. Each later feature decides whether to extend the seed in the same PR that creates its tables (plan D7).

**Note:** Seeding is **dev/worktree only**. Production (`SEED_DEV_USER=0`) never auto-creates test users.

## Assumptions

1. **Source of truth**: Finance-dashboard is the authoritative source for auth, UI patterns and deploy structure
2. **Versions fixed at start**: Python 3.12, Node versions specified in `.python-version` and `package.json` are locked for reproducibility
3. **Email delivery**: SMTP is configured in every environment, dev included; there is no local mock for outbound mail. A misconfigured SMTP fails loudly: the request that sends email returns `503` with `code: "smtp_config_error"` (or `smtp_send_error`), and the error is logged. The API still boots so `/health` keeps answering
4. **Secrets management**: `.env` is never committed; production secrets come from the server environment, not the repo
5. **Team size**: Small team (implied from the project) means coordination is fast; patterns can be enforced via code review rather than heavy process

## Constraints & Risks

**Constraint:** The authentication layer and core architecture cannot be changed without explicit written approval from Sebastián.

**Risk:** If Melos-specific code violates hexagonal architecture (e.g., domain importing from adapters), technical debt accrues quickly and refactoring becomes painful.

**Risk:** If patterns diverge from finance-dashboard (e.g., different error handling, different naming conventions), the codebase becomes harder to maintain and onboard new developers.

## Appendix A: Reuse Checklist

- [ ] Copy `api/` structure (preserve hexagonal layers)
- [ ] Copy `ui/` structure
- [ ] Copy `scripts/` with compose helpers
- [ ] Copy `.github/workflows/ci.yml`
- [ ] Copy `.cursor/worktrees.json`
- [ ] Adapt `.env.example` (new vars: `MELOS_*`, `GEMINI_*`)
- [ ] Adapt `docker-compose.yml` (pgvector image, new mcp service)
- [ ] Copy auth layer (no modifications)
- [ ] Copy UI shell components
- [ ] Adapt naming (list → kitchen)
- [ ] Document all adaptations with comments in code
- [ ] Verify test structure matches finance-dashboard patterns
- [ ] Verify no finance-dashboard credentials leaked
- [ ] Rename every finance-dashboard name in code per FR1.1 (auth layer and `settings.py` fallbacks included)
- [ ] Add migration `0002` (pgvector extension + `kitchens.content_language`)
- [ ] Seed two users (owner, member) and one shared kitchen
- [ ] Align `/health` on api, ui and mcp with [contracts/health.md](contracts/health.md) (no `version` field)

## Tech Stack Summary Table

| Component | Technology | Version | Reused | Notes |
|-----------|------------|---------|--------|-------|
| **Python Runtime** | Python | 3.12+ | ✓ | Locked in `.python-version` |
| **Python Package Mgr** | uv | Latest | ✓ | Never use pip or venv |
| **Web Framework** | FastAPI | 0.141.1 | ✓ | Reused architecture, new routes |
| **ASGI Server** | Uvicorn | 0.52.1 | ✓ | Reused |
| **ORM** | SQLAlchemy | 2.0.51 | ✓ | Reused for all domains |
| **DB Migrations** | Alembic | 1.18.5 | ✓ | Reused pattern |
| **Database** | PostgreSQL | 16 | ~ | pgvector extension added for Melos |
| **DB Driver** | psycopg | 3.3.4 | ✓ | Async support |
| **Password Hashing** | argon2-cffi | 25.1.0 | ✓ | Reused from auth layer |
| **Email** | aiosmtplib | 5.1.2 | ✓ | Reused from auth layer |
| **Data Validation** | Pydantic | 2.13.4 | ✓ | Request/response schemas |
| **Python Testing** | pytest | 9.1.1 | ✓ | Reused structure |
| **Python Linting** | ruff | 0.14.7 | ✓ | E,F,I,UP,B rulesets |
| **LLM (Melos)** | Gemini API | TBD | — | google-genai SDK (new) |
| **Web Scraping (Melos)** | — | — | — | HTTP + JSON-LD parsing (new) |
| **PDF Generation (Melos)** | WeasyPrint | TBD | — | With Unicode font support (new) |
| **Vector DB (Melos)** | pgvector | TBD | — | PostgreSQL extension (new) |
| **JavaScript Runtime** | Node.js | Latest | ✓ | Locked in `.node-version` or package.json |
| **Package Manager** | npm | Latest | ✓ | Use npm install, npm run |
| **Framework** | Next.js | 16.2.12 | ✓ | App Router + Turbopack |
| **React** | React | 19.2.4 | ✓ | Latest stable |
| **Styling** | Tailwind CSS | 4.3.3 | ✓ | Reused theme, components |
| **Styling Processor** | PostCSS | 8.5.26 | ✓ | Reused config |
| **Type Checking** | TypeScript | 5 | ✓ | Strict mode |
| **JS Linting** | ESLint | 9 | ✓ | Reused config |
| **JS Testing** | Vitest | 4.1.10 | ✓ | Reused patterns |
| **Bundler** | Turbopack | Built-in | ✓ | In dev mode only |

## Notes

**Specification Purpose:**
This specification is a one-time integration document that establishes how Melos will bootstrap from and reuse finance-dashboard. Once the initial integration is complete, this spec becomes historical reference.

**Future Feature Specifications:**
Once Melos is bootstrapped, new features (capture recipe, shopping list, conversations, MCP service, etc.) will be tracked as separate specifications under `specs/` following the same Spec Kit structure.

**Key Principles:**
1. **Reuse what works**: Proven auth, architecture, tooling, CI/CD patterns from finance-dashboard
2. **Adapt what needs changing**: Database (add pgvector), environment names (FH_ → MELOS_), UI (remove language toggle)
3. **Document what is new**: Gemini integration, recipe/cart/conversation logic, MCP service
4. **Enforce boundaries**: Auth layer unchanged; domain imports nothing from adapters; hexagonal architecture maintained

**Deployment Model:**
- **Development**: Docker Compose on local machines with hot-reload
- **Production**: Docker Compose + nginx reverse proxy + TLS managed outside this repo (owner's responsibility)
- **Data**: PostgreSQL pgdata lives at `$MELOS_DATA/pgdata` (host volume, outside repo)
