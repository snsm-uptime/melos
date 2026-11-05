# Tasks: Shopping by Store (S-070)

**Input**: `specs/070-shopping-by-store/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: included. Constitution principle 6 requires domain, application and HTTP tests, and vitest for components.

**Format**: `- [ ] Tnnn [P] [USn] description with path`. [P] = can run in parallel (different files, no open dependency).

Story map (spec.md): **US1** mark items bought (P1), **US2** Ingredients page with places (P1), **US3** store tabs on the list (P2).

---

## Phase 1: Setup

- [ ] T001 Create branch `070-shopping-by-store` from `main` and start `specs/070-shopping-by-store/notes.md` with a "Verification" heading for results

---

## Phase 2: Foundational (blocks every story)

- [ ] T002 Add the migration `api/adapters/persistence/migrations/versions/0018_shopping_places.py` (down revision `0017_merge_0016_heads`). It adds `shopping_list_item.bought boolean not null default false`. It creates table `place`: `id uuid PK`, `user_id uuid not null FK users.id ON DELETE CASCADE`, `name text not null`, `name_key text not null`, `created_at timestamptz default now()`, unique `(user_id, name_key)`. It creates table `ingredient_place`: `user_id uuid FK users.id ON DELETE CASCADE`, `name text`, PK `(user_id, name)`, `default_key text null` with a check that it is in ('supermarket','farmers_market','butcher','fish_market','bakery','pharmacy','other'), `place_id uuid null FK place.id ON DELETE CASCADE`, `updated_at timestamptz default now()`, and a check that exactly one of `default_key` and `place_id` is not null. Write a full downgrade.
- [ ] T003 Add `ShoppingListItemModel.bought`, `PlaceModel` and `IngredientPlaceModel`, matching T002, in `api/adapters/persistence/models.py`
- [ ] T004 [P] Add a migration test for upgrade, downgrade to 0017 and upgrade again in `api/tests/test_shopping_places_migration.py`, following `api/tests/test_shopping_lists_migration.py`
- [ ] T005 [P] Create `api/domain/places.py` with:
  - `DEFAULT_PLACE_KEYS` in the order supermarket, farmers_market, butcher, fish_market, bakery, pharmacy, other
  - `FALLBACK = "supermarket"`
  - the English and Spanish default names, used only for the duplicate check
  - `PlaceRef` (default key, or custom id and name)
  - `clean_place_name()`: trim and collapse spaces; 1–40 characters, else `PlaceNameInvalidError`
  - `fold()`: lower case, accents removed
  - `check_new_name(name, own_keys, count)`: `PlaceNameTakenError` when the name equals a default in either language or one of the person's own places; `PlaceLimitError` when the person already has 30
  - `resolve_place(name, choices)`: uses `normalize_name` from `api/domain/ingredient_catalog.py`, falls back to Supermarket

  Add the new errors to `api/domain/errors.py`.
- [ ] T006 [P] Add domain tests for T005 in `api/tests/test_places_domain.py`: name length edges (0, 1, 40, 41), "Supermercado" and "SUPERMARKET" refused, "Café" vs "cafe" refused, the 31st place refused, and `resolve_place` with no row, a default and a custom place
- [ ] T007 Add the `PlaceRepository` protocol in `api/application/ports.py`. Methods: `list_custom(user_id)`, `add`, `rename`, `delete`, `choices(user_id, names)` returning a map from normalized name to PlaceRef, `set_choice(user_id, name, ref)`, `catalog_names(user_id)`, `sources(user_id)`, `replace_with_copy(target_id, source_id)`
- [ ] T008 Implement `SqlAlchemyPlaceRepository` in `api/adapters/persistence/places.py`. `catalog_names` is the union described in research R7: the person's personal notebooks, the kitchen notebooks of their kitchens, and their `ingredient_place` names; unique and sorted. `sources` lists people sharing a kitchen or a personal notebook with the person, the person excluded, with their alias. `replace_with_copy` runs in one transaction, gives copied custom places new ids and remaps `place_id`.
- [ ] T009 Add `place` and `ingredient_place` to the schema guard test (the list of every table) in `api/tests/test_recipe_manage_integration.py`

**Checkpoint**: the migration runs and the domain tests pass.

---

## Phase 3: User Story 1, mark items bought (P1)

**Goal**: any kitchen member marks items of the active list bought or not bought. The state is shared, survives a cart refresh by the rule in research R2, and is kept read-only after Done.

**Independent test**: with an active list of three items, mark one bought, reload as a second member and see it bought, then unmark it.

- [ ] T010 [P] [US1] Add `bought: bool = False` to `SavedLine`, and add `carry_bought(old, new) -> tuple[SavedLine, ...]` (research R2) to `api/domain/shopping_list.py`. A new line is bought when an old bought line has the same `(section, name, kind, size)` and, for every unit in the new amounts, the old line has that unit with a quantity at least as large. Hand lines are not passed in. A `your_call` line keeps bought only when its notes are the same set as before.
- [ ] T011 [P] [US1] Add domain tests for `carry_bought` in `api/tests/test_shopping_list_bought_domain.py`: unchanged line kept, amount grew, unit added, size changed, an unbought line stays unbought, a your_call line with the same notes kept, a your_call line with a new note reset
- [ ] T012 [US1] Repository changes in `api/adapters/persistence/shopping_lists.py`:
  - `_row` and `_line` map `bought`
  - `replace_cart_lines` reads the old cart lines and applies `carry_bought` before inserting
  - add `set_bought(list_id, item_id, bought) -> SavedLine | None`, updating only when the list's `closing_date` is null
  - add `set_bought` to the `ShoppingListRepository` port in `api/application/ports.py`
- [ ] T013 [US1] Add `SetItemBoughtService` in `api/application/shopping_list.py`. Check membership (404 for a non-member), refuse an archived kitchen (`KitchenArchivedError`), return 404 for an unknown item and `ListClosedError` for an item on a closed list. It sets the value sent and does not flip it (research R10).
- [ ] T014 [US1] Response and route changes:
  - add `id: UUID | None` and `bought: bool` to `ShoppingLineResponse`, `YourCallResponse` and `HandItemResponse`, filled from the stored line when status is `active` or the list is closed, and `None`/false otherwise
  - add `SetBoughtBody {bought: bool}`
  - add route `PATCH /kitchens/{kitchen_id}/shopping-list/items/{item_id}`, which answers 200 with the item, 404, 409 `list_closed` or 403 `kitchen_archived`

  Files: `api/api/schemas/shopping_list.py`, `api/api/routes/shopping_list.py`.
- [ ] T015 [P] [US1] Add application tests with fake ports in `api/tests/test_shopping_list_bought_application.py`: member sets and clears the flag, a non-member gets 404, a closed list is refused, an archived kitchen is refused
- [ ] T016 [P] [US1] Add HTTP tests against Postgres in `api/tests/test_shopping_list_bought_integration.py`:
  - two members: A marks an item, B reads it as bought
  - a cart save keeps an unchanged bought line and resets a line whose amount grew
  - a hand item keeps its state through a cart save
  - Done keeps the flags, and a PATCH after Done answers 409
  - an archived kitchen answers 403 `kitchen_archived`
  - A sends `true` and B then sends `false` for the same item: the item reads not bought (last write wins)
- [ ] T017 [US1] Add `PATCH` to `ui/app/api/kitchens/[kitchenId]/shopping-list/items/[itemId]/route.ts`, forwarding as the existing `DELETE` does, and test it in the neighbouring `route.test.ts`
- [ ] T018 [US1] Add a bought toggle to each line in `ui/components/ShoppingList/ShoppingLine.tsx`, `YourCallList.tsx` and `HandItems.tsx`. Show it only when status is `active`. The update is optimistic and rolls back with a toast on error. A bought line is struck through and muted, with an accessible checked state (not color alone), and bought lines sort after the not-bought lines of their group (FR-005).
- [ ] T019 [US1] Add the "Everything is bought — press Done" note above `DoneButton` when every item is bought, in `ui/components/ShoppingList/ShoppingListSection.tsx`. Show read-only bought states on closed lists in `ui/components/ShoppingList/ClosedLists.tsx` and `ui/app/kitchens/[kitchenId]/shopping-lists/[listId]/page.tsx`.
- [ ] T020 [P] [US1] Add the English and Spanish strings (toggle label, all-bought note) to `ui/lib/i18n/shoppingList.ts`
- [ ] T021 [P] [US1] Add vitest tests in `ui/components/ShoppingList/ShoppingListSection.test.tsx` and `HandItems.test.tsx`: optimistic toggle, rollback, sort order, no toggle for live and draft lists, the all-bought note, closed lists read-only

**Checkpoint**: US1 works on its own, with every item under one list.

---

## Phase 4: User Story 2, Ingredients page with places (P1)

**Goal**: each person sets a place per ingredient name, manages custom places and can copy another member's places.

**Independent test**: open Ingredients from the side panel, set "tomato" to Farmers market, add "Asian market" and set "miso" to it, then reload.

- [ ] T022 [US2] Create the use cases in `api/application/places.py`, using `PlaceRepository` and `api/domain/places.py`:
  - `ListPlacesService`
  - `AddPlaceService`, `RenamePlaceService`, `DeletePlaceService`: 404 when the place is not the caller's
  - `IngredientPlacesService.list(user)`: the catalog names with their resolved place
  - `SetIngredientPlaceService(user, name, ref)`: normalizes the name, `IngredientNameInvalidError` when it is empty, `InvalidPlaceError` for an unknown key or another person's id
  - `PlaceSourcesService`
  - `CopyPlacesService(user, source_id)`: 404 when the source is not in the caller's sources
- [ ] T023 [P] [US2] Add application tests with a fake `PlaceRepository` in `api/tests/test_places_application.py`, covering every error in `contracts/places.md`. Include a copy that is a snapshot: a later rename by the source does not change the copy.
- [ ] T024 [US2] Add Pydantic schemas in `api/api/schemas/places.py`. Add the routes in `api/api/routes/places.py`, exactly as in `contracts/places.md`: `GET/POST /me/places`, `PATCH/DELETE /me/places/{id}`, `GET/PUT /me/ingredient-places`, `GET /me/place-sources`, `POST /me/places/copy`. Register the router in `api/api/app.py` with the same dependencies as the other user routes, and map the new domain errors to 422 or 409 codes.
- [ ] T025 [P] [US2] Add HTTP tests against Postgres in `api/tests/test_places_integration.py`:
  - every row of `contracts/places.md`
  - deleting a custom place sends its names back to Supermarket
  - a stranger's place id gets 404
  - a copy from a person who shares nothing gets 404
  - catalog names include kitchen notebooks and personal notebooks, and exclude other people's personal notebooks
  - after B leaves the only kitchen shared with A, B is gone from A's place sources, and places A already copied from B stay
- [ ] T026 [P] [US2] Add BFF routes under `ui/app/api/me/places/route.ts`, `ui/app/api/me/places/[placeId]/route.ts`, `ui/app/api/me/places/copy/route.ts`, `ui/app/api/me/ingredient-places/route.ts` and `ui/app/api/me/place-sources/route.ts`, following the existing BFF routes, each with a `route.test.ts`
- [ ] T027 [P] [US2] Add `ui/lib/i18n/places.ts` with the seven default names in English and Spanish, plus the page strings, errors and confirmations. Make the parity test (`ui/lib/i18n/parity.test.ts`) pass.
- [ ] T028 [P] [US2] Add `ui/lib/places.ts` with the `PlaceRef` type, `placeLabel(ref, t)` and `PLACE_ORDER` (research R9)
- [ ] T029 [US2] Create the Ingredients page at `ui/app/ingredients/page.tsx` with the client screen `ui/components/Ingredients/IngredientsScreen.tsx`:
  - alphabetical names with a text filter
  - one place picker per name that saves on change
  - a "Places" section to add, rename and delete custom places, with a confirmation before deleting
  - a "Copy places from…" action listing place sources, with a confirmation that the person's own places will be replaced

  Make it work at 360 px and 1280 px and by keyboard.
- [ ] T030 [US2] Add an "Ingredients" `SidePanelEntry` linking to `/ingredients` after the Notebook entry (near `href="/notebooks"`), with `current` set on that page, in `ui/components/SidePanel/SidePanel.tsx`. Add its label to `ui/lib/i18n/sidePanel.ts`.
- [ ] T031 [P] [US2] Add vitest tests in `ui/components/Ingredients/IngredientsScreen.test.tsx` (filter, picker save, add/rename/delete with errors, copy confirmation) and in `ui/components/SidePanel/SidePanel.test.tsx` (the entry and its href)

**Checkpoint**: US2 works on its own; places are saved but not used on the list yet.

---

## Phase 5: User Story 3, store tabs on the list (P2). Needs US1 (bought counts) and US2 (places)

**Goal**: the active and closed lists show an "All" tab and one tab per place, with counts of items not bought, resolved for the viewer.

**Independent test**: with places set, open the list, pick Farmers market and see only those items, then mark one bought and see the count drop.

- [ ] T032 [US3] Resolve places for the viewer in `api/application/shopping_list.py`. `GetShoppingListService` and `ClosedShoppingListsService.get` call `PlaceRepository.choices(caller, names)` once per read, so a list costs one extra query, and pass each item's resolved `PlaceRef` plus the caller's custom places to the view.
- [ ] T033 [US3] Add `place` to each item response and `custom_places` at the top level, as in `contracts/shopping-list.md`, in `api/api/schemas/shopping_list.py`
- [ ] T034 [US3] Let a hand-added item carry a place:
  - add the optional `place` to `AddShoppingItemBody`
  - `AddShoppingItemService` calls `SetIngredientPlaceService` in the same transaction (FR-016a)
  - an invalid place answers 422 `invalid_place`

  Files: `api/api/schemas/shopping_list.py`, `api/application/shopping_list.py`.
- [ ] T035 [P] [US3] Add HTTP tests in `api/tests/test_shopping_list_places_integration.py`:
  - two members with different places see different `place` values on the same list
  - a hand item with a place shows that place and its name appears in `GET /me/ingredient-places`
  - a closed list resolves places with the viewer's current places (not the places at closing)
  - a 100-item list read stays within spec 023's statement budget plus one
- [ ] T036 [US3] Create `ui/components/StoreTabs/StoreTabs.tsx`, the tab strip:
  - "All", then each place that has items, in `PLACE_ORDER` followed by custom places sorted alphabetically
  - each tab shows its count of items not bought
  - it scrolls sideways at 360 px
  - roving tabindex with arrow keys and `role="tablist"`
- [ ] T037 [US3] Use `StoreTabs` in `ui/components/ShoppingList/ShoppingListSection.tsx` and on the closed list page `ui/app/kitchens/[kitchenId]/shopping-lists/[listId]/page.tsx`. Filter the lines, Your call and hand items by the selected tab. Keep the selection while on the list and reset it to All when another list is opened (FR-017).
- [ ] T038 [US3] Add an optional place picker (defaults and custom places) to the add-item form in `ui/components/ShoppingList/HandItems.tsx`, sending `place` through the existing BFF POST
- [ ] T039 [P] [US3] Add vitest tests in `ui/components/StoreTabs/StoreTabs.test.tsx` (order, hidden empty tabs, counts, keyboard) and in `ShoppingListSection.test.tsx` (filtering, reset on list change, hand item place)

**Checkpoint**: the full feature works.

---

## Phase 6: Polish and cross-cutting

- [ ] T040 Run `ruff`, the api suite in the Compose test overlay, and the ui `vitest`, lint and typecheck. Record the counts and any failures already known before this story in `specs/070-shopping-by-store/notes.md`.
- [ ] T041 Do the browser walk in `specs/070-shopping-by-store/quickstart.md`, steps 1 to 10, at 360 px and 1280 px, in English and Spanish, and once by keyboard only, on an isolated stack. Record the results and the SC-001 and SC-005 timings in `notes.md`.
- [ ] T042 Update `dev/docs/backlog.yaml`: set S-070 to `in_progress` and then `done`, and write the verification text. Ask the owner to review the Spanish strings in `ui/lib/i18n/places.ts`.
- [ ] T043 Update `dev/docs/prd.md` J5 (Saved list), adding bought, places per person and store tabs, and its Appendix A entries (ShoppingListItem.bought, Place, IngredientPlace)

---

## Dependencies

- Phase 2 (T002–T009) blocks everything after it.
- US1 (T010–T021) and US2 (T022–T031) are independent of each other and can be built in parallel.
- US3 (T032–T039) needs US1's `id` and `bought` in the responses and US2's repository, use cases and `ui/lib/places.ts`.
- Polish comes after US3.

Within a story: domain, then repository and port, then use case, then route, then BFF, then UI. Tests marked [P] can be written alongside their code.

## Parallel examples

- Phase 2: T004, T005 and T006 together once T002 exists.
- US1: T010 and T011 together, then T015, T016, T020 and T021 alongside T012–T019.
- US2: T023, T025, T026, T027 and T028 together once T022 and T024 are drafted.
- US3: T035 and T039 alongside T032–T038.

## Implementation strategy

1. **MVP**: Phase 2 and US1. Marking items bought is useful in the shop on its own.
2. Then US2, so people can set their places; it can ship before the tabs.
3. Then US3, which turns the places into tabs on the list.
4. Polish, browser walk and backlog update.
