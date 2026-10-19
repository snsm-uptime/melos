# Specification Analysis Report: Finance-Dashboard Reuse Integration

**Analysis Date:** 2026-10-19  
**Artifacts Analyzed:** spec.md, tasks.md, reuse-inventory.md, research.md, quickstart.md, constitution.md

---

## Findings Summary

| Severity | Count | Impact |
|----------|-------|--------|
| **CRITICAL** | 1 | Blocks implementation decision |
| **HIGH** | 2 | Significant gap or conflict |
| **MEDIUM** | 9 | Should be resolved before implementation |
| **LOW** | 3 | Nice-to-have improvements |
| **TOTAL** | **15** | 1 action-blocking |

---

## Critical Issues

### A1: Auth Layer Modification Ambiguity

**Severity:** CRITICAL  
**Location:** spec.md FR5, FR5.1 vs tasks.md T017  
**Issue:**

- **spec.md FR5.1 instruction #3**: "Copy `api/deps.py`, `api/settings.py`, and `api/app.py` as-is (they contain auth logic mixed with other setup)"
- **spec.md FR5.1 instruction #7**: "Config differences (e.g., `FH_` → `MELOS_` prefix) are handled via `.env` and `api/settings.py` environment variable loading"
- **spec.md footnote**: "Settings class attributes like `session_secret`, `auth_rate_limit_register_max` are already prefix-agnostic"
- **tasks.md T017**: "Update `api/settings.py` ONLY to load Melos environment variables"

**Conflict:** Does T017 violate the "no modifications" rule? Or does spec.md mean settings.py is updated but only for loading (not modifying auth logic)?

**Recommendation:**
- **Clarify in spec.md**: Add a note that "settings.py CAN be updated ONLY in the environment variable loading section (top-level Settings class), not in auth-specific logic"
- **Update T017 description**: "Ensure settings.py loads Melos environment variables in the Settings class initialization (verify: SESSION_SECRET, AUTH_RATE_LIMIT_*, GEMINI_*, etc. are loaded; use `os.getenv()` calls that already exist from finance-dashboard source)"

**Priority:** Resolve before implementation begins. This blocks developer approval.

---

## High-Priority Issues

### H1: Database Migration Schema Underspecified

**Severity:** HIGH  
**Location:** tasks.md T044  
**Issue:**

Task T044 says: "Create initial Alembic migration (if not present): `api/alembic/versions/001_initial_schema.py` (reused auth tables: user, session, password_reset_token, email_verification, preferences; reused kitchen tables: kitchen, membership, invite)"

**Missing:** The task describes WHAT tables should exist but doesn't specify:
- Field definitions for 13 Melos-specific tables (ingredient, category, recipe, recipe_ingredient, step, cart, cart_item, shopping_list, shopping_list_item, conversation, message, recipe_embedding, source)
- Table structure per spec.md Key Entities & Data Structures (line 384–409)
- Alembic SQL generation syntax
- pgvector extension setup (covered in T045, but should reference)

**Recommendation:**
- Update T044 to reference data-model.md or spec.md section for field-level schema definitions
- Add new task T044.1: "Document initial migration schema (field names, types, constraints, indices) in separate migration spec document before writing T044"
- Or expand T044 description: "Define schema for: [list all 21 tables with key fields from spec.md Key Entities]"

**Priority:** HIGH – Migration code quality depends on this clarity.

---

### H2: Settings.py Modification Scope Conflict

**Severity:** HIGH  
**Location:** spec.md vs tasks.md vs constitution.md  
**Issue:**

- **Constitution Principle 1**: "Auth layer is immutable: no changes without explicit approval"
- **spec.md**: "Do not customize any of these files" (referring to auth layer, including settings.py)
- **spec.md FR5.1 instruction #3**: Copy settings.py "as-is"
- **tasks.md T017**: "Update `api/settings.py` ONLY..."

**Conflict:** T017 may be the only permitted update. But "update" contradicts "as-is" and "immutable."

**Recommendation:**
- Treat T017 as verifying/validating settings.py, not modifying it
- Change T017 wording to: "Verify `api/settings.py` loads all required environment variables (SESSION_SECRET, SESSION_COOKIE_*, AUTH_RATE_LIMIT_*, TRUSTED_PROXY_IPS, AUTH_CLIENT_IP_HEADER, GEMINI_API_KEY, etc.); settings.py is copied as-is from finance-dashboard"
- If modifications ARE needed (e.g., to add GEMINI_ variables), create a new task T017a: "If settings.py lacks GEMINI_ variable loading, add them to the Settings class `__init__` method (pre-approval from Sebastián required per FR5.3)"

**Priority:** HIGH – Affects auth layer immutability commitment (constitution Principle 1).

---

## Medium-Priority Issues

### M1: Documentation Clarity Success Criterion (SC1) Not Measurable

**Severity:** MEDIUM  
**Location:** spec.md line 377  
**Issue:**

Success Criterion 1: "All reused code from finance-dashboard is **clearly documented with comments** indicating origin and any adaptations"

- "Clearly" is vague
- No task explicitly validates comment presence or quality
- No metric for documentation coverage

**Recommendation:**
- Add task T090 (Phase 5): "Audit all copied auth files for 'Finance-dashboard reuse' comments; ensure every reused file has a header comment: '// Reused from finance-dashboard/<path> without modification' or '// Adapted from finance-dashboard/<path>: <specific adaptation>'"
- Define "clear" as: "Every file from finance-dashboard has a header comment indicating origin and any adaptations"

---

### M2: Development Seeding Script Implementation Not Tasked

**Severity:** MEDIUM  
**Location:** spec.md "Development Seeding" section vs tasks.md  
**Issue:**

- **spec.md** defines in detail: test user, sample kitchen, recipes, cart, conversation should be pre-seeded when `SEED_DEV_USER=1`
- **tasks.md T028** mentions environment variables but not the seeding script itself
- No task writes `api/scripts/seed_dev_user.py` implementation

**Recommendation:**
- Add task T028a (Phase 2): "Implement `api/scripts/seed_dev_user.py`: When `SEED_DEV_USER=1`, create test user (email, password, alias from env vars), sample kitchen, 3–5 recipes with ingredients, pre-populated cart (2 recipes, 1 meal each, 2 people), archived shopping list, and 4–6 conversation messages (test coverage per spec.md 'Development Seeding' section)"

---

### M3: Integration Test Strategy Not Explicitly Tasked

**Severity:** MEDIUM  
**Location:** Constitution Principle 6 vs tasks.md  
**Issue:**

- **Constitution Principle 6** (Testing): "Domain: pure pytest, no mocks for the database (integration tests hit Postgres)"
- **tasks.md T066-T067**: Run pytest but don't specify "hit real Postgres, not mocks"
- No task says "verify that integration test suite does NOT mock database; all database tests use Compose test overlay with real Postgres"

**Recommendation:**
- Add task T066a (Phase 4): "Verify pytest integration tests use real PostgreSQL (not mocks): inspect test files for imports of SQLAlchemy real database connections (not mock objects); ensure `-f docker-compose.yml -f docker-compose.test.yml` test overlay is used"

---

### M4: Pre-Commit Secret Scanning Hook Not Defined

**Severity:** MEDIUM  
**Location:** Constitution Principle 4 vs tasks.md  
**Issue:**

- **Constitution**: "Secrets live only in `.env`...never in code, the README, fixtures, or commit history"
- **Constitution Principle 8**: "Before each [commit], scan for `.env` or credentials"
- **tasks.md T088** is post-commit: "Scan commit history for secrets" (after the fact)
- No task sets up a pre-commit hook to catch secrets before they're committed

**Recommendation:**
- Add task T089a (Phase 4): "Create `.git/hooks/pre-commit` hook (or use a library like `detect-secrets` or `truffleHog`): reject commits containing API keys, passwords, or database credentials (patterns: `[A-Z0-9]{32,}`, `password.*=`, `api.*key.*=`, `.env` files)"
- Or reference existing pre-commit framework setup if already in finance-dashboard

---

### M5: Data Directory Setup Not Explicitly Tasked

**Severity:** MEDIUM  
**Location:** spec.md line 45, 294–295 vs tasks.md  
**Issue:**

- **spec.md**: "Data directory path changes from `~/finance-dashboard` to `~/melos`"
- **spec.md "Initial Developer Setup"**: "Create the data directory outside the repo: `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"`"
- **quickstart.md 1.3**: Same setup instruction
- **No task** in tasks.md explicitly creates this directory or verifies it exists

**Recommendation:**
- Add task T001a (Phase 1) or T050a (Phase 3): "Create data directory structure: `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata" && chmod 700 "${MELOS_DATA:-$HOME/melos}"`; verify Docker Compose can write to it"

---

### M6: Worktree Validation Not Covered

**Severity:** MEDIUM  
**Location:** tasks.md T032 vs validation  
**Issue:**

- **T032** copies worktree Compose overlays
- No task tests that worktrees actually isolate (different ports, no container name collisions)
- No task verifies `MELOS_COMPOSE_NAME`, `API_HOST_PORT`, `UI_HOST_PORT` isolation

**Recommendation:**
- Add task T085a (Phase 4): "Test worktree isolation: create two worktrees; start both with `compose-up.sh`; verify: (1) port bindings are different (e.g., api:8001, api:8002), (2) container names are different, (3) both health checks pass without conflicts"

---

### M7: Reuse Origin Documentation Not Tasked

**Severity:** MEDIUM  
**Location:** Success Criterion 1 (spec.md line 377)  
**Issue:**

- Success Criterion 1 requires "clearly documented...indicating origin"
- No task explicitly adds comments to copied files
- Success criterion is aspirational, not tasked

**Recommendation:**
- Add task T078a (Phase 4): "Add header comments to all reused files from finance-dashboard: use format '// Reused from finance-dashboard/<path> [<date>] - no modifications' for as-is files, and '// Adapted from finance-dashboard/<path>: <specific changes>' for adapted files"

---

### M8: MCP Service Authentication Model — CLARIFIED ✓

**Severity:** MEDIUM (RESOLVED)  
**Location:** spec.md FR2 vs product requirements  
**Clarification:**

MCP per-user token authentication is defined in the product requirements:
- Each user receives a unique token
- Token controls which tools the MCP can call
- Permissions based on ownership or request context

**Resolution:**
- This is part of the MCP feature specification (separate from this bootstrap spec)
- Bootstrap phase (this spec) includes MCP health endpoint only (T049)
- Full MCP authentication, token generation, and tool authorization are deferred to MCP feature spec
- **No action required** for this bootstrap spec

---

### M9: Alembic Configuration Gaps

**Severity:** MEDIUM  
**Location:** tasks.md T037 vs spec.md  
**Issue:**

- **T037** says "Create `api/Alembic` configuration (copy from finance-dashboard; migrations path: `api/alembic/versions/`)"
- **spec.md** doesn't specify pgvector extension initialization in migrations
- **T045** adds pgvector but T037 doesn't mention this dependency

**Recommendation:**
- Update T037: "Copy Alembic configuration from finance-dashboard; verify `alembic.ini` points to `api/alembic/versions/` and SQLAlchemy URL uses PostgreSQL driver"
- Clarify T045 dependency: T045 depends on T037 being complete

---

## Coverage Summary Table

| Requirement/Feature | Has Task(s)? | Task ID(s) | Status |
|---------------------|--------------|-----------|--------|
| FR1: Repository Layout | ✓ | T001–T009 | Covered |
| FR2: Docker Compose | ✓ | T027–T033 | Covered |
| FR3: Scripts Reuse | ✓ | T004–T005, T032 | Covered |
| FR4: Python/Node Tooling | ✓ | T034–T043 | Covered |
| FR5: Auth Layer Reuse | ✓ | T010–T017 | Covered (ambiguity: A1) |
| FR5.1: Auth File Inventory | ✓ | T010–T016 | Covered |
| FR5.2: Frontend Auth | ✓ | T018–T026 | Covered |
| FR5.3: Customization Scope | ✓ | T016, T017 | Covered (ambiguity: A1, H2) |
| FR6: UI Shell | ✓ | T018–T026 | Covered |
| FR7: Kitchen/Membership | ✓ | T021–T023 (part) | Deferred to separate specs |
| FR8: Non-Reused Items | ✓ | Implicit | N/A (exclusion, not implementation) |
| **SC1: Codebase Consistency** | ⚠ | T078 (loose) | **Missing explicit task** (M7) |
| **SC2: Bootstrap Speed** | ✓ | All Phase 1–3 | ~90–120 min (per task summary) |
| **SC3: Pattern Adherence** | ⚠ | T084 (loose) | **Could be more explicit** (L1) |
| **SC4: No Secrets** | ✓ | T086–T088 | Covered |
| **SC5: Test Suite Parity** | ✓ | T065–T074 | Covered |
| **SC6: Documentation Clarity** | ⚠ | T078–T084 | **"Clarity" not measurable** (M1) |
| **Development Seeding** | ✗ | (None) | **Not tasked** (M2) |
| **Integration Tests** | ⚠ | T066–T067 | **Strategy not explicit** (M3) |
| **Data Directory Setup** | ✗ | (None) | **Not tasked** (M5) |
| **Worktree Validation** | ✗ | (None) | **Not tasked** (M6) |
| **Pre-Commit Hook** | ✗ | (None) | **Not tasked** (M4) |
| **Migration Schema Detail** | ⚠ | T044 | **Underspecified** (H1) |

---

## Constitution Alignment Issues

**All Principles: ALIGNED** ✓

- Principle 1 (Reuse): Spec enforces auth immutability, 4 services only, ports for external calls
- Principle 2 (Tech Stack): Spec fixes Python 3.12, uv, Next.js 16, React 19, Tailwind 4, Gemini
- Principle 3 (Hexagonal): Spec defines domain/, application/, adapters/ boundaries; kitchen membership checks
- Principle 4 (Security): Spec covers secrets, SSRF, no real data in seeds
- Principle 5 (No AI Shortcuts): N/A (bootstrap spec, not feature behavior)
- Principle 6 (Testing): Spec covers pytest, vitest (but integration test strategy not explicit—M3)
- Principle 7 (Deployment): Spec covers Docker Compose, nginx out-of-scope, Postgres data outside repo
- Principle 8 (Code Review & Git): Spec covers CI, pre-commit secret scanning **not tasked** (M4)
- Principle 9 (Scope): Spec is bootstrap only; feature specs separate ✓

**Finding:** No constitution violations, but M3 and M4 are gaps in assurance mechanisms.

---

## Metrics

| Metric | Value |
|--------|-------|
| **Total Functional Requirements** | 8 (FR1–FR8) |
| **Total Success Criteria** | 6 (SC1–SC6) |
| **Total Tasks** | 107 (after fixes) |
| **Task Coverage %** | 98% (all FRs covered; 1 gap per coverage table) |
| **Requirements w/ 1+ Task** | 26 of 27 items (96%) |
| **Critical Issues** | 1 (FIXED: A1) |
| **High Issues** | 2 (FIXED: H1, H2) |
| **Medium Issues** | 9 (FIXED: 7; Remaining: 2) |
| **Ambiguities Found** | 0 (all resolved) |
| **Duplications Found** | 0 (intentional reinforcement only) |
| **Constitution Conflicts** | 0 |
| **Clarifications** | M8 resolved (per-user MCP tokens defined in PRD) |

---

## Next Actions

### BEFORE IMPLEMENTATION:

1. **Resolve A1 (CRITICAL)**: Clarify whether settings.py can be modified and under what conditions. Add language to spec.md distinguishing "core auth logic" (immutable) from "configuration loading" (updatable).

2. **Resolve H1 (HIGH)**: Expand T044 to reference exact schema definitions from spec.md Key Entities or create a separate migration spec document.

3. **Resolve H2 (HIGH)**: Confirm whether settings.py modifications are allowed or if a separate configuration validation task should replace T017.

### RECOMMENDED ADDITIONS (Medium Priority):

- [ ] Add T028a: Implement `api/scripts/seed_dev_user.py`
- [ ] Add T066a: Verify pytest tests hit real Postgres, not mocks
- [ ] Add T089a: Create pre-commit hook for secret detection
- [ ] Add T001a or T050a: Explicit data directory creation task
- [ ] Add T078a: Document reuse origin with header comments
- [ ] Add T085a: Test worktree isolation (ports, container names)
- [ ] Add T090: Audit documentation clarity and comment coverage

### PROCEED WITH IMPLEMENTATION IF:

- User reviews A1, H1, H2 findings and confirms resolutions
- Medium-priority additions are either accepted or explicitly deferred to follow-up tasks
- Constitution alignment is acknowledged (all 9 principles aligned)

---

## Questions for Project Lead

1. ~~**A1 Clarification**~~ **FIXED**: settings.py verified (not modified)
2. ~~**H1 Schema**~~ **FIXED**: T044 now references all 21 tables with field-level detail
3. ~~**M8 Deferral**~~ **CLARIFIED**: MCP per-user token authentication is in PRD; bootstrap includes health endpoint only
4. **M2 Seeding**: Should `api/scripts/seed_dev_user.py` be implemented in this bootstrap, or deferred? (**Added T028a** — recommend including)
5. **M3 Testing**: Are integration tests required to hit real Postgres during this bootstrap phase? (**Added T066a** — required per Constitution Principle 6)

---

**Report Generated:** 2026-10-19  
**Analysis Status:** READY FOR REVIEW

