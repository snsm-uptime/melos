# Feature Specification: Recipe Lists for a Personal Notebook and a Kitchen

**Feature Branch**: not created by this command

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "S-021" (Recipe lists for a personal notebook and for a kitchen (its notebooks), with a text filter)

**Related**: Builds on spec 020 (save a confirmed draft, which stores recipes but lists none), spec 056 (notebooks and their access rules) and spec 060 (notebook list and tabs, whose cards open the recipe list "once S-021 exists"). PRD J3 "Lists". Out of this feature: the richer kitchen cards of S-047 (ingredient, author and notebook filters, cart-frequency sort, "Add to cart" checkbox), recipe detail, edit and delete (S-027), the cart (S-022) and categories (S-061).

## Clarifications

### Session 2026-10-27

- Q: Should a member of an archived kitchen still see its recipe list, read-only? → A: Yes, read-only with no capture action (FR-011).
- Q: Should a long list use a "Load more" button, automatic loading on scroll, or numbered pages? → A: Numbered pages (FR-006).
- Q: How many recipe cards per page? → A: 12 (FR-006).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the recipes of a personal notebook (Priority: P1)

A member opens one of their personal notebooks (from a card on the Notebook tab, or after saving a recipe) and sees the recipes in it as cards. Each card shows a preview image or a default cooking-pot icon, the title, the author's alias and the number of ingredients. A notebook with no recipes says so and points to capture.

**Why this priority**: Spec 020 stores recipes that nobody can see. Without a list, saved work looks lost and every later recipe story has no entry point.

**Independent Test**: Save two recipes into a personal notebook, open the notebook, and check that both appear as cards with title, author alias and ingredient count, newest first.

**Acceptance Scenarios**:

1. **Given** a personal notebook with two recipes, **When** the owner opens it, **Then** two cards appear, newest first, each with a default cooking-pot icon, the title, the author alias and the ingredient count.
2. **Given** a member of another person's personal notebook, **When** they open it, **Then** they see the same recipes as the owner.
3. **Given** a personal notebook with no recipes, **When** it is opened, **Then** a message says the notebook has no recipes yet and suggests capturing one; no error is shown.
4. **Given** a recipe whose author's account is gone, **When** the list is shown, **Then** the author chip reads "unknown".
5. **Given** a person with no access to a personal notebook, **When** they try to open its list, **Then** the answer is the same as for a notebook that does not exist.
6. **Given** a member who has just saved a recipe (spec 020), **When** they land back on the notebook, **Then** the new recipe is the first card.

---

### User Story 2 - See all recipes of a kitchen across its notebooks (Priority: P1)

A kitchen member opens the kitchen's Notebook tab and sees the recipes of all of the kitchen's notebooks together as cards. A recipe saved by one member shows to every member of the kitchen. Personal notebooks never contribute to it.

**Why this priority**: The kitchen is where recipes are shared and, later, planned and shopped for. It is the second of the two lists named in the story.

**Independent Test**: In a kitchen with two members and one notebook, have each member save a recipe, then open the kitchen's Notebook tab as each member and check that both recipes appear with the right author chips.

**Acceptance Scenarios**:

1. **Given** a kitchen with two notebooks holding two and three recipes, **When** a member opens the kitchen's Notebook tab, **Then** all five recipes appear as cards, newest first.
2. **Given** a recipe saved into a kitchen notebook by member A, **When** member B opens the kitchen's Notebook tab, **Then** it appears with A's alias as the author chip.
3. **Given** a member whose personal notebook holds recipes, **When** they open a kitchen's Notebook tab, **Then** none of their personal recipes appear.
4. **Given** a kitchen whose notebooks hold no recipes, **When** a member opens the tab, **Then** a message says there are no recipes yet and suggests capturing one.
5. **Given** a person who is not a member of the kitchen, **When** they try to open its list, **Then** the answer is the same as for a kitchen that does not exist.
6. **Given** an archived kitchen the member still belongs to, **When** they open its list, **Then** the recipes are shown read-only, with no capture action offered.
7. **Given** a kitchen with a recipe from each of two notebooks, **When** the list is shown, **Then** each card says which notebook it is in.

---

### User Story 3 - Filter a list by text (Priority: P2)

On either list the member types a word and the list narrows to recipes whose title or any ingredient name contains it, ignoring letter case and accents. Clearing the box brings the whole list back.

**Why this priority**: Useful as soon as a notebook holds more than a screenful of recipes, but the lists are valuable without it.

**Independent Test**: With recipes "Lentil soup" (ingredients: lentil, onion) and "Pancakes" (flour, milk), type "onion" and see only the soup; type "PANCAKE" and see only the pancakes; clear the box and see both.

**Acceptance Scenarios**:

1. **Given** a list with "Lentil soup" and "Pancakes", **When** the member filters by "soup", **Then** only "Lentil soup" shows.
2. **Given** the same list, **When** the member filters by "milk", **Then** only "Pancakes" shows, because one of its ingredients matches.
3. **Given** a recipe titled "Crema de calabaza", **When** the member filters by "CALABAZA" or "calabazá", **Then** it shows.
4. **Given** a filter that matches nothing, **When** it is applied, **Then** a message says no recipes match the text and the filter can be cleared in one action.
5. **Given** a filter on the kitchen list, **When** it is applied, **Then** it searches the recipes of all the kitchen's notebooks, not only one.
6. **Given** a filter containing only spaces, **When** it is applied, **Then** the full list is shown.

---

### Edge Cases

- Many recipes: the list is split into numbered pages so a notebook with hundreds of recipes still opens quickly, and the filter applies to the whole notebook, not only the current page. A page number past the last page shows the last page.
- A recipe is saved while the list is open: it shows the next time the list is loaded; no live update is required.
- A recipe is deleted in another tab or by another member (S-027 later): it is absent on the next load; a stale card never opens a broken page.
- Titles and ingredient names with accents, ñ, ¿ or fractions display unchanged.
- A very long title is shortened on the card without breaking the layout and shown in full where there is room.
- A recipe with one ingredient line or with 100 lines shows the right count.
- A person belongs to a kitchen that has no notebook yet: the list is empty with the same message as an empty list; opening the list creates nothing.
- Different recipes with the same title in different notebooks both appear.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A member MUST be able to see the list of recipes of a personal notebook they own or belong to, and the list of recipes of all notebooks of a kitchen they belong to.
- **FR-002**: A personal notebook list MUST contain only that notebook's recipes. A kitchen list MUST contain the recipes of every notebook of that kitchen and MUST NOT contain any recipe of a personal notebook.
- **FR-003**: Each recipe MUST appear as a card showing a preview image or, when it has none, a default cooking-pot icon; the title; the author's alias as a chip ("unknown" if the account is gone); and the ingredient count.
- **FR-004**: On a kitchen list, each card MUST also show the name of the notebook the recipe is in.
- **FR-005**: Cards MUST be ordered newest first. A recipe just saved MUST be at the top on the next load.
- **FR-006**: Lists MUST be split into numbered pages of 12 cards in a stable order. The member MUST see the current page number and the total number of pages, and MUST be able to go to the previous page, the next page and a page by number. Changing the text filter MUST return to page 1.
- **FR-007**: Both lists MUST offer a text filter. A recipe matches when the text appears in its title or in the name of any of its ingredient lines, ignoring letter case and accents. Surrounding spaces in the text MUST be ignored, and empty text MUST show the whole list.
- **FR-008**: The filter MUST apply to every recipe of the list, not only the current page, and MUST NOT change the order of the cards.
- **FR-009**: An empty list and a list with no filter match MUST each show a distinct plain message; the empty list MUST point to capture, and the no-match message MUST offer to clear the filter.
- **FR-010**: A person without access to the notebook or kitchen MUST get the same answer as for one that does not exist; a non-member MUST NOT learn that it exists or what it holds.
- **FR-011**: An archived kitchen the person belongs to MUST show its recipes read-only, with no capture action.
- **FR-012**: Opening a list MUST NOT create, change or delete anything (no notebook, recipe or catalog entry).
- **FR-013**: The cards of the Notebook tab and of the kitchen notebooks section (spec 060) MUST open the notebook's recipe list, replacing the "does nothing until S-021" behavior of spec 060. After a Save (spec 020), the member MUST land on this list.
- **FR-014** *(superseded for the detail link by spec 027 FR-004: the cards now link to the recipe detail)*: Recipe cards MUST NOT carry a link to a detail page, an "Add to cart" checkbox, category chips, or ingredient, author, notebook and frequency controls; those belong to S-027, S-022, S-061 and S-047.
- **FR-015**: All messages shown by the lists MUST be in plain English, with no codes or technical terms.

### Key Entities *(include if feature involves data)*

- **Recipe card**: The list view of a saved recipe: its title, preview image (or default icon), author alias, ingredient count, creation time and, on kitchen lists, its notebook's name.
- **Recipe**: A saved recipe in exactly one notebook (spec 020). Listing only reads it.
- **Notebook**: A personal notebook (listed alone) or a kitchen's notebooks (listed together). Access rules are those of spec 056.
- **Text filter**: The words the member types; matched against the recipe title and the names of its ingredient lines.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member who saves a recipe sees it as the first card of its notebook without any further action, in 100% of saves.
- **SC-002**: A personal notebook or kitchen with up to 200 recipes shows its first cards within 2 seconds in normal conditions.
- **SC-003**: In 100% of checks, a kitchen list shows every recipe of the kitchen's notebooks and none from any personal notebook.
- **SC-004**: A member finds a recipe by a word from its title or one of its ingredients in one typed entry, and 100% of recipes containing that word (any case or accent) are included in the result.
- **SC-005**: A person without access cannot tell whether a notebook or kitchen exists: the answer is identical to a missing one in 100% of cases.
- **SC-006**: Opening any list leaves the stored data unchanged in 100% of checks.

## Assumptions

- Recipes already exist from spec 020; no recipe has a preview image yet, so every card shows the default cooking-pot icon until an image story exists.
- Sort is newest first only. Alphabetical and cart-frequency sort belong to S-047 and need the cart (S-022).
- The text filter searches title and ingredient names only; it is plain text matching, not the semantic search of S-019.
- "Newest" means the time the recipe was saved.
- The kitchen's Notebook tab is the screen that spec 060 already places for the kitchen; this feature fills it with the recipe list rather than adding a new navigation entry.
- Cards are not tappable into a detail page until S-027 exists; the cards of this feature are display-only.
- Archived kitchens keep their recipes readable (consistent with archived kitchens being read-only elsewhere).
