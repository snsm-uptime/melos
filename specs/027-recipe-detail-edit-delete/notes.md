# Notes: Recipe Detail, Edit and Delete (S-027)

## Baseline (before this feature, 2026-10-28)

- api (`uv run pytest -q`, no `DATABASE_URL`): 448 passed, 204 skipped. `ruff check`: clean.
- ui (`npm test`): 78 files, 449 tests passed. `npm run lint` and `npm run typecheck`: clean.
- Compose test overlay: not run at baseline; known failures from spec 021 notes (text limit 10000 vs 5000 in two capture tests) are expected there.

## T029: can the draft rows be reused? (2026-10-28)

Yes, as they are. `IngredientLineRow`, `RowControls` and `NameChangeNotice` take their data and callbacks through props; they import only types and two pure helpers (`chooseLineMatch`, `NEW_CHOICE`) from `captureStore`, never its state. No draft component was changed. The edit form keeps its own state (`ui/lib/recipeEdit.ts`) in the draft's `LineView` shape, so the match control and the name-change notice behave as at capture. The match control lists only the entries the lines are matched to, because the api does not send the whole catalog.

## Decisions made while building

- **Ingredient line required on edit.** The first save accepts a recipe with no ingredient lines (`check_edited_draft` only requires a title and steps). Spec 027 FR-008 requires at least one, so `UpdateRecipeService` adds `ingredients` to the missing parts (422 `draft_incomplete`). The first save is unchanged.
- **Size on a non-counted line is dropped, not refused.** The draft rules silently clear a size unless the unit is `unit`. The edit follows the first save; spec FR-008 and scenario 5 now say so.
- **`source` is null for pasted text.** The detail returns `{type, url}` only when the recipe has a URL; the pasted text is never returned.
- **Name check trigger.** The check runs when a name field loses focus and again when Save is pressed. A proposal found by Save stops that save so the member sees the change first.
- **Locales.** `lib/i18n/recipeDetail.ts` has `en` and `es`, like `recipeLists.ts`.

## After the build (2026-10-28)

- api in Compose (test overlay), whole suite: 721 passed, 2 failed (the two failures listed in the baseline). New: 29 application tests, 15 domain tests, 22 integration tests (including the concurrent-save and schema-guard tests).
- ui: 88 files, 529 tests passed. `npm run lint` and `npm run typecheck` clean.
- Walked over HTTP against the running dev stack (api restarted to load the new routes) through the BFF at `localhost:3000`: save, read, detail and edit pages answer 200, name matches, edit, stale edit (409), blank title (422), non-reader gets the same 404 as a missing id, non-reader delete (404), delete (204), second delete (404), list empty. Test users were removed from the dev database afterwards.
- A recipe of 100 lines and 100 steps read in 0.027 to 0.037 s through the BFF (SC-001 asks for first content within 2 s; the browser render time was not measured).
- **Not done:** the browser walk of quickstart §2 (detail, edit, delete screens at phone and desktop width, the two-tab conflict, the leave confirmation) and SC-001's render timing. The component tests cover each of those behaviors in jsdom only.

## Detail page reuses the draft layout (2026-10-28)

`IngredientLineRow` and the new `StepCard` (extracted from the draft editor, now also used by the edit form) have a `readOnly` mode that renders the same cards as text. `RecipeDetailView` composes them in the draft page's layout. Kept on the page: the Back icon link and, for those who can write, Delete and Edit (the feature needs them). `formatLine` was removed as unused. ui: 88 files, 526 tests pass; lint and typecheck clean. Not looked at in a browser.
