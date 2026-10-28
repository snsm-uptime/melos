# Quickstart: Recipe Lists

Validation guide for [spec.md](./spec.md). Contracts: [list-api.md](./contracts/list-api.md), [list-ui.md](./contracts/list-ui.md).

## Prerequisites

- Compose stack up (`./scripts/compose-up.sh`) with migrations applied (`0006_unaccent` included).
- Two test accounts with aliases (invented), one kitchen with both as members.

## 1. Automated

```sh
cd api && uv run pytest tests/test_recipe_search_domain.py tests/test_recipe_lists_application.py
uv run ruff check . && uv run ruff format --check .
# integration, in the Compose test overlay:
./scripts/compose-test.sh api tests/test_recipe_lists_integration.py tests/test_unaccent_migration.py
cd ../ui && npm run typecheck && npm run lint && npm test
```
(Use the project's usual test script names if they differ.)

## 2. Personal notebook (Story 1)

1. Capture and save two recipes into your default notebook.
2. Open Notebook tab, tap the notebook card → `/notebooks/{id}`.
3. Expect: two cards, newest first, pot icon, title, your alias chip, ingredient count.
4. Open an empty personal notebook → "No recipes yet" message, no error.
5. Sign in as a non-member and open the same URL → "not found" message, same as a made-up id.

## 3. Kitchen list (Story 2)

1. Each member saves a recipe into the kitchen's notebook.
2. Open `/kitchens/{id}` as each member → both recipes, author chips differ, notebook name on each card.
3. Confirm recipes from either member's personal notebook are absent.
4. Archive the kitchen → the list still shows, with no add-recipe action.

## 4. Filter and pages (Story 3)

1. Recipes "Lentil soup" (lentil, onion) and "Pancakes" (flour, milk): filter "onion" → soup only; "PANCAKE" → pancakes only; clear → both.
2. Title "Crema de calabaza": filter "calabazá" → found.
3. Filter "zzz" → "no recipes match" with Clear filter.
4. Filter "%" → matches only titles or ingredients containing a literal "%".
5. Save 13 recipes: page 1 shows 12, "Page 1 of 2"; page 2 shows 1; `?page=9` shows page 2.
6. Filter while on page 2 → returns to page 1.

## 5. No writes (FR-012)

Count rows of `notebook`, `recipe`, `ingredient` before and after opening each list, including a kitchen with no notebook: equal.

## 6. After Save (FR-013)

Save a draft captured in a personal notebook → land on `/notebooks/{id}` with "Recipe saved" and the new recipe first.
