# Tasks: Saved Shopping List, Closed with Done

**Input**: Design documents from `specs/025-finalize-shopping-list/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R7), data-model.md, contracts/shopping-list-api.md, quickstart.md

**Tests**: Included: constitution §6 requires domain, application, integration and ui tests.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Confirm how the cart write commits in api/adapters/persistence/carts.py and api/api/deps.py, and record in specs/025-finalize-shopping-list/notes.md how the list refresh joins the same transaction (research R4). If the cart write and the list refresh can't share one transaction, stop and report it before Phase 2; don't ship a non-atomic save

## Phase 2: Foundational

**Blocks every user story.**

- [X] T002 Create migration api/adapters/persistence/migrations/versions/0010_shopping_lists.py (down revision `0009_default_kitchen`) with both tables from data-model.md, the partial unique index on `kitchen_id` where `closing_date IS NULL`, the index on `(kitchen_id, closing_date DESC)`, and ON DELETE CASCADE from kitchen and list
- [X] T003 [P] Add a migration test for upgrade, downgrade and upgrade in api/tests/test_shopping_lists_migration.py
- [X] T004 [P] Add saved list types and rules in api/domain/shopping_list.py: `origin` is `cart` or `hand`; `section` is `measured` or `your_call`; a hand item has a non-blank name, normalized by `normalize_name`, `quantity` and `unit` together, a unit from the PRD set, and `size` only with unit `unit`; a mapping from `ShoppingList` to stored cart lines in S-023 order
- [X] T005 [P] Add domain tests in api/tests/test_shopping_list_saved_domain.py
- [X] T006 Add `ShoppingListRepository` to api/application/ports.py: active list, get-or-create, replace cart lines, add item, remove hand item, close, closed lists, closed list by id
- [X] T007 Implement the repository in api/adapters/persistence/shopping_lists.py: get-or-create re-reads on unique conflict (R3), refresh takes a row lock, close is a conditional update on `closing_date IS NULL` with the UTC day (R7)
- [X] T008 Extract the cart-to-list build from `GetShoppingListService` into one shared function in api/application/shopping_list.py, with existing tests still passing (R1)
- [X] T009 Wire the repository into api/api/deps.py

**Checkpoint**: Tables and the repository exist; behaviour is unchanged.

## Phase 3: User Story 1 - A saved list that follows the cart (P1) MVP

**Goal**: Saving the cart creates or refreshes the kitchen's active list.

**Independent Test**: Save a cart, read as a second member, save a change, see the list follow.

- [X] T010 [P] [US1] Add application tests with fake ports in api/tests/test_shopping_list_saved_application.py: create on save, no list from an empty cart with none active, refresh keeps hand rows, the draft does not write, the recipe edit does not refresh
- [X] T011 [P] [US1] Add HTTP tests in api/tests/test_shopping_list_saved_integration.py: two members, simultaneous first saves give one list, stored lines equal S-023's (SC-001), 404 for non-members
- [X] T012 [US1] Refresh the list in `SaveCartService` in api/application/carts.py, in the transaction from T001
- [X] T013 [US1] Make `GetShoppingListService` in api/application/shopping_list.py return `live`, `active` or `draft` with `list_id` and `hand_items` (R5)
- [X] T014 [US1] Extend the response in api/api/schemas/shopping_list.py per contracts/shopping-list-api.md
- [X] T015 [US1] Extend the type and fetch in ui/lib/shoppingListClient.ts, with tests in ui/lib/shoppingListClient.test.ts. Read `kitchen_is_archived` from the cart data the page already has; if it isn't available there, add it to the read shape
- [X] T016 [US1] Show the saved or not-saved status in ui/components/ShoppingList/ShoppingListSection.tsx with es and en text in ui/lib/i18n/shoppingList.ts, with tests in ui/components/ShoppingList/ShoppingListSection.test.tsx
- [X] T016a [US1] Render a chip with `exists: false` as plain text in ui/components/ShoppingList/RecipeChips.tsx, with tests in ui/components/ShoppingList/RecipeChips.test.tsx

**Checkpoint**: The list is stored and shared. This is the MVP.

## Phase 4: User Story 2 - Add individual items (P1)

**Goal**: Members add and remove hand items, even with an empty cart.

**Independent Test**: With an empty cart, add an item, read as the other member, remove it.

- [X] T017 [US2] Add application tests in api/tests/test_shopping_list_saved_application.py: first item creates a list with the saved cart's lines, same name stays separate, cart lines cannot be removed, archived refused
- [X] T018 [US2] Add HTTP tests in api/tests/test_shopping_list_saved_integration.py for 201, 422 `invalid_item`, 404 `item_not_found`, 409 `kitchen_archived` and two simultaneous adds
- [X] T019 [US2] Add `AddShoppingItemService` and `RemoveShoppingItemService` in api/application/shopping_list.py
- [X] T020 [US2] Add POST `/kitchens/{id}/shopping-list/items` and DELETE `/kitchens/{id}/shopping-list/items/{item_id}` in api/api/routes/shopping_list.py
- [X] T021 [P] [US2] Add BFF routes with tests in ui/app/api/kitchens/[kitchenId]/shopping-list/items/route.ts and ui/app/api/kitchens/[kitchenId]/shopping-list/items/[itemId]/route.ts
- [X] T022 [US2] Add client calls in ui/lib/shoppingListClient.ts
- [X] T023 [US2] Add the form and hand item rows in ui/components/ShoppingList/HandItems.tsx with tests in ui/components/ShoppingList/HandItems.test.tsx, es and en text in ui/lib/i18n/shoppingList.ts, and keyboard use at phone width. Replace the `is_empty` early return in ui/components/ShoppingList/ShoppingListSection.tsx so the form always shows, and hide the form and Remove in an archived kitchen

**Checkpoint**: Lists work from the cart, by hand, or both.

## Phase 5: User Story 3 - Press Done after shopping (P1)

**Goal**: Done sets the closing date and freezes the list.

**Independent Test**: Press Done, change the cart and a recipe, confirm the closed list is unchanged.

- [X] T024 [US3] Add application tests in api/tests/test_shopping_list_saved_application.py: closing date set, cart unchanged, empty list refused, second Done refused, the next save starts a new list
- [X] T025 [US3] Add HTTP tests in api/tests/test_shopping_list_saved_integration.py: 409 `list_not_active`, 409 `list_empty`, simultaneous Done, deleted recipes keep their titles (SC-003), Done while another member edits
- [X] T026 [US3] Add `CloseShoppingListService` in api/application/shopping_list.py
- [X] T027 [US3] Add POST `/kitchens/{id}/shopping-list/done` in api/api/routes/shopping_list.py
- [X] T028 [P] [US3] Add the BFF route with a test in ui/app/api/kitchens/[kitchenId]/shopping-list/done/route.ts
- [X] T029 [US3] Add the Done (Listo) button with `ActionDialog` confirmation, disabled for an empty list, in ui/components/ShoppingList/DoneButton.tsx with tests in ui/components/ShoppingList/DoneButton.test.tsx, and es and en text in ui/lib/i18n/shoppingList.ts. Works by keyboard at phone width. Show it only when a stored list exists, disable it for a member editing the cart until they save or discard, and hide it in an archived kitchen

**Checkpoint**: The whole weekly cycle works.

## Phase 6: User Story 4 - Look at past lists (P3)

**Goal**: Members browse closed lists, newest first.

**Independent Test**: Close two lists and check order, dates and contents.

- [X] T030 [US4] Add tests for order, contents and 404 for another kitchen's list in api/tests/test_shopping_list_saved_integration.py
- [X] T031 [US4] Add `ListClosedShoppingListsService` and `GetClosedShoppingListService` in api/application/shopping_list.py
- [X] T032 [US4] Add GET `/kitchens/{id}/shopping-lists` and GET `/kitchens/{id}/shopping-lists/{list_id}` in api/api/routes/shopping_list.py with schemas in api/api/schemas/shopping_list.py
- [X] T033 [P] [US4] Add BFF routes with tests in ui/app/api/kitchens/[kitchenId]/shopping-lists/route.ts and ui/app/api/kitchens/[kitchenId]/shopping-lists/[listId]/route.ts
- [X] T034 [US4] Add pages ui/app/kitchens/[kitchenId]/shopping-lists/page.tsx and ui/app/kitchens/[kitchenId]/shopping-lists/[listId]/page.tsx, with a link from ui/components/ShoppingList/ShoppingListSection.tsx. All text in es and en in ui/lib/i18n/shoppingList.ts, keyboard use at phone width, and tests beside each page

## Phase 7: Polish

- [X] T035 Add a 100-recipe statement count and timing test in api/tests/test_shopping_list_saved_integration.py (SC-005)
- [X] T036 Run ruff and the api tests in the Compose test overlay, then ui lint, typecheck and tests, and record results in specs/025-finalize-shopping-list/notes.md
- [ ] T037 Walk specs/025-finalize-shopping-list/quickstart.md in a browser with two accounts
- [X] T038 Update S-025's status and verification in dev/docs/backlog.yaml, and the row in README.md

## Dependencies

- Setup → Foundational → stories.
- US1 comes first: US2, US3 and US4 use its read shape.
- US2 and US3 can run in parallel after US1. US4 needs US3 to have closed lists.

## Parallel Example

After T009: T010 and T011 together. After US1: US2 and US3 may run side by side only where they touch different files; shared test and service files run in sequence.

## Implementation Strategy

1. MVP: Phases 1 to 3, then validate with two accounts.
2. Add US2 and US3: all three are P1, and the spec is not met without them.
3. Add US4, then Polish.
