# Configuration Contract (env, Compose names, ports, client keys)

**Status:** Bootstrap contract (D1–D3, D5).
**Scope:** The names that operators, scripts and worktrees depend on. Values are never committed. `.env.example` holds placeholders or invented values only (constitution §4).

## Renamed from finance-dashboard

| finance-dashboard | Melos | Where it appears |
|-------------------|-------|------------------|
| `FH_COMPOSE_NAME` (default `finance-helper`) | `MELOS_COMPOSE_NAME` (default `melos`) | `docker-compose.yml` `name:`, `scripts/compose-lib.sh`, `compose-up.sh`, `scripts/worktree/*` |
| `FINANCE_HELPER_DATA` (default `$HOME/finance-helper`) | `MELOS_DATA` (default `$HOME/melos`) | `docker-compose.yml` pgdata/pdfs binds, `compose-wipe-db.sh`, `compose-down.sh`, `.env.example` |
| worktree data `~/finance-helper-wt/<name>` | `~/melos-wt/<name>` | `scripts/worktree/setup-worktree-unix.sh`, `worktree-remove.sh`, README |
| worktree compose names `fh-<slug>` | `melos-<slug>` | worktree setup + detection in `compose-up.sh` |
| cookie `fh_session` | `melos_session` | `.env.example`, Compose default, the `api/api/settings.py` fallback, ui `proxy.ts` and `app/api/auth/sign-out/route.ts` defaults, api/ui tests |
| header `X-FH-Client-IP` | `X-Melos-Client-IP` | `.env.example`, Compose defaults (base + prod), `api/api/settings.py` fallback, `ui/lib/authBff.ts`, api/ui tests |
| database `finance_helper` (user `finance`) | `melos` | `.env.example`, `.github/workflows/ci.yml` |
| worktree checkouts `../finance-dashboard-wt-<slug>` | `../melos-wt-<slug>` | `scripts/worktree/*` |
| UI title "Finance Helper" | "Melos" | `ui/app/sign-in/SignInChrome.tsx`, `ui/components/AppShell.test.tsx` |
| localStorage/cookie `fh_theme_cache` | `melos_theme_cache` | `ui/components/PreferencesProvider.tsx` |
| localStorage/cookie `fh_lang_cache` | `melos_lang_cache` (read-only; locale is always `en`) | `PreferencesProvider.tsx`, `app/home/page.tsx`, `app/kitchens/[kitchenId]/page.tsx` |

**Invariant (spec FR1.1):** after the bootstrap, `git grep -nE 'FH_|fh_|fh-|X-FH-|FINANCE_HELPER|finance[-_]helper|Finance Helper'` outside `specs/`, `dev/` and `node_modules/` returns no matches. There are **no exceptions**: the auth layer and `settings.py` are renamed too (owner decision 2026-10-19). Comments and docs may still name finance-dashboard as the source.

## Environment variables

The variables in spec §"Configuration and Secrets" keep their names (`POSTGRES_*`, `SESSION_*`, `AUTH_RATE_LIMIT_*`, `SMTP_*`, `PUBLIC_APP_URL`, `TRUSTED_PROXY_IPS`, `AUTH_CLIENT_IP_HEADER`, `EMAIL_VERIFICATION_REQUIRED`, `PDF_STORAGE_PATH`, `SEED_DEV_USER*`). Melos adds:

| Variable | Required | Default | Consumed by (bootstrap) |
|----------|----------|---------|-------------------------|
| `MELOS_COMPOSE_NAME` | no | `melos` | Compose, scripts |
| `MELOS_DATA` | no (must not be set to an empty value) | `$HOME/melos` | Compose binds, scripts |
| `API_HOST_PORT` / `UI_HOST_PORT` / `MCP_HOST_PORT` | no | `8000` / `3000` / `9000` | Compose ports, worktrees |
| `GEMINI_API_KEY` | yes once AI features land | empty | passed through only (D5) |
| `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL` | yes once AI features land | set in `.env`, never hard-coded in code | passed through only |
| `GEMINI_EMBED_DIM` | no | `768` | passed through only |

**Rules:**
- Model names live only in `.env` and the Compose defaults, never in Python or TypeScript (constitution §2).
- `.env` is git-ignored. `.env.example` contains no real email addresses, passwords or keys.
- A dev seed runs only when `SEED_DEV_USER` is truthy. `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD`, `SEED_DEV_MEMBER_EMAIL` and `SEED_DEV_MEMBER_PASSWORD` are required then, with no silent defaults. `SEED_DEV_USER_ALIAS`, `SEED_DEV_MEMBER_ALIAS` and `SEED_DEV_USER_KITCHEN` (default "Dev Kitchen") are optional. Production sets `SEED_DEV_USER=0`.
- No Compose file has a top-level `version:` key, and no Docker configuration requires a version field.

## Ports (dev)

| Service | Container | Host |
|---------|-----------|------|
| ui | 3000 | `${UI_HOST_PORT:-3000}` |
| api | 8000 | `${API_HOST_PORT:-8000}` |
| mcp | 9000 | `${MCP_HOST_PORT:-9000}` |
| db | 5432 | not published in the base file |

Production: the owner's nginx forwards to `ui` and to `mcp` (`/mcp`). Proxy and TLS config stay outside the repo (constitution §7).
