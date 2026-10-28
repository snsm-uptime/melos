# Quickstart: validate Save

Prerequisites: Compose stack from `./scripts/compose-up.sh`; a signed-in user with an alias; a fake or real extractor (tests use the fake). Contracts: [save-api.md](./contracts/save-api.md), [save-ui.md](./contracts/save-ui.md). Tables: [data-model.md](./data-model.md).

## 1. Automated

- api (Compose test overlay): run the domain, application and integration tests for recipe save and the migration test (upgrade to `0005_recipes`, downgrade to `0004_drop_kitchen_hide`, upgrade again, with invented rows in `ingredient`).
- ui: `npm run lint`, typecheck and vitest in `ui/`.
- Expected: all green, no skipped save tests.

## 2. Personal notebook happy path (US1, US2)

1. Open Notebook, tap the plus, choose Text, paste "2 large onions, chopped. A pinch of salt. Simmer them." and submit.
2. Edit the title, press Save.
3. Expected: back on the notebook page with "Recipe saved". In the database: one `recipe` with your user as `author_id`, two `recipe_ingredient` rows (onion `2 unit large`, salt with `vague_note` and no quantity), one `step`, one `source` with the pasted text, and `ingredient` rows "onion" and "salt".
4. Capture "3 onions" in the same notebook: the draft shows the line as matched, and the catalog still has one "onion".

## 3. Kitchen notebook (US1)

Repeat in a kitchen's Notebook tab. Expected: the recipe is in a kitchen notebook, authored by you, and no row appears in any personal notebook.

## 4. Refusals (US3)

- Archive the kitchen after capturing, press Save: message shown, draft kept, no rows added.
- Delete the notebook after capturing, press Save: "no longer exists" message, no rows added.
- Press Save twice quickly, or retry after turning the network off and on: one `recipe` row.
- Sign in as a user without access and call `POST /recipes` with the notebook id: 404 `notebook_not_found`, identical to a random id.

## 5. Catalog rules (US2)

Save a draft where a line named "Onions " differs from catalog entry "onions" only by case and spaces: no second entry is added. Force a failure (invalid unit) and check that no catalog name was added.
