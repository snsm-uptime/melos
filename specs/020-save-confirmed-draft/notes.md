# Notes: S-020

## Baseline (2026-10-27, before any S-020 change, branch main)

- api (Compose test overlay): 544 passed, 2 failed, ruff clean. The 2 failures already existed:
  `tests/test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call` and
  `::test_vocabulary_lists_the_controlled_values`.
- ui: 392 vitest tests passed (70 files), lint and typecheck clean.
  Cause of the 2: the Compose env sets a 10000-character text limit where the tests expect 5000. Not related to S-020.

## Result (2026-10-27)

- api (Compose test overlay): 609 passed, 2 failed (the same 2 as the baseline), ruff clean. New: 11+1 domain, 20 application, 17 integration, 12 migration tests.
- ui: 412 vitest tests passed (71 files), lint and typecheck clean.
- T020: the concurrent-save case is covered by two deterministic tests (repository raises `DuplicateSaveKeyError` and the session stays usable; `add_names` twice leaves one row) instead of two real threads.
- T030: no change needed. Spec 016 FR-019 describes spec 016 only and already points to S-020 for Save.

## Decisions made while building

- A line's `note` is stored as `vague_note` only on vague lines (PRD 1.6 line rules); a note on a measured line is dropped.
- A vague line with no note is refused (`invalid_recipe`); the ui shows "Write the amount in words" on such a line and keeps Save disabled.
- The notice "Recipe saved" is keyed by the page path it returned to (not the notebook id), so the personal tab and a kitchen page each show it once.

## Verification

- Not done: the browser walk of quickstart sections 2 to 5 (no browser tool in this session, and migration 0005 is not applied to the dev database). Run `./scripts/compose-restart.sh` (or restart the api container) to apply it, then walk the quickstart.
