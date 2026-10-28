# Quickstart: Validate Capture from Pasted Text

> **Scope change 2026-10-27:** main ingredients and cuisines are out of the MVP (backlog S-061, PRD Appendix E). Anything below about them (main ingredient keys, cuisine scoring, category chips, the `main_ingredients` and `cuisines` fields, the category lists of `GET /recipe-vocabulary`) is not in force; the code is commented out under `MVP-OUT:`. Ingredient catalog matching (S-018) is unchanged. Plan: `dev/docs/mvp-descope-categories.md`.

How to check that S-016 works end to end. Shapes and codes are in
[contracts/capture-api.md](./contracts/capture-api.md) and
[contracts/capture-ui.md](./contracts/capture-ui.md). State is in
[data-model.md](./data-model.md).

## Prerequisites

- Docker with Compose v2, `uv`, Node/`npm` (AGENTS.md "Development environment").
- `.env` from `.env.example`. A real `GEMINI_API_KEY` is needed only for the
  manual AI checks (section 4). Automated tests use `FakeRecipeExtractor`.
- Two invented accounts with aliases, for example `ana@example.test` and
  `beto@example.test`. Ana owns kitchen "Test Kitchen". Beto is not a member.
  A second kitchen owned by Ana is archived.

## 1. Automated checks

```bash
# api, canonical (Postgres + migrations + fake extractor)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api

# api lint
cd api && uv run ruff check .

# ui
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: all green. The api suite includes:

| Test module | Proves |
|-------------|--------|
| `test_labels_domain.py` | `pick_label` uses the member's language and falls back to the other. (Notebook tests are in spec 056.) |
| `test_recipe_draft_domain.py` | `preparation` kept, trimmed, blank becomes None. |
| `test_recipe_capture_application.py` | A capture sends only its notebook's catalog. Another member's notebook, a missing notebook and a kitchen notebook of a non-member all give `NotebookNotFoundError` before any catalog read or extractor call. Archived → `KitchenArchivedError` with zero extractor calls. Too long → refused with zero extractor calls. Each S-015 result passes through. |
| `test_recipe_capture_integration.py` | Each route answers each status and `code` in the contract. 404 bodies are the same for a missing kitchen and a non-member. `Retry-After` is present when hinted. Row counts of `ingredient` (and later recipe tables) are unchanged after every capture (SC-005, SC-008). |

## 2. Migration

```bash
./scripts/compose-up.sh -d
docker compose exec api uv run alembic current    # expect 0003_notebooks_ingredients (head)
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select count(*) from notebook;"          # one per kitchen and per user with an alias (spec 056 backfill)
```

## 3. Browser walkthrough (with the fake or a real key)

Start the stack with `./scripts/compose-up.sh -d`, then open
<http://localhost:3000> and sign in as Ana.

| # | Do | Expect | Spec |
|---|----|--------|------|
| 1 | Tap the Notebook tab in the bottom bar. | Notebook page, Notebook tab marked current, the call to action below the header. | US1-1, FR-001b |
| 2 | Open Test Kitchen, then choose its Notebook tab. | Header "Test Kitchen", the same call to action. Members tab still works. | US1-2, FR-001b |
| 3 | Tap the plus. | Dialog without buttons: URL (disabled, not available yet), Picture (disabled, coming soon), Text, separated by dividers. Escape closes it and nothing changes. | US1-3, FR-023 |
| 4 | Choose Text. | Sheet titled "Test Kitchen", empty input, submit disabled. | US1-4 |
| 5 | Paste `api/tests/fixtures/ai_eval/salt_and_onion.txt` and submit. | Progress state, then the draft page: title, servings 4 with "estimated", no main-ingredient chip, cuisine "International", salt with no amount and note "a pinch", onion `2 unit large`, at least one step. | US1-5 to US1-8, AC2.1 |
| 6 | Edit the title, then tap the Home tab. | "Leave without saving? Your changes to this draft will be lost." Stay keeps the edit. | US1-11, FR-032 |
| 7 | Tap Back. | Sheet with the pasted text unchanged. | US1-10, FR-031 |
| 8 | Submit again, then tap Discard. | Sheet open with an empty input. | US4 |
| 9 | Make a line measured with no quantity, add a third cuisine, remove all steps. | Message next to the line, cuisine picker hidden at two, "Add at least one step." | Edge cases, FR-013 |
| 10 | Paste `weather_question.txt` and submit. | "That doesn't look like a recipe." + reason, text kept, no draft. | US2-1/2, AC2.4 |
| 11 | Paste `two_recipes.txt`, then `sauce_subsection.txt`. | "Upload only one recipe at a time", then one draft. | US2-3/4 |
| 12 | Paste 10,001 characters. | Submit disabled and the too-long message shown. | FR-002 |
| 13 | Reload the draft page. | Browser leave warning if edited, then the Notebook page with no draft. | Edge cases |
| 14 | Open the archived kitchen's Notebook tab. | No call to action. | FR-033 |
| 15 | As Beto, open `/kitchens/<Test Kitchen id>/notebook`. | Not-found view. | FR-022 |

Set Ana's language to Spanish in her account: the chips on the next draft read in Spanish.

Failure messages (US3), with the fake extractor scripted per case in a dev
override, or by setting `GEMINI_TEXT_TIMEOUT_S=0.01` (unavailable) and an empty
`GEMINI_API_KEY` (misconfigured):

| Case | Expect within 12 s, text kept |
|------|-------------------------------|
| Timeout or unreachable | "The assistant isn't responding. Your text is kept — try again." |
| Usage limit | "We've hit the assistant's limit. Try again in a minute." |
| Unreadable result | "We couldn't read that recipe. Try rephrasing or adding detail." |
| No key or model | "Assistant misconfigured. Your text is kept" |

Restore `.env` afterwards.

## 4. Manual AI evaluation (real key, not CI)

Run each file in `api/tests/fixtures/ai_eval/` through the ui 10 times (SC-002)
and compare each draft with the expected draft (SC-006: at least 90% correct
title, servings and lines). Check that `injected_instruction.txt` does not
change the draft's behaviour (FR-021). Record the results in `dev/memory/`.

## 5. Data unchanged

Open the Notebook page once and take these counts first, because that first visit creates the member's notebook (spec 056). After the walkthrough, every count should be the same as that baseline:

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select (select count(*) from ingredient) as ingredients, (select count(*) from notebook) as notebooks;"
```
