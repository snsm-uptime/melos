# Notes: Create, rename and delete notebooks

## Setup (T001)

Worktree `.env` made by `setup-worktree-unix.sh` with `START_COMPOSE=0`, given only the primary's `.env`. `worktree-bootstrap.sh` was not run as is: this worktree sits inside the primary's `.claude/`, and the bootstrap's `rsync -a --delete` of that folder into the worktree's `.claude/` would copy the worktree into itself and delete tracked skills.

`MCP_HOST_PORT` and `DEBUG_PORT` were added by hand, because the bootstrap does not rewrite them. Project `melos-worktree-059-notebook-rename`, data in `~/melos-wt/melos-worktree-059-notebook-rename`, test database `melos_test` in that project's `db`.

## Baseline at 83adc09

| Check | Result |
|---|---|
| api, Compose test overlay | 1370 passed, 2 failed |
| ui test | 1257 passed |
| ui lint | clean |
| ui typecheck | clean |

Failing before any change (the environment gives a 10000 character limit, the tests expect 5000):

- `tests/test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
- `tests/test_recipe_capture_integration.py::test_vocabulary_lists_the_controlled_values`

## Final checks (T042)

| Check | Result |
|---|---|
| api, Compose test overlay | 1451 passed, the same 2 failed |
| api ruff | clean |
| ui test | 1311 passed |
| ui lint | clean |
| ui typecheck | clean |

## Browser walk (T043)

Headless Chromium through Playwright against this worktree's stack, at 1280px and 360px in English and Spanish: 148 checks passed in the final run, none failed. Every setup included a keyboard-only pass. SC-001: a rename took 387 to 453 ms of machine time. SC-002: an add took 584 to 617 ms. These are scripted times: they show the flow has no slow step, not how long a person takes.

Not walked in a browser:

- Step 6, the pending invite's invalid-link message. Covered by the invite cascade and race tests.
- Step 12, a capture draft open when its notebook is deleted. It needs a real extraction. Covered by the save race tests and by the 404 on the save route.
- The side panel count dropping in step 7. `requestSidePanelRefresh()` is covered by unit tests.

Seen during the walk, and unexplained: in two of the five runs a `PATCH /auth/me` right after register answered 401 while setting up accounts, for accounts of the second setup. It did not recur in the last two runs. The auth routes are not changed by this feature.

## Changes beyond the tasks

- `lock_kitchen` and `lock_notebook` refresh the row they lock. Without it, a read after the lock returns the copy the session already holds, so the archived check and the unchanged name check would use old values.
- `IconButtonPopup` gained arrow keys and returns focus on Escape. The UI contract and FR-020 expect both, and it had neither. The kitchen menu gets them too.
- `NotebookNameDialog` focuses the input itself, because the dialog's focus trap gives focus to Cancel. The create dialog benefits too. The walk found this.
- `NewNotebookCard` follows the Name dialog table for `alias_required`, a redirect where it used to show the failure text.
- `ListKitchenNotebooksService` leaves out a notebook deleted as the list is read, and the capture notebook route answers 404 for one. Both were reachable 500s once kitchen notebooks can be deleted.
- `forwardRecipeRequest` accepts `PATCH`.
- `test_notebook_routes_are_gets_on_the_four_contract_paths` lists the new writes.

## Found, not changed

- `api/scripts/seed_dev_user.py` fails at startup in a fresh stack: `SaveRecipeDraft` needs a `units` argument it does not pass. The entrypoint logs it and carries on.
- `worktree-bootstrap.sh` was unsafe for a worktree under `.claude/worktrees/`: see Setup. It has since been replaced by `scripts/worktree/ensure.sh`.
