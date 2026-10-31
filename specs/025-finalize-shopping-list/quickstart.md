# Quickstart: Validate the Saved Shopping List

**Prerequisites**: The worktree stack is up (`./scripts/compose-up.sh -d`), the migration is applied, and two seeded members share a kitchen with recipes.

## Automated

Run the api tests in the Compose test overlay, then in `ui/`: `npm run lint`, `npm run typecheck`, `npm test`.

## Browser walk (two accounts, phone and desktop width, es and en)

1. Save a cart with two recipes. Both members see the same list, marked as saved.
2. Start editing the cart without saving. The editor's list follows the draft; the other member's does not change.
3. Save the change. The list follows.
4. Add "dish soap" with no amount, and "egg" with an amount when egg is already on the list. Both stay separate and survive a cart save. Remove one.
5. Edit a recipe with no cart save. The list does not change.
6. Press Done and confirm. The list shows in past lists with today's date, the cart is empty, and a toast says the cart was closed.
7. Delete one of its recipes. The closed list reads as before.
8. Add a recipe and save the cart. A new active list starts.
9. Archive the kitchen. Lists can be read; no change is allowed.
10. Open a list URL as a non-member. It answers not found.
11. Empty the active list. Done is disabled.

**Timed check**: with a 100-recipe cart, the list opens in under 1 second (SC-005).
