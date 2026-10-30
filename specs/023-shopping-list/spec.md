# Feature Specification: Consolidated Shopping List from the Kitchen Cart

**Feature Branch**: `023-shopping-list` (story S-023)

**Created**: 2026-10-29

**Status**: Draft (amended 2026-10-30: cart by servings, selected cards, remove icon)

**Input**: User description: "S-023 from dev/docs/backlog.yaml and dev/docs/prd.md: consolidated shopping list (domain/cart.py) with units, sizes, vague section and chips."

**Source**: `dev/docs/prd.md` §1.5 C, §1.6 (value sets, dimension order), J5 steps 1–7, AC5.1–AC5.4; backlog S-023. Builds on the shared cart of S-022 (`specs/022-shared-cart`).

## Clarifications

### Session 2026-10-29

- Q: Where should the shopping list live in the app? → A: On the Cart page itself, below the cart's recipes.
- Q: While editing the cart, does the list follow the unsaved draft? → A: Yes for the editor: their list follows their draft live (People, Meals, recipes added or removed); everyone else sees the list of the saved cart.

### Session 2026-10-30 (cart by servings)

- Q: How should servings work on the cart? → A: Each recipe has its own Servings number, and the cart's People number is removed entirely, input and logic. Factor = Servings ÷ base servings. This replaces People × Meals everywhere, including the older text of this spec.
- Q: What does Servings start at when a recipe is added? → A: The recipe's base servings, so the factor starts at 1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See one combined shopping list for the week (Priority: P1)

A member has put the week's recipes in the kitchen's cart, with Servings set for each. They open the shopping list and see every ingredient they need to buy once, with the amounts already scaled to the servings chosen, and the same ingredient from different recipes added together.

**Why this priority**: This is the reason the app exists (PRD Problem and Goal): no more building the list by hand from several recipes.

**Independent Test**: Put two recipes that share an ingredient in the cart, open the shopping list, and check the combined, scaled line.

**Acceptance Scenarios**:

1. **Given** recipe A needs 3 tbsp of flour and recipe B needs 1 cup of flour, both with factor 1, **When** the member opens the shopping list, **Then** it shows one line `flour — 1 cup + 3 tbsp` (AC5.1).
2. **Given** a recipe with base servings 4 and 2 eggs, Servings 3, **When** the list is shown, **Then** the eggs line reads `egg — 2`: the scaled 1.5 is rounded up (AC5.2).
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

The list is never out of date: whenever the cart, its Servings, or a recipe in it changes and is saved, the next time anyone opens the list it reflects the change.

**Why this priority**: The list is derived from the cart (PRD §1.5 C) and must not drift; it matters once the main list works.

**Independent Test**: With one recipe in the cart, double its Servings on the Cart page, save, reopen the list: every measured amount doubles (with counts rounded up again).

**Acceptance Scenarios**:

1. **Given** a saved cart, **When** a member changes Servings and saves, **Then** the list shows the new amounts on its next open.
2. **Given** a recipe in the cart whose ingredients are edited and saved, **When** the list is opened, **Then** it uses the edited ingredients.
3. **Given** member A is editing the cart and doubles a recipe's Servings without saving, **When** A looks at the list, **Then** that recipe's scaled amounts follow the new number at once; **When** member B opens the Cart page, **Then** B's list still shows the saved cart.
4. **Given** A discards the draft, **When** A looks at the list, **Then** it returns to the saved cart's list.
5. **Given** an empty cart, **When** the member opens the Cart page, **Then** no shopping list section is shown, only the Cart page's hint to add recipes.

---

### User Story 5 - Plan the cart by servings (Priority: P1)

A member decides, recipe by recipe, how many servings to make. "Meals" and the cart-wide People number are gone, because together they were confusing. The shopping list scales each recipe by the servings chosen for it.

**Why this priority**: Every amount on the shopping list depends on this number, so it has to be clear what it means.

**Independent Test**: Add a recipe with base servings 4 to the cart: Servings reads 4 and the factor 1. Set Servings to 6: the factor reads 1.5, and the shopping list amounts are 1.5 times the recipe's.

**Acceptance Scenarios**:

1. **Given** a recipe with base servings 4 not in the cart, **When** a member adds it, **Then** its Servings reads 4 and its factor reads 1.
2. **Given** that recipe in the cart with 2 eggs, **When** the editor sets Servings to 6, **Then** the factor reads 1.5 and the editor's list shows `egg — 3` before saving.
3. **Given** a recipe with base servings 3 and Servings 2, **When** the cart is shown, **Then** the factor reads 0.67.
4. **Given** two recipes in the cart, **When** the editor changes the Servings of one, **Then** the other's Servings and factor do not change.
5. **Given** the Cart page in either language, **When** it is shown, **Then** no People control and no "Meals" or "Comidas" label appears, and the per-recipe control reads "Servings" or "Porciones".
6. **Given** a cart saved before this change, with People 3 and Meals 2 on a recipe, **When** it is opened after the change, **Then** that recipe's Servings reads 6 and its shopping list amounts are unchanged.

---

### User Story 6 - See which recipe cards are in the cart (Priority: P2)

A member browsing the kitchen's recipes can tell at a glance which cards are already in the cart, because those cards have a different background colour.

**Why this priority**: The cart-icon button alone is easy to miss when scanning a list, but the cart still works without this.

**Independent Test**: With one of two recipes in the cart, open the kitchen's recipe list: only that card has the selected background, in light and dark themes. Remove it: the card returns to the normal background.

**Acceptance Scenarios**:

1. **Given** a kitchen's recipe list, **When** a recipe is in the cart the member sees, **Then** its card shows the selected background and the others show the normal one.
2. **Given** a card with the normal background, **When** the member adds it to the cart, **Then** the background changes at once; removing it restores the normal one.
3. **Given** the editor's unsaved draft, **When** they view the list, **Then** the backgrounds follow their draft; other members' backgrounds follow the saved cart.

---

### User Story 7 - Remove a recipe with the close icon (Priority: P3)

While editing the cart, a member removes a recipe with an icon button showing the app's close icon (✕) instead of a "Remove" text button.

**Why this priority**: A visual cleanup that saves room in each row.

**Independent Test**: Start editing a cart: each row shows the close icon button with no "Remove" text, and pressing it removes the recipe from the draft.

**Acceptance Scenarios**:

1. **Given** the cart in editing mode, **When** it is shown, **Then** each recipe has a close icon button, and pressing it removes that recipe from the draft.
2. **Given** a screen reader or keyboard user, **When** they reach the button, **Then** it can be focused and pressed by keyboard, and it is announced as removing that recipe, in the member's language.
3. **Given** the cart in read-only mode, **When** it is shown, **Then** no remove button appears.

---

### Edge Cases

- People × Meals above 99 on a saved cart converts to Servings 99, the top of the allowed range; that recipe's amounts then change, and this is accepted as such a cart is very unlikely.
- A cart that never set People converts using the kitchen's member count at conversion time, as People defaulted to that.
- An editor's unsaved draft at the moment of the change may be lost; the draft is not guaranteed to survive the conversion.
- Servings outside 1 to 99, blank, a decimal or text is refused as Meals was: the last valid value stays and the field says what is accepted.
- Editing a recipe's base servings while it is in the cart keeps its Servings and recomputes its factor.
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

- **FR-001**: Every member of a kitchen MUST see the kitchen's shopping list, built from the kitchen's **saved** cart: its recipes and each recipe's Servings (S-022, FR-015). The member who is editing the cart MUST instead see the list built from their own draft, updated as they change Servings or the recipes, without saving. Nobody else MUST ever see an unsaved draft in their list.
- **FR-002**: The list MUST be built fresh on every open from the current cart and the current recipes; it MUST NOT be stored (PRD §1.5 C). Finalizing a list as a snapshot is S-025.
- **FR-003**: Each measured or counted ingredient line of a cart recipe MUST be scaled by that recipe's factor, Servings ÷ base servings, computed exactly (no rounding before the sums).
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
- **FR-015**: Each cart entry MUST have a Servings number, whole, from 1 to 99, set to the recipe's base servings when it is added. It replaces Meals.
- **FR-016**: A recipe's factor MUST be Servings ÷ base servings, recomputed on every read and never stored, shown as today (at most 2 decimals, no trailing zeros). This replaces People × Meals ÷ base servings (spec 022 FR-007).
- **FR-017**: The cart's People number and the Meals number MUST be removed from the product: controls, saved data, default-to-member-count logic and every other use. No code, label or test for them MUST remain, except where needed to convert saved carts (FR-018). "Meals" as an everyday word in landing page copy is not affected.
- **FR-018**: Saved carts MUST be converted so that each entry's Servings is People × Meals, capped at 99, with the member count used where People was never set.
- **FR-019**: The per-recipe control MUST read "Servings" in English and "Porciones" in Spanish, in the editing and read-only views.
- **FR-020**: A recipe card in a kitchen's list MUST use a distinct background while its recipe is in the cart that member sees (their draft if they are the editor, otherwise the saved cart), must keep readable text in light and dark themes, and MUST still show the cart-icon button's state, so colour is not the only signal.
- **FR-021**: The cart's remove action MUST be an icon button showing the app's existing close icon, with no visible text, and with an accessible name in the member's language that names the recipe.

### Key Entities

- **Shopping list (derived, not stored)**: for one kitchen at one moment: the measured lines, the "Your call" entries, and whether the cart is empty.
- **Measured line**: ingredient name, kind of measure, size (counts only), the amounts per unit (or one whole count), and the recipes it comes from.
- **"Your call" entry**: ingredient name, its distinct vague notes, and the recipes it comes from.
- Read from existing data: the saved cart (recipes and their Servings), and each recipe's base servings and ingredient lines (name, quantity, unit, size, vague note).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: AC5.1–AC5.4 of the PRD pass exactly as written, in automated tests and in the app.
- **SC-002**: A member gets a complete list for a cart of 10 recipes without typing or adding anything by hand.
- **SC-003**: For a cart of 100 recipes with 20 lines each, the list opens in under 1 second.
- **SC-004**: Every amount on the list matches a hand calculation of scale-then-sum for at least 20 invented test carts, including counts rounded up only after summing.
- **SC-005**: Every line and entry can be traced to its recipes through its chips: 100% of lines show at least one chip.
- **SC-006**: A member who changes Servings and saves sees the new amounts the next time they open the list, with no manual refresh of cached data.
- **SC-007**: For every cart entry, the shown factor equals Servings ÷ base servings to 2 decimals, in 100% of tested combinations.
- **SC-008**: After the change, every shopping list amount of a converted cart matches its amount before the change, for carts with People × Meals of 99 or less.
- **SC-009**: No screen, in either language, shows People or Meals as a cart control.

## Assumptions

- Scope: this amends S-023 at the owner's request (2026-10-30). The rule change also supersedes spec 022's People and Meals text and PRD J4, J5 and AC5.2, which must be brought in line (AC5.2 becomes base servings 4, Servings 3, 2 eggs → 1.5 shown as 2 eggs).
- "Porciones" is the Spanish wording, for the owner's review.
- The selected card background is a tint of the app's accent colour; the exact shade is a design detail.
- The recipe's cart add count and the single-editor lock do not change.
- Adding a recipe no longer depends on the kitchen's member count, so a new member changes nothing in the cart.
- The list is shown on the Cart page, below the recipes (clarified 2026-10-29).
- Other members see the saved cart's list; they see the editor's changes after the editor saves (S-022 has no live push; they refresh on focus).
- Names merge exactly as stored. Recipe lines already carry normalized catalog names (S-018), and lines from different notebooks merge when the strings are equal; nothing is translated between `content_language` values.
- Vague lines are not scaled and carry no amount.
- The rounding and formatting of measured amounts follow the cart's factor formatting (half up, at most 2 decimals, trailing zeros removed); counts always show whole numbers.
- "Your call" is "A tu criterio" in Spanish (wording for the owner's review).
- Out of scope: export as Markdown or PDF (S-024), finalizing a list with a closing date (S-025), editing list items (S-046), shopping list history in chat (S-031), MCP tools (S-032), unit conversion of any kind (PRD §4).
