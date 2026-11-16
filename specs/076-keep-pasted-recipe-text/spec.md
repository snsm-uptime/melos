# Feature Specification: Keep Pasted Recipe Text and Offer Personal Notebooks

**Feature Branch**: `076-keep-pasted-recipe-text`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "I want to keep the text from the add recipe by text pop up in case they misclick or go out of the app. this should persist only during the current session, i also noticed that when adding a recipe personal notebooks didn't show up"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pasted text survives a misclick or leaving the app (Priority: P1)

A member opens "Add recipe" → Text and pastes or types a long recipe. Before submitting, they tap outside the sheet by mistake, press close, switch to another app, or the page reloads. When they open the text sheet again in the same session, the text they had is still there, and they can submit it without pasting again.

**Why this priority**: Losing a long pasted recipe is the main pain the user named. Retyping or finding the source again makes people give up on adding the recipe.

**Independent Test**: Paste text into the text sheet, close the sheet, reload the page, open the text sheet again: the same text is shown.

**Acceptance Scenarios**:

1. **Given** a member has typed text into the text sheet, **When** they close the sheet by tapping outside it or pressing close and open it again, **Then** the text sheet shows the same text.
2. **Given** a member has typed text into the text sheet, **When** they leave the app (switch app, lock the phone, go to another site) and come back in the same session, **Then** opening the text sheet shows the same text.
3. **Given** a member has typed text into the text sheet, **When** the page reloads or they navigate to another page of the app and open the text sheet again, **Then** the text is still there.
4. **Given** a member submitted kept text and is on the draft, **When** they press Back, **Then** the text sheet shows the text, as today (spec 016 FR-031); **When** they save the recipe or discard the draft instead, **Then** the kept text is cleared, and the next time they open the text sheet it is empty.
5. **Given** a member has kept text, **When** the session ends (they close the browser tab or window, or sign out), **Then** the text is gone, and opening the text sheet in a new session shows an empty field.
6. **Given** a member has kept text, **When** they clear the field themselves, **Then** nothing is kept and the sheet opens empty next time.

---

### User Story 2 - The right notebooks are offered when adding a recipe (Priority: P2)

Where a member starts "Add recipe" decides which notebooks they can choose from:

- **Side panel (quick add)**: every notebook the member can add to is offered: their personal notebooks (owned or shared with them) and the notebooks of every active kitchen they belong to. Today it offers only personal notebooks outside a kitchen, and only the current kitchen's notebooks inside one.
- **Inside a notebook** (personal or kitchen): the recipe goes into that notebook, with no choice. This already works and is kept as is.
- **On a kitchen's page**: the member picks one of that kitchen's notebooks, as today.

**Why this priority**: Without it the member can't put a recipe where they want from the side panel, but there is a workaround (open the notebook first). Losing pasted text has no workaround.

**Independent Test**: As a member who owns two personal notebooks, belongs to one shared by someone else, and belongs to a kitchen with two notebooks, open Add recipe from the side panel: all five notebooks are offered, and the default is preselected.

**Acceptance Scenarios**:

1. **Given** a member owns several personal notebooks and belongs to a personal notebook someone else owns, **When** they open Add recipe from the side panel, **Then** each of those notebooks is offered by name.
2. **Given** a member belongs to one or more active kitchens, **When** they open Add recipe from the side panel, **Then** each of those kitchens' notebooks is offered too, named so the member can tell which kitchen it belongs to.
3. **Given** a member opens Add recipe from the side panel outside a kitchen, **When** the choice opens, **Then** their default personal notebook is preselected.
4. **Given** a member opens Add recipe from the side panel while on a kitchen's pages, **When** the choice opens, **Then** their own notebook in that kitchen is preselected (or the "new notebook" row if they have none yet), as today.
5. **Given** a member is inside a notebook, **When** they add a recipe from that notebook's page, **Then** it goes into that notebook with no notebook choice shown.
6. **Given** a member is on a kitchen's page, **When** they add a recipe there, **Then** they choose among that kitchen's notebooks only.
7. **Given** a member has only one notebook they can add to, **When** they add a recipe from the side panel, **Then** it is used without asking, as today.

---

### Edge Cases

- The member pastes text, then switches the target notebook in the picker: the text stays.
- The member pastes text in one place (for example quick add) and opens the text sheet from another place (a notebook page) in the same session: the same text is shown, since there is one text-in-progress per member per session.
- The submission fails (the service is unavailable, the text is too long): the text stays, as today, and is still kept after a reload.
- The member opens the app in a second tab: the second tab starts empty; each tab is its own session.
- Another person signs in on the same browser after a sign-out: they never see the previous member's text.
- The kept text is longer than the paste limit: it is shown as kept, with the usual too-long message, and is not cut.
- The member uses link or picture capture: those are not covered; only the text sheet's text is kept.
- A kitchen is archived, a notebook is archived, or the member's access was removed: it is not offered in the side panel.
- A member belongs to a kitchen where they have no notebook of their own yet: outside a kitchen, the side panel offers that kitchen's existing notebooks only (a kitchen always has one once its page has been opened, spec 056 FR-008a). On that kitchen's own pages, the side panel also offers the "new notebook" row, as today.
- Two notebooks share a name (for example "Dinners" in two kitchens): the side panel names them so they can be told apart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The text typed or pasted into the add-recipe text sheet MUST be kept until the recipe made from it is saved or discarded, the member clears it, or the session ends.
- **FR-002**: Kept text MUST survive closing the sheet (tap outside, close button, Back), navigating within the app, leaving the app and coming back, and reloading the page.
- **FR-003**: Kept text MUST be kept only for the current browser session: closing the tab or window ends it, and a new session starts with an empty text sheet.
- **FR-004**: Kept text MUST be cleared when the member signs out, and MUST never be shown to a different signed-in member.
- **FR-005**: Kept text MUST be stored only on the member's device and MUST NOT be sent anywhere until the member submits it.
- **FR-006**: Kept text MUST be cleared when the recipe made from it is saved or its draft is discarded. Creating the draft does not clear it, so Back from the draft still shows the text (spec 016 FR-031).
- **FR-007**: Reopening the text sheet with kept text MUST show it in full and allow submitting it right away, with the same length checks as a fresh paste.
- **FR-008**: Add recipe from the side panel MUST offer every notebook the member can add to: the personal notebooks they own or belong to, and the notebooks of every active kitchen they belong to. Outside a kitchen the member's default personal notebook MUST be preselected; on a kitchen's pages their own notebook in that kitchen (or the "new notebook" row) MUST be preselected.
- **FR-009**: Add recipe from a notebook's page MUST use that notebook without offering a choice (current behaviour, kept).
- **FR-010**: Add recipe from a kitchen's page MUST offer only that kitchen's notebooks (current behaviour, kept).
- **FR-011**: Notebooks the member cannot add to (archived notebooks or kitchens, removed access, notebooks they don't belong to) MUST NOT be offered anywhere.
- **FR-012**: When notebooks from more than one place are offered, each MUST show which kitchen it belongs to, or that it is personal.

### Key Entities

- **Text in progress**: The text a member has typed or pasted into the text sheet but not yet submitted. One per member per browser session. Lives only on the device.
- **Notebook choice**: The list of notebooks offered as the destination of a new recipe, with one preselected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of tested cases (close sheet, tap outside, navigate away, switch app, reload), reopening the text sheet in the same session shows exactly the text that was there before.
- **SC-002**: In 100% of tested cases, a new session (new tab or window, or after sign-out) opens the text sheet empty.
- **SC-003**: A member who closed the sheet by mistake can get back to their text and submit it in under 10 seconds, with no re-pasting.
- **SC-004**: A member with N personal notebooks and M notebooks across their active kitchens sees all N + M offered from the side panel.
- **SC-005**: Adding from a notebook's page never shows a notebook choice, and adding from a kitchen's page never offers a notebook from outside that kitchen.

## Assumptions

- "Session" means the browser tab's session: it ends when the tab or window is closed or the member signs out. A reload or leaving and returning to the tab does not end it.
- Only the text capture's text is kept. The chosen notebook is not kept beyond what the app already does, and link and picture captures are out of scope.
- There is one text-in-progress at a time, shared by every place the text sheet opens from, not one per notebook.
- Once submitted, the draft review screen keeps its own state as it does today; this feature does not change how drafts are kept.
- This feature changes spec 016 FR-001a for the side panel only: it now offers personal and kitchen notebooks together. The notebook-page and kitchen-page rules, and spec 035 and spec 056, stay as they are.
- The "Recipe from another notebook" option keeps its own rules (spec 069); this feature changes only the text, link and picture captures' notebook choice.
