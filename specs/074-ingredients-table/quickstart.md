# Quickstart: Ingredients Table Layout (spec 074)

Use this guide to check the feature once it is built. It runs against the Compose stack; no production data.

## Prerequisites

- Compose stack running locally with `./scripts/compose-up.sh` (constitution 7).
- Two test accounts: one admin (`users.is_admin = true`) and one ordinary member. Use invented names (constitution 4).
- A notebook with recipes that share ingredient names, including one plural form ("tomates" and "tomate") and one name in both languages.
- Spec 073 job run at least once, so some standard rows have `ai_checked_at` set.

## 1. Run the automated checks

```bash
cd api && uv run pytest tests/test_ingredient_catalog_domain.py tests/test_admin_ingredients_application.py -q
cd api && uv run pytest tests/test_admin_ingredients_integration.py -q   # needs the test Postgres
cd ui && npm run test -- --run app/admin components/Ingredients components/CatalogManager
cd ui && npm run lint && npm run typecheck
```

Expected: all pass.

## 2. Admin Ingredients table

1. Sign in as the admin and open the dashboard, Ingredients section.
2. Check the columns in this order: Ingredient (with other names), Recipes, People, Notebooks, Standard status, Source.
3. Find "tomate" and "tomates" (if seeded). They should be one row each, with the same Standard status (the join uses the singular key, R1).
4. Sort Recipes ascending and descending, then People. Confirm the order changes and the default is recipes descending, then name.
5. Search "tom": only matching names remain (spec 066 FR-005).
6. Check the Review section below the table. Each pending item shows the replaced name, the proposed name, the language, who proposed it and the date.

## 3. Member Ingredients page

1. Sign in as the member and open Ingredients from the side panel.
2. On the places view, open a Place picker. Custom places are listed first, then the defaults (owner decision, spec 074 row 3).
3. Open the place tabs on the shopping list. Defaults come first, then custom places alphabetically (spec 070 FR-014). The tab order differs from the picker order on purpose.
4. Open a notebook's catalog as a writer. The Language column is always shown (owner decision, row 5). Rename, Merge and Delete are visible.
5. Open the same catalog as a reader. The Actions column is not shown.

## 4. Language and layout

1. Switch the interface to Spanish. Check the column labels and the review section labels in Spanish.
2. Check both views at 360 px and 1280 px. No horizontal page scroll (constitution 6).
3. Use the keyboard to reach the sortable headings. Each announces its direction and level.

## 5. Network check

Open the browser's network panel and sort or search the admin table. No request should fire (spec 066 FR-008).

## Expected outcome

Both views share their first columns. Admin figures match the seeded data. Sorting and searching make no server call. The review list is separate from the table.
