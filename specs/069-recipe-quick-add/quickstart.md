# Quickstart: validate 069

Prereqs: dev stack up (`./scripts/compose-up.sh -d`), two invented accounts A and B in one active kitchen K; A has a personal notebook with recipe "Lentil soup".

1. **api tests**: `cd api && uv run pytest tests -k "recipe_copy"`; integration via the Compose test overlay. Expect pass.
2. **ui tests**: `cd ui && npm test -- QuickAddRecipe RecipeFromNotebookSheet AddRecipeOptionsDialog`; `npm run lint && npm run typecheck`.
3. **Kitchen flow** (A, in K): add dialog shows 4 options → Recipe from another notebook → pick "Lentil soup" → confirm → appears in A's kitchen notebook in K; personal original unchanged.
4. **Repeat**: same again → "already added" with Add another copy / Overwrite / Cancel. Edit the personal recipe, Overwrite → the kitchen copy shows the new content, same recipe page.
5. **Quick add** from the shopping list page → 4 options; Text capture works and Back returns to the list. Outside a kitchen with two kitchens → kitchen choice shown.
6. **Access**: B posts A's recipe id → 404. Archived kitchen → option absent.
7. **Delete source** → re-add creates a new copy without the warning.
8. Browser walk at 360px and 1280px, light/dark, en/es (see browser-walk memory: run on the host).
