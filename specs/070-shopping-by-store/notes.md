# Notes: Shopping by Store (S-070)

## Verification

### 2026-11-05, branch 070-shopping-by-store (not committed)

**api** (Compose test overlay, `./scripts/compose-test.sh pytest -q`): 2015 passed, 8 failed. The 8
failed before this story and are listed in the backlog for S-069: the live embedder, four Spanish
kitchen-notebook name tests, the paste-limit test, the vocabulary test, and
`test_a_saved_and_a_closed_list_keep_a_custom_line`, which sends the fixed closing date 2026-11-02
and is refused as "not today" since 2026-11-04. `ruff check` and `ruff format --check` clean.

New api tests: `test_places_domain.py` (16), `test_shopping_list_bought_domain.py` (9),
`test_places_application.py` (5), `test_shopping_list_bought_application.py` (4),
`test_shopping_list_bought_integration.py` (5), `test_places_integration.py` (7),
`test_shopping_places_migration.py` (1: upgrade, downgrade to 0017, upgrade). Older list tests were
updated for the new `id`, `bought`, `place` and `custom_places` fields.

**ui**: 173 files, 1503 vitest tests pass; typecheck clean; lint clean apart from one warning that
was already there (`app/kitchens/KitchenNotebooksSection.tsx`).

### Decisions taken while building

- **Store tabs reuse `components/Tabs`** (`components/ShoppingList/PlaceTabs.tsx`) instead of a new
  `components/StoreTabs` (constitution 1). The tab row scrolls with arrows at phone width.
- **No tabs while every item is at one place.** "All" and the single place would show the same
  items. This refines FR-014; tabs appear as soon as two places have items.
- **PATCH answers with the whole list**, like the other list writes; contracts/shopping-list.md was
  updated.
- **T009**: the schema guard test lists only tables pointing at `recipe`; the new tables do not, so
  it needed no change.
- The Ingredients page shows each name with its first catalog spelling (accents kept); choices are
  stored under the normalized name (`normalize_name`), as list items are resolved.

### Not done

- **T041**: the browser walk of quickstart.md (360 px and 1280 px, English and Spanish, keyboard),
  and the SC-001 and SC-005 timings on the dev stack. Migration 0018 is not applied to the dev
  database.
- **T043**: PRD J5 and Appendix A wait until the story is done (constitution 9).
- The Spanish strings in `ui/lib/i18n/places.ts` and the new ones in `ui/lib/i18n/shoppingList.ts`
  were drafted by the assistant and need the owner's review.
