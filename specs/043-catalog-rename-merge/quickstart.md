# Quickstart: validate catalog management (S-043)

Contracts: [contracts/catalog.md](contracts/catalog.md). Data: [data-model.md](data-model.md).

## Prerequisites

- An isolated dev stack (never a second Compose project on the main `.env`; see AGENTS.md and the
  worktree scripts). Migrations run on boot (`scripts.entrypoint`).
- Seeded owner and member in a shared kitchen (`SEED_DEV_USER_KITCHEN`), both with a saved language:
  owner English, member Spanish.
- Browser walk: Playwright on the host, as in earlier specs' notes.

## Automated checks

```bash
cd api
uv run pytest tests/test_ingredient_catalog_domain.py tests/test_catalog_manage_domain.py
uv run pytest tests/test_catalog_manage_application.py tests/test_pair_suggest_application.py
./scripts/compose-test.sh pytest tests/test_catalog_manage_integration.py tests/test_catalog_other_names_migration.py
cd ../ui && npm run test -- ingredients && npm run lint && npm run typecheck
```

## Scenarios (browser, 360 px and 1280 px, en and es)

1. **Migration**: after boot, every recipe has a language; recipes in a kitchen notebook have the
   kitchen's content language, personal ones the author's language (FR-005a fallback).
2. **Detect**: `docker compose exec api uv run python -m scripts.recipe_languages detect` prints
   counts; a Spanish recipe in an English kitchen shows "Detected: Spanish. Apply?" and still has
   English until applied; applying it changes the shown names, dismissing removes the banner.
   Running the command again changes nothing.
3. **Merge across languages** (US1): in the kitchen notebook, recipe A (es) uses "cebolla", recipe
   B (en) uses "onion". Ingredients → pick the notebook → "cebolla" → Merge → "onion". The
   confirmation lists every writable notebook with both names and the recipe counts, and the
   languages (es, en). Confirm. A shows "cebolla", B shows "onion"; the catalog shows one row
   "onion" with variant "cebolla (es)". Count the taps from the Ingredients page to the merge
   result: SC-001 allows at most 4.
4. **Shopping list** (FR-007): add A and B to the cart. The owner sees one line "onion"; the member
   sees the same line as "cebolla", amounts summed. The owner's place for "onion" (set before)
   puts it in the same store tab for both names.
5. **Matching** (FR-008): capture a Spanish recipe with "2 cebollas". The draft lists the change to
   the ingredient, no new name; after save the line shows "cebolla".
6. **Rename** (US2): rename "tomatoe" to "tomato" (absent): recipes follow. Rename "tomatoe" to
   "tomatoes" when "tomato" exists: told it exists, merge offered.
7. **Delete** (US3): delete an unused name; try to delete "onion": refused with the count.
8. **Split** (US4): split "cebolla" out of "onion": A still shows "cebolla", the list shows two
   lines again.
9. **Suggest pairs** (US5): with "ajo", "garlic", "harina", "flour" in the catalog, press Suggest
   pairs; accept one (merge confirmation opens prefilled), dismiss the other, press again: the
   dismissed pair is gone. With the AI key unset: a clear message, manual merge still works.
10. **Read-only**: as a person who can only read a notebook, the page shows no actions for it.
11. **Concurrency**: two tabs merge the same name; the second gets "changed, reload" or a skipped
    notebook in the result.
12. **Timing**: SC-004 merge across 10 notebooks / 200 recipes under 2 s; SC-006 suggestions for
    300 names under 10 s. Record in `notes.md`.

## AI evaluation (manual, constitution 6)

Fixtures in `api/tests/fixtures/ai_eval/pairs/`: 10 catalogs with known pairs. SC-006 asks at least
8 of 10 suggested pairs to be real pairs. Language detection: 10 recipes of known language.
