# Implementation notes: S-018 Match captured ingredient names

## Baseline (T001, before any change, 2026-10-26)

- api, host (`uv run pytest -q`): 368 passed, 1 failed, 149 skipped. The failure predates this work:
  `test_vocabulary_copies_in_domain_match_dev_docs[categories.yaml]`. `api/domain/categories.yaml` and
  `dev/docs/categories.yaml` differ from byte 4852 on. Not fixed here.
- api, ruff: clean.
- ui (`npx vitest run`): 376 passed. `npm run lint` and `npm run typecheck`: clean.

## Final checks (T038, 2026-10-26)

- api, host: 403 passed, 1 failed (the same pre-existing copy drift), 152 skipped (no database on the host).
- api, Compose test overlay (`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`):
  554 passed, 2 skipped, 0 failed, with `RECIPE_TEXT_MAX_CHARS=5000` passed on the command line.
  Without that override, two existing tests in `test_recipe_capture_integration.py` fail
  (`test_empty_and_too_long_text_are_refused_with_no_assistant_call`, `test_vocabulary_lists_the_controlled_values`):
  the root `.env` sets `RECIPE_TEXT_MAX_CHARS=10000`, and the tests expect 5000. This is a `.env` setting,
  not a code change; left as it is.
- api, ruff: clean. `ruff format` is not applied to `api/domain/recipe_draft.py`, which was already unformatted
  before this work.
- ui: 391 passed, lint and typecheck clean.
- Prompt templates ship in the API image: `/app/adapters/llm/prompts/` holds `README.md`,
  `recipe_extraction_system.md` and `recipe_extraction_user.md`, and `load_template` reads them.

## Decisions made during implementation

- T018 (fake extractor): no change. `FakeRecipeExtractor` returns the scripted result, so the new fields go
  into the scripted drafts in the tests.
- T028 and T029: the change list is derived in `ui/lib/capture/nameChanges.ts`, and the undo and
  match helpers are in `captureStore.ts` (`undoLineChange`, `chooseLineMatch`, `undoChange`, `chooseMatch`).
- `text_name` is always set after the check, falling back to the assistant's name. Undo returns a line to
  this name (spec US2 scenario 2 reads "onions").
- `match_line` returns a `LineMatch` in every case (never `None`), which is simpler for callers than the
  `LineMatch | None` the tasks described.
- The `-ves` singular rule applies to the last word of a name, so "bay leaves" → "bay leaf".

## Not done (needs a person or a live model)

- T039 (SC-004 evaluation): the fixtures are in `api/tests/fixtures/ai_eval/matching/` with the expected entries
  in `CASES.md`. The live model run and the count are still to do. It needs the Gemini key and a person to
  check the labels. Target 90%.
- T040 (browser walkthrough, quickstart §4): not run. A capture needs the live model to return a draft.
- T042 (backlog status to `done`): waits for T039 and T040, so `dev/docs/backlog.yaml` stays at `in_design`.
