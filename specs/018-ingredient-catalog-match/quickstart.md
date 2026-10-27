# Quickstart: Match Captured Ingredient Names to the Notebook's Catalog

Validation guide for S-018. Setup is the same as spec 016's quickstart. Implementation detail goes in `tasks.md`.

## Prerequisites

- Compose stack running: `./scripts/compose-up.sh -d` (see [016 quickstart](../016-capture-recipe-text/quickstart.md)).
- Migrations at head: `docker compose exec api uv run alembic current` shows `0003_notebooks_ingredients`.
- A test member with a notebook whose catalog contains `onion` and `spring onion` (use the dev seed or add them through the notebook once S-020 saves recipes; until then, insert them in the test database).

## 1. Unit checks (domain)

```bash
cd api && uv run pytest tests/test_ingredient_catalog_domain.py -q
cd api && uv run ruff check .
```

Expect: all tests pass, covering match, reject, plural (English and Spanish), accents, case, spaces, duplicates and an empty catalog.

## 2. Application and integration checks

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api   # real Postgres, as AGENTS.md describes
```

Expect: `test_recipe_capture_integration.py` and `test_recipe_extraction_application.py` pass, and a draft for "2 large onions" with catalog `onion` returns `match: matched onion` and one change `onions → onion`.

## 3. UI checks

```bash
cd ui && npm test && npm run lint && npm run typecheck
```

Expect: vitest passes for the label, change list, undo and choose-match behaviour.

## 4. Browser walkthrough

1. Sign in, open the Notebook tab, and open the Text option.
2. Paste:
   ```text
   Quick onion soup
   Serves 2.
   2 large onions
   200 g flour
   Fry the onions. Add the flour.
   ```
3. Submit. Expect:
   - Onions line: "matched: onion"; flour line: "new ingredient".
   - Change list shows "onions → onion".
4. Tap Undo on the change. Expect: the onions line reads "new ingredient" with "onions"; the change disappears; the flour line is unchanged.
5. Change the flour line's match to an existing entry, if one exists. Expect the label and list update at once.
6. Reload the page. Expect the draft is gone (the draft lives only in the browser, FR-013).

## 5. AI evaluation (SC-004)

Run the plural, letter-case and spacing fixtures in `api/tests/fixtures/ai_eval/` against the live model. Count lines that end on the expected entry without a member change. Expect at least 90% (spec SC-004). Record the count in the feature's notes.

## 6. Constitution check

- No table, migration or new package was added.
- `api/domain/ingredient_catalog.py` imports nothing outside the standard library.
- The catalog and the text are sent only inside their delimited blocks.
