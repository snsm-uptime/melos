# Quickstart: validating Custom Units and Admin Dashboard

Design references: [data-model.md](data-model.md), [contracts/units-api.md](contracts/units-api.md), [contracts/admin-api.md](contracts/admin-api.md).

## Prerequisites

- Work on an isolated stack. Compose projects share the dev data directory, so don't run a second project with the main `.env`. Use `./scripts/worktree/worktree-add.sh`.
- The dev database moves to `0013_custom_units`. Going back to main needs a downgrade, and that downgrade refuses while any line uses a custom unit.
- Three accounts on the stack: A and B share a kitchen; C shares nothing. Invented data only.
- A `GEMINI_API_KEY` for steps 1 and 2 of the walk, as the model decides what it reports.

## Automated checks

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
cd api && uv run ruff check .
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: all pass. The tests that matter most for this feature:

| Risk | What must be proved |
|------|---------------------|
| Same text, two accounts, at once | Each gets a draft judged by their own units (R5) |
| Two people, or two tabs, keep one word | One row, right count, no error (R2) |
| Removal | Count drops, an empty non-default row goes, a default stays, recipes don't change |
| Prompt | No stored unit appears in what is sent to the model (R4) |
| Shopping list | 1 + 2 lata is `3 lata`; 1.5 lata is `2 lata`; lata and g don't merge |
| Default recipes | Every existing shopping list test passes unchanged (SC-004) |
| Non-admin | Signed out and non-admin answers equal an unknown path, byte for byte |
| Dashboard fields | Response keys match the contract exactly (FR-019) |
| Cart activity | Create, edit, Done gives 1, 1, 1 for that person and none for others |

Add `api/tests/fixtures/ai_eval/canned_beans.txt` and run it by hand against the real model. Expected: unit "lata", name "frijoles".

## Browser walk

At 360px and 1280px, in both languages.

1. **Keep a unit.** As A, paste a recipe with "una lata de frijoles", and "2 latas de maíz". One question appears, for "lata". Accept and save. The recipe reads `1 lata frijoles`.
2. **Known from then on.** As A, paste "2 latas de atún". No question. Open a recipe to edit: "lata" is in the picker.
3. **Decline and discard.** As A, paste a recipe with "un bote de crema". Decline: the line stays flagged and Save is blocked until a unit is picked. Paste it again and accept, then discard. "bote" is not in the picker.
4. **Typed by hand.** As A, edit a recipe, choose Other…, type "Sobres", leave the field. The question reads "sobre". Type "tazas" instead: the line becomes `cup` with no question.
5. **Another account.** As C, paste "una lata de frijoles": the question appears. "lata" was not in C's picker before.
6. **Shared recipe.** As B, in the kitchen with A's recipe: read it, scale it, change its title, save. No question and no error. Open the line's picker: B's units plus "lata".
7. **Shopping list.** Put two recipes with 1 and 2 lata in the cart: `frijoles — 3 lata`. Scale one to get 1.5: it rounds up. Add 200 g of frijoles in a third recipe: it shows too, with no conversion.
8. **Hand item.** The shopping list's add form shows the default units only.
9. **Dashboard.** Open `/admin` as B: not found, and no entry in the side panel. Run the SQL from the contract for A, then reload. The entry shows. Compare each section to what you created. Confirm no ingredients or steps appear in Recipes.
10. **Cart activity.** Make a new cart, change it, press Done. The Users section shows 1, 1 and 1 for that person.

## Not walkable

Account deletion (FR-020b) has no route until S-054. It's covered by the service tests only.
