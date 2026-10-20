# Implementation Plan: Finance-Dashboard Reuse Integration (Bootstrap)

**Branch**: `implementation/001-bootstrap` (feature dir `001-finance-dashboard-reuse`) | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-finance-dashboard-reuse/spec.md`, with product context from `dev/docs/prd.md` (§1.1–1.3, §1.9, Appendix C "v0 by 20/10").

## Summary

Bootstrap Melos on the `snsm-uptime/finance-dashboard` architecture: copy its hexagonal FastAPI `api/`, Next.js `ui/` BFF, Compose overlays, scripts, CI and the auth layer unchanged; rename "list" to **kitchen**; swap the db image to `pgvector/pgvector:pg16`; add a fourth, isolated `mcp` service; and finish the rename from finance-dashboard names (`FH_*`, `FINANCE_HELPER_DATA`, `finance-helper`, `fh_*`) to Melos names (`MELOS_*`, `MELOS_DATA`, `melos`, `melos_*`).

The bulk copy, squash and prune are already in the repo (baseline migration `0001_melos_baseline`, kitchens API + BFF, auth tests). This plan covers what is still needed for the PRD's v0 milestone: **scaffold, auth, kitchens, health checks**, with every service healthy and the spec's adaptations finished. Recipe, cart, shopping-list, conversation and MCP-tool work is **not** in this plan. Each of those comes later as its own feature spec (spec "Notes → Future Feature Specifications").

## Technical Context

**Language/Version**: Python 3.12 (`api/`, `mcp/`, managed by `uv`), TypeScript 5 / Node per `.node-version` (`ui/`)

**Primary Dependencies**: FastAPI 0.141.1, Uvicorn 0.52.1, SQLAlchemy 2.0.51, Alembic 1.18.5, psycopg 3.3.4, Pydantic 2.13.4, argon2-cffi 25.1.0, aiosmtplib 5.1.2 · Next.js 16.2.12, React 19.2.4, Tailwind 4.3.3, Vitest 4.1.10, ESLint 9 (spec FR4)

**Storage**: PostgreSQL 16 with the pgvector extension (`pgvector/pgvector:pg16`). Data is bind-mounted at `${MELOS_DATA:-$HOME/melos}/pgdata`, outside the repo.

**Testing**: pytest (domain, application with fake ports, integration against real Postgres via `docker-compose.test.yml`), vitest (jsdom) for ui, ruff, eslint, `tsc`

**Target Platform**: Linux containers via Docker Compose v2. Dev runs on the developer's machine (WSL2/macOS/Linux); prod runs on the owner's server (`docker-compose.yml` + `docker-compose.prod.yml`).

**Project Type**: Web application. Python API, Next.js BFF UI and a separate Python MCP service.

**Performance Goals**: Not a bootstrap concern. The only timing goal is SC-2: first-time setup in under 15 minutes, and all four services healthy within about 30 s of `compose-up.sh -d`.

**Constraints**: Auth layer is unchanged (FR5.3 off-limits list). Exactly four services (constitution §1). `domain/` stays pure (§3). No secrets in the repo (§4). No reverse proxy or TLS in the repo (§7).

**Scale/Scope**: One household-scale app (a couple per kitchen). Bootstrap scope is 4 services, about 16 auth files on the api side and about 35 on the ui side, 6 Compose files and about 10 scripts.

No `NEEDS CLARIFICATION` items remain. The open PRD item "exact Gemini models" (Appendix D) does not block this plan: the bootstrap only passes the `GEMINI_*` variables through, and the capture feature chooses the models (see [research.md](research.md) §Plan-phase decisions, D5).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

| # | Principle | Gate for this feature | Status |
|---|-----------|-----------------------|--------|
| 1 | Simplicity and Reuse | Architecture, auth and tooling copied from finance-dashboard. Exactly `db`, `api`, `ui`, `mcp`. No queue or worker | ✅ Pass. Compose has exactly four services |
| 2 | Tech Stack Stability | Python 3.12 + `uv` only. Next 16 / React 19 / Tailwind 4. Gemini only via `google-genai`. Model names come from env | ✅ Pass. `GEMINI_*` are env-only, and no SDK is imported yet |
| 3 | Hexagonal Architecture | `domain/` imports no adapters, FastAPI, SQLAlchemy or SDK code. Kitchen membership checks in `application/` return 404 | ✅ Pass. `application/kitchen_access.py` enforces 404. Verified by the existing integration tests |
| 4 | Security and Privacy | No secrets or real personal data in the repo | ⚠️ Pass with a follow-up. `.env.example` now has invented values, but finance-looking seed credentials remain in git history (memory 19/10 12:51). The owner must rotate them if they were real. No history rewrite without approval (§8) |
| 5 | No AI Shortcuts | — | N/A. There are no AI flows in the bootstrap |
| 6 | Testing and Quality | Integration tests hit real Postgres. Tests pass in the Compose test overlay | ⚠️ Gate open. `test_health` currently fails because the test expects `{"status":"ok"}` and the route returns `"healthy"`. Resolved by [contracts/health.md](contracts/health.md) |
| 7 | Deployment and Operations | Compose-only dev. `/health` on ui, api and mcp. Data under `MELOS_DATA` | ⚠️ Gate open. Compose still binds `FINANCE_HELPER_DATA:-$HOME/finance-helper`. Resolved by the naming decision D1 |
| 8 | Code Review and Git Discipline | Schema changes go through Alembic. No push without review | ✅ Pass. Baseline migration plus new revision `0002` |
| 9 | Product Scope and Schedule | Only v0 Must items: scaffold, auth, kitchens, health | ✅ Pass. Feature tables, MCP tools and Should items are explicitly out of scope |

**Result:** No unjustified violations. The two open gates (⚠️) are implementation gaps, not design conflicts. Phase 1 resolves them and the re-check is below.

## Project Structure

### Documentation (this feature)

```text
specs/001-finance-dashboard-reuse/
├── spec.md               # Feature spec (input)
├── plan.md               # This file
├── research.md           # Phase 0: decisions (existing + plan-phase decisions D1–D7)
├── data-model.md         # Phase 1: bootstrap-owned tables + deferred entity map
├── quickstart.md         # Phase 1: setup + validation run guide
├── contracts/
│   ├── auth-api.md               # Reused /auth/* contract (existing)
│   ├── kitchen-membership-api.md # /kitchens, members, invites (existing)
│   ├── error-responses.md        # Error envelope + domain error mapping (existing)
│   ├── health.md                 # NEW: /health on api, ui, mcp (supersedes error-responses §Health)
│   └── configuration.md          # NEW: env vars, Compose names, ports, cookie/storage keys
├── reuse-inventory.md    # Copy / adapt / new inventory (existing)
├── analysis.md           # /speckit-analyze report (existing)
├── checklists/requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks; already present)
```

### Source Code (repository root)

These paths exist now, except the ones marked ➕, which this plan adds.

```text
docker-compose.yml                 # db (pgvector) | api | ui | mcp; name: ${MELOS_COMPOSE_NAME:-melos}
docker-compose.{dev,prod,test,worktree,worktree-lite}.yml
.env.example                       # MELOS_* names, invented values only
scripts/
├── compose-{up,down,restart,wipe-db}.sh, compose-lib.sh
└── worktree/ (worktree-add.sh, setup-worktree-unix.sh, worktree-remove.sh, README.md)

api/
├── domain/          # alias, email_verification, errors, kitchen_access, kitchen_invite,
│                    # kitchens, password_reset, photo, preferences, signup  (pure)
├── application/     # ports.py, kitchens, kitchen_access, kitchen_invite(_accept),
│                    # signup, signin, password_reset, email_verification, preferences, rate_limit
├── adapters/
│   ├── email/       # smtp.py, settings.py (reused)
│   └── persistence/ # models, repositories, sessions, password_*, kitchen_invite, db, base
│       └── migrations/versions/
│           ├── 0001_melos_baseline.py
│           └── ➕ 0002_pgvector_and_kitchen_language.py
├── api/             # app.py, deps.py, settings.py, routes/{auth,kitchens,invites,health}.py, schemas/
├── scripts/         # entrypoint.py (alembic upgrade head → seed → uvicorn), seed_dev_user.py
└── tests/           # domain/application/integration tests (reused + kitchen)

mcp/
├── Dockerfile, pyproject.toml, ➕ uv.lock, ➕ .python-version
├── server/main.py   # FastAPI app: /health only in bootstrap
└── tools/           # empty package; tools arrive with the MCP feature spec

ui/
├── app/             # sign-in, sign-up, forgot-password, reset-password, verify, account,
│                    # invites, kitchens/[kitchenId], home, health/route.ts, api/* (BFF)
├── components/      # AppShell, AccountMenu, PreferencesProvider, ActionDialog, Chip, ChipPicker,
│                    # IconButton, Disclosure, CopyButton, … (reused)
└── lib/             # session.ts, authBff.ts, … (restored from finance-dashboard@main)
```

**Structure Decision**: Web application with three code roots (`api/`, `ui/`, `mcp/`) plus Compose and scripts at the repo root, matching AGENTS.md "Project structure". In the api, the FastAPI package is `api/api/` (`app.py`, `routes/`, `schemas/`, `deps.py`, `settings.py`), as in finance-dashboard. Paths written as `api/routes/…` in the spec mean `api/api/routes/…`. No new top-level folders.

## Phase 0: Research (complete)

[research.md](research.md) already records the spec-level decisions (pgvector, prefix strategy, English-only UI, auth immutability, MCP in every overlay, seeding, auto-migrations). Planning added **D1–D7** for the gaps found in the current code:

| ID | Decision (summary) |
|----|--------------------|
| D1 | Finish the rename: `FH_COMPOSE_NAME`→`MELOS_COMPOSE_NAME`, `FINANCE_HELPER_DATA`→`MELOS_DATA`, default project/data name `finance-helper`→`melos`, worktree data under `~/melos-wt/` |
| D2 | Session cookie `melos_session` and header `X-Melos-Client-IP` everywhere: `.env.example`, Compose defaults, the `settings.py` fallbacks, ui defaults and tests. The rename was approved 2026-10-19 (spec FR1.1); the auth logic is not changed |
| D3 | UI storage and cookie keys `fh_theme_cache`/`fh_lang_cache` → `melos_theme_cache`/`melos_lang_cache`. Language toggle removed, locale fixed to `en` |
| D4 | Schema: add revision `0002` that enables the `vector` extension and adds `kitchens.content_language` (`en`/`es`, default `en`). Recipe, cart and chat tables are added by their own feature specs |
| D5 | Gemini variables are passed through only. Model choice is deferred to the capture feature (PRD App. D) |
| D6 | One `/health` contract for all three services: `200 {"status":"healthy", …}`. The stale `test_health` assertion is updated to match |
| D7 | Dev seed: exactly two verified users (owner, member) sharing one kitchen. Nothing else. Later features decide whether to extend the seed once their tables exist |

## Phase 1: Design & Contracts (complete)

- **[data-model.md](data-model.md)**: tables this feature owns (auth + kitchens), the `0002` revision, validation rules, and a map of each deferred PRD entity to the feature that owns it.
- **[contracts/health.md](contracts/health.md)**: `/health` for api, ui and mcp, and the Compose healthcheck probes.
- **[contracts/configuration.md](contracts/configuration.md)**: the environment and naming interface (env vars, Compose project name, ports, data paths, cookie/storage keys) and which finance-dashboard names it replaces.
- Unchanged and still valid: [auth-api.md](contracts/auth-api.md), [kitchen-membership-api.md](contracts/kitchen-membership-api.md), [error-responses.md](contracts/error-responses.md). Its §Health is superseded by `health.md`.
- **[quickstart.md](quickstart.md)**: an appended "Bootstrap acceptance checks" section with runnable checks for D1–D7.

### Implementation outline (input for `/speckit-tasks` / `/speckit-converge`)

1. **Naming (D1, D2, spec FR1.1):** update `docker-compose.yml` (`name:`, pgdata/pdfs sources, `SESSION_COOKIE_NAME` and `AUTH_CLIENT_IP_HEADER` defaults), `docker-compose.prod.yml`, `.env.example` (incl. DB name `melos`), `.github/workflows/ci.yml` (DB name, PDF path), `scripts/compose-lib.sh`, `compose-{up,down,restart,wipe-db}.sh`, `scripts/worktree/*` and `scripts/README.md`. Rename the `fh_session`/`X-FH-Client-IP` fallbacks in `api/api/settings.py`, `ui/proxy.ts`, `ui/app/api/auth/sign-out/route.ts`, `ui/lib/authBff.ts`, the "Finance Helper" title, and every api/ui test fixture. Done when quickstart A1 returns nothing.
1a. **Dev seed (D7):** extend `seed_dev_user.py` to create the member user (`SEED_DEV_MEMBER_*`) and one shared kitchen (`SEED_DEV_USER_KITCHEN`, default "Dev Kitchen") with owner and member memberships. Add the new variables to `docker-compose.yml` and `.env.example` (placeholders only).
2. **UI adaptations (D3, FR5.2):** update `PreferencesProvider.tsx` (keys, no `setLanguage`, `en` only), `AccountMenu.tsx` (no language selector), `app/account/page.tsx` (no language section), `app/home/page.tsx` and `app/kitchens/[kitchenId]/page.tsx` (cookie key), and the tests they affect.
3. **Schema (D4):** add `0002_pgvector_and_kitchen_language.py`. Add `content_language` to the SQLAlchemy model, the kitchen domain value set and the kitchens schema/routes (create and rename take an optional `content_language`).
4. **Health (D6):** align `api/api/routes/health.py`, `ui/app/health/route.ts` and `mcp/server/main.py` with the contract (timezone-aware UTC). Update `api/tests/test_health.py` and add one mcp health test.
5. **MCP packaging:** add `mcp/uv.lock` and `.python-version` (uv only), and make sure the image installs from the lock file.
6. **Verification (existing tasks T050–T089b):** run the Compose stack, auth flow, lint, tests and secret scan, following the quickstart.

### Constitution re-check (post-design)

| Gate | Result |
|------|--------|
| §4 Security | ✅ The configuration contract allows only placeholders in `.env.example`. Rotating credentials found in git history is an owner action, logged as a risk |
| §6 Testing | ✅ D6 sets one health contract that the tests assert. The new `0002` migration is covered by the existing Compose integration run |
| §7 Deployment | ✅ D1 binds data to `MELOS_DATA`. `/health` is defined for all three services |
| §1 / §3 | ✅ No new services, layers or libraries. `content_language` validation lives in `domain/kitchens.py` |
| FR5.3 auth boundary | ✅ D2 renames the cookie and header *names* only (approved 2026-10-19), which is the PRD §1.2 "names only" adaptation. Cookie flags, hashing, rate limits, auth schema and endpoints are not touched |

## Complexity Tracking

No constitution violations need justification. There are no open deviations from the spec. After the plan review on 2026-10-19 (checklist `checklists/bootstrap.md`), the spec was updated to match the plan:

- The dev seed is two users and one shared kitchen (spec "Development Seeding", D7).
- The bootstrap owns only the auth and kitchen tables (spec "Key Entities", D4).
- The `fh_session` fallback exception was withdrawn. `settings.py` is renamed like every other file (spec FR1.1).
