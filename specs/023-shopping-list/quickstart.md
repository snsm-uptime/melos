# Quickstart: validating the shopping list (S-023)

A validation guide, not an implementation guide. Rules are in [spec.md](./spec.md), the data in [data-model.md](./data-model.md), the shapes in [contracts/](./contracts/).

## Prerequisites

- Compose dev stack up: `./scripts/compose-up.sh` (db, api, ui; migrations at head — this story adds none).
- Two accounts with aliases, `ana` and `ben`, in one kitchen (invented names only).
- A kitchen notebook with these invented recipes (all `base_servings` 4 unless noted):
  - **Bread**: flour 3 tbsp; salt "a pinch"; onion, large, 1 unit, preparation chopped.
  - **Pancakes**: flour 1 cup; butter "to taste"; egg 2 units.
  - **Stew**: onion, large, 1 unit, preparation sliced; onion, small, 1 unit; rice 200 g; butter 100 g; salt "to taste".
  - **Pilaf**: rice 1 cup.

## 1. Automated checks

```bash
# api: domain + application (fast, no database)
cd api && uv run pytest tests/test_shopping_list_domain.py tests/test_shopping_list_application.py
# api: HTTP + Postgres, in the Compose test overlay (see CONTRIBUTING.md / scripts)
# ui
cd ui && npm run test -- shoppingList ShoppingList CartScreen && npm run lint && npm run typecheck
```

Expected: all pass. The domain tests include AC5.1–AC5.4 as written and the 20 hand-calculated carts (SC-004). The integration test reads a 100-recipe × 20-line cart in a bounded number of SQL statements (SC-003).

## 2. Browser walk (two accounts)

Set `ana` in one browser profile and `ben` in another.

| Step | Do | Expect |
|---|---|---|
| 1 | `ana`: add Bread and Pancakes to the cart, People 4, Meals 1, Save. Open the Cart page. | Below the recipes: `flour — 1 cup + 3 tbsp` with chips Bread, Pancakes (AC5.1). |
| 2 | Same page. | `onion, large — 1` [Bread]; `egg — 2` [Pancakes]; "Your call": `salt — a pinch` [Bread], `butter — to taste` [Pancakes]. |
| 3 | Add Stew, Save. | `onion, large — 2` [Bread, Stew]; `onion, small — 1` [Stew] (AC5.4); `onion` chopped and sliced are one line. `rice — 200 g` [Stew]; `butter — 100 g` [Stew] and butter also under "Your call" [Pancakes]. `salt` under "Your call" shows "a pinch, to taste" with chips Bread, Stew. |
| 4 | Add Pilaf, Save. | Two rice lines: `rice — 200 g` and `rice — 1 cup`, never converted (AC5.3). |
| 5 | Tap the Stew chip. | Stew's page opens; Back returns to the Cart page. |
| 6 | `ana`: Edit, change People from 4 to 3 (do not save). | `ana`'s list changes within about a second (factor 3/4): `flour — 0.75 cup + 2.25 tbsp`, `egg — 2` (1.5 rounded up). The saved numbers are not shown to `ana` while editing. |
| 7 | `ben`: open the Cart page while `ana` edits. | `ben` still sees the list of the saved cart (People 4). Reading did not end `ana`'s edit. |
| 8 | `ana`: Discard. | `ana`'s list returns to the saved cart's. |
| 9 | `ana`: Edit, People 3, Save. `ben`: focus the tab. | `ben`'s list shows the new amounts with no manual refresh (SC-006). |
| 10 | `ana`: Edit, remove every recipe, Save. | No list section; only the empty hint with its link. |
| 11 | Archive the kitchen (owner), reload as `ben`. | The list can still be read. |
| 12 | Open `/kitchens/{id}/cart` signed in as a person outside the kitchen. | Same "not found" as for a kitchen that does not exist. |

Also check at phone width (about 360 px): chips wrap, no sideways scroll; keyboard only: Tab reaches each chip, Enter opens it; Spanish (account language): headings and "A tu criterio" show, names and titles stay as stored.

## 3. Read-only check

Before and after opening the list, compare `cart_item`, `recipe.cart_add_count`, the ingredient catalog and the lock row: they must not change (FR-014). The integration test asserts this; the browser walk can confirm with a quick query on the dev database.

## 4. Performance check

On the dev stack with a seeded cart of 100 recipes × 20 lines, `GET /api/kitchens/{id}/shopping-list` answers in under 1 s (SC-003). Record the time in `notes.md` as spec 022 did.
