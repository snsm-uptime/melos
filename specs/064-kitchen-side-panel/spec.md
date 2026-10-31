# Feature Specification: Kitchen Side Panel

**Feature Branch**: `064-kitchen-side-panel`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "I want to use the current kitchens page and merge it with the @ui/components/soft-ledger/TabBar.tsx as a left panel that uses icons only on the closed version, and icons and labels when opened. The left panel will have the following order: [Avatar Icon](remove logout from settings) [Alias] (amount of recipes added) [home] (default kitchen) [other kitchens listed] [notebooks] at the very end [log out]"

## Clarifications

### Session 2026-10-30

- Q: On phones, should the drawer stay open after someone picks a page, or close? → A: It closes after choosing an entry; remembered state applies only to larger screens.
- Q: On phones, should the kitchen actions sit behind a "more" menu, or stay as separate buttons in the header row? → A: Cart and invite stay visible; the other actions go in a "more" menu on phones; larger screens show all buttons.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Move around the app from one left panel (Priority: P1)

A signed-in person uses a single left panel, instead of the bottom tab bar and the separate kitchens list, to reach their default kitchen, any other kitchen, and their notebooks.

**Why this priority**: This is the feature's core: all main destinations in one place, with kitchens one tap away from anywhere.

**Independent Test**: Sign in as a person with three kitchens, then reach each kitchen and the notebooks from the panel, starting from a recipe page.

**Acceptance Scenarios**:

1. **Given** a signed-in person on any authenticated page, **When** the page loads, **Then** the left panel is present and the bottom tab bar is not.
2. **Given** the panel, **When** the person reads it from top to bottom, **Then** the entries appear in this order: avatar, alias with recipe count, home, other kitchens, notebooks, and, at the very end, log out.
3. **Given** a person with several kitchens, **When** they choose Home, **Then** their default kitchen opens.
4. **Given** the panel, **When** they choose another kitchen, **Then** that kitchen opens and is remembered as the last opened one.
5. **Given** the panel, **When** they choose Notebooks, **Then** their notebooks page opens.
6. **Given** a person is on a kitchen or a page that belongs to a panel entry, **When** the panel shows, **Then** that entry is marked as the current one, and a recipe page marks Notebooks, as the Notebook tab does today.

---

### User Story 2 - Open and close the panel (Priority: P1)

The person keeps the panel closed to save space, showing icons only, and opens it when they want to see labels.

**Why this priority**: The two states are the explicit shape of the request, and icons without labels must stay usable.

**Independent Test**: Toggle the panel with the mouse, by touch and by keyboard, and compare what each state shows.

**Acceptance Scenarios**:

1. **Given** a closed panel, **When** it is shown, **Then** each entry shows only its icon, and each entry still has an accessible name.
2. **Given** a closed panel, **When** the person opens it, **Then** each entry shows its icon and its label, and the alias and recipe count are visible.
3. **Given** an open panel, **When** the person closes it, **Then** it returns to icons only.
4. **Given** a person on a larger screen left the panel open or closed, **When** they move to another page, **Then** it stays in that state. On phones, the panel closes after the person chooses an entry.
5. **Given** kitchens with the same icon in a closed panel, **When** the person looks at them, **Then** each one can be told apart without opening the panel.

---

### User Story 3 - See who I am and what I have added (Priority: P2)

The person sees their avatar, alias and how many recipes they have added, and reaches their settings from the avatar.

**Why this priority**: It gives identity and a small sense of progress, but navigation works without it.

**Independent Test**: Sign in as a person who added five recipes and check the avatar, the alias and the count, then add one recipe and check the count again.

**Acceptance Scenarios**:

1. **Given** a signed-in person, **When** the panel is shown, **Then** the avatar is at the top, using their photo or the existing fallback.
2. **Given** the panel is open, **When** it is shown, **Then** the alias and the number of recipes the person added are shown directly below the avatar.
3. **Given** the avatar, **When** the person chooses it, **Then** the settings page opens.
4. **Given** a person who has just saved or deleted a recipe, **When** the panel is next shown, **Then** the count reflects the change.
5. **Given** a person who added no recipes, **When** the panel is open, **Then** the count reads zero rather than being hidden.

---

### User Story 4 - Log out from the panel (Priority: P2)

The person logs out from the last entry of the panel. The log out action no longer exists in settings.

**Why this priority**: The request moves this action; it must exist in exactly one place.

**Independent Test**: Log out from the panel and confirm the sign-in page opens and a protected page is no longer reachable; confirm settings has no log out control.

**Acceptance Scenarios**:

1. **Given** the panel in either state, **When** the person looks at its bottom, **Then** log out is the last entry, separated from the navigation entries.
2. **Given** a person chooses log out, **When** it completes, **Then** their session has ended, no cached personal data remains on the screen, and the sign-in page opens.
3. **Given** the settings page, **When** it is shown, **Then** it has no log out control, and the password reset action stays available.

---

### User Story 5 - Keep managing kitchens (Priority: P2)

The person can still create, rename, invite to, archive, restore and delete kitchens after the kitchens list moves into the panel.

**Why this priority**: The merge must not remove anything a person can do today.

**Independent Test**: Do each management action once, starting from the panel.

**Acceptance Scenarios**:

1. **Given** the merged navigation, **When** the person wants to manage a kitchen, **Then** every action available on today's kitchens page is still reachable, with the same owner-only limits. Rename, invite, delete and archive or restore are icon buttons at the end of the kitchen's header row; creating is a "+" in the panel.
2. **Given** a person creates a kitchen from the panel's "+", **When** it is saved, **Then** it appears in the panel without a page reload.
3. **Given** a person archives or deletes a kitchen, or is removed from one, **When** that completes, **Then** it no longer appears in the panel.
4. **Given** the open panel, **When** the person looks at the "Kitchens" subtitle row, **Then** the archive toggle sits at the end of that row, and using it switches the panel's kitchen list between active and archived kitchens.
5. **Given** a person who does not own a kitchen, **When** they open it, **Then** the owner-only icon buttons are not shown, as today.

---

### Edge Cases

- A person belongs to many kitchens: the kitchen entries scroll inside the panel, while the avatar block and log out stay reachable.
- A long alias or kitchen name is cut off in the open panel and remains fully available to assistive technology and as a tooltip.
- The default kitchen is archived, deleted or left: Home falls back to the first remaining active kitchen; with no kitchens left, Home opens the place to create one.
- In the closed state the "Kitchens" subtitle and archive toggle are not shown; opening the panel reveals them.
- People invited at sign-up who have a sign-up kitchen start with that kitchen as default.
- The person's only kitchen is the default one: the "other kitchens" group is simply absent.
- The kitchen list fails to load: Home, Notebooks, the avatar and log out still work, and the panel shows a short error.
- The recipe count fails to load: the panel shows no number rather than a wrong one, and nothing else is blocked.
- Log out fails because of the network: the person is still sent to the sign-in page and local data is cleared, as today.
- A person without an alias is sent to alias setup, as today, and sees no panel until it is set.
- Signed-out pages do not show the panel.
- Screens that hide the tab bar today, such as a full-screen flow, keep hiding navigation.
- Open sheets, toasts and the cart still sit correctly above or beside the panel.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST replace the bottom tab bar with one left panel on all authenticated pages that show the tab bar today.
- **FR-002**: The panel MUST have a closed state showing icons only and an open state showing icons and labels.
- **FR-003**: The panel MUST show its entries in this order: avatar; alias with recipe count; home; other kitchens; notebooks; log out as the very last entry.
- **FR-004**: The avatar MUST open the settings page, and the alias and recipe count MUST show only in the open state.
- **FR-005**: The recipe count MUST be the number of existing recipes whose author is the signed-in person, across all kitchens and notebooks they can currently reach.
- **FR-006**: Home MUST open the person's default kitchen. Each person has exactly one default kitchen: the kitchen created at sign-up until they pick another. Existing people MUST start with their sign-up kitchen.
- **FR-006a**: A person MUST be able to set any active kitchen they belong to as their default.
- **FR-007**: Other kitchens MUST list the person's non-archived kitchens, excluding the default one, in a stable order: alphabetical by name.
- **FR-008**: Opening a kitchen from the panel MUST record it as last opened, as the kitchens page does today.
- **FR-009**: The Notebooks entry MUST open the notebooks page.
- **FR-010**: The panel MUST mark the entry matching the current page, including for pages nested under a kitchen or notebook.
- **FR-011**: On larger screens, the panel's open or closed state MUST persist across pages and reloads on the same device. On phones, the panel MUST start closed and MUST close after the person chooses an entry.
- **FR-012**: Each closed-state entry MUST have an accessible name, and kitchens MUST be distinguishable from each other, for example by an initial.
- **FR-013**: Every panel entry and the open/close control MUST work with keyboard and touch, and meet the app's existing touch-target size.
- **FR-014**: The log out control MUST be removed from settings and added to the panel, ending the session and clearing cached personal data exactly as today. Password reset MUST stay in settings.
- **FR-015**: All panel text MUST be available in English and Spanish, with the recipe count correctly pluralized.
- **FR-016**: All kitchen management actions available today MUST remain available, with unchanged permissions. The standalone kitchens list page is removed. Rename, invite, delete and archive or restore MUST be icon buttons at the end of the kitchen's header row. Creating MUST be a "+" entry in the panel. On phones, invite MUST stay in the header row, and rename, delete, archive or restore, and set as default MUST be in a "more" menu at the end of that row.
- **FR-016a**: The archive toggle MUST move to the end of the "Kitchens" subtitle row in the panel and switch the panel's kitchen list between active and archived kitchens.
- **FR-017**: The panel's kitchen list MUST update without a reload after a kitchen is created, renamed, archived, restored or deleted.
- **FR-018**: On phones, the panel MUST be fully hidden when closed, MUST open from a header button, and MUST open over the content, so recipe and cart content keeps the full screen width. Icons-only applies to larger screens.

### Key Entities

- **Default kitchen**: The kitchen that the Home entry opens for a person; one per person, recorded and changeable by them.
- **Recipe count**: The number of recipes a person has added, read for display only.
- **Panel state**: Whether a person's panel is open or closed on the current device.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any authenticated page, a person reaches any of their kitchens or notebooks in at most two taps.
- **SC-002**: 100% of actions available today on the kitchens page and bottom tab bar remain reachable after the change.
- **SC-003**: In the closed state, 100% of entries are announced by name by a screen reader.
- **SC-004**: Log out exists in exactly one place, and after using it no protected page can be opened without signing in again.
- **SC-005**: On larger screens, the panel state survives 100% of page changes and reloads on the same device.
- **SC-006**: A newly saved recipe is included in the count the next time the panel is shown.
- **SC-007**: With 20 kitchens, the avatar and log out remain reachable without scrolling the page.

## Assumptions

- "Settings" means the current account page, which keeps theme, language, photo and password reset.
- "Amount of recipes added" means recipes authored by the person, not all recipes they can see; a deleted recipe stops counting.
- The avatar has one fixed position in both states, and its photo and fallback are the ones used today.
- Panel state is stored per device and is not a synced account preference.
- The existing avatar in page headers is removed where the panel now provides it.
- Archived kitchens appear in the panel only while the archive toggle is on.
- An archived kitchen cannot be the default; archiving it triggers the existing Home fallback, and the fallback kitchen becomes the new default.
- The authentication layer is not changed; the existing sign-out behaviour is only called from a new place.
- The shopping cart and kitchen pages keep their own content and only gain the panel as navigation.
