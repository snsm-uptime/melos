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

---

**Next Phase:** Proceed to Phase 1 design (data-model.md, contracts, quickstart.md)
