# Quickstart: validate S-062 end to end

Prerequisites: the stack runs through Compose (`./scripts/compose-up.sh`); a signed-in user with an alias; a recipe saved for 4 servings with "1 cup rice", "2 large onion", "salt, to taste" and "0.1 tsp saffron" (use the capture flow or `POST /api/recipes`). Invented data only.

## 1. Automated checks

```sh
cd ui && npm test && npm run lint && npm run typecheck
```
Expected: the new `recipeScale`, `recipeLines`, `ServingsControl` and `RecipeDetailView` tests pass and the earlier ones are unchanged. No api or Compose run is needed: nothing in `api/` changes.

## 2. Browser walk (constitution §6)

1. Open the recipe's detail. **Expect** the control at 4 and the saved amounts, no "Makes" line and no Reset.
2. Press `+` twice (6). **Expect** rice `1.5 cup`, onion `3 large`, salt note unchanged, saffron `0.15 tsp`, "Makes 4", Reset, and the note above the steps. Steps text is unchanged.
3. Type `5` in the field. **Expect** onion `2.5 large`. Type `abc`, `0`, `101`, `2.5` and clear the field: **Expect** the amounts stay at 5 servings and the hint shows; leaving the field restores `5`.
4. Press Reset. **Expect** the saved amounts, and "Makes", Reset and the steps note gone.
5. Set 6, then press Edit. **Expect** the edit form shows 4 servings and the saved amounts. Go back, reload the page: **Expect** 4 and the saved amounts.
6. Open the same recipe as another member. **Expect** 4.
7. Open it as a read-only member (archived kitchen). **Expect** the control works and Edit and Delete are absent.
8. Set 100 on a recipe with 100 lines. **Expect** the amounts change with no visible delay.
9. Use only the keyboard (Tab, type, Enter, Space on the buttons). **Expect** everything works and a screen reader announces "Amounts for N servings".

## 3. Data check

After steps 2 to 5, the recipe row (`base_servings`, lines, steps, `updated_at`) is identical to before (psql on the dev database), and the browser's network log shows no request when the servings change.
