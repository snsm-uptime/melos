# Notes: S-035 notebook snapshots

## Test setup

`melos_test` doesn't exist in the Compose db, and a test run there touches the dev pgdata
(see the 30/10/2026 incident in `dev/memory/301026.md`). So every api run below used a throwaway
`pgvector/pgvector:pg16` container on tmpfs, with `uv run pytest -q` on the host. The canonical
Compose overlay command was not run.

## Baseline (T002), commit 0ff1ccc

- api: 969 passed, 0 failed.
- ui (`npm test`): 142 files, 1085 passed, 0 failed.

## Migration (T010)

`0011_notebook_snapshot_key` on a scratch database with invented rows (one personal notebook, one
kitchen notebook, plus one snapshot row added after the upgrade):

- Upgrade from 0010: existing rows kept, all `snapshot_key` null.
- A key on a personal notebook is refused by `ck_notebook_snapshot_is_kitchen`.
- The same key twice in a kitchen is refused by `uq_notebook_kitchen_snapshot_key`.
- Downgrade: the column, check and index go, and rows stay. Upgrade again: rows kept, keys null.
- `alembic check` shows differences on `users`, `sessions` and `cart_item` only. They predate this
  story, and none is on `notebook`.

## Findings (T035)

The independence tests (T032) found nothing to fix. The browser walk found one problem: on a phone
the add cell collapsed to a strip of about 20px, too small to tap. It now has a 44px minimum height,
measured in the browser at 360px.

## Final checks (T043)

Run on a throwaway Postgres, as above. The Compose overlay command in `quickstart.md` was not run.

| Check | Baseline | Now |
|-------|----------|-----|
| api, `uv run pytest -q` | 969 passed | 1029 passed, 0 failed |
| `uv run ruff check .` | | clean |
| ui, `npm test` | 1085 passed | 1119 passed, 0 failed |
| `npm run lint`, `npm run typecheck` | | clean |

## Browser walk (T044): partly done

Headless Chromium through Playwright, on a separate api and a copy of the ui with a throwaway
database and invented accounts, in 4 runs: 360px and 1280px, each in English and Spanish. All 83
checks passed. An earlier run had failures that came from the walk script reading the page too
early, not from the app; the checks were tightened and rerun on fresh data.

| Quickstart step | Result |
|-----------------|--------|
| 1, 2, 4, 5, 6, 9, 10, 11, 13, 14, 15 | Passed in all 4 runs. 9 to 11 were checked through the api |
| 12 | Passed once, locally: 112 ms for 100 one-line recipes, 100 copies confirmed in the database. Not the deployed server, see T046 |
| 3 | Not walked in a browser. Covered by the integration tests |
| 7 | Partly. The picker offers "My own notebook (new)", submitting creates the notebook, and it stays after extraction fails. No Gemini key, so no recipe was captured into it |
| 8 | Partly. The member's own notebook is preselected. No recipe was captured, for the same reason |

Keyboard (both 1280px runs): Enter opens the dialog and picks a row, Escape closes it, and Tab
reaches a row. The walk put focus on the add button directly, so a full keyboard-only pass from the
top of the page is not done. Screen reader output was not tried; the result is a `role="status"`
toast, covered by a ui test.

Still needed from the owner: steps 3, 7 and 8 with a real Gemini key, and the keyboard-only pass.

## After the walk: the add-recipe picker

The owner reported a notebook picker when adding a recipe inside a notebook. A notebook's own page never showed one in the browser, by direct address or by moving there from the Notebook tab, the kitchen or the kitchen's notebooks view. Two bugs nearby were fixed:

- The Notebook tab offered kitchen notebooks as capture targets, marked personal, so a person with one personal notebook still got a picker. The tile now offers personal notebooks only; the cards are unchanged.
- `openSheet` kept the previous `returnPath` when the notebook was the same, so opening the sheet from the tab and then adding inside that notebook opened nothing.

The kitchen recipe page keeps its picker on purpose (FR-017).
