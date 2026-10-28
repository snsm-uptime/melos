# Feature Specification: Spanish by Default, with English and Spanish for Every Screen

**Feature Branch**: not created by this command

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Internationalization with Spanish as the default language (backlog story S-063). Spanish is the default interface language for everyone who has no saved language, new and existing accounts alike. Members can choose English or Spanish in their account, and the choice is saved to their account. All screens show text in the chosen language, including the recipe capture flow and the shared draft components that the recipe detail and edit pages reuse. Server pages, the client provider and the language cookie must agree on one language source. Recipe content language is a separate setting and is not changed."

**Related**: Replaces the "English for now, Spanish with the account language story" deferrals in specs 016 (FR-034), 017, 018 and 060. The PRD (§1.2) already says the UI is English and Spanish, chosen in the account; S-005 removed the language selector from the profile page and this story brings a language choice back. Out of this feature: the kitchen's recipe content language (`kitchen.content_language`, PRD §1.6), translating anything a member typed or a recipe contains, the language of emails, and a third language.

## Clarifications

### Session 2026-10-28

- Q: Which people get Spanish by default? → A: Everyone who has no saved language, whether their account is new or already exists (given with the request).
- Q: Can members choose English? → A: Yes. English or Spanish, chosen in the account and saved to the account (given with the request).
- Q: Should the signed-out screens have their own English/Spanish switch? → A: Yes. A small switch on the signed-out screens; the default stays Spanish. A new account keeps the language picked at sign-up; an account with a saved language shows that language after sign-in, whatever was picked while signed out; the signed-out pick is not remembered for later visits.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Spanish unless the member chose otherwise (Priority: P1)

A person who has never chosen a language opens the app, or signs up, or signs in to an account that has no saved language. Every screen they see is in Spanish. A member who chose English in the past keeps English.

**Why this priority**: This is the point of the request: Spanish must be what people get without doing anything. It must also not take English away from anyone who already chose it.

**Independent Test**: Sign up a new account and check the sign-up, sign-in, home, notebook and account screens are Spanish. Sign in as an existing account with no saved language and check the same. Sign in as an account with English saved and check it stays English.

**Acceptance Scenarios**:

1. **Given** a visitor who is not signed in and has not used the language switch, **When** they open the sign-in, sign-up, forgot-password or invite screens, **Then** all text is Spanish, whatever language their browser reports.
2. **Given** a new account created through sign-up, **When** the member lands in the app, **Then** every screen is Spanish and the account has no language chosen yet.
3. **Given** an existing account with no saved language, **When** the member signs in, **Then** every screen is Spanish.
4. **Given** an account with English saved, **When** the member signs in on any device, **Then** every screen is English.
5. **Given** an account with Spanish saved, **When** the member signs in on any device, **Then** every screen is Spanish.

---

### User Story 2 - Choose English or Spanish, in the account or before signing in (Priority: P1)

In the account screen a member sees their current language and switches between English and Spanish. Before signing in, a visitor can do the same with a small switch on the sign-in, sign-up and other signed-out screens. The new language shows at once on the screen they are on and on every screen after, without reloading the page, and it is still the language the next time they sign in anywhere.

**Why this priority**: Spanish by default is only acceptable if people can get English back, and the choice must follow the member, not the device.

**Independent Test**: As a Spanish-default member, switch to English in the account, check the account screen turns English at once, open home and a recipe and check English, sign out and sign in on another browser and check English.

**Acceptance Scenarios**:

1. **Given** the account screen, **When** the member opens it, **Then** it shows a language choice with English and Spanish, with the current language marked.
2. **Given** a member viewing the account screen in Spanish, **When** they choose English, **Then** that screen and every other screen show English immediately, without a page reload.
3. **Given** the member chose English, **When** they sign out and sign in on another browser or device, **Then** the app is in English.
4. **Given** the member chose English on one device, **When** they have the app open on a second device, **Then** that device shows English the next time it loads a page, without the member choosing again.
5. **Given** the language cannot be saved (the member is offline or the save fails), **When** they choose a language, **Then** they are told it was not saved, and the app keeps showing the language that is saved.
6. **Given** a member who chose Spanish, **When** they look at the language choice later, **Then** Spanish is shown as chosen, not as the default.
7. **Given** a visitor on the sign-in, sign-up, forgot-password or invite screen, **When** they look at the page, **Then** a small English/Spanish switch marks the current language.
8. **Given** a visitor viewing a signed-out screen in Spanish, **When** they choose English with the switch, **Then** that screen and the other signed-out screens they open during the visit show English at once, without a reload, and still in English after a reload of the page, with no moment in Spanish.
9. **Given** a visitor who chose English on the sign-up screen, **When** they create the account, **Then** the account is saved with English and every screen after sign-up is English.
10. **Given** a visitor who chose English with the switch, **When** they sign in to an account whose saved language is Spanish, **Then** the app is in Spanish; and when they sign in to an account with no saved language, the app is in Spanish.
11. **Given** a visitor who chose English with the switch and then closed the browser, **When** they come back later, **Then** the signed-out screens are in Spanish again.
12. **Given** a member who signs out, **When** the sign-in screen appears, **Then** it is in Spanish, whatever language the member had just been using.

---

### User Story 3 - Every screen in the chosen language, including capture (Priority: P1)

A Spanish member never sees English interface text, and an English member never sees Spanish interface text. This includes the recipe capture flow (the add-recipe options, the text sheet, the draft editor with its ingredient and step cards, the name-change notice, and all the messages shown when something goes wrong), and the same cards reused on the recipe detail and edit pages.

**Why this priority**: A mix of languages on one screen looks broken. Today the capture flow and the cards it shares with the detail and edit pages are English only, so a Spanish default would show English next to Spanish on the pages members use most.

**Independent Test**: As a Spanish member, walk sign-up, home, a kitchen, a notebook, the recipe list, adding a recipe from text through the draft and the save, the recipe detail, edit and delete, and the account, and note any English interface text. Repeat in English and note any Spanish.

**Acceptance Scenarios**:

1. **Given** a Spanish member, **When** they open the add-recipe options, the text sheet and the draft editor, **Then** every label, button, hint and placeholder is Spanish.
2. **Given** a Spanish member with a draft on screen, **When** an ingredient name is matched to the notebook's catalog, **Then** the "matched" and "new ingredient" labels, the change notice with its undo, and the catalog control are Spanish.
3. **Given** a Spanish member, **When** something fails (the assistant is unavailable or at its limit, the text is not a recipe, a rule is broken, the save fails), **Then** the message is Spanish and says the same thing as the English one.
4. **Given** a Spanish member opening a saved recipe, **When** the detail and edit pages show ingredient cards and step cards, **Then** the labels on them ("Preparation", "Note", "Add ingredient", "Remove", "Move up", step numbers) are Spanish.
5. **Given** an English member, **When** they use the same screens, **Then** all interface text is English.
6. **Given** any member, **When** a screen shows a recipe title, an ingredient name, a note, a step, a notebook name, a kitchen name or an alias, **Then** it is shown exactly as stored, in whatever language it was written.

---

### User Story 4 - The first thing on screen is already in the right language (Priority: P2)

When a signed-in member opens or reloads any page, the text they first see is already in their language. The page does not show English and then flip to Spanish, or the other way, and the page, the browser tab and screen readers all agree on the language.

**Why this priority**: A flash of the wrong language on every load makes the choice feel unreliable, and today the server-built pages cannot know the member's saved language.

**Independent Test**: As a member with English saved, hard-reload home, a notebook, a recipe and the account screen and check no Spanish text appears at any moment; repeat for Spanish. Check the page declares its language.

**Acceptance Scenarios**:

1. **Given** a member with English saved, **When** they reload any page, **Then** the first content shown is English and never changes language by itself.
2. **Given** a member with Spanish saved or with no language saved, **When** they reload any page, **Then** the first content shown is Spanish.
3. **Given** a page in a language, **When** a screen reader or the browser reads the page, **Then** the page declares that same language, and it follows a language change without a reload.
4. **Given** a member who changed language on another device, **When** this device loads a page, **Then** it shows the account's language, not a stale one remembered from before.
5. **Given** a visitor who is not signed in, **When** a page loads, **Then** it is in Spanish with no flash of English.

---

### Edge Cases

- A message exists in only one language by mistake: the member sees the other language's text, never a blank or a message code, and a check fails the build so it is caught before release.
- A member signed in on two devices changes language on one: the other device keeps what it shows until its next page load or refresh, then shows the account's language.
- The member's account has a saved language that is not English or Spanish (a bad value): it is treated as no saved language, so the app is Spanish.
- A recipe written in English is viewed by a Spanish member (and the reverse): the recipe stays as written; only the interface around it changes.
- Notebook names created before this feature, such as "ana's Notebook", keep the name they were stored with; they are not translated.
- A screen that needs a plural or a count ("1 ingredient", "3 ingredients") reads correctly in both languages.
- Text that grows in Spanish (it is usually longer) still fits on a phone width without breaking the layout or hiding a button.
- A visitor who picked English on the invite screen and then signs up through the invite: the new account is saved with English, like any sign-up.
- A visitor's pick while signed out is kept only until the browser is closed or the visitor signs in or out; it is never saved as a lasting device setting and never shown to the next person who uses the device.
- Dates, if shown, and the "estimated" and "unknown" markers follow the interface language.
- The quantity format on recipes (for example "1.5 cup") is not changed by the language in this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interface language MUST default to Spanish for every person who has no saved language: visitors who are not signed in, new accounts, and existing accounts with no saved language. The browser's reported language MUST NOT change this default.
- **FR-002**: An account with English or Spanish saved MUST show that language on every screen and every device it signs in on.
- **FR-003**: The account screen MUST offer a language choice with exactly English and Spanish, marking the current language, and MUST save the member's choice to their account.
- **FR-004**: A language change MUST take effect immediately on the current screen and on every later screen without reloading the page.
- **FR-005**: If the choice cannot be saved, the member MUST be told in plain words, and the app MUST keep showing the language that is saved.
- **FR-006**: Every piece of interface text MUST exist in both English and Spanish and MUST be shown in the interface language: sign-up, sign-in, password reset, email verification, invites, home, kitchens, notebooks, recipe lists, the add-recipe options and text sheet, the draft editor and its ingredient and step cards, the name-change notice and catalog control, the recipe detail, edit, servings and delete screens, the account screen, confirmation dialogs, empty states, loading states and every error message.
- **FR-007**: Cards and controls shared between screens (the ingredient and step cards used by the draft editor, the edit form and the detail) MUST take their text from the interface language, so one component never shows a language different from the screen around it.
- **FR-008**: Text a member or a recipe supplies (recipe titles, ingredient names, preparation and notes, steps, notebook and kitchen names, aliases, source links) MUST be shown exactly as stored and MUST NOT be translated or changed.
- **FR-009**: A message missing in the chosen language MUST fall back to the other language rather than show blank text or a code, and the project's checks MUST fail when any message exists in one language but not the other.
- **FR-010**: There MUST be one source of truth for the interface language: the account's saved language for a signed-in member, Spanish otherwise. Pages built on the server, pages built in the browser and anything remembered between visits MUST all give the same language, and a remembered value MUST NOT outrank the account's saved language.
- **FR-011**: A signed-in member's pages MUST first appear in their language, without showing the other language first, on both first load and reload.
- **FR-012**: The page MUST declare its language to the browser and assistive technology, matching the interface language, and keep doing so after a language change.
- **FR-013**: The language shown on a signed-out screen MUST NOT depend on a previous member's choice on the same device: a pick made on a signed-out screen lasts only until the browser is closed (a reload and other tabs keep it) and is cleared on sign-in and on sign-out.
- **FR-017**: The signed-out screens (sign-in, sign-up, forgot-password, reset-password, verify, invite) MUST offer an English/Spanish switch that marks the current language and takes effect immediately across the signed-out screens of the visit, without a reload.
- **FR-018**: Creating an account MUST save the language the visitor had picked, if any; with no pick the new account has no saved language. Signing in MUST show the account's saved language, or Spanish when it has none, and MUST NOT let a signed-out pick override it.
- **FR-014**: The kitchen's recipe content language MUST remain a separate setting and MUST NOT change, be derived from, or change the interface language.
- **FR-015**: Spanish wording MUST be consistent across screens (the same word for the same thing: recipe, notebook, kitchen, ingredient, servings, step), and plurals and counts MUST read correctly in both languages.
- **FR-016**: A language that is saved but is not English or Spanish MUST be treated as no saved language.

### Key Entities *(include if feature involves data)*

- **Account language**: The member's saved choice, English or Spanish, or none. Stored with the account. None means Spanish.
- **Signed-out pick**: The visitor's choice on a signed-out screen. Held until the browser is closed, saved to the account only when it is created, and never above an account's saved language.
- **Interface language**: The language the screens use right now: the account language, or Spanish when there is none or the person is signed out.
- **Message**: One piece of interface text, with an English and a Spanish version, identified once and used wherever it appears.
- **Recipe content language**: A kitchen's separate setting that fixes the language of ingredient names for merging; unrelated to the interface language.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a walk of every screen listed in FR-006 in Spanish, a reviewer finds no English interface text, and in English finds no Spanish interface text (0 findings).
- **SC-002**: 100% of messages exist in both languages, checked automatically on every build.
- **SC-003**: A language change shows on the current screen within 1 second and without a page reload.
- **SC-004**: In 100% of sign-ins, the language shown is the account's saved language, or Spanish when none is saved, on any device.
- **SC-005**: In 100% of page loads for a signed-in member, the first content shown is already in their language, with no visible switch.
- **SC-006**: A person who does nothing gets Spanish on every screen, and a member who wants English can get it in at most 3 actions from any screen (open the account, choose English, see it applied).
- **SC-008**: A visitor on any signed-out screen can switch language in one action, and it shows within 1 second without a reload.
- **SC-009**: In 100% of sign-ups, the new account's saved language equals the visitor's pick, or is empty when they made none.
- **SC-007**: In 100% of checks, recipe titles, ingredient names, notes, steps, notebook and kitchen names are identical before and after a language change.

## Assumptions

- "Everyone with no saved language" includes signed-out visitors, so the signed-out screens are Spanish for all, even for a browser set to English, until the visitor uses the switch on those screens; members change it in the account after signing in.
- The signed-out pick is held for the browser session (so moving from sign-in to sign-up, reloading, and opening a second tab all keep it) and no longer; it is not a lasting device setting. Holding it so that the server can build the first page in the right language is a planning decision.
- The set of languages is English and Spanish only; a third language is a separate story.
- Today, the language cannot be seen by pages built on the server, so they always show English, and the saved language is only read in the browser after the page loads. This story fixes that by giving all of them the same source; how is a planning decision.
- The language cookie or any remembered copy exists only to avoid delays and never decides the language over the account's saved value.
- Emails (invites, password reset, verification) are not part of this story and stay as they are; an invitee has no account language to use.
- Names stored before this story (for example the default notebook "{alias}'s Notebook") are not translated or renamed; naming of new default notebooks in Spanish is a follow-up if wanted.
- Quantities keep the decimal point they use today ("1.5"); a Spanish decimal comma and a localized number input are a follow-up, because members may also type amounts and the recipe rules read a point.
- The spec 016 and spec 017 error wording is the English reference; the Spanish text says the same thing, written by the owner or reviewed by them before release.
- The existing screens that already have English and Spanish text (account, sign-in, sign-up, kitchens, notebooks, recipe lists, recipe detail) are reviewed for the same missing pieces, but are not rewritten.
- Layout checks cover phone width, where longer Spanish text is most likely to break.
