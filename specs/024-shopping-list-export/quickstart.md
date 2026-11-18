# Quickstart: Shopping List Export

Validates the feature end to end. Requires the local stack (Docker Compose) and two accounts: a member of a kitchen and a person who is not in it.

## 1. Run the checks

```sh
cd api && uv run pytest tests/domain/test_shopping_export.py tests/application/test_shopping_export.py tests/api/test_shopping_list_export.py
cd api && uv run ruff check .
cd ui && npm run test -- ShoppingListExport
cd ui && npm run lint && npm run typecheck
```

Expected: all pass.

## 2. Prepare a list

1. Sign in as the member. Open the kitchen, add two recipes to the cart, and save the cart so the kitchen has a shopping list.
2. Add one manual item (for example "lemon") on the list page.
3. Close the list with "Done" (to check that closed lists export).

## 3. Markdown copy

1. Open the list page. The copy box shows the list.
2. Check: each recipe line shows its quantity and recipe titles in parentheses; "lemon" shows "(manual)"; the "Your call" section comes after the measured lines.
3. Press Copy. Paste into a plain text field. The text matches the copy box. (SC-001, SC-004)

## 4. PDF download

1. Press Download PDF. A file named `shopping-list-YYYY-MM-DD.pdf` downloads.
2. Open it. Every line from the copy box is present, with the recipe titles after each line and the "Your call" section. (SC-002)
3. Check accented names (for example "crème" or "ñoquis") display correctly.

## 5. Failure path (AC5.5)

1. Make the PDF step fail on purpose (for example stop the API's PDF path in a test build).
2. Press Download PDF. An error message appears and no file downloads.
3. Press Copy. It still works. (SC-003)

## 6. Access (FR-013)

1. As the non-member, request the export URL for the member's list ID (`/api/kitchens/<id>/shopping-lists/<list_id>/export?format=markdown`).
2. Expect 404 with the same body as an unknown list ID.

## 7. Closed list (FR-012)

1. Open the closed list and export it as Markdown and PDF.
2. Expect both to work, and the list to still show as closed.
