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
- Environment prefix changes from `FH_` to `MELOS_`
- Data directory path changes from `~/finance-dashboard` to `~/melos`

### FR2: Docker Compose Configuration Reuse
- Base `docker-compose.yml` is copied and reused with these services:
  - **db**: PostgreSQL 16 (base image in finance-dashboard; upgraded to `pgvector/pgvector:pg16` for vector embeddings in Melos)
  - **api**: FastAPI service (Dockerfile builds from `./api`, port 8000; Dockerfile reused as-is)
  - **ui**: Next.js service (Dockerfile builds from `./ui`, port 3000; Dockerfile reused as-is)
  - **mcp** (new for Melos): FastAPI MCP service (separate container for security, port 9000)
- **Overlay files:**
  - `docker-compose.dev.yml` (reused from finance with adaptations: Gemini/pgvector environment variables injected; port bindings changed to `API_HOST_PORT` and `MELOS_COMPOSE_NAME`)
  - `docker-compose.prod.yml` (reused as-is)
  - `docker-compose.test.yml` (reused as-is)
  - `docker-compose.worktree.yml`, `docker-compose.worktree-lite.yml` (reused for parallel Cursor development)
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
  - Environment prefix changes from `FH_` to `MELOS_` (e.g., session cookie name, client IP header, rate limit headers)
  - **Dev-specific additions** (docker-compose.dev.yml): `SEED_DEV_USER`, `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD`, `SEED_DEV_USER_ALIAS` for pre-seeding test users

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
- The auth layer is **not modified** without explicit approval

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
   - `SMTP_*` (optional for local dev; leave blank or fill for testing email)
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
   - UI: http://localhost:3000 (should show login page)
   - API: http://localhost:8000/health (should return 200 with status)
   - MCP: http://localhost:9000/health (should return 200 with MCP status)
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
- This allows multiple developers to run isolated instances simultaneously

**CI/CD** (GitHub Actions):
- `.github/workflows/ci.yml` runs the same commands (lint, test, build) on push
- Must pass locally before pushing

### FR7: List/Kitchen Conceptual Reuse
- Membership model (kitchen_id, user_id, role as owner|member) is reused
- Access control patterns (non-members get 404, not 403) are reused
- Invite-by-email flow is reused
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

## Success Criteria

1. **Codebase Consistency**: All reused code from finance-dashboard is clearly documented with comments indicating origin and any adaptations
2. **Bootstrap Speed**: A developer can set up the Melos codebase for the first time in under 15 minutes using the reused patterns
3. **Pattern Adherence**: All new features follow the established patterns (hexagonal architecture, port/adapter, naming conventions) with no deviations without approval
4. **No Secrets Exposure**: No finance-dashboard credentials or Melos secrets appear in code, the repo, .env.example or documentation
5. **Test Suite Parity**: Test structure, tooling and patterns match those of finance-dashboard (pytest, vitest, same directory layout)
6. **Documentation Clarity**: The spec and README clearly explain which parts come from finance and which are Melos-specific

## Key Entities & Data Structures

**Reused Database Entities:**
- `user` (auth tables)
- `session` (auth)
- `password_reset_token` (auth)
- `email_verification` (auth)
- `preferences` (auth, for theme/locale)
- `kitchen` (replaces "list")
- `membership` (kitchen_id, user_id, role)
- `invite` (kitchen_id, email, token_hash)

**Melos-Specific Entities:**
- `ingredient`
- `category`
- `recipe`
- `recipe_ingredient`
- `step`
- `cart`
- `cart_item`
- `shopping_list`
- `shopping_list_item`
- `conversation`
- `message`
- `recipe_embedding`
- `source`

## Implementation Boundaries

### API Layer Separation (Hexagonal Architecture)
- **domain/**: Pure business logic (no I/O, no framework dependencies)
  - `recipe.py` (Unit, Size, Dimension, validation rules)
  - `cart.py` (scaling, consolidation)
  - `ingredient_catalog.py` (name normalization)
  - `toon.py` (object encoding for LLM prompts)
  - `render.py` (Markdown/embed text generation)
  - `kitchen.py`, `membership.py`, `invite.py` (reused from finance-dashboard)
- **application/**: Use cases and port definitions
  - `ports.py`: RecipeExtractor, Embedder, ChatModel, PageFetcher, PdfRenderer, repositories (abstractions for external services)
  - Use cases: `capture_recipe`, `recipes`, `ingredients`, `categories`, `carts`, `shopping_list`, `conversations`, `exports`, `kitchens`, `invites` + reused auth
  - All kitchen-scoped queries enforce membership checks here
- **adapters/**: Concrete implementations of ports
  - `llm/gemini.py` (Gemini API via google-genai SDK)
  - `web/page_fetcher.py`, `web/jsonld.py` (URL fetching with SSRF protection)
  - `pdf/weasyprint.py` + `templates/`, `fonts/` (PDF generation with Unicode fonts)
  - `persistence/` (SQLAlchemy, Alembic, pgvector)
  - `email/` (aiosmtplib — reused from finance)
- **api/**: FastAPI application layer
  - `main.py` (FastAPI app entry point)
  - `routes/` (HTTP endpoints):
    - `auth.*` (reused from finance-dashboard)
    - `kitchens.py`, `members.py`, `invites.py` (kitchen management)
    - `recipes.py`, `drafts.py` (recipe capture, CRUD)
    - `ingredients.py`, `categories.py` (catalog)
    - `carts.py`, `shopping_list.py` (cart and shopping list)
    - `conversations.py`, `messages.py` (chat)
    - `exports.py` (PDF/Markdown generation)
    - `health.py` (health check endpoint)
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
├── docker-compose.yml              # Reused (db, api, ui services; adapted: db image → pgvector, env prefix → MELOS_)
├── docker-compose.{dev,prod,test,worktree,worktree-lite}.yml  # All overlays reused
├── .env.example                    # Adapted: new Gemini vars, MELOS_ prefix, no finance credentials
├── .env                            # LOCAL ONLY (never committed) — copy from .env.example
├── api/
│   ├── pyproject.toml             # Reused structure; Gemini/pgvector libs added
│   ├── uv.lock                    # Locked dependencies (commit this, never edit by hand)
│   ├── Dockerfile, alembic.ini    # Reused
│   ├── domain/                    # Pure business logic (reused structure, Melos rules)
│   │   ├── recipe.py, cart.py, ingredient_catalog.py, toon.py, render.py
│   │   └── kitchen.py, membership.py, invite.py  # From finance-dashboard
│   ├── application/               # Use cases + ports (reused pattern)
│   │   ├── ports.py
│   │   └── use_cases/  # Melos-specific: capture_recipe, shopping_list, conversations
│   ├── adapters/
│   │   ├── llm/gemini.py          # NEW: Gemini integration
│   │   ├── web/                   # NEW: Page fetcher, JSON-LD
│   │   ├── pdf/                   # NEW: WeasyPrint renderer
│   │   ├── persistence/           # Reused: SQLAlchemy, Alembic, pgvector
│   │   ├── email/                 # Reused from finance: aiosmtplib
│   │   └── auth/                  # Reused from finance
│   ├── api/
│   │   ├── main.py               # FastAPI app setup
│   │   ├── routes/               # HTTP endpoints (auth: reused; rest: Melos-specific)
│   │   ├── schemas/              # Pydantic models (reused pattern)
│   │   ├── deps.py               # Dependency injection
│   │   └── settings.py           # Environment config
│   ├── tests/                    # pytest suite (reused structure)
│   └── scripts/                  # Seeding, migrations (reused pattern)
├── ui/
│   ├── package.json              # Reused; dependencies locked (npm install)
│   ├── Dockerfile, Dockerfile.dev # Reused
│   ├── app/                      # Next.js App Router structure (reused)
│   │   ├── layout.tsx            # Root layout (AppShell)
│   │   ├── api/                  # BFF routes (proxy /api/* to FastAPI)
│   │   └── [kitchen]/            # Kitchen-scoped pages (recipes, carts, conversations)
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
└── .specify/                     # Spec Kit configuration (planning)
    ├── specs/                   # Feature specifications (planning & tracking)
    ├── memory/constitution.md   # Project constitution (principles, boundaries)
    └── templates/               # Spec templates
```

## Configuration and Secrets (Reused Pattern)

**Environment Variables** (from finance-dashboard pattern, adapted for Melos):

| Category | Variables | Purpose |
|----------|-----------|---------|
| **Database** | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL credentials |
| **Session** | `SESSION_SECRET`, `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` | Session cookie config (httpOnly, Secure in prod, SameSite=Lax) |
| **Auth Rate Limits** | `AUTH_RATE_LIMIT_REGISTER_MAX`, `AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_SIGN_IN_MAX`, `AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_MAX`, `AUTH_RATE_LIMIT_VERIFY_REQUEST_MAX` | Rate limiting per IP and per user |
| **Email** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_STARTTLS`, `SMTP_TIMEOUT_SECONDS` | Outbound email via SMTP (fail loudly if misconfigured) |
| **App URLs** | `PUBLIC_APP_URL` | Where the app is reachable (for reset links, invites) |
| **Network** | `TRUSTED_PROXY_IPS`, `AUTH_CLIENT_IP_HEADER` | IP headers trusted from BFF (Compose: 172.16.0.0/12, localhost) |
| **Auth** | `EMAIL_VERIFICATION_REQUIRED` | Gate email verification on sign-up (default false) |
| **Storage** | `PDF_STORAGE_PATH`, `MELOS_DATA` | File storage locations (outside repo) |
| **Dev Seeds** | `SEED_DEV_USER`, `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD`, `SEED_DEV_USER_ALIAS`, `SEED_DEV_USER_KITCHEN` | Pre-verified test users with sample data (dev/worktree only) |
| **Gemini (Melos)** | `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`, `GEMINI_EMBED_DIM` | LLM configuration |

**Secrets Management** (strict reuse):
- `.env` file is **never committed** (in `.gitignore`)
- `.env.example` documents all variables with NO real values (e.g., `GEMINI_API_KEY=` empty)
- Local development: copy `.env.example` to `.env` and fill in actual values
- Production: secrets come from the server environment (e.g., systemd, Docker Compose secret files), never from the repo
- SMTP misconfiguration fails loudly (no silent email loss)

## Development Seeding (Test Data)

When `SEED_DEV_USER=1`, the API bootstrap script (`api/scripts/seed_dev_user.py`) creates:

**User Account:**
- Email: `$SEED_DEV_USER_EMAIL` (e.g., `dev@example.com`)
- Password: `$SEED_DEV_USER_PASSWORD` (pre-hashed, bypasses reset flow)
- Alias: `$SEED_DEV_USER_ALIAS` (display name)
- Email verified: `true` (if `EMAIL_VERIFICATION_REQUIRED=true`)

**Sample Kitchen:**
- Name: "Dev Kitchen" or `$SEED_DEV_USER_KITCHEN` (if specified)
- Content language: English (en)
- User is owner

**Sample Data (for immediate testing without manual data entry):**
- **Recipes**: 3–5 realistic recipes (e.g., pasta, curry, soup) with:
  - Title, base servings, categories
  - Ingredient lines with units (grams, cups, tbsp, units)
  - Step-by-step instructions
  - Source: marked as "dev seed" (not from a URL or upload)
- **Ingredients**: ~15 auto-created from recipe ingredients (normalized, lower-case, singular)
- **Categories**: ~8 auto-created from recipes (produce, grains, proteins, etc.)
- **Cart**: Pre-populated with 2 recipes at different meal counts (1 meal each) for 2 people
- **Shopping List**: One archived/finalized shopping list (closing_date set) with items from past recipes, for testing chat history queries
- **Conversation**: One conversation with 4–6 messages testing:
  - Simple question answered by recipes
  - Question not covered by recipes (found=false)
  - Citation of specific recipes
  - Shopping list history query

**Purpose:** Developers can sign in and immediately see the UI with realistic data, test cart consolidation, run chat queries, and verify PDF/Markdown export without manual setup.

**Note:** Seeding is **dev/worktree only**. Production (`SEED_DEV_USER=0`) never auto-creates test users.

## Assumptions

1. **Source of truth**: Finance-dashboard is the authoritative source for auth, UI patterns and deploy structure
2. **Versions fixed at start**: Python 3.12, Node versions specified in `.python-version` and `package.json` are locked for reproducibility
3. **Email delivery**: SMTP must be configured (fail loudly if not); there is no local mock for outbound mail
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
