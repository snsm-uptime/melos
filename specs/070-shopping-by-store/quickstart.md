# Quickstart: Shopping by Store (S-070)

Use invented accounts only. Stack: `./scripts/compose-up.sh` (see AGENTS.md); browser walk per the "Browser walk on WSL" setup, on an isolated stack.

## Automated checks

1. Migration: `0018_shopping_places` upgrade, downgrade to `0017`, upgrade again on a scratch database.
2. api in the Compose test overlay: domain tests for `carry_bought` (same line kept, amount grew, unit added, size changed, hand items untouched) and for place names (length, folded duplicates against en and es defaults, limit 30); application tests with fake ports for each use case; HTTP tests for every row of [contracts/shopping-list.md](contracts/shopping-list.md) and [contracts/places.md](contracts/places.md), including 404 for a stranger's place and a non-sharing copy source; schema guard test knows `place` and `ingredient_place`; a 100-item list read stays within the statement budget of spec 023 plus one.
3. ui: vitest for the tab strip (order, counts, hidden empty tabs), the bought toggle (optimistic, rollback on error), the Ingredients page (filter, picker, place management, copy confirmation), the side-panel entry; lint and typecheck.

## Browser walk (360 px and 1280 px, English and Spanish, once by keyboard only)

Accounts A and B, members of kitchen K with a saved cart of three recipes.

1. A opens the side panel: an "Ingredients" entry opens the page. Every name shows Supermarket.
2. A sets "tomato" to Farmers market (count the taps after finding the name: at most 2, SC-003) and adds the place "Asian market"; sets "miso" to it. Reload: both kept. A tries to add "supermercado": refused.
3. A opens K's active list: tabs All, Supermarket, Farmers market, Asian market with counts of items left.
4. A marks tomato bought: struck through, moves to the end of its group, the Farmers market count drops. B reloads: bought; B's tabs show only Supermarket (B has no places).
5. B opens Ingredients, copies A's places, confirms. B's list now shows A's tabs. A renames "Asian market": B's copy keeps the old name.
6. A raises a recipe's servings in the cart and saves: tomato goes back to not bought; an unchanged bought line stays bought.
7. A adds "dish soap" by hand with place Pharmacy: it shows under Pharmacy, and "dish soap" is on A's Ingredients page.
8. A deletes "Asian market" after the confirmation: miso returns to Supermarket.
9. A marks every item bought: the list says so and suggests Done. A presses Done: the closed list shows tabs and bought states, and nothing can be changed.
10. Timing: SC-001 toggle under 0.5 s; SC-005 a 100-item list with tabs under 1 s on the dev stack.

Record results in `specs/070-shopping-by-store/notes.md`.
