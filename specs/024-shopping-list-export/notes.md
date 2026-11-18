# Notes: Shopping List Export (024)

## T001: spec 025 read path and fixtures

- Read path: `api/application/shopping_list.py` (`ClosedShoppingListsService.get`, `_member_kitchen`,
  `viewer_language`), repository port `ShoppingListRepository` in `api/application/ports.py`.
- The export reuses `_member_kitchen` (same membership rule as every list read) and the stored
  `SavedList` from `active()` / `closed_by_id()`.
- Application fixtures to reuse: `tests/test_shopping_list_saved_application.py` (`Saved`, `rice()`,
  `done()`, `add()`), `tests/test_shopping_list_application.py` (`Fixture`, `measured`, `vague`),
  `tests/test_carts_application.py` (`ANA`, `BEN`, `CAT` users).
- Integration fixtures to reuse: `tests/test_shopping_list_integration.py` (`bread_and_pancakes`,
  `save_cart`, `measured`, `_list`) and `tests/test_carts_integration.py` (`People`, `_home`).

## T002: baseline

- `cd api && uv run pytest -k "shopping or cart"` against Postgres 16 + pgvector: 281 passed.
- `cd ui && npx vitest run` (full suite): 199 files, 1762 tests passed.

## Verification of the implementation

- API: `tests/test_shopping_export_{domain,markdown,pdf,application}.py` (unit) and
  `tests/test_shopping_list_export_api.py` (integration, Postgres): 25 passed.
- The PDF was also parsed with pypdf (outside the project): 3 pages for 100 lines, accents intact.
- UI: `components/ShoppingListExport/*.test.*` and `lib/i18n/parity.test.ts`: passing.
- `ruff check` and `ruff format --check` clean for the whole api; `npm run lint` has no new
  findings (one existing warning in `app/signup/SignupForm.tsx`); `npm run typecheck` clean.

## T038: browser walk (not done)

The quickstart browser walk at 360 px and 1280 px, in English and Spanish, has not been run.
It needs the full Compose stack. Record the outcome here once it is run.

## Open items

- T034 (feature inventory entry in `ui/lib/featureInventory.ts`) waits for the owner's confirmation
  that the feature is ready for the landing page.
- The export is mounted on the closed-list page (`/kitchens/[id]/shopping-lists/[listId]`). The
  active list has no page keyed by list ID, so it has no export entry point yet. SC-001 names the
  cart page. Adding the component to the active-list view (which has `list_id` when saved) is the
  next step.
- Spec R2 (standard-library PDF writer, WinAnsi limit) is still the owner decision it was: a
  third-party library would need approval.
