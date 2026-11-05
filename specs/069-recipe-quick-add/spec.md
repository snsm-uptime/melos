# Feature Specification: Recipe quick add, and a recipe from another notebook

**Feature Branch**: `069-recipe-quick-add`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Story S-069 (dev/docs/backlog.yaml). "A recipe quick add button on the navigation that
allows to select any of the existing add recipe options but also allows the user to add a recipe
from a personal notebook into a kitchen. This option should also be added inside the kitchen add as
'Recipe from another notebook' and assign that recipe to the currently open kitchen."

## Summary

Today a recipe is added from the add-recipe call to action on a notebook or recipe list (specs 016,
026): it opens the options dialog (URL, Picture, Text). This feature adds:

1. A **quick add** button in the app navigation, reachable from every signed-in page, that opens
   the same options plus a new one, **Recipe from another notebook**.
2. **Recipe from another notebook**: the person picks one recipe from a personal notebook they can
   read and it is added to a kitchen. A recipe is in exactly one notebook (AGENTS.md domain rules),
   so "adding" makes an independent copy in a kitchen notebook; the original stays where it is.
3. The same option inside a kitchen's add-recipe dialog, where the target kitchen is the open one.

## Clarifications

### Session 2026-11-04

- Q: Copy or move a personal recipe added to a kitchen? → A: Independent copy; it always goes to the kitchen notebook the current member is the author of (their own, created if missing). The original stays and the two never sync.
- Q: Does the copy keep an origin label? → A: No; the copy is a plain kitchen recipe with no visible link to its source.
- Q: Same personal recipe added to the same kitchen twice? → A: Warn "already added"; the member chooses Add another copy, Overwrite the existing copy, or Cancel. The copy keeps a hidden record of its source recipe for this check only (never shown, cleared if the source is deleted).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a recipe to the open kitchen from a personal notebook (Priority: P1)

A member is in a kitchen and wants a recipe they keep in their personal notebook to be available
to the kitchen. In the kitchen's add-recipe dialog they choose "Recipe from another notebook", pick
the recipe, confirm, and it appears in the kitchen.

**Why this priority**: It is the new capability; without it the quick add button is only a shortcut.

**Independent Test**: With a personal recipe and an active kitchen, add it from the kitchen's dialog
and see the copy in the member's kitchen notebook, with the original unchanged.

**Acceptance Scenarios**:

1. **Given** a member of an active kitchen with recipes in a personal notebook, **When** they open
   the kitchen's add dialog, **Then** "Recipe from another notebook" is listed after the existing
   options.
2. **Given** they choose it, **When** the picker opens, **Then** it lists the personal notebooks they
   own or are a member of, and the recipes of the chosen notebook, searchable by name.
3. **Given** they pick a recipe and confirm, **Then** a copy is saved in their own kitchen notebook of
   the open kitchen (created if they have none, as on first capture), they see a confirmation, and
   the original recipe is unchanged.
4. **Given** the copy exists, **When** either the original or the copy is edited or deleted, **Then**
   the other is not affected.

---

### User Story 2 - Quick add from the navigation (Priority: P1)

From any signed-in page, the person taps the quick add button in the navigation and sees URL,
Picture, Text and Recipe from another notebook. The capture options behave as they do today.

**Why this priority**: The entry point the owner asked for.

**Independent Test**: From a page with no add-recipe call to action (for example the shopping list),
open quick add, choose Text, and finish a capture into the default notebook.

**Acceptance Scenarios**:

1. **Given** a signed-in person on any page, **When** they tap quick add, **Then** the options dialog
   opens with URL, Picture, Text and Recipe from another notebook.
2. **Given** they choose URL or Text, **Then** the sheet opens with the same notebook picker and
   default as the capture rules: inside a kitchen page, the member's own kitchen notebook; elsewhere,
   their default personal notebook.
3. **Given** they choose Recipe from another notebook while inside a kitchen page, **Then** it
   targets that kitchen (Story 1).
4. **Given** they choose it outside a kitchen page, **Then** they also pick the target kitchen among
   their active kitchens; with exactly one, it is preselected.
5. **Given** a Back or Discard from a capture opened by quick add, **Then** they return to the page
   they were on.

---

### Edge Cases

- The person has no personal recipes: the picker says so and offers no confirm.
- The person belongs to no active kitchen: the option is shown disabled with a short reason
  (outside a kitchen) and never shown inside an archived kitchen; no capture or copy happens in an
  archived kitchen.
- The same recipe is added to the same kitchen twice (any member's earlier copy still in that
  kitchen): the member is warned it was already added and chooses Add another copy, Overwrite, or
  Cancel. Overwrite replaces the earlier copy's content with the source's current content, keeps it
  in its notebook, and makes the member its author; if several copies exist, the most recent one is
  overwritten.
- The earlier copy was deleted: no warning; a new copy is added.
- The original is deleted while the picker is open: the confirm fails with a clear message.
- The member leaves the kitchen: the copy stays with the kitchen (kitchen notebooks belong to the
  kitchen).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app navigation MUST show a quick add button on every signed-in page, on mobile and
  desktop, labelled in the person's language.
- **FR-002**: Quick add MUST open the existing add-recipe options in the existing order, followed by
  "Recipe from another notebook" ("Receta de otro cuaderno" in Spanish).
- **FR-003**: The kitchen's add-recipe dialog MUST list "Recipe from another notebook" in the same
  place. Personal-notebook add dialogs do not show it.
- **FR-004**: The picker MUST list only personal notebooks the person owns or is a member of, and
  their recipes, with search by recipe name.
- **FR-005**: Confirming MUST create an independent copy in the person's own kitchen notebook of the
  target kitchen, creating that notebook first if needed with the existing naming rule (spec 056,
  063). The person is the copy's author. The copy and the original never sync.
- **FR-006**: The target notebook is always the current member's own kitchen notebook of the target
  kitchen; the member does not pick another notebook for this option.
- **FR-007**: The copy MUST keep the recipe's full content (name, ingredients with amounts and units,
  steps, servings, image and source if present) and be searchable and usable in the shopping list
  and chat like any other recipe.
- **FR-008**: Copying MUST be refused for kitchens the person is not an active member of, and for
  source recipes they cannot read, even if requested directly.
- **FR-009**: Outside a kitchen page, the person MUST choose the target kitchen; inside one, the open
  kitchen is used without asking.
- **FR-011**: Each copy MUST keep a hidden record of its source recipe, used only to detect a repeat
  add to the same kitchen (edge cases); it is never shown and is cleared when the source is deleted.
  Overwrite MUST NOT change the source recipe.
- **FR-010**: Ingredient names are copied as they are. Name normalization against the target's
  catalog is S-048's and is not part of this story.

### Key Entities

- **Recipe copy**: a new recipe in a kitchen notebook, built from a personal recipe; no live link to
  the original. It keeps no visible origin label; a hidden
  source reference is kept only for repeat detection (FR-011).
- **Quick add**: a navigation entry point; no stored data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any signed-in page, a person reaches the add-recipe options in one tap.
- **SC-002**: A member adds a personal recipe to the open kitchen in four taps or fewer (open add,
  choose option, pick recipe, confirm) when the recipe is in their default notebook.
- **SC-003**: In every test, editing or deleting the copy or the original leaves the other unchanged.
- **SC-004**: No copy is ever made into a kitchen the person does not belong to, or from a notebook
  they cannot read.

## Assumptions

- "Personal notebook" means any personal notebook the person owns or is a member of, not only
  their default one.
- The source is limited to personal notebooks, as asked; copying between kitchens is S-048.
- The Picture option keeps its current state (shown as in the existing dialog).
