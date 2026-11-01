# Quickstart: Validate notebook snapshots

## Prerequisites

- Stack running with `./scripts/compose-up.sh`, migration `0011_notebook_snapshot_key` applied.
- Two invented accounts, Ana and Ben, in one kitchen, Home. Ana owns a personal notebook with 3 recipes: one with a vague amount, one with a size, and one with a source link. Its catalog has one name no recipe uses.

## Automated checks

```sh
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
cd ui && npm test && npm run lint && npm run typecheck
```

## Browser walk

Do this at 360px and 1280px, in English and Spanish, and once with the keyboard only.

| # | Steps | Expected |
|---|-------|----------|
| 1 | As Ana, open Home, press the notebooks icon, add her notebook | Added at once with no confirmation; a new notebook with the same name and 3 recipes, no reload (FR-002a, FR-007) |
| 2 | As Ben, open Home and a copied recipe | Same content, Ana as author, source link works; add it to the cart (US1) |
| 3 | Edit a recipe on each side | Neither change reaches the other side (AC1a.4) |
| 4 | As Ben, open the snapshot | Plain-text label naming the original, no link. The original's address answers not found (US3) |
| 5 | As Ana, add the same notebook again, then cancel | Warning shown; nothing created (FR-008a) |
| 6 | Add it again and confirm | A second snapshot |
| 7 | As Ben, with no notebook of his own, capture a recipe in Home without picking | His own notebook is created and receives it (FR-017) |
| 8 | As Ana, capture a recipe in Home without picking | Goes to her own notebook, not a snapshot |
| 9 | Open the side panel as Ana | Her recipe count hasn't risen from the snapshot |
| 10 | Archive Home | No add action; a direct `POST` answers 403 |
| 11 | As Ben, `POST` Ana's notebook as the source | 404; nothing created |
| 12 | Add a notebook with 100 invented recipes | Finishes in under 5 seconds (SC-002) |
| 13 | Before archiving Home, add an empty personal notebook, then open it from Home's notebooks view as Ben | Its card shows and its page opens (FR-007a) |
| 14 | In an archived kitchen, press the notebooks icon | Cards still show and open, with no add action (FR-004, FR-007a) |
| 15 | Open Home's recipe page | Recipes only, no notebook cards (FR-007a) |

## Automated-only cases

- A forced failure halfway through the copy leaves nothing behind (SC-005).
- Deleting the original clears the label and keeps the recipes, and FR-017 still holds. No route deletes a personal notebook until S-059.
- The same `snapshot_key` sent twice, in sequence and concurrently, makes one snapshot.
- A field-by-field comparison of original and copy (SC-003).
