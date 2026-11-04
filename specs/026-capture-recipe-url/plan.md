# Implementation Plan: Capture a Recipe from a URL

**Branch**: `worktree-26` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-capture-recipe-url/spec.md` (backlog S-026, clarified 2026-11-04). Owner input for this plan: "Enable a partial page mode in the recipe extractor (spec 015 port) so each batch of a long page can hold only part of a recipe."

## Summary

Turn on the URL option of the shared add-recipe dialog. The api fetches the one page the member gave through a new SSRF-safe `PageFetcher` port (http/https, ports 80 and 443, every resolved address public, connection pinned to the checked address, 3 redirects, 10 s, 2 MB, HTML only), and reads it through a new `PageReader` port. If the page holds exactly one schema.org Recipe with ingredients, its title and steps (and numeric servings) are kept and its ingredient lines go through the existing extractor in whole-recipe mode (AC2.3). Otherwise the page's main content is turned into Markdown with trafilatura. Markdown that fits one batch goes through whole-recipe mode, like pasted text. Longer Markdown is split into block-aligned batches, sent at the same time to the extractor in a new **partial page mode**, and merged in pure domain code into one draft, which is then checked by the existing draft rules. The page's main photo is fetched under the same rules, returned as a data URI, shrunk in the browser and stored on the recipe (new column `preview_image_base64`). Save stores a `url` source with no page content.

## Technical Context

**Language/Version**: Python 3.12 (api, uv); TypeScript with Next.js 16, React 19, Tailwind 4 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, `google-genai` (existing); `httpx` 0.28.1 (already locked through google-genai, declared directly); **new: `trafilatura` 2.3.1 (Apache-2.0), approved by the owner 2026-11-04** (research R6)

**Storage**: PostgreSQL 16; one migration `0015_recipe_preview_image` adds a nullable `recipe.preview_image_base64`; `source` already supports `type='url'`

**Testing**: pytest (domain pure; application with `FakePageFetcher`, `FakePageReader`, `FakeRecipeExtractor`; adapter tests with `httpx.MockTransport` and an injected resolver; integration in the Compose test overlay), vitest (ui), Playwright walk on the host (memory: browser walk on WSL)

**Target Platform**: Linux server, Docker Compose (four services, unchanged)

**Project Type**: Web application (api + ui BFF)

**Performance Goals**: draft or message within 22 s (SC-002): page ≤ 10 s, then extractor calls in parallel ≤ `GEMINI_TEXT_TIMEOUT_S` (10 s), photo in parallel ≤ 5 s, 2 s margin

**Constraints**: PRD §1.7 URL rules and constitution principle 4; nothing stored before Save; no page HTML or text stored; no site contact from the browser; English and Spanish strings

**Scale/Scope**: a household of a few people; at most `RECIPE_PAGE_MAX_BATCHES` (4) assistant calls per capture; one new route, one changed route body, one new column

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and reuse: four services, no queue, no worker; external calls through ports | No new service. Page and photo fetch through `PageFetcher`; HTML reading through `PageReader`. The batch thread pool lives inside one request (research R8), not a worker. Draft screen, save, catalog matching, unit questions and messages reused. | Pass |
| 2. Tech stack | `httpx` is already in the lock. `trafilatura` is a new library, approved by the owner on 2026-11-04 (AGENTS.md: say so when adding); added with `uv add`. | Pass |
| 3. Hexagonal | `domain/page_link.py` (link rules, public-address check with stdlib `ipaddress`), `domain/recipe_page.py` (JSON-LD mapping, splitting, merging), `domain/recipe_preview.py` (data URI rule) import no framework. Membership and archived checks in `application/` before any fetch. Adapter errors become result values, mapped to codes in the route. | Pass |
| 4. Security and privacy | http/https only, public addresses only (checked on every resolved address and every redirect, connection pinned), 3 redirects, 10 s, 2 MB, HTML only, ports 80/443, no cookies or personal data sent, `trust_env=False`. Page content wrapped in the existing delimited data block in both prompt modes. Logs keep host and counts only. Invented fixtures only. | Pass |
| 5. No AI shortcuts | Draft is never saved without Save. Images: constitution 2.0.0 (2026-11-04) stores an image only where a story says so, with a size limit and a format check; this story stores the page's main photo as the recipe image, ≤ 300 KB, JPEG/PNG/WebP (research R9). | Pass |
| 6. Testing | Domain tests first, fakes for every port, Compose integration, vitest, browser walk, AI evaluation pages. | Pass |
| 7. Deployment | No proxy, TLS or server config. Two new settings documented in `.env.example` and the README. | Pass |
| 8. Git discipline | Migration through Alembic; no push without review. | Pass |
| 9. Scope | Capture from URL is a Must (Appendix C). Rendering pages (S-066) stays Later. | Pass |

No violation needs the Complexity Tracking table. The two open items of the first draft were settled by the owner on 2026-11-04: trafilatura is approved, and constitution 2.0.0 lifted the MVP photo rule.

## Design overview

```text
POST /notebooks/{id}/captures/url {url}
  → CaptureRecipeUrl (application/recipe_capture_url.py)
     1. domain.page_link.normalize_link / check_link          → link_* | page_fetch_failed
     2. notebook visible, kitchen not archived                → 404 | 409
     3. PageFetcher.fetch_page(url)                           → page_fetch_failed
     4. PageReader.read(html, final_url) → PageContent
        start PageFetcher.fetch_image(main_image_url) in parallel (≤ 5 s, None on failure)
     5a. exactly 1 schema.org Recipe with ingredients
           → whole-mode extract(markdown_from(page_recipe)) → apply_page_recipe (title, steps, servings)
     5b. ≥ 2 Recipe items                                     → one_recipe_at_a_time
     5c. else markdown → split_markdown(batch_chars, max_batches)
           1 batch  → whole-mode extract (NotARecipe → page_no_recipe)
           n batches→ PAGE_PART extract × n at the same time → merge_parts → check_draft
     6. CapturedPageDraft{recipe, notebook, catalog, source_url, preview_image, page_cut}
```

Partial page mode (owner request): a second system template and response schema in the Gemini adapter, selected by `mode=ExtractionMode.PAGE_PART`; the whole-recipe prompt and schema used by text capture are not touched (contracts/ports.md).

## Project Structure

### Documentation (this feature)

```text
specs/026-capture-recipe-url/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R13
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-url-api.md
│   └── ports.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, not created here
```

### Source Code

```text
api/
├── domain/
│   ├── page_link.py                 # new: link rules, is_public_address
│   ├── recipe_page.py               # new: PageRecipe, recipes_from_jsonld, parse_yield,
│   │                                #      markdown_from, apply_page_recipe, split_markdown, merge_parts
│   └── recipe_preview.py            # new: validate_preview_image (like domain/photo.py)
├── application/
│   ├── ports.py                     # + PageFetcher, PageReader, FetchedPage, PageFetchFailed,
│   │                                #   FetchedImage, PageContent
│   ├── recipe_extraction.py         # + ExtractionMode, DraftPart, NoRecipeContent; mode/part pass-through
│   ├── recipe_capture_url.py        # new: CaptureRecipeUrl use case
│   └── recipe_save.py               # + source_url, preview_image
├── adapters/
│   ├── llm/gemini_extractor.py      # + PAGE_PART schema and payload mapping
│   ├── llm/prompt.py                # + page_part_system_instruction, part line
│   ├── llm/prompts/recipe_extraction_page_part_system.md   # new
│   ├── llm/fake_extractor.py        # + mode, part in ExtractionCall
│   ├── web/__init__.py              # new folder named in PRD §1.4
│   ├── web/page_fetcher.py          # new: HttpxPageFetcher
│   ├── web/fake_page_fetcher.py     # new
│   ├── web/jsonld.py                # new: html.parser for ld+json blocks and og:image
│   ├── web/page_reader.py           # new: TrafilaturaPageReader (+ FakePageReader)
│   └── persistence/
│       ├── models.py                # + RecipeModel.preview_image_base64
│       ├── recipes.py               # add(): url source, preview; copy_all copies preview; detail reads it
│       └── migrations/versions/0015_recipe_preview_image.py   # new
├── api/
│   ├── routes/recipe_capture.py     # + POST /notebooks/{id}/captures/url, new codes
│   ├── routes/recipes.py            # save body and detail response fields
│   ├── schemas/recipe_capture.py    # + CaptureUrlBody
│   ├── schemas/recipes.py           # + source_url, preview_image
│   ├── deps.py                      # + get_capture_recipe_url, fetcher and reader wiring
│   └── settings.py                  # + RECIPE_PAGE_BATCH_CHARS, RECIPE_PAGE_MAX_BATCHES
└── tests/
    ├── fixtures/pages/              # new: invented HTML pages and two small invented photos
    ├── test_page_link_domain.py
    ├── test_recipe_page_domain.py
    ├── test_recipe_preview_domain.py
    ├── test_page_fetcher_adapter.py
    ├── test_page_reader_adapter.py
    ├── test_recipe_capture_url_application.py
    ├── test_recipe_capture_url_integration.py
    ├── test_recipe_preview_migration.py
    └── (extended) test_gemini_extractor_adapter.py, test_prompt_characterization.py,
        test_recipe_extraction_application.py, test_recipe_save_*.py, test_recipe_manage_integration.py,
        test_notebook_snapshots_integration.py

ui/
├── app/api/notebooks/[notebookId]/captures/url/route.ts   # new BFF route (+ test)
├── components/AddRecipeCallToAction/
│   ├── AddRecipeOptionsDialog.tsx   # URL enabled, opens the link sheet
│   ├── UrlCaptureSheet.tsx          # new (+ test): one field, submit, field messages, cauldron loader
│   └── AddRecipeCallToAction.tsx    # route the URL option to the sheet
├── components/RecipeDraft/RecipeDraftEditor.tsx  # photo with remove control, long-page note
├── components/RecipeDetail/RecipeDetailView.tsx  # preview image at the top (source link already shown)
├── lib/capture/
│   ├── linkRules.ts                 # new (+ test): same rules as domain/page_link.py for the button
│   ├── captureClient.ts             # + submitLinkCapture, page fields
│   ├── captureStore.ts              # + source kind, link, preview, pageCut
│   └── saveClient.ts                # + source_url, preview_image
├── lib/imageEncode.ts               # + encodeRecipePreview (800 px, JPEG, ≤ 300 KB)
└── lib/i18n/capture.ts, recipeDetail.ts   # English and Spanish strings (parity test)
```

**Structure Decision**: The existing api hexagon and ui BFF layout. The only new folder is `api/adapters/web/`, which PRD §1.4 already names (`web/page_fetcher.py + web/jsonld.py`).

## Post-design Constitution Check

Re-checked after research, data model and contracts: no new service, queue or background worker; every network call is in `adapters/web/` behind `PageFetcher`; `domain/` stays pure (stdlib `ipaddress`, `json` values passed in, no I/O); the whole-recipe prompt and schema are unchanged; nothing is stored before Save; no page text is stored. No open items remain.

## Follow-ups outside this plan

- PRD updates when the story is done (spec Assumptions): §1.7 table (`page_no_recipe` message, ports 80/443), §4 "No crawling" (page and its one main photo), §1.10 and J2 (URL no longer disabled), §1.6 (preview image filled by link capture).
- Backlog: S-026 to `in_progress` when implementation starts; S-047 cards and S-067 (recipe image) build on `preview_image_base64` and `domain/recipe_preview.py`.
- `dev/docs/backlog.yaml` S-019 note: recipes saved from links are embedded like any other save (no change needed).

## Complexity Tracking

No constitution violations to justify.
