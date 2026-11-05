---
description: "Task list for Refused Site Registry"
---

# Tasks: Refused Site Registry

**Input**: Design documents from `specs/067-refused-site-registry/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included. Constitution §6 requires domain, application (fake ports), integration (Compose) and vitest layers.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Add `tldextract` with `cd api && uv add tldextract`. It must be used only as `tldextract.TLDExtract(suffix_list_urls=())`, so it reads the bundled suffix list and makes no network call (research R3). Commit `api/pyproject.toml` and `api/uv.lock`.

---

## Phase 2: Foundational (blocks all stories)

- [X] T002 In `api/application/ports.py`: add `"refused"` to `PageFetchFailureKind`. Give `PageFetchFailed` the fields `status: int | None = None` and `message: str = ""`, and update its docstring: every kind except `refused` shows the generic message. Add a `RefusedSiteLog` Protocol with `record(self, host: str, actor_user_id: UUID, status: int, message: str) -> None` (contracts/ports.md). Add a frozen `AdminRefusedSiteRow(domain: str, total_refusals: int, distinct_members: int, first_seen_at: datetime, last_seen_at: datetime, last_status: int, last_message: str)`. Add `refused_sites(self) -> Sequence[AdminRefusedSiteRow]` to `AdminReportRepository`.
- [X] T003 Create `api/adapters/persistence/migrations/versions/0016_refused_sites.py`, revision `0016_refused_sites`, revising `0015_recipe_preview_image`. It adds:
  - table `refused_site`:
    - `domain text PK`
    - `total_refusals integer not null`
    - `distinct_members integer not null`
    - `first_seen_at timestamptz not null`
    - `last_seen_at timestamptz not null`
    - `last_status smallint not null CHECK (last_status IN (401,402,403,451))`
    - `last_message text not null default ''` with `CHECK (char_length(last_message) <= 1000)`
    - `CHECK (char_length(domain) <= 253)`
  - table `refused_site_member`:
    - `domain text not null`, FK to `refused_site.domain` ON DELETE CASCADE
    - `member_key bytea not null` with `CHECK (octet_length(member_key) = 32)`
    - PK (`domain`, `member_key`)

  `downgrade` drops both tables. Neither table references `users`.
- [X] T004 [P] Add `RefusedSiteModel` and `RefusedSiteMemberModel` to `api/adapters/persistence/models.py`, matching T003.

**Checkpoint**: The migration applies on the Compose test overlay (`scripts/compose-test.sh`).

---

## Phase 3: User Story 1 - Member is told the site needs a license (P1) 🎯 MVP

**Goal**: A site answering 401/402/403/451 gives `422 site_requires_license` and the license message. Every other failure is unchanged.

**Independent Test**: A capture through a transport stubbed to answer 402 shows the license text. A 404 or a timeout still shows "We couldn't open that page…".

### Tests

- [X] T005 [P] [US1] In `api/tests/test_refusal_text.py`, test `refusal_text(html: bytes, content_type: str) -> str`:
  - `script`, `style`, `noscript` and `template` content is dropped
  - entities are unescaped and whitespace collapsed
  - a `mailto:` target is kept as text
  - the result is cut to ≤ 1,000 chars on a word boundary
  - a non-HTML content type gives `""`
  - an empty body gives `""`
- [X] T006 [P] [US1] Extend `api/tests/test_page_fetcher_adapter.py`:
  - for each of 401/402/403/451 with an HTML body, the result is `PageFetchFailed("refused", status=<code>, message=<text>)`
  - 404, 429 and 500 are still `PageFetchFailed("status")` with `status is None`
  - a refusal body larger than 64 KB is read only to 64 KB and still gives a message
  - a refusal after one redirect is still `refused`
  - a blocked redirect target is still `blocked`
  - the log line holds the kind, the status and the host, but not the message or the path
- [X] T007 [P] [US1] Extend `api/tests/test_recipe_capture_url_application.py` with a `FakeRefusedSiteLog`:
  - a fetcher returning `refused` → the outcome is that same `PageFetchFailed` and `record` is called once with `(final-or-link host, actor id, status, message)`
  - a fake whose `record` raises → the outcome is still `refused`
  - a `status`, `blocked` or `timeout` failure → `record` is not called
- [X] T008 [P] [US1] Extend `api/tests/test_recipe_capture_url_integration.py`:
  - a stubbed fetcher returning `refused` → `422 {"code":"site_requires_license","detail":""}`, and the body contains no status, domain or site text
  - `blocked` → `page_fetch_failed`, unchanged
- [X] T009 [P] [US1] Extend `ui/lib/i18n/capture.test.ts` and `ui/components/AddRecipeCallToAction/UrlCaptureSheet.test.tsx`: code `site_requires_license` shows "This website requires a license, it's not supported yet." in en and "Este sitio web requiere una licencia, aún no es compatible." in es. `page_fetch_failed` is unchanged.

### Implementation

- [X] T010 [P] [US1] Create `api/adapters/web/refusal_text.py`: a stdlib `html.parser.HTMLParser` subclass and `refusal_text(data: bytes, content_type: str) -> str`, as in research R5. Decode with the existing `_decode` logic, either moved here or imported, and keep it pure.
- [X] T011 [US1] In `api/adapters/web/page_fetcher.py`:
  - add `_REFUSALS = frozenset({401, 402, 403, 451})` and `REFUSAL_MAX_BYTES = 64 * 1024`
  - in `_get`, when the final status is in `_REFUSALS`, read the body up to `REFUSAL_MAX_BYTES` within the same deadline. A read error or timeout gives an empty body.
  - then raise `_Failed("refused", status=..., message=refusal_text(...))`, so `_Failed` carries status and message
  - `fetch_page` returns `PageFetchFailed("refused", status, message)`; `fetch_image` still returns `None`
  - log `kind=refused status=%d host=%s` only
- [X] T012 [US1] In `api/application/recipe_capture_url.py`: take `refused_sites: RefusedSiteLog` as a keyword-only constructor argument. On `PageFetchFailed` with kind `refused`, call `record(link.host, command.actor_user_id, page.status, page.message)` inside `try/except Exception`. On error, log `refused site record failed: host=%s` and still return `page`.
- [X] T013 [US1] In `api/api/routes/recipe_capture.py`: add `_site_requires_license()` returning `_error(422, "site_requires_license", "")`. Return it when `outcome.kind == "refused"`; every other `PageFetchFailed` still returns `_page_fetch_failed()`. Update the R10 comment to say a site refusal gets its own code (spec 067 R2).
- [X] T014 [US1] In `api/api/deps.py`: pass a `RefusedSiteLog` into `CaptureRecipeUrl`. Until US2 lands, use a no-op adapter in `api/adapters/persistence/refused_sites.py` (`NullRefusedSiteLog`) so US1 ships on its own.
- [X] T015 [P] [US1] In `ui/lib/i18n/capture.ts`: add `siteRequiresLicense`, en "This website requires a license, it's not supported yet." and es "Este sitio web requiere una licencia, aún no es compatible.", plus `case "site_requires_license": return t.siteRequiresLicense;` next to `page_fetch_failed`. Check that `ui/lib/capture/captureClient.ts` and `ui/app/api/notebooks/[notebookId]/captures/url/route.ts` pass the code through unchanged, and add it to any allow-list there.

**Checkpoint**: US1 works with nothing recorded.

---

## Phase 4: User Story 2 - Refusals are recorded per domain (P1)

**Goal**: Each refusal updates one row per registrable domain, with an HMAC-keyed distinct-member count.

**Independent Test**: Three refusals from 2 accounts on `www.example.com` and `example.com` → one `example.com` row, total 3, distinct 2.

### Tests

- [X] T016 [P] [US2] Create `api/tests/test_refused_sites_integration.py` (Compose overlay, real Postgres). Cases:
  - first refusal → total 1, distinct 1, first_seen == last_seen, status and message stored
  - a second refusal from the same member → total 2, distinct 1, last_status and last_message replaced
  - a second member → distinct 2
  - `www.example.com`, `m.example.com` and `example.com` → one row `example.com`
  - `news.bbc.co.uk` → `bbc.co.uk`
  - two threads recording a new domain at once → one row, total 2
  - a message over 1,000 chars is cut so the CHECK never fails
  - `refused_site_member` holds no user id; the key is 32 bytes and differs for the same user on two domains
  - an insert failure inside `record` leaves the outer session usable (savepoint)

### Implementation

- [X] T017 [US2] Implement `SqlRefusedSiteLog` in `api/adapters/persistence/refused_sites.py`, replacing `NullRefusedSiteLog`:
  - `domain` is lower-cased `tldextract.TLDExtract(suffix_list_urls=())(host)` `domain.suffix`, falling back to the host when there is no suffix. Build the extractor once at module level.
  - `member_key = hmac.new(k, f"{domain}\n{user_id}".encode(), sha256).digest()`, with `k = hmac.new(SESSION_SECRET.encode(), b"melos-refused-site-v1", sha256).digest()`. Pass `k` into the constructor; never import auth code.
  - inside `session.begin_nested()`:
    - `INSERT … ON CONFLICT (domain) DO UPDATE SET total_refusals = refused_site.total_refusals + 1, last_seen_at = now(), last_status = EXCLUDED.last_status, last_message = EXCLUDED.last_message`, inserting with `distinct_members` 0
    - then `INSERT INTO refused_site_member … ON CONFLICT DO NOTHING`
    - if rowcount == 1, `UPDATE refused_site SET distinct_members = distinct_members + 1`
  - cut `message` to 1,000 chars as a safety net
- [X] T018 [US2] In `api/api/deps.py`, wire `SqlRefusedSiteLog(session, key=derive(settings.session_secret))`. If `session_secret` is empty (test boot), fall back to `NullRefusedSiteLog`.

**Checkpoint**: US1 and US2 work together. The quickstart allrecipes capture adds one row.

---

## Phase 5: User Story 3 - Admin reviews the refused sites (P2)

**Goal**: `GET /admin/refused-sites` and a "Refused sites" dashboard tab.

**Independent Test**: With seeded rows, the admin sees them sorted by total, highest first. A non-admin gets a 404 byte-identical to an unknown path.

### Tests

- [X] T019 [P] [US3] Extend `api/tests/test_admin_application.py`: `AdminDashboard.refused_sites` raises `AdminNotFoundError` for a non-admin or `None`, and returns the repo rows for an admin.
- [X] T020 [P] [US3] Extend `api/tests/test_admin_integration.py`:
  - `GET /admin/refused-sites` signed out or as a non-admin gives the same 404 body as an unknown path
  - as admin it returns `{"refused_sites":[...]}` sorted by `total_refusals` DESC then `domain`, with the fields in contracts/admin-api.md
  - an empty table gives `[]`
- [X] T021 [P] [US3] Extend `ui/app/admin/AdminDashboard.test.tsx` and `ui/app/api/admin/admin.bff.test.ts`:
  - the BFF accepts `refused-sites`
  - the tab shows the columns domain, total, members, first seen, last seen, status and message
  - a message of `<img src=x onerror=alert(1)>` is shown as literal text, with no `img` element in the DOM

### Implementation

- [X] T022 [US3] Add `refused_sites()` to `SqlAdminReportRepository` in `api/adapters/persistence/admin.py` (`ORDER BY total_refusals DESC, domain`), and `refused_sites(user_id)` to `api/application/admin.py` behind `_require_admin`.
- [X] T023 [US3] Add `AdminRefusedSite` and `AdminRefusedSitesResponse` to `api/api/schemas/admin.py`, and `GET /admin/refused-sites` to `api/api/routes/admin.py` using the existing `_read` helper.
- [X] T024 [US3] Add `"refused-sites"` to `SECTIONS` in `ui/app/api/admin/[section]/route.ts`.
- [X] T025 [US3] In `ui/app/admin/AdminDashboard.tsx` and `ui/app/admin/admin.ts`:
  - add the `refused-sites` section (en "Refused sites", es "Sitios rechazados") with column labels in both languages
  - format the dates like the other sections
  - render `last_message` as a text node, never with `dangerouslySetInnerHTML`, wrapped and capped in width

---

## Phase 6: Polish & Cross-Cutting

- [X] T026 [P] Update `specs/026-capture-recipe-url/` (R10/FR-024 note) and `specs/055-*/contracts/admin-api.md` to point to spec 067 for the new code and section.
- [X] T027 [P] Add "site refusal → license message, recorded for the admin" to the PRD and backlog entry in `dev/docs/` per constitution §9.
- [X] T028 Run `cd api && uv run ruff check . && uv run pytest -q`, `scripts/compose-test.sh`, and `cd ui && npm run lint && npm test`.
- [ ] T029 Do the manual walk in `quickstart.md` on an isolated stack, with Playwright on the host per the "browser walk on WSL" memory.

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T004) → US1 → US2 → US3 → Polish.
- US1 doesn't need the tables (it uses `NullRefusedSiteLog`). T003 and T004 are only needed by US2 and US3, so they can be pushed back if US1 ships first.
- US3 needs rows to show (from US2 or seeded in tests). Its code depends only on T002–T004.
- Within a story, write the tests first and confirm they fail before implementing.

## Parallel Opportunities

- US1: T005, T006, T007, T008 and T009 together, then T010 and T015 together. T011 → T012 → T013 → T014 run in order.
- US2: T016 can run alongside the US3 tests.
- US3: T019, T020 and T021 together. T024 and T025 (ui) in parallel with T022 and T023 (api).
- Polish: T026 and T027 together.

## Implementation Strategy

1. **MVP**: Phases 1–3 (US1). Members stop seeing a misleading error. Ship it.
2. **Increment**: Phase 4 (US2) starts collecting demand data.
3. **Increment**: Phase 5 (US3) shows it to the admin.
4. Phase 6 updates the docs and runs the full validation.
