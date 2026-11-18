# Feature Specification: Shopping List Export (Markdown copy and PDF)

**Feature Branch**: `024-shopping-list-export`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "Shopping list export as Markdown copy and PDF" (backlog S-024, epic Cart, journey J5, acceptance AC5.5)

## Clarifications

### Session 2026-11-17

- Q: Should the export cover only the cart the member is building, or also the saved shopping list the kitchen has started? → A: The saved shopping list, so manual items that do not come from recipes are included.
- Q: Should a shopping list that has already been closed with "Done" also be exportable, or only the active one? → A: Any shopping list, active or closed. The export is a reusable component that takes a shopping list ID. The only check is that the member can read the list's kitchen; an ID from a kitchen the member does not belong to is refused.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Copy the shopping list as Markdown (Priority: P1)

A kitchen member has added recipes to the cart and wants the consolidated shopping list in a chat or note app. They open the export, copy the list as Markdown, and paste it wherever they need it.

**Why this priority**: It is the quickest way to get the list out of the app and needs no file handling. It is also the fallback when PDF generation fails (AC5.5), so it must work on its own.

**Independent Test**: With a cart holding two recipes, open the export, copy the Markdown, paste it into a plain text field, and check that every consolidated line and its recipe titles appear.

**Acceptance Scenarios**:

1. **Given** a cart with recipes, **When** the member opens the export and chooses copy, **Then** the Markdown version of the consolidated list is copied and the member sees a confirmation.
2. **Given** a cart with a vague line ("Your call"), **When** the member copies the Markdown, **Then** the "Your call" section appears after the measured lines, with each note listed.
3. **Given** the copied text, **When** it is pasted into a chat, **Then** each line shows its quantity with units and its recipe titles, in the same wording as on screen.

---

### User Story 2 - Download the shopping list as PDF (Priority: P2)

A member wants a printable list for the shop. They choose PDF and get a file with the same consolidated lines, the recipe titles written after each line in parentheses, and the "Your call" section.

**Why this priority**: Useful for printing and carrying to the shop, but Markdown already covers sharing. PDF depends on the same consolidated list.

**Independent Test**: With a cart of three recipes, including a vague line and a line with a recipe scaled to a different servings count, download the PDF and compare every line against the on-screen list.

**Acceptance Scenarios**:

1. **Given** a cart with recipes, **When** the member chooses PDF, **Then** a PDF file of the consolidated list downloads.
2. **Given** a line such as "flour, 1 cup + 3 tbsp" from recipes A and B, **When** the PDF is read, **Then** the line shows the quantity and the text "(A, B)".
3. **Given** a downloaded PDF, **When** it is compared with the list on screen, **Then** the lines, quantities, units and recipe titles match.

---

### User Story 3 - Recover when PDF fails (Priority: P3)

The PDF cannot be made (for example, the service is unavailable). The member sees a clear error, and the Markdown copy still works.

**Why this priority**: It is a failure path. It must exist, but it is not a first-use flow.

**Independent Test**: Make PDF generation fail on purpose, then confirm the error message appears and the Markdown copy still succeeds.

**Acceptance Scenarios**:

1. **Given** PDF generation fails, **When** the member chooses PDF, **Then** an error message is shown and no partial file is downloaded.
2. **Given** PDF generation failed, **When** the member chooses copy as Markdown, **Then** the copy succeeds as usual.

---

### Edge Cases

- What happens when the cart is empty? The export actions are disabled and a hint tells the member to add recipes first.
- What happens when a manual item is added or removed while the export is open? The export shows the list as it is at the time of the action.
- What happens when the list has only vague lines? The export contains the "Your call" section and no measured lines.
- What happens when a recipe title contains accents or Spanish characters? The PDF and the Markdown show them correctly.
- What happens when the list is long (for example, 100 lines)? The PDF runs over several pages and keeps every line; the Markdown copy contains all lines.
- What happens when the list is closed? It exports the same way as an active list; the closing date is not changed.
- What happens when the list ID belongs to a kitchen the member is not part of? The export is refused with the same "not found" result as an unknown ID (FR-013).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The export MUST take a shopping list (spec 025) and MUST export every line on it, including manual items that do not come from a recipe. Recipe-derived lines carry the same scaling, merging and "Your call" rules as J5 Consolidation.
- **FR-002**: The export MUST offer two formats: a Markdown copy and a PDF download.
- **FR-003**: The Markdown copy MUST place the text in a copy box and MUST copy it to the clipboard in one action, with a confirmation shown to the member.
- **FR-004**: The Markdown MUST list each consolidated line with its quantity and units, followed by its recipe titles, and MUST list the "Your call" lines in their own section after the measured lines.
- **FR-005**: The PDF MUST contain the same lines as the Markdown, with each line's recipe titles written as text in parentheses after the line.
- **FR-006**: The PDF MUST keep every line and recipe title, including accented and Spanish characters, and MUST span as many pages as needed.
- **FR-007**: When the cart is empty, both export actions MUST be disabled and a hint MUST tell the member to add recipes.
- **FR-008**: If PDF generation fails, the member MUST see an error message, and the Markdown copy MUST still work. No partial PDF is downloaded.
- **FR-009**: Export MUST NOT change the cart, the saved shopping list, or its open or closed state. Export does not close a list (J5 Saved list).
- **FR-010**: The export labels, messages and the list's section headings MUST appear in the member's interface language (English or Spanish).
- **FR-011**: The export MUST use the same consolidation rules as the cart (J5 Consolidation): quantities are scaled by each recipe's servings, same-name lines in different dimensions stay separate, and numbers are shown with at most two decimals.
- **FR-012**: The export MUST be a reusable component that takes a shopping list ID and works the same whether the list is active or closed. Exporting a closed list does not change it.
- **FR-013**: The export MUST refuse a shopping list ID when the member cannot read the list's kitchen, and MUST show the same "not found" result as for an ID that does not exist, so no list details leak.

### Key Entities *(include if feature involves data)*

- **Shopping list**: any list of a kitchen (spec 025), active or closed. Each line has a quantity, units, the recipe titles it comes from (none for a manual item), and a flag for vague lines. The export reads it; it stores nothing new.
- **Export file or copy**: a Markdown text or a PDF file made from the consolidated list at the time of the action. It is not saved on the server.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member can copy the list as Markdown from the cart page in two actions or fewer.
- **SC-002**: In a check of sample carts (including vague lines, scaled servings and accented titles), 100% of lines and recipe titles on screen appear in the Markdown copy and the PDF.
- **SC-003**: When PDF generation fails, the member sees the error and can still copy the Markdown in 100% of failure checks.
- **SC-004**: A member can paste the copied Markdown into a chat and read the list without editing it.

## Assumptions

- The export covers any shopping list (spec 025), active or closed, and includes manual items. The cart's draft is not exported. Choosing which list to export is the caller's job; this story does not design the list picker.
- "Shopping list export" means the two formats in J5 Export only (PDF and Markdown copy). No other formats (for example, plain text files, CSV or printing from the browser) are in scope.
- The PDF is generated for the download only; the export is not stored, emailed or attached to the list.
- Prices, receipts and store grouping are out of scope. Store grouping is handled by spec 070 and is not a part of this export.
- The PDF uses the same wording and order as the on-screen list; no new layout beyond a simple, printable list is required.
- Export reads the saved list only. Unsaved cart changes made by an editor (spec 022) do not appear in the export until saved.
- Dependencies: the consolidated list from the cart (J5 Consolidation) and the Spanish and English interface strings already in use.
