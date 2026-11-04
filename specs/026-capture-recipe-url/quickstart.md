# Quickstart: validate link capture (spec 026)

Run everything in this worktree's own Compose project (`./scripts/compose-up.sh -d`, UI on port 3090). Never start a second project with the main `.env` (shared pgdata). No automated test opens a real website: they use saved, invented pages through `FakePageFetcher`. The manual walk (steps 6 to 9) uses public recipe pages the tester picks, because the address checks refuse any page served from this machine or the Docker network.

## 1. Prerequisites

- The owner approved adding `trafilatura` (research R6) and it is in `api/uv.lock`.
- Migration 0015 applied: `docker compose exec api uv run alembic upgrade head`.
- `.env` has `GEMINI_API_KEY` and `GEMINI_CHAT_MODEL` for steps 6 to 9 (steps 2 to 5 need no key).
- Fixtures in `api/tests/fixtures/pages/`: invented recipe pages (with schema.org data, without, schema.org without ingredients, two Recipe items, a long blog page with comments, a page with no recipe, a script-only page) and two small invented photos.

## 2. Automated checks

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm api uv run pytest -q
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm api uv run ruff check .
cd ui && npm run lint && npm run typecheck && npx vitest run
```

Expected: all green except the known baseline failures listed in the backlog (paste-limit tests when `RECIPE_TEXT_MAX_CHARS=10000`). New suites to look for: `test_page_link_domain`, `test_recipe_page_domain` (JSON-LD mapping, splitting, merging, SC-009), `test_page_fetcher_adapter` (SC-003 address set, redirects, size, type, timeout), `test_page_reader_adapter`, `test_recipe_capture_url_application`, `test_recipe_capture_url_integration`, `test_recipe_preview_migration`, `test_prompt_characterization` (shared rule block).

## 3. Migration round trip

`alembic downgrade 0014_recipe_embeddings && alembic upgrade head` on a scratch database with invented recipes: rows unchanged, `preview_image_base64` null.

## 4. Address safety by hand (SC-003)

With the stack running, through the BFF as a signed-in invented member, POST `/api/notebooks/{id}/captures/url` with each of: `http://127.0.0.1/`, `http://localhost:8000/health`, `http://[::1]/`, `http://169.254.169.254/latest/meta-data/`, `http://10.0.0.1/`, `http://db:5432/`, `http://api:8000/health`, `https://example.test:8080/`, `https://user:pw@example.test/`, `file:///etc/passwd`. Expected: 422 `page_fetch_failed` (or `link_invalid` for `file:`), and the api log shows no connection to the target.

## 5. Saved pages through the fake fetcher (no key needed)

`test_recipe_capture_url_integration` swaps `PageFetcher` for `FakePageFetcher` loaded with the fixtures and `RecipeExtractor` for `FakeRecipeExtractor`. Expected outcomes per fixture: schema.org page → draft title and steps equal the data (AC2.3, SC-001); two Recipe items → `one_recipe_at_a_time`; PDF → `page_fetch_failed`; page over 2 MB → `page_fetch_failed`.

## 6. Browser walk: capture and save (needs a key)

Follow the Playwright-on-host note in memory (no browser in WSL). At 360 px and 1280 px, English and Spanish:
1. Notebook → add-recipe tile → URL is enabled; Picture still disabled.
2. Empty field: Submit disabled. `example` → "Paste a link that starts with http:// or https://". A 2,049-character link → "That link is too long."
3. Paste a schema.org recipe page link → cauldron loader → draft with title, servings without the "estimated" badge, lines with matched/new labels, the photo at the top with a remove control.
4. Back → link sheet with the link unchanged. Submit again → Save → recipe detail shows the photo and a link to the page that opens in a new tab.
5. Discard on another capture → empty link sheet.

## 7. Messages (SC-004)

A link to a page that returns 404 → "We couldn't open that page. Paste the recipe text instead." A page with no recipe → "We couldn't find a recipe on that page. Paste the recipe text instead." With `GEMINI_API_KEY` emptied → "Assistant misconfigured. Your link is kept". The link stays in the field every time.

## 8. Long page in batches (SC-009)

A long public recipe blog page (Markdown over 10,000 characters after cleanup; the api log shows `batches=` above 1): the draft has every expected line and step once, in order. With `RECIPE_PAGE_MAX_BATCHES=1` the draft shows "This page was long, so part of it was not read. Check the ingredients and steps."

## 9. Timing (SC-002)

Ten link captures of the long page from step 8: each shows a draft or a message within 22 s. Record the times in `specs/026-capture-recipe-url/notes.md`.

## 10. Evaluation set (SC-006)

At least 5 saved, invented pages from different site layouts, English and Spanish, with and without schema.org data, plus one with no recipe, in `api/tests/fixtures/ai_eval/` (S-034). At least 90% correct title, servings and lines.
