# Feature Specification: Scale a Recipe's Servings on the Detail Page

**Feature Branch**: not created by this command

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "I want to modify the servings number to view the proportional changes to the ingredient amounts. The serving change does not persist, it is just to see how the recipe would adapt to the expectation." (story S-062, added to the backlog by this command)

**Related**: Builds on spec 027 (the recipe detail page, read-only, in the draft page layout). Not in `dev/docs/prd.md`: the PRD scales only in the cart (`people × meals / base_servings`, J4). Out of this feature: the cart's scale factor and shopping list (S-022, S-023), saving a scaled recipe or changing its stored servings (that is Edit, spec 027), converting between units (PRD §4), and rewriting numbers written inside the step text.

## Clarifications

### Session 2026-10-28

- Q: Does changing the servings on the detail page change the saved recipe or stay for the next visit? → A: Neither. The change is only a view: it is not saved, not remembered, and not shared; it exists only while the page is open (given with the request).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the amounts for a different number of servings (Priority: P1)

A member opens a recipe that makes 4 servings and wants to cook for 6. On the detail page they set the servings to 6 and every measured ingredient amount changes in proportion (1 cup becomes 1.5 cups, 2 large onions become 3). They read the new amounts and cook from them. They have not changed the recipe.

**Why this priority**: This is the whole feature. A recipe is written for one number of servings and people rarely cook for exactly that number.

**Independent Test**: Open a recipe with base servings 4 and the lines "1 cup rice" and "2 large onion". Set the servings to 6. Check that the lines read "1.5 cup" and "3 large", and that the saved recipe still says 4 servings.

**Acceptance Scenarios**:

1. **Given** a recipe for 4 servings with "1 cup rice", **When** the member sets the servings to 8, **Then** the rice reads "2 cup" and the other measured lines are doubled.
2. **Given** the same recipe, **When** the member sets the servings to 2, **Then** the rice reads "0.5 cup".
3. **Given** a counted line "2 large onion", **When** the servings go from 4 to 6, **Then** it reads "3 large"; with servings 5 it reads "2.5 large".
4. **Given** a line with a vague amount ("salt, to taste"), **When** the servings change, **Then** its note stays exactly as saved.
5. **Given** a recipe whose servings were estimated, **When** the member scales it, **Then** the amounts scale from that same number and the "estimated" badge stays on the original servings.
6. **Given** any chosen servings, **When** the member looks at the preparation text, the unit names and the order of the lines, **Then** none of them changed; only quantities did.

---

### User Story 2 - The change is only a view and never persists (Priority: P1)

The member changes the servings to try a number, and then leaves, reloads or comes back later. The recipe is as it was saved. Nothing is stored, no one else sees the change, and the recipe's saved servings are untouched.

**Why this priority**: The member asked for this explicitly. A viewing tool that quietly edits recipes would destroy data.

**Independent Test**: Set the servings to 6, reload the page, and check it shows 4 and the original amounts; open the recipe as another member and check it shows 4.

**Acceptance Scenarios**:

1. **Given** the servings set to 6 on the detail page, **When** the member reloads the page, **Then** the servings show the saved number and the amounts are the saved ones.
2. **Given** the servings set to 6, **When** the member goes back to the list and opens the same recipe again, **Then** it shows the saved servings.
3. **Given** the servings set to 6, **When** another member opens the same recipe, **Then** they see the saved servings.
4. **Given** the servings set to 6, **When** the member opens Edit, **Then** the edit form shows the saved servings and the saved amounts, not the scaled ones.
5. **Given** the servings set to 6, **When** the recipe is looked at in a list, a cart or an export, **Then** it still says the saved servings.
6. **Given** a member who can only read the recipe (for example in an archived kitchen), **When** they set the servings, **Then** it works the same way, because it changes nothing stored.

---

### User Story 3 - Go back to the recipe's own servings (Priority: P2)

After trying numbers the member wants the original amounts back in one action, and always knows what the recipe's own servings are.

**Why this priority**: Useful and cheap, but the page is usable without it, since the member can type the original number or reload.

**Independent Test**: Scale to 7, use the reset action, and check the servings and every amount are the saved ones again.

**Acceptance Scenarios**:

1. **Given** servings changed to 6, **When** the member uses the reset action, **Then** the servings and all amounts return to the saved ones.
2. **Given** servings equal to the saved number, **When** the page is shown, **Then** no reset action is offered.
3. **Given** servings changed to 6, **When** the page is shown, **Then** it also states the recipe's own servings (for example "Makes 4") so the member knows what the amounts were written for.

---

### Edge Cases

- Servings are whole numbers from 1 to 100. A value outside that range, a blank value, a decimal or text is not applied: the page keeps the last valid servings and the control shows what is accepted.
- Amounts show at most 2 decimals with no trailing zeros ("1.5", "0.33", "2"). A result that rounds to zero at 2 decimals (for example 1 tsp scaled to 1 of 100 servings) still shows a positive value, never "0".
- Lines are never converted to another unit and never merged: "1 cup + 3 tbsp" style combining belongs to the shopping list.
- Counted items may become fractional ("2.5 large onion"); they are shown exactly, not rounded up as in the shopping list.
- Numbers written inside the step text ("add 2 cups of water") do not change; the member is told once, near the steps, that steps show the saved text when the servings were changed.
- A recipe of 100 lines still updates the instant the servings change.
- The member leaves the page with changed servings: nothing is asked and nothing is kept (there is nothing to lose).
- A recipe that is edited by another member while open: the scaled view keeps its own servings, and a reload shows the new content at the saved servings.
- Titles, names and notes with accents, ñ, ¿ or fractions are unchanged by scaling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The recipe detail page MUST offer a control to set the number of servings, starting at the recipe's saved servings.
- **FR-002**: When the servings are changed, every ingredient line with a quantity MUST show its saved quantity multiplied by (chosen servings ÷ saved servings), immediately, without leaving the page.
- **FR-003**: Lines with a vague amount MUST keep their note unchanged, and units, sizes, names and preparation notes MUST NOT change.
- **FR-004**: Quantities MUST be shown with at most 2 decimals and no trailing zeros, and a nonzero result MUST NOT be shown as zero.
- **FR-005**: The accepted servings MUST be whole numbers from 1 to 100. Any other entry MUST NOT be applied, and the member MUST see what is accepted.
- **FR-006**: The changed servings MUST NOT be saved, remembered between visits, or visible to anyone else; the recipe's stored data (servings, amounts, steps, times) MUST NOT change.
- **FR-007**: A reload, a new visit, or opening the recipe from another page MUST show the saved servings.
- **FR-008**: The edit form MUST show the saved servings and saved amounts, whatever servings were chosen on the detail page.
- **FR-009**: The page MUST state the recipe's saved servings while they differ from the chosen ones, and MUST offer one action that returns to them; the action MUST NOT be offered when they are the same.
- **FR-010**: The step text MUST NOT be changed by scaling; when the servings differ from the saved ones, the page MUST say that the steps show the saved text.
- **FR-011**: Any member who can read the recipe MUST be able to use the control, including members who cannot edit it.
- **FR-012**: The control MUST be operable with the keyboard, and the changed amounts MUST be announced to assistive technology.
- **FR-013**: All text added by this feature MUST be plain, in English and Spanish like the rest of the detail page, with no codes or technical terms.

### Key Entities *(include if feature involves data)*

- **Saved servings**: The number of servings the recipe is written for; stored with the recipe and never changed by this feature.
- **Chosen servings**: The number the member is looking at right now; held only while the page is open, not stored.
- **Scale factor**: Chosen servings divided by saved servings; applied to quantities for display only.
- **Ingredient line**: Unchanged; only the shown quantity of a measured or counted line is derived from it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member sees every amount of a recipe (up to 100 lines) update within 0.1 seconds of changing the servings, with no page reload.
- **SC-002**: In 100% of checks, each shown quantity equals the saved quantity × chosen ÷ saved servings, within the 2-decimal display.
- **SC-003**: In 100% of checks, the stored recipe is identical before and after any number of servings changes.
- **SC-004**: In 100% of checks, reloading, reopening, another member's view and the edit form all show the saved servings and amounts.
- **SC-005**: A member goes from the saved servings to a different number and back to the saved one in at most 2 actions.
- **SC-006**: 100% of entries outside 1 to 100 or not whole numbers leave the shown amounts unchanged.

## Assumptions

- The control lives on the recipe detail page of spec 027, whose layout is display only; this control is the one interactive element it adds, besides Edit and Delete.
- Scaling is a multiplication on the page; no new stored data, no new route and no change to who may read or write a recipe.
- The upper limit of 100 servings matches the limit on lines and steps and is a reasonable cap for home cooking; it can be changed later.
- Fractions are shown as decimals ("1.5") rather than glyphs ("1½"), consistent with the rest of the app's amounts.
- Scaling steps' text would need reading numbers out of free text, which the app does not do; this is why steps are left alone and the member is told.
- The cart's own scale factor (people × meals ÷ base servings) is a separate story and does not read this view-only value.
- Recipe lists, cards, exports and the PDF always use the saved servings.
