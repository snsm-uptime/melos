# Feature Specification: Saved Shopping List, Closed with Done

**Feature Branch**: `025-finalize-shopping-list` (story S-025)

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "S-025 from dev/docs/backlog.yaml and dev/docs/prd.md: finalize shopping list as a snapshot with closing_date."

**Source**: `dev/docs/prd.md` J5 Finalize and History, §1.5 C, §1.6 (`shopping_list`, `shopping_list_item`), Appendix A (ShoppingList, ShoppingListItem); backlog S-025. Builds on the shared cart of S-022 (`specs/022-shared-cart`) and the shopping list of S-023 (`specs/023-shopping-list`).

## Clarifications

### Session 2026-10-30

- Q: How does a list get finalized? → A: There is no Finalize step. The list comes from the cart or from individual items a member adds, every update is saved, and when the items are bought the member presses "Done" ("Listo") and the closing date is set. This replaces the PRD's finalize on export or on "done".
- Q: When the cart changes while a list is active? → A: Each saved cart change refreshes the cart-based lines and saves the list. Items added by hand are kept.
- Q: What happens to the cart on Done? → A: It is emptied, and the member gets a toast saying it was closed. This replaces the earlier answer that the cart is kept.
- Q: Should the PRD change to match this spec (stored list, export does not close it, hand items are a Must)? → A: Yes; §1.5 C, §1.6, J5 and Appendix A were updated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A saved list that follows the cart (Priority: P1)

A member plans the week in the cart. Each time the cart is saved, the kitchen's active list is updated and saved, so both members see the same list, also in the shop.

**Why this priority**: The saved list is what the whole story adds, and the cart is its main source.

**Independent Test**: Save a cart, reload as a second member and see the list; save a cart change and see the list follow.

**Acceptance Scenarios**:

1. **Given** no active list, **When** a member saves a non-empty cart, **Then** an active list is saved with the same lines, amounts, order, recipe chips and "Your call" section that S-023 builds for that cart.
2. **Given** an active list, **When** a member saves a cart change, **Then** the cart-based lines are refreshed and saved, and items added by hand stay.
3. **Given** an active list, **When** a recipe is edited or deleted without a cart save, **Then** the list does not change until the next cart save.
4. **Given** a member editing the cart, **When** they have not saved, **Then** the active list and what others see do not change.

---

### User Story 2 - Add individual items (Priority: P1)

A member needs something that is in no recipe, such as dish soap. They add it to the list by hand, with or without an amount, and can remove it.

**Why this priority**: The owner asked for it: a list can be built from the cart, from individual items, or both.

**Independent Test**: With an empty cart, add an item, reload as the other member and see it; then remove it.

**Acceptance Scenarios**:

1. **Given** no active list, **When** a member adds an item, **Then** an active list is saved holding it, even with an empty cart.
2. **Given** an active list, **When** a member adds an item with a name and optionally an amount and unit, **Then** it is saved at once and the other member sees it on their next load.
3. **Given** an item added by hand, **When** a member removes it, **Then** it is gone from the list.
4. **Given** an item with the same name as a cart-based line, **When** it is added, **Then** it stays a separate line, marked as added by hand, with no recipe chips.

---

### User Story 3 - Press Done after shopping (Priority: P1)

After shopping, a member presses Done (Listo) and confirms. The list gets its closing date and never changes again.

**Why this priority**: The rule of one active list per kitchen needs a way to end a list, and history depends on the closing date.

**Independent Test**: Press Done, edit the cart and a recipe, and check that the closed list is unchanged.

**Acceptance Scenarios**:

1. **Given** an active list with items, **When** a member presses Done and confirms, **Then** the closing date is today and the list is closed.
2. **Given** a closed list, **When** recipes or the cart change, **Then** it does not change, and a deleted recipe's title still shows on its chips.
3. **Given** a list just closed, **Then** the saved cart is empty, and the member who pressed Done sees a toast saying the cart was closed.
4. **Given** no active list, **When** a member saves a non-empty cart or adds an item, **Then** a new active list starts.
5. **Given** an active list with no items, **Then** Done is disabled.

---

### User Story 4 - Look at past lists (Priority: P3)

A member opens the kitchen's closed lists, newest first, and opens one.

**Why this priority**: Useful, but the main way to reach history is the chat (S-031).

**Independent Test**: Close two lists and check the order, dates and contents.

**Acceptance Scenarios**:

1. **Given** two closed lists, **When** a member opens past lists, **Then** they see both, newest first, with closing date and recipe titles.
2. **Given** a closed list, **When** a member opens it, **Then** its lines show exactly as saved, with no way to change or reopen it.

---

### Edge Cases

- Cart saved empty while a list is active: cart-based lines go, items added by hand stay; with none left, the list stays active and empty, and Done is disabled.
- Cart non-empty with no active list (it was filled before this story shipped): the Cart page shows the S-023 live list, clearly not saved yet, until the next cart save or added item.
- Two members add items at once: both are saved.
- Two first saves at once: one active list exists, holding both.
- Done pressed while someone edits the cart: the list closes and the saved cart empties; their draft stays, and their later save starts a new list.
- Done pressed twice: closes once; the second member sees it closed.
- Item added just after the list closes: it goes to a new active list, which starts from the saved cart. It never goes into a closed list.
- A member editing the cart: Done is disabled for them until they save or discard, so they never close a list that differs from what they see. Other members may still press Done.
- Archived kitchen: lists can be read; every change and Done are refused.
- A person outside the kitchen: every list answers as not found.
- Blank item name: refused; names follow the usual trimmed, lower-case normalization.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Saving a cart MUST create or update the kitchen's active list from the saved cart using the S-023 rules, with no recalculation of its own. Saving an empty cart with no active list MUST NOT create one.
- **FR-002**: Unsaved cart drafts MUST NOT change the active list.
- **FR-003**: Any kitchen member MUST be able to add an item by hand (name required; amount, unit and size optional) and remove items added by hand. Each change MUST be saved at once and takes no cart lock.
- **FR-004**: Refreshing from the cart MUST keep items added by hand and MUST NOT merge them with cart-based lines.
- **FR-005**: A saved line MUST keep its name, amounts, size, position, section, "Your call" notes, origin (cart or by hand), and the identifiers and titles of its recipes.
- **FR-006**: A kitchen MUST have at most one active list at a time, even with simultaneous requests.
- **FR-007**: Done (Listo) MUST ask for confirmation, then set the closing date to the current day. It MUST be disabled for a list with no items, and shown only when a stored list exists (hidden while the list is live).
- **FR-008**: A closed list MUST be read only, MUST NOT be reopened and MUST NOT change when recipes, notebooks, the cart or memberships change.
- **FR-009**: Done MUST empty the saved cart in the same step as closing the list, and the member who pressed it MUST see a toast saying the cart was closed.
- **FR-010**: The Cart page MUST show the active list when there is one, and otherwise the S-023 live list. Members MUST be able to open closed lists, newest first.
- **FR-011**: People outside the kitchen MUST get a not-found answer for its lists; all changes MUST be refused in an archived kitchen.
- **FR-012**: All new text MUST exist in English and Spanish, and all new controls MUST work by keyboard at phone and desktop width.

### Key Entities *(include if feature involves data)*

- **Shopping list**: A saved list of one kitchen, with its creation time and, once closed, its closing date. Active while it has no closing date.
- **Shopping list item**: One saved line of a list, from the cart or added by hand, with the details in FR-005.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of tested carts, the saved list matches the S-023 list for that cart, line by line.
- **SC-002**: A member can add an item in under 15 seconds at phone width.
- **SC-003**: After editing and deleting every recipe of a closed list, 100% of its lines read as before.
- **SC-004**: With simultaneous requests, exactly one active list exists afterwards, every time.
- **SC-005**: A list from a 100-recipe cart opens in under 1 second.

## Assumptions

- The closing date is the current day where the member is; members do not pick it.
- Any kitchen member may change a list and press Done (PRD §3).
- Lists are kept as long as the kitchen exists and go with it; the v1 UI has no delete.
- Cart-based lines cannot be edited or removed from the list; members change them through the cart. Items do not get bought-ticks.

## Out of Scope

- Editing cart-based lines of an active list (the rest of S-046).
- Export as Markdown or PDF (S-024). Export no longer closes a list.
- Shopping list history in chat (S-031) and MCP tools (S-032).
