# Feature Specification: Share a recipe with a person from the recipe page

**Feature Branch**: `071-share-recipe-to-user`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "when a user clicks the share icon on the recipe detail page chrome, a popup should appear with a SearchableSelect with list of user aliases, always show first the other users the current user shares a kitchen or notebook with. this way it's easy to find recent users. The action button should be the send icon used to invite by email, a success message should show instead of these items inside the popup."

**Backlog story**: S-071 (Must, owner request 2026-11-05). Placed next to implement.

## Summary

A member of a kitchen who is looking at a recipe wants to pass it on to someone they cook with. They press a share icon in the recipe page header. A popup opens with a searchable list of aliases. The people they already share a kitchen or notebook with come first, so recent cooking partners are easy to find. They choose a person and press the send icon. The recipe is copied into that person's default notebook, and the popup then shows a success message in place of the list.

## Clarifications

### Session 2026-11-05

- Q: Which people appear in the list? → A: Only people who share a kitchen or a notebook with the current user. No search of all accounts. (Assumed; see Assumptions.)
- Q: Where does the recipe land? → A: In the recipient's default notebook, as the owner asked. The recipient is the copy's author.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Share a recipe with a cooking partner (Priority: P1)

Ana is reading a recipe in her kitchen. She wants Ben to have it, and Ben shares a kitchen with her. She presses the share icon in the page header. The popup lists Ben first, with the other people she shares a kitchen or notebook with. She selects Ben and presses the send icon. The popup shows "Recipe sent to Ben", and Ben finds the recipe in his default notebook.

**Why this priority**: This is the whole feature. It lets someone pass a recipe to a person without copying notebooks or exporting text.

**Independent Test**: With two accounts that share a kitchen, open a recipe as the first, share it to the second, and check that the second account's default notebook holds a copy.

**Acceptance Scenarios**:

1. **Given** Ana is viewing a recipe, **When** she presses the share icon in the page header, **Then** a popup opens with a searchable list of aliases.
2. **Given** Ana shares a kitchen with Ben and a notebook with Carla, **When** the popup opens, **Then** Ben and Carla are listed before any other entry.
3. **Given** the list is open, **When** Ana types part of an alias, **Then** the list narrows to the matching people and the same ordering holds.
4. **Given** Ana has chosen Ben, **When** she presses the send icon, **Then** the recipe is copied into Ben's default notebook and the list is replaced by a success message.
5. **Given** Ana has chosen nobody, **When** she looks at the send icon, **Then** it is disabled.
6. **Given** the popup shows the success message, **When** Ana closes it, **Then** she is back on the recipe page and nothing else changed.

---

### User Story 2 - Recipient sees a usable copy (Priority: P2)

Ben receives a shared recipe. It lands in his default notebook as his own copy, and it can be edited or deleted by him without touching Ana's version.

**Why this priority**: The copy is only useful if the recipient can work with it on their own.

**Independent Test**: Share a recipe, then edit the copy as the recipient and confirm the original is unchanged.

**Acceptance Scenarios**:

1. **Given** Ana shared a recipe with Ben, **When** Ben opens his default notebook, **Then** the copy is listed there with Ben as its author.
2. **Given** Ben edits the copy, **When** Ana opens the original, **Then** it is unchanged.

---

### Edge Cases

- The current user shares no kitchen or notebook with anyone: the popup shows the empty-result message and the send icon stays disabled.
- The recipient has no default notebook: the share is refused with a message, and no copy is made.
- The recipe has ingredient names the recipient's catalog does not have: names are normalized as in S-048 and the copy still succeeds.
- The recipient's account is deleted between listing and sending: the send fails with a message, and the popup stays open with the list.
- The same person is in both a shared kitchen and a shared notebook: they appear once.
- The user presses send twice quickly: only one copy is made.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The recipe page header MUST show a share icon button for any recipe the user can read.
- **FR-002**: Pressing the share icon MUST open a popup containing a searchable select of user aliases.
- **FR-003**: The list MUST contain only people who share at least one kitchen or notebook with the current user, excluding the current user.
- **FR-004**: The list MUST show those people first, grouped ahead of any other entries, and order them by most recent shared activity, then alphabetically by alias.
- **FR-005**: Typing in the select MUST narrow the list by alias while keeping the same ordering.
- **FR-006**: The popup's action button MUST use the same send icon as the invite-by-email action.
- **FR-007**: The action MUST be disabled until a person is chosen.
- **FR-008**: Sending MUST copy the recipe into the chosen person's default notebook, with that person as the copy's author.
- **FR-009**: On success, the popup MUST replace the list with a success message naming the person. The list MUST NOT show again until the popup is reopened.
- **FR-010**: On failure, the popup MUST show an error message and keep the chosen person so the user can retry.
- **FR-011**: The original recipe MUST NOT change when a copy is sent.
- **FR-012**: The recipe page MUST show the share icon and popup in English and Spanish.

### Key Entities

- **Recipe**: the recipe being shared; read-only in this feature.
- **Shareable person**: a user who shares a kitchen or notebook with the current user; carries an alias.
- **Share copy**: a new recipe in the recipient's default notebook, authored by the recipient, with no link to the original.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can share a recipe with a cooking partner in under 30 seconds from the recipe page.
- **SC-002**: The people a user shares a kitchen or notebook with appear before all other entries in 100% of popups opened.
- **SC-003**: Every recipe shared in testing appears in the recipient's default notebook, and the original is unchanged in 100% of cases.
- **SC-004**: The popup shows the success message within 2 seconds of pressing send under normal conditions.

## Assumptions

- The list is limited to people already linked by a shared kitchen or notebook. There is no search of all accounts, which avoids exposing aliases of strangers.
- "Recently" in the ordering means most recent shared activity in those kitchens or notebooks; if that is not available, alphabetical order is the fallback.
- Sending copies the recipe the way S-048 copies a recipe into another notebook, including its name normalization against the recipient's catalog. This story depends on that copy behaviour; S-048 is still backlog, so its copy step is needed first or built here.
- Sharing does not notify the recipient by email in this version.
- The recipient gets a copy only; no access link to the original is created.
- The share icon and popup live in the existing recipe page header, not in the side panel.
