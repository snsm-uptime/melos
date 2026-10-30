# Notes: Consolidated Shopping List (S-023)

## Baseline (2026-10-30, before any change of this story, HEAD 44aac52)

- api, Compose test overlay (`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`): **803 passed, 5 failed**. The 5 failures are the ones already named in the S-022 verification in `dev/docs/backlog.yaml`, none touched by this story:
  - `test_notebook_integration.py::test_capture_auto_selects_user_notebook_or_creates_one`
  - `test_notebooks_application.py::test_kitchen_capture_with_no_notebook_creates_one_and_commits_once`
  - `test_notebooks_application.py::test_kitchen_capture_creates_user_notebook_on_first_capture`
  - `test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
  - `test_recipe_capture_integration.py::test_vocabulary_lists_the_controlled_values`
- api, `uv run ruff check .`: 4 errors already on HEAD (none in this story's files).
- ui: 126 test files, **888 tests passed**; `npm run lint` and `npm run typecheck` clean.
- Environment: the test database `melos_test` did not exist after the dev stack was restarted by other work; it was recreated with `docker compose exec db createdb -U $POSTGRES_USER melos_test`.
- Unrelated uncommitted changes were already in the working tree during this work (dev-seed accounts: `.env.example`, `README.md`, `api/scripts/*`, `docker-compose*.yml`). They are not part of this story and were left as they are.

## Result (2026-10-30, branch `023-shopping-list` work, not committed)

- api, Compose test overlay (full suite, image rebuilt): **903 passed, 5 failed**. The 5 failures are the same 5 as the baseline; this story adds 100 tests, all passing:
  - `test_shopping_list_domain.py` (38: AC5.1–AC5.4, rounding after the sum, ordering, chips, "Your call"),
  - `test_shopping_list_carts.py` (21: the 20 hand-calculated carts of SC-004 and a count check),
  - `test_shopping_list_application.py` (22: saved cart, draft vs saved, deleted recipes, 404, archived, read only),
  - `test_shopping_list_integration.py` (19, over HTTP with Postgres: shape, two members, draft/discard/save, People changes, edited ingredients, read-only, 100 × 20 lines).
- api, ruff: the 4 errors already on HEAD (all in `test_notebook*.py`); none in files of this story, which are also `ruff format` clean.
- ui: **131 files, 929 tests passed** (888 before); `npm run lint` and `npm run typecheck` clean. `parity.test.ts` covers the new `shoppingList` message set in es and en.
- No migration, no table, no write: the route only reads.
- SQL statements for a cart of 100 recipes × 20 lines: at most 10 touching `cart`, `recipe` or `recipe_ingredient` (asserted), and the request answers in under 1 second (asserted, measured in the test harness over HTTP against the Compose Postgres, not on the dev stack).
- Logging (T049): the only log call is `shopping list outcome=built draft=… recipes=… lines=… your_call=…` (counts and a boolean); no ingredient name, note or title is logged. Tests use invented names only.

## Not done

- **Browser walk of `quickstart.md` section 2 (T047)**: not run. This session has no browser; the dev stack that was running is a built image of HEAD without this story. Still to check by a person: the layout at phone width (about 360 px: chips wrap, no sideways scroll), keyboard-only use (Tab to each chip, Enter), Spanish text on the page, the tap-a-chip-then-Back round trip, and the two-account draft/saved walk (steps 6–10). The same behaviours are covered by vitest and by the HTTP tests above.
- **Timed 100 × 20 read on the dev stack (T048)**: not run, for the same reason. The in-test timing above is the only measurement.
- Tasks T029, T037 and T043 each end with a look at the dev stack; their automated parts passed, the dev-stack part is open for the same reason.

## Decisions taken while implementing

- The Spanish wording "A tu criterio" (Your call) is still for the owner's review.
- A total that rounds to 0 at 2 decimals (for example 0.25 tsp at factor 1/99) shows as `0`, as FR-006 reads literally (research R5, open edge).
- Vague notes are compared after trimming and ignoring letter case, and the first spelling is shown (research R7).
- The ui fetches the list inside a cancellable effect keyed on the cart state, which drops stale answers and keeps the previous list on screen while the next one loads. The eslint rule `react-hooks/set-state-in-effect` rejected the first version, which called a local async function from the effect.

## Amendment 2026-10-30: cart by servings

- Migration `0008_cart_servings`: tested in `api/tests/test_cart_servings_migration.py` (People × Meals, member-count default, cap at 99, locks cleared, downgrade, upgrade again). It is not applied to the dev database by this work.
- api, Compose test overlay: see the backlog verification. Only the 5 baseline tests fail. ruff: the same baseline errors, in `test_notebook*.py` only.
- ui: 947 tests passed; lint and typecheck clean.
- The `recipe_edit_lock` part of T051 is not asserted: the migration's only lock statement targets `cart_edit_lock`.
- Tests were updated with the code rather than strictly first (T051 to T072).
- The existing `ui/components/IconButton` has `tone="danger"`, used for Remove.

### Not done

- T078's browser walk, `quickstart.md` amendment section: selected card contrast in both themes, `CountField` error at 360 px, keyboard and screen reader on the close button, Spanish wording "Porciones". Also T047 and T048 above, which now apply to the servings version.
