# Notes: S-022 implementation

## Baseline (T001, 2026-10-29)

- The Compose test database `melos_test` did not exist; created with
  `docker compose exec db createdb -U $POSTGRES_USER melos_test` (as the overlay documents).
- api (Compose test overlay, run with domain/cart.py, models and migration 0007 already in the
  tree): **751 passed, 6 failed**.
  - Known (S-027 verification): `test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
    (limit 10000 vs 5000), `::test_vocabulary_lists_the_controlled_values` (MVP-OUT).
  - Failing on HEAD (commit 88986a0, per-member kitchen notebooks), not this feature:
    `test_notebooks_application.py::test_kitchen_capture_with_no_notebook_creates_one_and_commits_once`,
    `::test_kitchen_capture_creates_user_notebook_on_first_capture`,
    `test_notebook_integration.py::test_capture_auto_selects_user_notebook_or_creates_one`.
  - Expected from the new FKs, fixed by T047: `test_recipe_manage_integration.py::test_only_the_lines_and_steps_point_at_recipe_ids`.
- ruff: 4 errors, all on HEAD in `tests/test_notebook_integration.py` (F401, 2× E501) and
  `tests/test_notebooks_application.py` (F841).
- ui: vitest 108 files / 789 tests passed; lint clean; typecheck clean.

## Migration (T006)

- Scratch database `melos_scratch_022` (created and dropped): `alembic upgrade head` →
  `0007_cart_and_edit_locks`, `downgrade 0006_unaccent` → `0006_unaccent`, `upgrade head` →
  `0007_cart_and_edit_locks (head)`. All three steps ran without error.

## Final run (T051)

- api (Compose test overlay): **803 passed, 5 failed**. The 5 are baseline failures (2 known, 3 on
  HEAD). The schema guard test now passes with `cart_item` and `recipe_edit_lock` in its list.
- ruff: the same 4 baseline errors, none new.
- ui: vitest 123 files / 877 tests passed (baseline 108 / 789); lint clean; typecheck clean.

## Browser walk (T052): not done

- Not walked in a browser. The quickstart §1–§6 walk with two accounts at phone and desktop
  width, in Spanish and English, still has to be done by hand against the dev stack once migration
  0007 is applied to the dev database (restarting the api applies it).
- FR-016 (the detail page's servings control never changes the cart factor) is covered by
  application tests only: the cart reads `recipe.base_servings` and never writes it.
- SC-008: the integration test reads a 100-entry cart with all factors in at most 5 SQL
  statements (cart row, items, recipe facts, member count, live lock). Timing on the dev stack
  was not measured.

## Deviations from tasks.md

- `EditLockRepository` also has `now()` (the clock liveness uses), so the fakes can drive the
  idle limit.
- Application services are one class per use case sharing a small base (`_CartUseCase`) rather
  than separate constructors.
- `recipe_locks.AcquireRecipeLockService` imports `_recipe_for` inside `execute`, because
  `recipe_manage` imports the lock rules from `recipe_locks` (avoids an import cycle).
- In the Cart editing view, the debounced `PUT …/draft` is the activity that renews the lock;
  no separate keep-alive is sent from the view. The editing bar's **Keep editing** and the recipe
  edit page use `useLockKeepAlive`.
- `RecipeEditForm` gained two optional props, `onLockLost` and `onSaved`, so a 409
  `recipe_locked`/`not_editing` keeps the typed edits and the page explains it, instead of the
  "recipe changed" message.
- Other uncommitted ui changes seen during the work (`RecipeDraft/*`, `HeaderActions.tsx`, parts of
  `RecipeDetailView.tsx` and `RecipeEditForm.tsx`) are not from this feature and were left as found.

## UI clarification run (T063, 2026-10-29)

- ui: vitest 126 files / 887 tests passed; lint clean; typecheck clean.
- api (Compose test overlay): 803 passed, 5 failed (the same 5 baseline failures); ruff: the same 4
  baseline errors. No api code changed in Phase 9.
- Found while testing: `useToast()` first returned a new object on every toast change, which made
  `useCartIdleToasts` re-show its toast in a loop; it now returns an object that stays the same
  while the provider lives. The Cart page's docked bar is memoized for the same reason.

## Browser walk (T064): not done

- Not walked in a browser; see the T064 checklist in tasks.md (icon "+" → "×", no message on
  success, the refusal toast above the tab bar, the bar only on the Cart page, idle toasts on the
  kitchen list, FR-016, SC-008 timing). Restarting the dev api applies migration 0007.
