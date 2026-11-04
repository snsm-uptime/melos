# Implementation notes: capture a recipe from a URL (spec 026)

Recorded 2026-11-04 on `worktree-26`, in this worktree's own Compose project (`melos-26`,
its own data folder).

## Automated checks (T057)

| Suite | Result |
|---|---|
| api, `./scripts/compose-test.sh uv run pytest -q` | 1910 passed, 4 failed |
| api, `ruff check .` and `ruff format --check .` | clean |
| ui, `npx vitest run` | 1387 passed (160 files) |
| ui, `npm run lint`, `npm run typecheck` | clean |

The 4 api failures are environment failures, in files this spec does not touch:
- `test_gemini_embedder_adapter::test_live_model_returns_768_values` (live service call).
- `test_recipe_capture_integration::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
  and `::test_vocabulary_lists_the_controlled_values`: the known baseline with
  `RECIPE_TEXT_MAX_CHARS=10000` in `.env`.
- `test_shopping_list_integration::test_a_saved_and_a_closed_list_keep_a_custom_line`: "That
  closing date isn't today." (date at the time of the run).

## Migration and address safety (T058, quickstart 3 and 4)

- Dev database: `alembic downgrade 0014_recipe_embeddings && alembic upgrade head` ran clean; head
  is `0015_recipe_preview_image`. The test database round trip is `test_recipe_preview_migration`.
- Through the BFF on :3090 as an invented member, all 19 links were refused with 422
  `page_fetch_failed` (`link_invalid` for `file:`), body `{detail: "", code}` only, each under
  0.6 s: 127.0.0.1, localhost (port 80 and 8000), [::1], 169.254.169.254, 10.0.0.1, db, api, ui,
  host.docker.internal, db:5432, api:8000, example.test:8080, user:pw@, [fd00:ec2::254],
  100.64.0.1, 0.0.0.0, [::ffff:127.0.0.1], file:///etc/passwd. The api log shows
  `kind=blocked host=…` only, no path, query or resolved address, and no request was sent.

## Browser walk (T059, quickstart 6 and 7)

Playwright 1.64.1 headless on the host (libraries copied from the local Playwright image), against
the worktree stack, on a public schema.org recipe page. 15 checks per run, all passed:

| Run | Result |
|---|---|
| English, 1280 px | 15/15 |
| Spanish, 360 px | 15/15 |
| English, 360 px, keyboard only | 15/15 |

Checks: URL enabled and Picture disabled; empty field disables submit; `example` and a
2,049-character link show their field messages; a 404 page shows "We couldn't open that page…"
and keeps the link; the cauldron loader shows while waiting; the draft shows the page photo with a
remove control; Back keeps the link; Save stores the recipe; the detail shows the photo and a
source link with `target=_blank rel="noopener noreferrer"`; Discard leaves an empty link sheet.
Not walked in the browser: the long-page note (covered by vitest) and the "Assistant
misconfigured" message with the key emptied (covered by vitest and the integration test).

## Long page and timing (T060, quickstart 8 and 9)

- The schema.org path on a public blog page: draft in 4.1 s, 17 lines, 6 steps, photo.
- Batches on a public page with no schema.org data (Wikibooks "Paella Valenciana", 5,280
  characters), with `RECIPE_PAGE_BATCH_CHARS=1500` set for the run: `batches=4 cut=True`, draft in
  4.7 s with 17 lines and 10 steps in order, no repeated line.
- Ten timed runs of that page: runs 1 and 2 gave drafts in 4.9 s and 2.9 s; runs 3 to 10 hit the
  key's usage limit and showed the limit message within 3.2 s. Every run answered well within
  22 s, but SC-002 is not shown for ten drafts in a row. Each long page sends up to 4 requests at
  once, so this key allows about two long captures in quick succession.
- Found and fixed during the walk: the Gemini client was created lazily without a lock, so the
  first parallel batch after an api start failed with "client has been closed" (now locked, with a
  test). trafilatura's `deduplicate=True` emptied a page read three times in one process (now off,
  with a test).
- Wikibooks "Lasagna" first gave `draft_incomplete` (missing title) in 1,500-character batches.
  Changed on the owner's request (2026-11-04): an incomplete link draft now opens with what the
  page gave, and the draft form marks the missing title, steps or amounts (Save stays disabled
  until they are filled). Lines are then not matched to the catalog, and missing servings take
  the default, marked estimated. Text capture is unchanged. With the default batch size the same
  page now reads as one batch and the model answers `page_no_recipe`.

## Evaluation set (T061, SC-006)

Six invented pages in `api/tests/fixtures/ai_eval/pages/` (`CASES.md`), run with
`api/scripts/eval_link_capture.py` and the real model, twice:
- English schema.org, English table, English plain lines, Spanish blog: right both times (servings
  of the plain-lines page right but marked estimated; once "rama de canela" as a name).
- Spanish schema.org page: refused two times in three; the model left quantity and unit off
  "1 cebolla", "2 zanahorias" and "1 pimiento rojo". This comes from the whole-recipe prompt,
  which this spec keeps unchanged.
- The no-recipe page: `page_no_recipe` (second run hit the usage limit).

Score about 75% of checked values, below the 90% target. Needs an owner decision on the
whole-recipe prompt for Spanish counted items (likely also affects text capture; not checked).

## Other

- The dev user seed fails at api start: `SaveRecipeDraft.__init__() missing … 'units'`
  (`api/scripts`, older than this spec).
