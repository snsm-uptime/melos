# Implementation Plan: Refused Site Registry

**Branch**: `067-refused-site-registry` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/067-refused-site-registry/spec.md`

## Summary

When the site itself answers a link capture with 401, 402, 403 or 451, the fetcher returns a new failure kind, `refused`. That failure carries the status and up to 1,000 characters of the refusal page's readable text. The capture use case then records the refusal through a new port, `RefusedSiteLog`. The API answers `422 site_requires_license`, and the UI shows "This website requires a license, it's not supported yet" in the member's language. The new tables are `refused_site`, one row per registrable domain, and `refused_site_member`, which holds one keyed fingerprint per (domain, member) for the distinct-member count. The admin dashboard (spec 055) gets a fifth section, `refused-sites`.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript / Next.js 16 / React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, httpx (existing); `tldextract` (new, using its bundled suffix list with no network access, R3)

**Storage**: PostgreSQL. Migration `0016_refused_sites` adds two tables.

**Testing**: pytest for domain, application with fake ports, and integration on the Compose test overlay; vitest for UI

**Target Platform**: Linux server, Docker Compose (db, api, ui, mcp)

**Project Type**: Web application (api + ui)

**Performance Goals**: A refused capture answers as fast as today (SC-005). Recording is one upsert plus one insert-if-absent in the request's transaction.

**Constraints**: SSRF limits unchanged (10 s, 2 MB, 3 redirects). A refusal body is read up to 64 KB at most. Recording must never change the member's answer (FR-004).

**Scale/Scope**: Tens of domains and thousands of refusals. No pagination is needed (same as spec 055).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| 1 Simplicity/Reuse | PASS | No new service. The web fetch stays behind `PageFetcher`. The dashboard and its admin gate are reused. The auth layer is untouched: `SESSION_SECRET` is only read, to derive a separate key (R4). |
| 2 Tech stack | PASS | `tldextract` is added with `uv add`. Nothing else is new. |
| 3 Hexagonal | PASS | The new port is `RefusedSiteLog` in `application/ports.py`, with its adapter in `adapters/persistence/`. Domain reduction and text cleanup live in adapters because they use third-party or HTML parsing (R3, R5). The new error maps to a clear HTTP code and message. |
| 4 Security/Privacy | PASS | The site's text is never sent to members or to Gemini, and the admin UI renders it as plain text. Blocked addresses never reach a refusal, so they still get the generic message (R2). No URL path and no user id is stored, only an HMAC fingerprint (R4). |
| 5 No AI shortcuts | PASS | No AI involvement. |
| 6 Testing | PASS | Covered by fetcher adapter tests, a use case with a fake log, an integration test of the route, repo and admin, and vitest. |
| 8 Git | PASS | The schema change goes through Alembic 0016. |
| 9 Scope | PASS | The spec exists. Spec 026's "one body for every fetch failure" rule (R10/FR-024) is narrowed: a refusal from the site gets its own code, because it reveals nothing about the network. Spec 026's docs are updated when this ships. |

Post-design re-check: PASS (no new violations).

## Project Structure

### Documentation (this feature)

```text
specs/067-refused-site-registry/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-url-api.md
│   ├── admin-api.md
│   └── ports.md
└── tasks.md        # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── application/
│   ├── ports.py                       # PageFetchFailed gains "refused" + status/message; RefusedSiteLog port; AdminRefusedSiteRow
│   ├── recipe_capture_url.py          # records refusals, swallows log errors
│   └── admin.py                       # refused_sites() read
├── adapters/
│   ├── web/page_fetcher.py            # 401/402/403/451 → refused, body text ≤1,000 chars
│   ├── web/refusal_text.py            # HTML → plain text (stdlib html.parser)
│   └── persistence/
│       ├── refused_sites.py           # SqlRefusedSiteLog (upsert + HMAC member key + tldextract)
│       ├── admin.py                   # refused_sites() query
│       ├── models.py                  # RefusedSiteModel, RefusedSiteMemberModel
│       └── migrations/versions/0016_refused_sites.py
├── api/
│   ├── routes/recipe_capture.py       # 422 site_requires_license
│   ├── routes/admin.py                # GET /admin/refused-sites
│   ├── schemas/admin.py
│   └── deps.py                        # wiring
└── tests/                             # adapter, use case, integration

ui/
├── lib/i18n/capture.ts                # siteRequiresLicense (en/es) + code case
├── app/api/admin/[section]/route.ts   # allow "refused-sites"
└── app/admin/AdminDashboard.tsx       # fifth section, plain-text message column
```

**Structure Decision**: Extend the existing link-capture flow (spec 026) and the admin dashboard (spec 055) in place. No new modules beyond the refusal-text helper and the persistence adapter.

## Complexity Tracking

No violations.
