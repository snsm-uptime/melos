# Finance-Dashboard Reuse Integration — Research & Decisions

**Status:** Closed — No outstanding unknowns  
**Date:** 2026-10-19

## Resolved Decisions

### Database Versioning & pgvector
- **Decision:** Use PostgreSQL 16 with pgvector extension (upgrade from finance-dashboard base image)
- **Rationale:** pgvector is required for recipe embedding and semantic search. v16 is the latest stable LTS release.
- **Alternatives considered:** Using a separate vector database (Pinecone, Weaviate); rejected due to operational complexity and MELOS_DATA requirement to keep data local
- **Status:** ✓ Confirmed in FR2 (pgvector/pgvector:pg16 image)

### Environment Prefix Strategy
- **Superseded (2026-10-19):** every `fh_`/`FH_` name in code is renamed, auth files included (spec FR1.1). The original decision follows for history.
- **Decision:** Rename environment variables from `FH_` to `MELOS_` via `.env` and `api/settings.py`, not file-level find-replace
- **Rationale:** Centralizing configuration in settings.py avoids editing dozens of auth files and prevents prefix-related bugs
- **Alternatives considered:** Naive find-replace of `FH_` → `MELOS_` in all auth files; rejected due to maintenance risk
- **Status:** ✓ Confirmed in FR5.3 with detailed examples of what NOT to do

### Frontend Language Support
- **Decision:** English-only UI (remove language toggle from finance-dashboard)
- **Rationale:** Melos v1 MVP does not require multi-language support. Simplifies PreferencesProvider and AccountMenu
- **Alternatives considered:** Keep language toggle disabled but present; rejected as technical debt with no user value
- **Status:** ✓ Confirmed in FR5.2 with specific adaptations to PreferencesProvider, AccountMenu, app/account/page

### Auth Layer Immutability
- **Decision:** Copy auth layer as-is; no modifications without explicit written pre-approval
- **Rationale:** Auth is security-critical. Minimizing changes reduces risk and leverages tested finance-dashboard patterns
- **Alternatives considered:** Adapting auth for Melos-specific features (e.g., kitchen ownership checks at auth layer); rejected per FR5.3 permit/prohibit list
- **Status:** ✓ Established in FR5.3 with explicit pre-approval requirement and common-mistakes guidance

### MCP Service Deployment
- **Decision:** MCP runs as a fourth container (port 9000) in all Compose configurations (dev, test, prod)
- **Rationale:** Isolation from API improves security; local testing requires MCP available
- **Alternatives considered:** MCP runs only in production; rejected due to dev/test integration requirement (Q5)
- **Status:** ✓ Confirmed in FR2 and clarification Q5

### Development Seeding Strategy
- **Superseded by D7 (2026-10-19):** the seed is two users (owner, member) and one shared kitchen only. The original decision follows for history.
- **Decision:** Pre-seed test user, kitchen, recipes, and conversation history when `SEED_DEV_USER=1`
- **Rationale:** Developers can immediately test UI without manual data entry; supports quick iteration
- **Alternatives considered:** Manual seeding steps in README; rejected due to friction and inconsistency
- **Status:** ✓ Detailed in "Development Seeding (Test Data)" section with exact sample data structure

### Database Migrations
- **Decision:** API entrypoint auto-runs `alembic upgrade head` on container start (reused from finance-dashboard)
- **Rationale:** No manual migration steps required; idempotent and self-healing
- **Alternatives considered:** Requiring developers to run migrations manually; rejected due to setup friction
- **Status:** ✓ Confirmed in FR6.5 and clarification Q4

## Unresolved Clarifications (None)

All clarifications from sessions 2026-10-19 are integrated into the spec. No outstanding questions remain.

## Dependencies & Integrations

### External Dependencies (Confirmed)
- **Google Gemini API** (FR4): google-genai SDK, model/embedding configuration via environment
- **PostgreSQL 16 + pgvector**: Host volume at `$MELOS_DATA/pgdata`
- **Finance-dashboard repository**: Source of truth for auth, UI patterns, Dockerfiles, scripts

### Known Risks & Mitigations
1. **Risk:** Auth layer bugs break the entire app (security and UX)
   - **Mitigation:** Pre-approval requirement in FR5.3; copy as-is, zero modifications
2. **Risk:** Manual copy of 50+ auth files introduces typos or missed updates
   - **Mitigation:** Detailed file inventory in FR5.1; checklist in Appendix A; verify with tests
3. **Risk:** Environment variable confusion (FH_ vs MELOS_ vs no prefix)
   - **Mitigation:** Detailed explanation in FR5.3 with before/after examples; centralized in settings.py
4. **Risk:** pgvector version incompatibility with Alembic migrations
   - **Mitigation:** Test full migration suite in Compose before deployment; verify in CI

## Decision Record Summary

| Area | Decision | Confidence | Review Date |
|------|----------|-----------|-------------|
| Database (pgvector) | pg16 + pgvector extension | ✓ High | 2026-10-19 |
| Config (env vars) | Centralized in settings.py, no file-level find-replace | ✓ High | 2026-10-19 |
| Frontend (language) | English-only, remove toggle | ✓ High | 2026-10-19 |
| Auth (copying) | As-is, pre-approval for changes | ✓ High | 2026-10-19 |
| MCP (deployment) | Fourth container in all Compose configurations | ✓ High | 2026-10-19 |
| Dev seeding | Pre-populate test data with SEED_DEV_USER | ✓ High | 2026-10-19 |
| Migrations | Auto-run alembic upgrade head on container start | ✓ High | 2026-10-19 |

## Plan-Phase Decisions (2026-10-19, `/speckit-plan`)

These come from checking the current code against the spec while planning. Each closes a gap; none changes the spec's intent.

### D1 · Finish the finance-dashboard → Melos rename
- **Decision:** `FH_COMPOSE_NAME` → `MELOS_COMPOSE_NAME` (default `melos`), `FINANCE_HELPER_DATA` → `MELOS_DATA` (default `$HOME/melos`), worktree data `~/finance-helper-wt/` → `~/melos-wt/`, worktree compose names `fh-*` → `melos-*`. This applies to `docker-compose.yml`, `.env.example`, `scripts/compose-*.sh`, `scripts/compose-lib.sh` and `scripts/worktree/*`.
- **Rationale:** FR1, FR2 and FR3 call for the `MELOS_` prefix and `~/melos`. Compose currently still binds `${FINANCE_HELPER_DATA:-$HOME/finance-helper}/pgdata`, which breaks constitution §7 ("data lives under `MELOS_DATA`").
- **Alternatives considered:** Keep the finance names and document them. Rejected because it contradicts FR1, FR2 and AGENTS.md and makes two stacks on one host collide by name.
- **Migration note:** existing local `.env` files must rename the two keys. The quickstart covers this.

### D2 · Session cookie and client-IP header names
- **Decision (revised 2026-10-19):** `melos_session` and `X-Melos-Client-IP` everywhere: `.env.example`, Compose defaults, the fallbacks in `api/api/settings.py`, ui defaults (`proxy.ts`, `sign-out/route.ts`, `authBff.ts`) and all tests. Only the names change; cookie flags, lifetime and auth logic do not.
- **Rationale:** PRD §1.2 lists "cookie `melos_session`" as the allowed adaptation to auth. The owner then ruled that no `fh` name may remain in code (spec FR1.1), which approves the `settings.py` edit.
- **Superseded alternative:** Keep the `fh_session` fallback in `settings.py` as an exception. Withdrawn by the owner.

### D3 · UI keys and English-only locale
- **Decision:** localStorage and cookie keys `fh_theme_cache`/`fh_lang_cache` → `melos_theme_cache`/`melos_lang_cache`. Remove `setLanguage` and the language selector, and fix the locale to `en`. This includes the server pages that read `fh_lang_cache` (`app/home/page.tsx`, `app/kitchens/[kitchenId]/page.tsx`).
- **Rationale:** FR5.2 and FR6. Tasks T021–T023 are still open.

### D4 · Bootstrap schema scope
- **Decision:** Add Alembic revision `0002_pgvector_kitchen_lang`: `CREATE EXTENSION IF NOT EXISTS vector` and `kitchens.content_language VARCHAR(2) NOT NULL DEFAULT 'en'` with a check constraint for `en`/`es`. The recipe, catalog, cart, shopping-list, conversation and embedding tables are each created by the feature spec that owns them.
- **Rationale:** The PRD v0 milestone is "scaffold, auth, kitchens, health checks". The kitchen entity in PRD §1.6 includes `content_language`, and J1 needs it. Enabling the extension now proves the pgvector image works (FR2) before any embedding code depends on it.
- **Alternatives considered:** One migration with all 21 tables, as worded in T044. Rejected because it builds future features without specs. The approved squash and prune on 19/10 already narrowed the baseline to auth and kitchens.

### D5 · Gemini configuration is passed through only
- **Decision:** The bootstrap only defines `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL` and `GEMINI_EMBED_DIM=768` in `.env.example` and Compose. No SDK and no adapter yet.
- **Rationale:** PRD Appendix D leaves the exact models open until implementation. The capture feature checks that the embedding model supports 768 dimensions.

### D6 · One health contract
- **Decision:** `GET /health` → `200 {"status":"healthy","service":"<api|ui|mcp>","timestamp":"<ISO-8601 UTC>"}` on all three services. This is a liveness check only; a DB readiness check is not part of the bootstrap. Update `api/tests/test_health.py`, which still expects finance's `{"status":"ok"}`.
- **Rationale:** The current code returns three different shapes and the reused test fails. A single shape makes Compose healthchecks and grading-day checks (§7) easy to rely on.
- **Alternatives considered:** Go back to finance's `{"status":"ok"}`. Rejected because `contracts/error-responses.md` already published the `healthy` shape.

### D7 · Staged dev seed

- **Revised 2026-10-19 (owner):** seed exactly two verified users, an owner (`SEED_DEV_USER_*`) and a member (`SEED_DEV_MEMBER_*`). They share one kitchen (`SEED_DEV_USER_KITCHEN`, default "Dev Kitchen"), and sign-up gives each user a personal "My kitchen". Nothing else is seeded. Real credentials live only in the local `.env`. The original text follows.

- **Decision:** `seed_dev_user.py` seeds the verified user, alias, "My kitchen" and the optional extra kitchen. Each later feature adds its own sample data (recipes, cart, finalized list, conversation) to the seed in the same PR that creates its tables.
- **Rationale:** You can't seed tables that don't exist yet. The script's docstring already says this.

### Additional risk
5. **Risk:** finance-looking seed credentials are still in git history from the bootstrap commit.
   - **Mitigation:** Rotate them if they were real. Rewriting history needs explicit approval (constitution §8).

---

**Next Phase:** Proceed to Phase 1 design (data-model.md, contracts, quickstart.md)
