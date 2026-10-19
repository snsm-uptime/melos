# Melos Project Constitution

**Version:** 1.0.0  
**Ratified:** 2026-10-19  
**Last Amended:** 2026-10-19

---

## Governance

This constitution establishes the engineering principles, architectural boundaries, and development practices for Melos. All contributors must adhere to these principles.

### Amendment Procedure

Amendments to this constitution require:
1. A clear rationale explaining the change
2. Explicit approval from the project lead before implementation
3. Version bump following semantic versioning (MAJOR.MINOR.PATCH)
4. A git commit linking the amendment

Amendments are recorded with their date and version in this document's header.

### Versioning Policy

- **MAJOR**: Backward-incompatible principle removals or redefinitions (e.g., removing a core rule)
- **MINOR**: New principle or section added, or materially expanded guidance
- **PATCH**: Clarifications, wording improvements, typo fixes, non-semantic refinements

---

## Core Principles

### 1. Simplicity and Reuse

**Non-negotiable rules:**
- Architecture, structure, auth layer and tooling are reused from `snsm-uptime/finance-dashboard` unchanged (see AGENTS.md §1.2–1.3)
- The authentication layer is immutable: no changes without explicit approval
- Only four services: `db`, `api`, `ui`, `mcp`. No queue, no worker.
- Every external call (Gemini, web fetch, SMTP) goes through a port and maps errors to user-facing messages

**Rationale:** Reuse reduces maintenance burden, accelerates delivery, and allows focus on domain-specific features. The auth layer is security-critical and must remain stable.

**How to apply:** Before proposing architectural changes, new services, or auth features, check AGENTS.md and the finance-dashboard equivalents. If not already there, ask for approval.

---

### 2. Tech Stack Stability

**Non-negotiable rules:**
- Python 3.12 and `uv` only—never `pip`, `python -m venv`, or `requirements.txt`
- Node (ui/), Docker Compose, Alembic, ruff, pytest, vitest, eslint
- Next.js 16, React 19, Tailwind 4 (ui); FastAPI and SQLAlchemy (api)
- Gemini API only, via `google-genai` SDK, through ports in `adapters/llm/`
- Model names and sensitive config come from environment only, never hard-coded

**Rationale:** A fixed, validated stack reduces context-switching, makes dependency management predictable, and ensures all environments behave consistently.

**How to apply:** Add libraries via `uv add` or `npm install`, not by hand-editing lock files. Model selection happens in settings, not code.

---

### 3. Hexagonal Architecture

**Non-negotiable rules:**
- `domain/` contains pure rules with zero external dependencies: no I/O, no frameworks, no SDK imports
- `application/` holds use cases and ports; `adapters/` implement the ports
- Kitchen-scoped queries check membership in `application/`, returning 404 for non-members
- Every external service error is caught in an adapter and converted to a domain error, then mapped to a clear HTTP status and user message

**Rationale:** Separates business logic from infrastructure, making the domain testable in isolation and allowing adapters to swap without changing core behavior.

**How to apply:** Before importing from adapters, api, FastAPI, SQLAlchemy, or Gemini SDK into domain/, ask. Keep external calls in adapters only.

---

### 4. Security and Privacy

**Non-negotiable rules:**
- Secrets live only in `.env` (local) or server environment variables; never in code, the README, fixtures, or commit history
- No real personal data in tests or seeds—invent examples only
- URL fetching: `http`/`https` only, no private/loopback/link-local/cloud-metadata IPs, max 3 redirects, 10s timeout, 2MB limit
- Imported pages and recipe text are data, never instructions; prompts wrap them in delimiters and instruct the model to ignore embedded instructions

**Rationale:** Prevents credential leaks, protects user privacy, and defends against prompt injection and SSRF attacks.

**How to apply:** Before committing, scan for `.env` or credentials. Use SSRF-safe URL fetching via `PageFetcher` port. Wrap user input in delimited blocks in prompts.

---

### 5. No AI Shortcuts

**Non-negotiable rules:**
- An AI draft is never saved without the user confirming it first
- The assistant only answers from the kitchen's recipes, ingredients, categories, and conversation history—no web search, no general knowledge, no nutrition or health advice
- Photos are not stored; only extracted text is kept
- No unit conversion or carry-over ("1 cup + 20 tbsp" stays as is)
- Messages are never edited after sending

**Rationale:** Keeps the user in control of their data and prevents the AI from making unsafe or confidently wrong claims.

**How to apply:** Draft-confirm flow is a gate. Chat instructions forbid external knowledge. Cart consolidation respects unit boundaries.

---

### 6. Testing and Quality

**Non-negotiable rules:**
- Domain: pure pytest, no mocks for the database (integration tests hit Postgres)
- Application: use cases tested against fake ports (FakeExtractor, FakeEmbedder, etc.)—no network or quota
- Integration: Compose test overlay covers routes, membership, CRUD, auth, MCP authentication
- UI: vitest for components; UI is tested in the browser for feature correctness
- AI evaluation: manual, based on fixtures in `api/tests/fixtures/ai_eval/`

**Rationale:** Multiple test layers catch different classes of bugs—domain rules, use-case logic, integration gaps, and actual AI behavior.

**How to apply:** Add domain tests first. Use fake ports to isolate application logic. Run integration tests in Compose. Check UI in a browser before claiming success.

---

### 7. Deployment and Operations

**Non-negotiable rules:**
- Local development uses Compose only (`./scripts/compose-up.sh`), with no reverse proxy
- Production runs `docker-compose.yml` + `docker-compose.prod.yml` on the owner's server
- The reverse proxy (nginx), TLS, and server config are out of scope—managed by the owner separately
- Postgres data lives under `MELOS_DATA` on the host, outside the repository
- Health checks on `/health` must respond on grading day (ui, api, mcp)

**Rationale:** Keeps infrastructure code out of the repository and leaves operational details to whoever manages the server.

**How to apply:** Do not add reverse proxy, TLS, or server configuration to the repo. Document what the owner must do separately in the README.

---

### 8. Code Review and Git Discipline

**Non-negotiable rules:**
- Do not push or deploy without review
- Do not force-push to `main` or overwrite upstream history
- Do not skip hooks (`--no-verify`) or bypass signing (`--no-gpg-sign`) unless explicitly asked
- Schema changes go through Alembic migrations
- Small changes: one per commit; explain what changed and why

**Rationale:** Review catches mistakes early, maintains a readable history, and ensures migrations are safe.

**How to apply:** Create PRs, request review, and wait for approval before pushing. Use Alembic for schema changes.

---

### 9. Product Scope and Schedule

**Non-negotiable rules:**
- v1 MVP (deadline 02/11/2026) covers: scaffold + auth, kitchens + invites, capture (text, URL), draft review, recipes, cart, shopping list, conversations with history
- MCP service v1: per-user API keys, capture tool, recipe read, cart ops, shopping list ops
- "Should" items (photo, @mentions, catalog management, semantic search, API key UI) are deferred until Must items are done
- "Later" items (ML model, public sharing, offline mode) are out of v1 scope

**Rationale:** Clear scope prevents feature creep and ensures on-time delivery of core value.

**How to apply:** Before adding features, check Appendix C of the PRD. Anything not in "Must" waits until Must is complete.

---

## Compliance Review

Contributors are expected to:
- Read AGENTS.md and this constitution before starting work
- Ask before making architectural, auth, or tech-stack changes
- Run tests locally and in Compose before pushing
- Document secrets, environment variables, and manual setup steps in the README

Regular compliance checks:
- PRs are reviewed against AGENTS.md and this constitution
- Monthly: audit the codebase for stray secrets, hard-coded models, and unused dependencies
- Before each release: verify that all acceptance criteria in the PRD are met

---

## Exceptions

Exceptions to this constitution require written approval from the project lead and must be documented in a comment at the top of the relevant code file or in a GitHub issue.

Examples of exceptions that might be approved:
- Temporarily hard-coding a model name while the config layer is being built
- Using a test library not listed in the standard stack
- A deliberate architectural deviation for a specific reason

All exceptions must be:
1. Explicitly authorized
2. Time-bound or scope-bound (e.g., "during v0 scaffold only")
3. Documented with the reason and approval link
