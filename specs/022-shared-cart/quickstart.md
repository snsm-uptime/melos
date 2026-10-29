# Quickstart: validate S-022

## Prerequisites

- Dev stack: `./scripts/compose-up.sh`; migration applied (`0007_cart_and_edit_locks`).
- Two accounts in one kitchen, **A** and **B** (dev seed: owner and member of the shared kitchen), in two browsers or one normal and one private window. A third account **C** outside the kitchen.
- At least two recipes in the kitchen's notebooks, one with base servings 4.

## Automated

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
cd ui && npm run lint && npm run typecheck && npx vitest run
```
Expected: new domain, application and integration tests pass; the schema guard test lists `cart_item` and `recipe_edit_lock`.

## 1. Default people and factors (US2, FR-002)
1. A opens Cart: empty, people = member count (2), hint shown.
2. A taps the cart-icon button on the 4-serving recipe's card → no message; the icon's "+" turns into "×". A opens Cart → the editing bar above the tab bar says "You're editing the cart. Others can't change it until you save or discard." → Save. Factor `×0.5`.
3. A edits: people 3, meals 2 → factor `×1.5` live; Save. Reload: unchanged.

## 2. One editor at a time (US3)
1. A presses Edit, changes meals, does not save.
2. B opens Cart: saved values, "A is editing the cart", Cart controls unavailable. B taps a card's cart-icon button → toast above the tab bar "A is editing the cart"; the icon does not change.
3. A signs out. B refreshes: no notice, B can edit; A's unsaved meals are gone.

## 3. Recipe lock (US4)
1. A opens Edit on a recipe. B opens its detail: Edit and Delete disabled with the notice.
2. A cancels → B can edit. A opens Edit again and signs out → B can edit; the recipe is unchanged.

## 2b. Idle limit and access loss (FR-020a, FR-020b)
1. A taps a card's cart-icon button and stays on the kitchen list: no bar there.
2. A does nothing for 4 minutes: a toast above the tab bar warns "Your cart changes will be discarded in 1 minute" with Keep editing. A waits 1 more minute: the toast says "Your cart changes were discarded"; B can edit.
3. A opens a recipe's Edit and leaves the tab open untouched for 5 minutes: B can open Edit.
4. A starts editing the cart; the owner archives the kitchen, then unarchives it: the cart is unlocked and A's draft is gone (`cart_edit_lock` has no row).

## 4. Consistency (US5)
1. Recipe in the saved cart; delete it → gone from the cart, others unchanged.
2. A adds recipe X to a cart draft without saving; B deletes X from its detail page (the cart lock does not block recipe deletes); A saves → banner names X as dropped, X is not in the cart.
3. Add, save, remove, save, add, save → `cart_add_count` = 2 (check via psql).

## 5. Access
- C requests `/api/kitchens/{id}/cart` → 404. Archive the kitchen → Cart read-only, POST `…/cart/edit` → 403.

## 6. Language and width
- Switch account language es/en: all cart, lock and toast text translated. At phone and desktop width the toasts and the Cart page's editing bar sit directly above the tab bar, inside the screen body, and never cover it.
