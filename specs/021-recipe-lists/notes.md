# Notes: Recipe Lists (S-021)

## Baseline (before this feature, 2026-10-27)

- api (`uv run pytest -q`, no `DATABASE_URL`): 426 passed, 185 skipped. `ruff check`: clean.
- ui (`npm test`): 71 files, 412 tests passed. `npm run typecheck`: clean.
- Compose test overlay (Postgres, `melos_test`): `tests/test_recipe_capture_integration.py` already fails 2 tests
  before this feature (`test_empty_and_too_long_text_are_refused_with_no_assistant_call`,
  `test_vocabulary_lists_the_controlled_values`): the local `.env` sets a text limit of 10000 where the tests
  expect 5000, and the vocabulary is MVP-OUT. Not related to S-021.

## After the api work

- Compose test overlay: all new `test_recipe_lists_integration.py` and `test_unaccent_migration.py` tests pass;
  the only other failures are the two above.
- Do not run `ruff format .` on the whole api: it reformats eight unrelated files. Format only touched files.
