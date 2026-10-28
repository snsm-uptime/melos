# Notes: Scale a Recipe's Servings (S-062)

## Baseline (before this feature, 2026-10-28)

- ui (`npm test`): 88 files, 526 tests passed. `npm run lint` and `npm run typecheck`: clean.
- api: untouched (`git diff --stat api/` empty); this feature is ui only.
- Branch `062-recipe-servings-scale` was created from `027-recipe-detail-edit-delete`, which holds the detail page this feature changes and is not on `main` yet.

## After the build (2026-10-28)

- ui: 90 files, 584 tests passed (baseline 88 files, 526 tests). `npm run lint` and `npm run typecheck` clean.
- Guards: nothing under `ui/components/RecipeEdit`, `ui/lib/recipeEdit.ts` or `ui/app` imports `recipeScale`; `git diff --stat api/` is empty.
- A bug the tests caught: a typed number that was applied was kept as "typed text", so after Reset to the saved number the field showed the old typed number again. An applied entry now clears the typed text; only an entry that was not applied is kept (test "follows the value when it is changed from outside").
- Against the running dev stack: a saved recipe's detail page answers 200 and the recipe is identical before and after (no request is made by the control). Test user removed afterwards.
- Decisions: `<0.01` is shown for an amount above zero that rounds to 0; a recipe saved above 100 servings opens at its own number and steps down to 100.
- **Not done:** the browser walk (T017): control layout and wrapping at phone width, keyboard-only use, screen-reader announcement, and the network log. The component tests cover the behaviors in jsdom only.
