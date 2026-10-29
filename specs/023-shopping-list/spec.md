# Feature Specification: Consolidated Shopping List from the Kitchen Cart

**Feature Branch**: `023-shopping-list` (story S-023)

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "S-023 from dev/docs/backlog.yaml and dev/docs/prd.md: consolidated shopping list (domain/cart.py) with units, sizes, vague section and chips."

**Source**: `dev/docs/prd.md` §1.5 C, §1.6 (value sets, dimension order), J5 steps 1–7, AC5.1–AC5.4; backlog S-023. Builds on the shared cart of S-022 (`specs/022-shared-cart`).

## Clarifications

### Session 2026-10-29

- Q: Where should the shopping list live in the app? → A: On the Cart page itself, below the cart's recipes.
- Q: While editing the cart, does the list follow the unsaved draft? → A: Yes for the editor: their list follows their draft live (People, Meals, recipes added or removed); everyone else sees the list of the saved cart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See one combined shopping list for the week (Priority: P1)

A member has put the week's recipes in the kitchen's cart, with People and Meals set. They open the shopping list and see every ingredient they need to buy once, with the amounts already scaled to the number of people and meals, and the same ingredient from different recipes added together.

**Why this priority**: This is the reason the app exists (PRD Problem and Goal): no more building the list by hand from several recipes.

**Independent Test**: Put two recipes that share an ingredient in the cart, open the shopping list, and check the combined, scaled line.

**Acceptance Scenarios**:

1. **Given** recipe A needs 3 tbsp of flour and recipe B needs 1 cup of flour, both with factor 1, **When** the member opens the shopping list, **Then** it shows one line `flour — 1 cup + 3 tbsp` (AC5.1).
2. **Given** a recipe with base servings 4 and 2 eggs, People 3 and Meals 1, **When** the list is shown, **Then** the eggs line reads `egg — 2`: the scaled 1.5 is rounded up (AC5.2).
3. **Given** rice in grams in one recipe and in cups in another, **When** the list is shown, **Then** rice appears on two lines, one per kind of measure (mass and volume), never converted (AC5.3).
4. **Given** two recipes with 1 large onion each and one with 1 small onion, **When** the list is shown, **Then** it shows `onion, large — 2` and `onion, small — 1` (AC5.4).
5. **Given** the same ingredient with different preparations ("chopped onion", "sliced onion"), **When** the list is shown, **Then** they are one line: preparation is ignored.
6. **Given** recipes from two different kitchen notebooks that both use "garlic", **When** the list is shown, **Then** garlic is one line.

---

### User Story 2 - See which recipes each line is for (Priority: P1)

Each line of the list shows small labels (chips) with the titles of the recipes it comes from, so the member knows why they are buying it and can skip a line if they drop a recipe.

**Why this priority**: PRD J5 step 7; without it a combined line cannot be traced back.

**Independent Test**: A line made from two recipes shows both titles; a line from one recipe shows one.

**Acceptance Scenarios**:

1. **Given** flour comes from recipes A and B, **When** the list is shown, **Then** the flour line shows chips "A" and "B", in the order the recipes are in the cart.
2. **Given** a chip, **When** the member taps it, **Then** the recipe's page opens, with Back returning to the Cart page.

---

### User Story 3 - Vague amounts in their own "Your call" section (Priority: P1)

Ingredients a recipe gives without an amount ("a pinch of salt", "oil to taste") are listed apart, in a section called "Your call", once per ingredient with every note it has, because the member decides how much to buy.

**Why this priority**: PRD J5 step 6; mixing them into measured lines would give wrong or meaningless amounts.

**Independent Test**: A cart with "salt — a pinch" in one recipe and "salt — to taste" in another shows one "salt" entry under "Your call" with both notes.

**Acceptance Scenarios**:

1. **Given** salt is vague in two recipes ("a pinch", "to taste"), **When** the list is shown, **Then** "Your call" has one salt entry listing "a pinch" and "to taste", with chips for both recipes.
2. **Given** butter is vague in recipe A and 100 g in recipe B, **When** the list is shown, **Then** butter appears in the measured list (`butter — 100 g`, chip B) and under "Your call" (chip A).
3. **Given** the same note in two recipes, **When** the list is shown, **Then** the note appears once.

---

### User Story 4 - The list always matches the current cart (Priority: P2)

The list is never out of date: whenever the cart, its People or Meals, or a recipe in it changes and is saved, the next time anyone opens the list it reflects the change.

**Why this priority**: The list is derived from the cart (PRD §1.5 C) and must not drift; it matters once the main list works.

**Independent Test**: Change People from 2 to 4 on the Cart page, save, reopen the list: every measured amount doubles (with counts rounded up again).

**Acceptance Scenarios**:

1. **Given** a saved cart, **When** a member changes People or Meals and saves, **Then** the list shows the new amounts on its next open.
2. **Given** a recipe in the cart whose ingredients are edited and saved, **When** the list is opened, **Then** it uses the edited ingredients.
3. **Given** member A is editing the cart and changes People from 2 to 4 without saving, **When** A looks at the list, **Then** every scaled amount follows the new number at once; **When** member B opens the Cart page, **Then** B's list still shows the saved cart.
4. **Given** A discards the draft, **When** A looks at the list, **Then** it returns to the saved cart's list.
5. **Given** an empty cart, **When** the member opens the Cart page, **Then** no shopping list section is shown, only the Cart page's hint to add recipes.

---

### Edge Cases

- A recipe deleted while in the cart leaves the cart (S-022), so it never reaches the list.
- A count total that is already whole is not rounded (2 + 1 eggs → 3). Rounding up happens once, after summing (two lines of 0.5 egg give 1, not 2).
- A mass or volume total with more than 2 decimals is shown with at most 2, trailing zeros removed (`0.33 cup`, `1.5 cup`, `2 cup`).
- Units of the same kind are summed per unit and never converted or carried over: `1 cup + 20 tbsp` stays as is (PRD §4).
- A counted ingredient with no size is its own line, separate from its sized lines (`onion — 1`, `onion, large — 2`).
- Two recipes with the same title in the cart: each gets its own chip, both reading the same title.
- A non-member opening a kitchen's shopping list gets the same "not found" as for a kitchen that does not exist.
- An archived kitchen's list can still be read.
- Names that differ only by spelling ("onion" vs "onions") are separate lines; names are merged exactly as stored, already normalized by the catalog (S-018).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every member of a kitchen MUST see the kitchen's shopping list, built from the kitchen's **saved** cart: its People number, its recipes and each recipe's Meals (S-022). The member who is editing the cart MUST instead see the list built from their own draft, updated as they change People, Meals or the recipes, without saving. Nobody else MUST ever see an unsaved draft in their list.
- **FR-002**: The list MUST be built fresh on every open from the current cart and the current recipes; it MUST NOT be stored (PRD §1.5 C). Finalizing a list as a snapshot is S-025.
- **FR-003**: Each measured or counted ingredient line of a cart recipe MUST be scaled by that recipe's factor, People × Meals ÷ base servings, computed exactly (no rounding before the sums).
- **FR-004**: Scaled lines MUST be grouped by ingredient name and kind of measure, where the kind is mass (`kg, lb, oz, g`), volume (`l, cup, tbsp, tsp, ml`) or count (`unit`), derived from the unit. Preparation MUST be ignored. The same name in two kinds MUST give two lines.
- **FR-005**: Count lines MUST also be split by size: one line per size (small, medium, large) and one for no size. Each count total MUST be summed first, then rounded **up** to a whole number.
- **FR-006**: Mass and volume lines MUST sum per unit without converting, and show the units from largest to smallest (mass: kg, lb, oz, g; volume: l, cup, tbsp, tsp, ml), joined with " + " (`flour — 1 cup + 3 tbsp`). Each amount MUST show at most 2 decimals, rounded half up, with trailing zeros removed.
- **FR-007**: Lines with a vague amount MUST NOT be scaled and MUST go into a separate section, "Your call", one entry per ingredient name, listing each distinct note once in the order first met. An ingredient both vague and measured MUST appear in both places.
- **FR-008**: Every line and every "Your call" entry MUST show chips with the titles of the recipes it comes from, each recipe once, in cart order. Tapping a chip MUST open that recipe's page, with Back returning to the Cart page.
- **FR-009**: Line display MUST read `{name} — {amounts}`, with the size after the name for sized counts (`onion, large — 2`); count amounts show the number only.
- **FR-010**: Measured lines MUST be listed in alphabetical order of name (ignoring accents and case); for the same name, mass before volume before count, and for counts large, medium, small, then no size. "Your call" entries MUST be in alphabetical order.
- **FR-011**: When the cart (or the editor's draft) is empty, the shopping list section MUST NOT be shown; the Cart page's existing empty hint (S-022), with its link to the kitchen's recipes, covers it.
- **FR-012**: The list MUST be shown on the kitchen's Cart page, below the cart's recipes, and MUST be readable by every kitchen member, including in an archived kitchen and while another member is editing the cart. Non-members and unknown kitchens MUST get the same "not found".
- **FR-013**: All text of the list (titles, "Your call", the hint, errors) MUST exist in Spanish and English (spec 063). Ingredient names, notes and recipe titles are shown as stored, untranslated.
- **FR-014**: Opening the list MUST NOT change the cart, the recipes, the catalog or any recipe's cart add count.

### Key Entities

- **Shopping list (derived, not stored)**: for one kitchen at one moment: the measured lines, the "Your call" entries, and whether the cart is empty.
- **Measured line**: ingredient name, kind of measure, size (counts only), the amounts per unit (or one whole count), and the recipes it comes from.
- **"Your call" entry**: ingredient name, its distinct vague notes, and the recipes it comes from.
- Read from existing data: the saved cart (People, recipes, Meals), and each recipe's base servings and ingredient lines (name, quantity, unit, size, vague note).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: AC5.1–AC5.4 of the PRD pass exactly as written, in automated tests and in the app.
- **SC-002**: A member gets a complete list for a cart of 10 recipes without typing or adding anything by hand.
- **SC-003**: For a cart of 100 recipes with 20 lines each, the list opens in under 1 second.
- **SC-004**: Every amount on the list matches a hand calculation of scale-then-sum for at least 20 invented test carts, including counts rounded up only after summing.
- **SC-005**: Every line and entry can be traced to its recipes through its chips: 100% of lines show at least one chip.
- **SC-006**: A member who changes People and saves sees the new amounts the next time they open the list, with no manual refresh of cached data.

## Assumptions

- The list is shown on the Cart page, below the recipes (clarified 2026-10-29).
- Other members see the saved cart's list; they see the editor's changes after the editor saves (S-022 has no live push; they refresh on focus).
- Names merge exactly as stored. Recipe lines already carry normalized catalog names (S-018), and lines from different notebooks merge when the strings are equal; nothing is translated between `content_language` values.
- Vague lines are not scaled and carry no amount.
- The rounding and formatting of measured amounts follow the cart's factor formatting (half up, at most 2 decimals, trailing zeros removed); counts always show whole numbers.
- "Your call" is "A tu criterio" in Spanish (wording for the owner's review).
- Out of scope: export as Markdown or PDF (S-024), finalizing a list with a closing date (S-025), editing list items (S-046), shopping list history in chat (S-031), MCP tools (S-032), unit conversion of any kind (PRD §4).
