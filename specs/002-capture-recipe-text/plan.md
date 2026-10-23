# Implementation Plan: Capture a Recipe from Pasted Text

**Branch**: `s20` (spec folder `002-capture-recipe-text`) | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-capture-recipe-text/spec.md`

## Summary

A member pastes recipe text into a sheet opened from the shared add-recipe call
to action. The call to action is on the member's own Notebook page (new
bottom-bar Notebook tab) and on a kitchen's Notebook tab. The text goes to the api with the
owner key of the notebook the page belongs to: the kitchen id, or the member's user id and
notebook id. The api resolves the notebook's owner, checks
access and archive state, reads the notebook's ingredient catalog, and calls the `RecipeExtraction` use case from S-015. It then returns
either a draft or a coded refusal. The ui shows the draft on its own full-screen
page, where the member can edit it and discard it. Nothing is saved.

Technical approach: notebooks are their own entity, owned by one member or one kitchen,
and are created and read by the prerequisite spec `specs/004-notebooks`. One new
application use case (`CaptureRecipeText`) wraps the S-015 use case with notebook
access, the archive check and the catalog read. Two thin capture routes keyed by the
owner (`/notebooks/kitchens/{kitchen_id}/captures/text` and
`/notebooks/members/{user_id}/{notebook_id}/captures/text`) and one read-only vocabulary
route sit on top of it. Chip labels use the member's configured language. The paste limit comes from
`RECIPE_TEXT_MAX_CHARS`. The ui gets the `AddRecipeCallToAction` component, a client-only
capture store, two Notebook pages, a draft page per notebook, and a leave guard. Two small changes reach
into S-015: ingredient lines gain `preparation`, and the too-long refusal text
matches this spec.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, pydantic (api); the S-015 `RecipeExtraction` use case, `GeminiRecipeExtractor` and `FakeRecipeExtractor`; existing ui components `ActionDialog`, `Sheet`, `Chip`, `ChipPicker`, `TabBar`, `useFocusTrap`. **No new library** in api or ui.

**Storage**: PostgreSQL 16. The `notebook` and `ingredient` tables, their Alembic revision `0003` and the backfill are delivered by spec 004-notebooks. This feature adds no table: it only reads notebooks and the ingredient catalog (FR-003, FR-019). `ingredient` stays empty until S-019 saves recipes.

**Testing**: pytest + ruff (api). Domain tests are pure. Use-case tests use fake ports and the `FakeRecipeExtractor`. Integration tests run in the Compose test overlay with a real Postgres and the fake extractor injected through a FastAPI dependency override. vitest + eslint + typecheck (ui). Browser walkthrough per `quickstart.md`. Manual AI evaluation for SC-002 and SC-006 uses `api/tests/fixtures/ai_eval/`.

**Target Platform**: Linux containers (`api`, `ui`, `db`) under Docker Compose. Mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: A draft or a message within `GEMINI_TEXT_TIMEOUT_S` + 2 s (12 s by default) in every run (FR-026, SC-001).

**Constraints**:
- Paste limit is `RECIPE_TEXT_MAX_CHARS` (default 5,000) after trimming, enforced in the ui (submit disabled) and in the use case (FR-002).
- One attempt per submission, no automatic retry (FR-025).
- No writes: no recipe, ingredient, category, source or step row is created (FR-019, SC-005).
- Non-members get 404 with no existence oracle. Archived kitchens are refused before any assistant call (FR-022, FR-033, SC-008).
- No raw service error, key or trace in any response or ui message (FR-029).
- The paste limit is `RECIPE_TEXT_MAX_CHARS` (default 5,000) after trimming. The request body is guarded at twice that value.
- The draft lives only in browser memory: it is lost on reload and never sent back to the api in this feature.

**Scale/Scope**: One household (two to a few members). About 4 new api modules and 2 api edits into S-015, about 15 new ui files and 4 ui edits. The notebook work (migration, entity, repositories, creation, read routes) is in spec 004.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| §1 Simplicity and Reuse | No new service, queue or worker. Auth and signup untouched: routes use the existing `require_user_alias` and session cookie, and the member's notebook is created on first use by spec 004, not in the alias code. The Gemini call goes only through the S-015 port. ui reuses `ActionDialog`, `Sheet`, `Chip`, `ChipPicker`, `TabBar`. | PASS |
| §2 Tech stack | uv/npm, no new libraries. Model name and timeouts come from settings. The BFF reads the same `GEMINI_TEXT_TIMEOUT_S` env var for its safety deadline. | PASS |
| §3 Hexagonal | `CaptureRecipeText` (application) resolves the notebook's owner, checks membership and archive state, and calls the ports `NotebookRepository`, `IngredientCatalogReader`, `KitchenAccessAuthorizer` and `RecipeExtraction`. The SQLAlchemy readers live in `adapters/persistence/`. Routes only map results to HTTP. | PASS |
| §4 Security and Privacy | Pasted text is delimited as data by the existing S-015 prompt (FR-021). Personal captures read only `ingredient.user_id = caller` (FR-022). Logs keep the text length, never the text. Test data is invented. | PASS |
| §5 No AI Shortcuts | Draft-only: no save path exists in this feature (FR-019). Discard is always available. No unit conversion. | PASS |
| §6 Testing | Domain pure tests, use case against fakes, integration in Compose with the fake extractor, vitest for components, browser walkthrough, manual AI eval. | PASS |
| §7 Deployment | No compose, proxy or TLS change. No new env var: the ui already loads `.env` through `env_file`. | PASS |
| §8 Git discipline | One Alembic revision for the `ingredient` table. Work split into small commits (see Phase breakdown). | PASS |
| §9 Scope | S-016 is Must (capture from text with draft review). URL and Picture show disabled. Save, matching and copying are left to S-019, S-017 and S-034. | PASS |
| AGENTS.md: shared add-recipe call to action | Built once in `ui/components/AddRecipeCallToAction/`, used by both Notebook pages. `ActionDialog` confirm/cancel become optional without changing existing callers. | PASS |
| AGENTS.md: every kitchen query checks membership in `application/`; non-member gets 404 | A kitchen-owned notebook goes through `capture_recipe` (404-deny) before the archive check, so archive state is not revealed to non-members. A member-owned notebook that is not the caller's answers 404 `notebook_not_found`. | PASS |
| AGENTS.md: "Do not add new folders without asking" | New folders: `ui/components/AddRecipeCallToAction/` (named by AGENTS.md), `ui/app/notebook/`, `ui/app/kitchens/[kitchenId]/notebook/` (pages, inside `app/`), and `ui/lib/capture/` (inside `lib/`). `ui/lib/capture/` is the only one not implied by an existing convention; it follows the `lib/i18n/` pattern. | PASS (flagged for review) |

**Cross-spec changes (approved scope needed at review)**:

1. **`preparation` on ingredient lines.** Spec 002 FR-007, FR-010 and FR-012 show and edit a preparation ("onion" + "chopped"). The S-015 result type has no such field, so the preparation is lost. This plan adds an optional `preparation` to `IngredientLine`, to the adapter's response schema, to the prompt, and to the spec 003 data model and contract (research R2).
2. **Too-long text.** The capture use case checks the trimmed length against `RECIPE_TEXT_MAX_CHARS` (default 5,000) before any extraction call and refuses with that limit in the message, "That text is too long. Paste up to {limit} characters." Spec 003's own 10,000-character refusal stays as the upper bound (research R6).
3. **Notebook entity.** The PRD (§1.6, Appendix A) and AGENTS.md already record the notebook model (decided and approved 2026-10-22). Spec 004-notebooks implements it (research R1).
4. **Member notebook on first use.** Spec 004 creates the member's notebook the first time the member asks for their default notebook, and stores its id in the new nullable `users.default_notebook_id`. The alias claim and the auth routes are not changed; the user model gains one column (research R13).
5. **Kitchen notebook.** Spec 004 creates the kitchen's notebook with the kitchen, in the same transaction (`CreateOwnedKitchenService`).
6. **Tab name.** The bottom-bar tab and the kitchen's tab are both named "Notebook" (route `/notebook` and `/kitchens/[kitchenId]/notebook`).
7. **Language.** Chip labels use the member's configured language (research R4). Spec 002 FR-011 and the draft-language edge case should say the labels follow the member's language; the draft text itself still follows the pasted text.

**Result**: No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-capture-recipe-text/
├── spec.md                       # Feature spec (input)
├── plan.md                       # This file
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output
├── quickstart.md                 # Phase 1 output (validation guide)
├── contracts/
│   ├── capture-api.md            # HTTP: capture routes, vocabulary route, BFF
│   └── capture-ui.md             # Routes, components, store, messages
├── checklists/requirements.md
└── tasks.md                      # Created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── recipe_draft.py                     # EDIT: IngredientLine.preparation (trimmed, None when blank)
│   ├── notebook.py                         # NEW: Notebook value (id, kind, owner), labels fallback rule
│   └── kitchen_access.py                   # EDIT: add "capture_recipe" (member, deny as 404)
├── application/
│   ├── recipe_extraction.py                # EDIT: TOO_LONG wording (FR-002)
│   ├── kitchens.py                         # (spec 004) CreateOwnedKitchenService creates the kitchen's notebook
│   ├── recipe_capture.py                   # NEW: CaptureRecipeText use case, outcomes
│   └── ports.py                            # (spec 004) NotebookRepository, IngredientCatalogReader
├── adapters/
│   ├── llm/gemini_extractor.py             # EDIT: _LinePayload.preparation → IngredientLine
│   ├── llm/prompt.py                       # EDIT: preparation rule in the ingredient fields
│   ├── llm/fake_extractor.py               # unchanged (scripts any DraftRecipe)
│   └── persistence/
│       ├── models.py                       # (spec 004) NotebookModel, IngredientModel
│       ├── notebooks.py                    # (spec 004) SqlAlchemyNotebookRepository
│       ├── ingredient_catalog.py           # (spec 004) SqlAlchemyIngredientCatalogReader
│       └── migrations/versions/0003_notebooks_ingredients.py  # (spec 004) notebook, ingredient, backfill
├── api/
│   ├── deps.py                             # EDIT: get_recipe_extraction (app.state singleton), get_vocabulary
│   ├── routes/notebooks.py                 # (spec 004) GET /notebooks/kitchens/{kitchen_id}, GET /notebooks/members/{user_id}, GET /notebooks/members/{user_id}/{notebook_id}
│   ├── routes/recipe_capture.py            # NEW: POST /notebooks/kitchens/{kitchen_id}/captures/text, POST /notebooks/members/{user_id}/{notebook_id}/captures/text, GET /recipe-vocabulary
│   ├── schemas/recipe_capture.py           # NEW: request/response models
│   └── app.py                              # EDIT: include router with require_user_alias
└── tests/
    ├── test_recipe_draft_domain.py         # EDIT: preparation cases
    ├── test_gemini_extractor_adapter.py    # EDIT: preparation mapped
    ├── test_recipe_capture_application.py  # NEW: fakes; access, archive, catalog choice, outcomes, no writes
    └── test_recipe_capture_integration.py  # NEW: Compose; routes, 404, 409, codes, row counts unchanged

ui/
├── components/
│   ├── ActionDialog/ActionDialog.tsx       # EDIT: confirm/cancel optional; footer omitted when both absent
│   ├── AddRecipeCallToAction/              # NEW (AGENTS.md shared component)
│   │   ├── AddRecipeCallToAction.tsx       #   placeholder + plus → options dialog → text sheet
│   │   ├── AddRecipeOptionsDialog.tsx
│   │   ├── TextCaptureSheet.tsx
│   │   ├── index.ts
│   │   └── *.test.tsx
│   ├── RecipeDraft/                        # NEW: draft review page body
│   │   ├── RecipeDraftEditor.tsx           #   title, servings, chips, ingredient table, steps, Discard
│   │   ├── IngredientLineRow.tsx
│   │   ├── CategoryChips.tsx
│   │   ├── LeaveDraftGuard.tsx             #   link interception + beforeunload (FR-032)
│   │   ├── index.ts
│   │   └── *.test.tsx
│   ├── AppShell.tsx                        # EDIT: Notebook tab item
│   └── (soft-ledger/TabBar.tsx unchanged)
├── app/
│   ├── icons/BookIcon.tsx                  # NEW: Notebook tab icon (+ index.ts export)
│   ├── notebook/page.tsx                   # NEW: my notebook page
│   ├── notebook/draft/page.tsx             # NEW: my notebook draft page
│   ├── kitchens/[kitchenId]/page.tsx       # EDIT: Members | Notebook tab switcher
│   ├── kitchens/[kitchenId]/notebook/page.tsx        # NEW
│   ├── kitchens/[kitchenId]/notebook/draft/page.tsx  # NEW
│   ├── kitchens/KitchenSectionTabs.tsx     # NEW: Members | Notebook links
│   └── api/
│       ├── notebooks/kitchens/[kitchenId]/captures/text/route.ts          # NEW BFF
│       ├── notebooks/members/[userId]/[notebookId]/captures/text/route.ts # NEW BFF
│       ├── notebooks/kitchens/[kitchenId]/route.ts                        # NEW BFF (spec 004)
│       ├── notebooks/members/[userId]/route.ts                            # NEW BFF (spec 004, default notebook)
│       ├── notebooks/members/[userId]/[notebookId]/route.ts               # NEW BFF (spec 004)
│       └── recipe-vocabulary/route.ts                      # NEW BFF
└── lib/
    ├── appChrome.ts                        # EDIT: /notebook prefix, "notebook" tab key
    ├── capture/
    │   ├── captureStore.ts                 # NEW: module store (useSyncExternalStore)
    │   ├── captureClient.ts                # NEW: fetch + code → message key
    │   ├── draftRules.ts                   # NEW: FR-013 checks, mirrors domain
    │   ├── draftHash.ts                    # NEW: content hash that decides `edited` (FR-032)
    │   └── *.test.ts
    └── i18n/capture.ts                     # NEW: en/es strings (exact spec wording in en)
```

**Structure Decision**: Extend the existing `api/` hexagonal layers and the
`ui/` App Router. Both new api modules follow the S-015 and kitchens patterns.
No change to `mcp/`. The capture's MCP tool (`capture_recipe`, capture + save) is
a later story that reuses `CaptureRecipeText`.

## Design Decisions (summary; detail in research.md)

1. **One use case, two capture routes.** `CaptureRecipeText.execute(actor, owner, text, language)`, where `owner` is the kitchen id or the member's user id and notebook id from the route. It loads the notebook, then: a member-owned notebook must be the caller's (404); a kitchen-owned notebook goes through `capture_recipe` (404), then the archive check (409). Then the catalog read, then extraction. Text length is checked before any of these, so a too-long text never costs a database read (R3).
2. **Catalog is real but empty.** The `ingredient` table from PRD Appendix A is created by spec 004, so `IngredientCatalogReader` has a real query and integration tests can prove which catalog is sent. S-019 is the first writer (R1).
3. **Results to HTTP.** Draft → 200. Not a recipe and one-at-a-time → 422 with distinct codes. Invalid output → 422. Unavailable → 503. Limit → 429 with `Retry-After` when hinted. Misconfigured → 503 `ai_misconfigured`. Text refused → 422. Archived → 409. Non-member → 404. This follows PRD §1.7, with `code` telling apart the statuses that share a number ([contracts/capture-api.md](./contracts/capture-api.md)).
4. **Chip labels in the member's language.** The route reads the member's configured language (`users.language`, falling back as `effective_language` does). The response carries `language` and the labels in it, using the other language for any label missing. No detection logic, one extraction attempt. `GET /recipe-vocabulary` gives the full lists in both languages for editing (R4).
5. **Draft state is client-only.** A module store (`captureStore.ts`, the same pattern as `membershipKitchensStore.ts`) holds the notebook, the pasted text, the sheet state, the draft, its edits flag and the language. Reload clears it, so the draft page with no draft redirects to its Notebook page (R5).
6. **Leave guard without router blocking.** The App Router has no navigation-blocking API. `LeaveDraftGuard` listens for clicks in the capture phase on same-origin `<a>` elements and shows the "Leave without saving?" `ActionDialog`, and registers `beforeunload` while the draft is edited. Back and Discard bypass it (R7).
7. **Client rules mirror the domain.** `draftRules.ts` implements the FR-013 checks for messages next to each field. The server does not re-check edits in this feature because nothing is submitted. S-019's save re-checks with `check_draft` (R8).
8. **BFF deadline.** The BFF aborts the upstream call at `GEMINI_TEXT_TIMEOUT_S` + 2 s and answers 503 `ai_unavailable`, so FR-026 holds even if the api stalls (R9).
9. **Kitchen page tabs.** `/kitchens/[id]` (Members, unchanged) and `/kitchens/[id]/notebook` are linked by a two-item tab switcher under the header. Members stays the default, so existing links and tests keep working (R10).

## Phase breakdown (for tasks; not tasks.md)

- **P0 Research**: done in `research.md`.
- **P0 Prerequisite**: spec `004-notebooks` merged first (notebook entity, tables, creation, read routes).
- **P1 S-015 touch-ups**: `preparation` through domain, adapter, prompt and tests. Configured paste limit. Spec 003 data model and contract notes. One commit.
- **P2 Domain + application**: the capture errors, the `capture_recipe` action, `CaptureRecipeText` against fakes.
- **P3 (spec 004)**: notebook entity, tables, migration with backfill, repositories, creation, read routes.
- **P4 API**: schemas, capture routes, deps (extraction singleton, vocabulary), integration tests in Compose.
- **P5 ui foundation**: optional `ActionDialog` buttons, `BookIcon`, Notebook tab, `appChrome`, i18n, BFF routes, `captureClient`, `captureStore`.
- **P6 ui capture**: `AddRecipeCallToAction` (options dialog, text sheet, progress, messages), the two Notebook pages, kitchen tab switcher, archived hides the call to action.
- **P7 ui draft**: draft pages, `RecipeDraftEditor`, `draftRules`, category picker from the vocabulary, Discard, Back, `LeaveDraftGuard`.
- **P8 Verify**: api tests in Compose, ruff, ui test/lint/typecheck, browser walkthrough (`quickstart.md`), manual AI eval for SC-002 and SC-006.

## Re-check after Phase 1 design

The data model is delivered by spec 004-notebooks, and this feature adds no table. The
contracts add two capture routes and the vocabulary route behind the existing auth
dependency, plus three BFF proxies. They add no service, library or env var beyond
`RECIPE_TEXT_MAX_CHARS`. Membership is checked in `application/`, and archive state is
checked after membership. The cross-spec changes are listed above. Re-check result:
**PASS**.

## Complexity Tracking

Not needed: no constitution violations.
