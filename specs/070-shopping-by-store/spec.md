# Feature Specification: Shopping by Store

**Feature Branch**: `070-shopping-by-store` (story S-070)

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "Focus on the shopping list: 1. marking items as bought 2. using tab filters based on the type of item to buy, for example if an item is best bought at the farmers market, a grocery store, some other types of places. Allow the user to define extra ones but use default ones for common places. The idea is the user picks where they buy each ingredient (by editing their ingredient catalog); this Ingredient catalog view must be a nav item on the side panel."

## Clarifications

### Session 2026-11-05

- Q: Who owns where an ingredient is bought? → A: Each person has their own places, even when the catalog is shared. A person may copy another member's places as a snapshot (no later sync) or define their own.
- Q: What place does an ingredient have before the person picks one? → A: Supermarket; the person changes only the exceptions.
- Q: Can a member pick a place when adding an item by hand? → A: Yes, optionally; it is saved to that person's places for the name, and the name then appears on their catalog page.

**Source**: owner request 2026-11-05 (post-MVP, not in `dev/docs/prd.md`; extends J5 Saved list). Builds on the saved shopping list of S-025 (`specs/025-finalize-shopping-list`), the shopping list of S-023 (`specs/023-shopping-list`), the ingredient catalog of S-018 and the side panel of S-064 (`specs/064-kitchen-side-panel`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mark items as bought (Priority: P1)

In the shop, a member taps an item on the kitchen's active shopping list to mark it bought. It moves out of the way (shown struck through at the end of its group), and the other members of the kitchen see it bought too. A wrong tap is undone by tapping again.

**Why this priority**: It is the basic use of a list in the shop and works without any store setup.

**Independent Test**: With an active list of three items, mark one bought, reload as a second member and see it bought; unmark it and see it back.

**Acceptance Scenarios**:

1. **Given** an active list, **When** a member marks an item bought, **Then** it is saved at once, shown as bought, and placed after the items not yet bought in its group.
2. **Given** a bought item, **When** a member marks it again, **Then** it is back to not bought.
3. **Given** a bought cart-based item, **When** a cart save refreshes the list and the same line (same ingredient name, unit and size) is still there, **Then** it stays bought; a line whose amount grew goes back to not bought.
4. **Given** a list closed with Done, **When** anyone opens it, **Then** each item shows whether it was bought, and nothing can be changed.
5. **Given** an active list, **When** every item is bought, **Then** the list shows that everything is bought and suggests pressing Done (Done is not pressed for the member).

---

### User Story 2 - Choose where each ingredient is bought, on the ingredient catalog page (Priority: P1)

A member opens "Ingredients" from the side panel. The page lists the ingredient names they work with and, for each, the place it is bought. They pick a place from a short list of default places (Supermarket, Farmers market, Butcher, Fish market, Bakery, Pharmacy or drugstore, Other) or add their own place, such as "Asian market".

**Why this priority**: The store tabs (story 3) need each ingredient to have a place; without this page there is nothing to filter by.

**Independent Test**: Open Ingredients from the side panel, set "tomato" to Farmers market, add a place "Asian market" and set "miso" to it, reload and see both saved.

**Acceptance Scenarios**:

1. **Given** a signed-in member, **When** they look at the side panel, **Then** it has an "Ingredients" item that opens the ingredient catalog page.
2. **Given** the catalog page, **When** it opens, **Then** it lists every ingredient name in scope (see FR-010 and FR-016a) in alphabetical order, with a text filter, each showing its place (Supermarket until picked).
3. **Given** an ingredient, **When** the member picks a place, **Then** it is saved at once.
4. **Given** the place picker, **When** the member adds a new place by name, **Then** it is saved, offered from then on next to the defaults, and can be renamed or deleted; deleting it sets its ingredients back to Supermarket after a confirmation.
5. **Given** another member of a shared kitchen or notebook, **When** the person chooses to copy that member's places and confirms, **Then** the member's places they do not have yet, and the member's choices for ingredients they have not set yet, are added to their own; nothing of their own is removed or changed, and later changes by either one do not affect the other.
6. **Given** the default places, **When** shown, **Then** their names are in the member's interface language (Spanish or English).

---

### User Story 3 - Store tabs on the shopping list (Priority: P2)

On the active list, tabs across the top show "All" and one tab per place that has items on the list (for example "Supermarket 8", "Farmers market 5"). Picking a tab shows only the items bought there, so the member can work through one shop at a time.

**Why this priority**: It is the main reason for the places, but it needs stories 1 and 2 first.

**Independent Test**: With places set for some ingredients, open the list, pick "Farmers market" and see only those items; mark one bought and see the tab's count of items left go down.

**Acceptance Scenarios**:

1. **Given** an active list, **When** it opens, **Then** the "All" tab is selected and a tab is shown for each place with at least one item,.
2. **Given** a place tab, **When** selected, **Then** only items of that place are shown, and its count shows the items not yet bought.
3. **Given** a hand-added item whose name matches a catalog ingredient, **When** shown, **Then** it takes that ingredient's place; otherwise it is under Supermarket.
4. **Given** a member changes an ingredient's place on the catalog page, **When** they return to the list, **Then** the item is under the new tab.
5. **Given** a phone-width screen, **When** the tabs do not fit, **Then** they scroll sideways and stay usable by keyboard.

---

### Edge Cases

- An ingredient name appears in more than one catalog: it has one place per person (places are set by name).
- A person copies places from a member who later leaves the kitchen: the copy stays; the member is no longer offered as a source.
- Two members look at the same list: each sees tabs from their own places.
- Two members mark the same item at nearly the same time: the last change wins and both see the same final state on their next load.
- A custom place has the same name as a default place (case and accents ignored): refused with a message.
- A custom place is deleted while a list is open on another device: its items show under Supermarket on the next load.
- The "Your call" (vague amounts) section of S-023: its items are filtered by place and can be marked bought like any other. A bought Your call line goes back to not bought when a cart save changes its notes (for example a new recipe adds "a pinch").
- An archived kitchen: its list is read-only, bought included (as S-025 refuses other list changes).
- A closed list opened later: its tabs use the viewer's current places, since places are not saved with the list.
- An empty list: no tabs other than "All", and the existing empty message.

## Requirements *(mandatory)*

### Functional Requirements

**Bought**

- **FR-001**: Any member of the kitchen MUST be able to mark an item of the kitchen's active shopping list as bought and unmark it; each change is saved at once.
- **FR-002**: The bought state MUST be shared: every member of the kitchen sees the same state on their next load.
- **FR-003**: A cart save that refreshes the cart-based lines (S-025) MUST keep the bought state of a line that is still present and has not grown, by the rule in research R2 (same section, name, kind and size; no amount larger and no unit added; for a "Your call" line, the same notes); any other refreshed line starts not bought. Hand-added items keep their state.
- **FR-004**: Done (S-025) MUST keep each item's bought state on the closed list, read-only. Done stays allowed with items not bought.
- **FR-005**: Bought items MUST be shown visibly different (struck through and muted) and after the items not yet bought in their group, without relying on color alone.

**Places**

- **FR-006**: The system MUST offer default places: Supermarket, Farmers market, Butcher, Fish market, Bakery, Pharmacy or drugstore, and Other, named in English and Spanish.
- **FR-007**: A person MUST be able to add, rename and delete their own places; names are 1 to 40 characters, unique among the defaults and their places, ignoring case and accents. At most 30 custom places.
- **FR-008**: Each ingredient name MUST have exactly one place per person; until the person picks one it is Supermarket. Picking Supermarket again is allowed and is the same as the starting value.
- **FR-009**: Default places MUST NOT be renamed or deleted.

**Ingredient catalog page**

- **FR-010**: Places of ingredients and custom places MUST belong to each person: their choices apply on every list they open, in every kitchen, even when the catalog or list is shared, so two members may see different tabs for the same list. The catalog page lists every ingredient name in the catalogs of the notebooks the person can read (personal and kitchen), each name once.
- **FR-010a**: A person MUST be able to copy the places (ingredient places and custom places) of another member of a kitchen or notebook they share. The copy is a snapshot merged into the person's own after a confirmation (changed 2026-11-05, was a replace): only places whose name the person does not have yet (ignoring case and accents, within the 30-place limit) and choices for ingredients the person has not set yet are added; nothing of the person's is removed or changed. A copied choice of one of the member's places points at the person's place of the same name. Later changes by either person do not reach the other. The person can then change any place on their own.
- **FR-011**: The side panel MUST have an "Ingredients" nav item that opens the catalog page, at phone and desktop widths, in both languages.
- **FR-012**: The catalog page MUST list ingredient names alphabetically with a text filter, and a place picker per name that saves on change; it MUST also let the person manage their custom places (FR-007).
- **FR-013**: The catalog page MUST NOT rename, merge or delete ingredient names; that is S-043.

**Store tabs**

- **FR-014**: The active list and closed lists MUST show an "All" tab and one tab per place with at least one item,; defaults first in the FR-006 order, then custom places alphabetically. The Place picker of a catalog or ingredient table is a separate control and lists custom places first, then defaults (spec 074, owner decision 2026-11-08).
- **FR-015**: Each place tab MUST show the number of its items not yet bought.
- **FR-016**: An item's place MUST be the place of the ingredient with the same normalized name (S-018 normalization); hand-added items follow the same rule.
- **FR-016a**: Adding an item by hand (S-025) MUST offer an optional place picker. A picked place is saved to the adding person's places for that normalized name (replacing any earlier choice), and the name is listed on their catalog page from then on even if no catalog has it. Other members still see the item under their own place for that name.
- **FR-017**: The selected tab MUST be kept while the person stays on the list and MUST reset to "All" when another list is opened.
- **FR-018**: Tabs, bought toggles and the place picker MUST be usable by keyboard and announced by screen readers, at 360 px and 1280 px.

### Key Entities

- **Place**: where items are bought. A default place (fixed, translated name) or a custom place (name, owned by one person).
- **Ingredient place**: one person's choice of place for one ingredient name.
- **Shopping list item** (existing, S-025): gains a bought state, kept on the closed list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member marks an item bought with one tap, and the change shows on screen in under 0.5 s.
- **SC-002**: A second member sees the bought state on their next load in every test case.
- **SC-003**: Setting the place of an ingredient on the catalog page takes at most 2 taps after finding it.
- **SC-004**: With places set, a member sees only one shop's items in one tap from the list.
- **SC-005**: A list of 100 items opens with its tabs and counts in under 1 s on the dev stack.

## Assumptions

- The shopping list in scope is the kitchen's saved list of S-025 (active and closed); the derived cart preview of S-023 gets no bought state.
- The bought state belongs to the list item, not to the person who marked it; who marked it is not shown.
- Prices, quantities bought and receipts are out of scope (S-068 may later mark items bought from a receipt).
- Choosing a place while editing a draft or recipe is out of scope; places are set on the catalog page or when adding an item by hand.
- S-064's side panel is the navigation this story extends.
- Places are not saved with a list: a closed list's tabs follow the viewer's places at the time it is opened.
- "Store tabs" is the on-screen name of the tab strip; everywhere else the term is "place".
- This story lifts no MVP-era rule.
