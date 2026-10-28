# Feature Specification: Capture a Recipe from Pasted Text

> **Scope change 2026-10-27:** main ingredients and cuisines are out of the MVP (backlog S-061, PRD Appendix E). Anything below about them (main ingredient keys, cuisine scoring, category chips, the `main_ingredients` and `cuisines` fields, the category lists of `GET /recipe-vocabulary`) is not in force; the code is commented out under `MVP-OUT:`. Ingredient catalog matching (S-018) is unchanged. Plan: `dev/docs/mvp-descope-categories.md`.

**Feature Branch**: `s20`

**Created**: 2026-10-20

**Updated**: 2026-10-25 (re-synced with the notebook redesign of 2026-10-23 and spec 056's snapshot model; earlier: spec 015 and the PRD as of 2026-10-22)

**Status**: Draft

**Input**: User description: "Capture a recipe from pasted text into a draft review screen" (backlog S-016, journey J2, acceptance AC2.1, AC2.4, AC2.5; PRD `dev/docs/prd.md` §1.5A, §1.10, §2 J2, Appendix B.1). Builds on the extraction boundary delivered by S-015 (`specs/015-gemini-recipe-extractor`).

## Clarifications

### Session 2026-10-20

- Q: Should S-016 build the Gemini extraction adapter itself (port, `google-genai` implementation, fake, error mapping), or depend on a separate prerequisite story? → A: Separate prerequisite story. S-016 consumes the `RecipeExtractor` port and its error mapping; the adapter is delivered first by its own backlog story.
- Q: Should the capture screen be its own page, a panel on the recipe list, or an overlay? → A: Entry point on the kitchen's recipes page. A placeholder image rectangle (standard rounded corners) sits below the page header and shows a plus icon at its centre. Activating it opens an options dialog with no confirm or cancel buttons: a vertical list of options separated by dividers, in this order: URL (not implemented yet), Picture (opens an upload sheet), Text.
- Q: In this feature, should the Picture option be shown but disabled until photo capture is built, hidden, or functional now? → A: Shown but disabled, marked "coming soon", same as URL. Photo capture is S-041.
- Q: On the kitchen's recipes page, what should the header show? → A: The kitchen name. The page header uses the kitchen name in the app chrome; recipe names appear on the cards and the recipe detail page, not in the header.
- Q: Should a recipe stay owned by the kitchen (PRD §1.6, author as a separate field), or belong to the user who created it and be shared with the kitchen? → A: Belongs to the user. A kitchen sees a recipe only when its owner shares it there. The kitchen shows the owner's alias as the author. If the owner removes the recipe from their account, it stays in the kitchen with the author alias "unknown". Out of scope: author history. Cloning a shared recipe into one's own account is a separate story (S-048).
- Q: Open item: how are names and categories of a shared recipe stored? → A: The recipe stores its names as confirmed when it enters a kitchen. Gemini normalizes each name against the kitchen's existing ingredients and categories, and the app tells the member which changes were made.
- Q: Open item: how are recipe preview images stored? → A: Saved as base64 text on the recipe. Captured source photos are still not stored.
- Q: Open item: does removing a recipe from the cart lower its cart frequency? → A: No. The count is the number of additions.

### Session 2026-10-22 (re-sync with spec 015 and the PRD)

These entries record decisions made in spec 015 and the PRD after the first draft of this spec. Where they differ from the 2026-10-20 entries, these win.

- Categories are a controlled vocabulary (spec 015, decided 2026-10-21). A draft has zero to two main ingredients from `dev/docs/categories.yaml` and zero to two cuisines from `dev/docs/cuisine.yml`, scored by the app; with no cuisine match, the cuisine is International. The "3 to 5 categories, preferring kitchen categories" rule is removed. Categories are never renamed or matched against the kitchen; only ingredient names are (supersedes part of the "names and categories" entry above).
- The Picture option is shown disabled, marked "coming soon"; it opens nothing in this feature (supersedes "Picture (opens an upload sheet)" above; PRD §1.10).
- The pasted text is limited to 10,000 characters (spec 015).
- Two or more recipes in one text: the member sees "Upload only one recipe at a time" (spec 015 FR-002, PRD J2).
- Draft names and steps follow the pasted text's language, not the kitchen's language. Translation is a later story (spec 015). Category chip labels follow the member's configured language (plan review, below).
- When the text gives no servings, base servings are 4 and marked as estimated (spec 015 FR-006b).
- The extraction makes one attempt per submission; the member retries by submitting again (PRD §1.7).
- The ownership conflict noted in the first draft (PRD J3 and AC3.2 against the sharing rule) is resolved in the PRD: deleting a recipe keeps it in the kitchens it was shared into, with author "unknown". It is no longer an open item for this feature.
- Q: The kitchen's recipes page does not exist yet, and its list stories (S-021, S-047) come later. Where does the add-recipe call to action go in this feature? → A: In two places. (1) A Recipes tab in the app's bottom tab bar, next to Home, opens the member's own recipes page (per user). (2) The kitchen page gets a Recipes tab. Both show the shared add-recipe call to action below their header. The recipe lists on both are built by later stories (S-021, S-047). Supersedes "Entry point on the kitchen's recipes page" above.
- Q: A capture started from the member's own Recipes page has no kitchen. Which notebook is it for? → A: Recipes are kept in notebooks. Each member has a personal notebook (their own recipes), and each kitchen has a shared notebook (the kitchen's recipes). A capture is for the notebook it was started from: the bottom-bar Recipes tab is the member's notebook; the kitchen's Recipes tab is that kitchen's shared notebook. Supersedes the "last-opened kitchen" assumption made earlier this session.
- Q: Spec 015 says unique vague amounts are saved by S-016 after the member confirms a draft, but saving a draft is S-020. Does S-016 include Save? → A: No. S-016 offers Discard only. Storing unique vague amounts moves to S-020, together with Save; spec 015 carries a note.
- Q: Which message does the member see when the assistant is not set up (missing key or model name)? → A: "Assistant misconfigured. Your text is kept", with no technical detail.
- Q: The PRD keeps ingredients per kitchen only. Where do the ingredients of a recipe in a member's own notebook live? → A: Ingredients belong to a member or to a kitchen: each member has a personal ingredient catalog, and each kitchen has its own. When a member uses one of their recipes in a kitchen, the recipe is copied into the kitchen, and its ingredient names are normalized against the kitchen's catalog; the kitchen's names take priority. The copy and the normalization belong to S-020 and S-018, not to this feature.
- Q: Do a recipe and its copy stay in sync? Who owns a kitchen copy? Does a capture in a kitchen also go to the member's notebook? → A: Copies drift apart; editing one never changes the other. A kitchen recipe belongs to the kitchen and records its author; any kitchen member can copy it into their own notebook. A recipe captured in a kitchen is saved into the kitchen and into the member's notebook, and the kitchen recipe's author is that member. These replace the 2026-10-20 ownership and sharing entries above; PRD §1.5 flow G, §1.6 and J3 are updated to match.
- Q: Should the list of name changes on the draft ("onions" → "onion", FR-024) move entirely to S-018, since the assistant's result does not include the original names from the text? → A: Yes. S-018 owns the change list and the per-line "matched" / "new ingredient" labels. S-016 shows names exactly as the assistant returned them.
- Q: Where does the draft review screen appear: inside the same sheet as the pasted text, or as its own page? → A: Its own full-screen page within the notebook. Back returns to the text sheet with the pasted text still there.
- Q: When a member has edited a draft and then tries to leave it some other way than Back or Discard, should the app ask first? → A: Ask only when the draft has been edited. An untouched draft leaves without a prompt.
- Q: Can members capture a recipe in an archived kitchen? → A: No. An archived kitchen's Recipes tab shows no add-recipe call to action, and a capture sent for it anyway is refused.
- Q (plan review): Is a notebook the same thing as a kitchen or a member? → A: No. A notebook is its own entity with an id, owned by one member or one kitchen. A kitchen has one notebook and a member has one. Recipes, ingredients and copies point at the notebook id. A capture is addressed to a notebook id; the api resolves the owner, checks access and, for a kitchen's notebook, the archive state. A notebook is created with its owner (the kitchen, or the member when the alias is first claimed); a migration backfills existing ones.
- Q (plan review): Which language do the chip labels use? → A: The member's configured language (English or Spanish), and the other language for a label missing in it. No language detection. The draft's names and steps still follow the pasted text. Supersedes "Chip labels MUST be in the pasted text's language" in FR-011 and the Spanish-text edge case.
- Q: Should each member be limited in how many captures they can submit per minute, to protect the assistant's shared usage limit? → A: No. There is no per-member capture limit; the assistant's own usage limit applies (FR-017).

### Session 2026-10-25 (re-sync with the notebook redesign and spec 056)

These entries supersede the 2026-10-22 entries on notebook ownership, copies and catalogs wherever they differ. The notebook model is PRD §1.5 flow H and spec 056.

- Q: Where does a capture go? → A: Outside a kitchen, into a personal notebook the member owns or belongs to. The member picks one, with the default preselected; with one eligible notebook, it is used without a picker. In a kitchen, into one of that kitchen's notebooks; with several, the member picks one. A capture never creates a notebook. Supersedes "A capture is for the notebook it was started from" and "A recipe captured in a kitchen is saved into the kitchen and into the member's notebook" (2026-10-22).
- Q: Does a kitchen capture also write to a personal notebook? → A: No. Saving writes one recipe, into the kitchen notebook, with the member as author. The automatic personal copy is removed; S-020 owns the save.
- Q: Which ingredient catalog is sent with the text? → A: The catalog of the capture's notebook. A kitchen with no notebook yet sends the member's own names (spec 056, `names_for_person`).
- Q: When a kitchen has no notebook yet, should the text sheet still accept a capture and create the notebook at save, or refuse the capture until one exists? → A: Accept the capture. The text sheet says the notebook is "a new notebook, created when the recipe is saved". Nothing is created until save (S-020). (Superseded later on 2026-10-25 by the first-open rule below.)
- Q: Should the text sheet, its buttons and the error messages appear in the member's account language (English or Spanish), or stay in English for everyone? → A: The member's account language. Every message exists in English and Spanish (FR-034). (Superseded later on 2026-10-25 by the owner's answer below.)
- Q: (owner, 2026-10-25) When a kitchen has no notebook, should the first open of its Notebook page create one? → A: Yes. The first open creates the kitchen's notebook (spec 056 FR-008a). This replaces the answer above about a kitchen with no notebook: the capture uses the notebook the page creates, and the save creates one only as a fallback (FR-009).
- Q: (owner, 2026-10-25) Where do the strings and the language come from? → A: The account language setting (`users.language`) is the language source. Strings stay English in this feature. Spanish and the internationalization work come after MVP, as in the finance-helper repo. This replaces FR-034's bilingual requirement.

### Session 2026-10-22 (decisions after the analysis)

These entries supersede the earlier wording wherever they differ.

- The bottom-bar tab and the kitchen's tab are both named "Notebook" (Spanish: "Cuaderno"). Their routes are `/notebook` and `/kitchens/[kitchenId]/notebook`. Every "Recipes tab" and "Recipes page" in the body below means the Notebook tab or page.
- Notebook creation and the notebook read routes are not part of this feature. They are delivered first by the prerequisite spec `specs/056-notebooks`. This feature reads notebooks and never creates or changes them. A member's notebook is created on first use, by spec 056, not in the signup or alias code.
- The text limit is set by the environment variable `RECIPE_TEXT_MAX_CHARS` (default 5,000). Wherever the body says 5,000 characters, it means the configured limit. The limit applies after trimming, and the request body is guarded at twice the limit. Messages show the configured number. Supersedes "10,000 characters" for this feature only; spec 015 keeps its own 10,000-character limit as the upper bound.
- Reordering ingredient lines and steps (FR-012) is required. It is not a cut line.
- SC-007 is checked by a short usability session with the two household members before release.
- Logging: a capture logs the text length and the outcome, never the pasted text (constitution §4). This is a documented rule, not a tested one.
- (Superseded 2026-10-25 by spec 056's final routes: `GET /notebooks/default`; see `contracts/capture-api.md`.) The member's page gets its notebook from `GET /notebooks/members/{user_id}` (spec 056): it returns the member's default notebook, and the first call creates it when the member has none. A route with the notebook id also exists for a specific notebook. The creation, and any later re-creation after the default is deleted, happens in the backend and is invisible to the page: it only receives the notebook.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn pasted recipe text into a reviewable draft (Priority: P1)

A member has a recipe written in a message, a note or a cookbook transcription. In a personal notebook (the Notebook tab in the bottom bar) or in one of a kitchen's notebooks (the kitchen's Notebook tab), they tap the plus icon in the placeholder rectangle, choose Text from the options, paste the text into the text sheet, and submit it. After a short wait, they see a draft review screen with the recipe's title, base servings, categories, ingredients and steps. They can correct any of it. Nothing is saved to the notebook.

**Why this priority**: This is the core value of the product. Every later step (saving, cart, shopping list, chat) depends on a correct draft from text. It is the smallest slice that gives a usable result.

**Independent Test**: Sign in, open the Notebook tab in the bottom bar, open the Text option, paste text containing "a pinch of salt" and "2 large onions", submit, and check the draft screen. The member's notebook is unchanged. Repeat from a kitchen's Notebook tab: that kitchen's notebook and its catalog are unchanged.

**Acceptance Scenarios**:

1. **Given** a signed-in member taps the Notebook tab in the bottom bar, **When** the page opens, **Then** it shows the add-recipe call to action below the header, and the Notebook tab is marked as the current tab.
2. **Given** a signed-in member opens a kitchen they belong to, **When** they choose the kitchen's Notebook tab, **Then** it shows the same add-recipe call to action below the header with the kitchen name.
3. **Given** a signed-in member is on either page, **When** they tap the plus icon, **Then** an options dialog opens with no confirm or cancel buttons, listing URL (disabled, not available yet), Picture (disabled, "coming soon") and Text, in that order, separated by dividers.
4. **Given** the options dialog is open, **When** the member chooses Text, **Then** a text sheet opens with an empty paste input and a submit control that is disabled. The sheet names the notebook the capture is for, and the member picks it when there is more than one.
5. **Given** the text sheet is open, **When** the member pastes a recipe that contains "a pinch of salt" and "2 large onions" and submits, **Then** a draft review screen appears with a title, base servings, no main-ingredient chip, a single cuisine chip "International", an ingredient table with both ingredients, and at least one step (AC2.1).
6. **Given** the draft from scenario 5, **When** the member reads the salt line, **Then** it has no quantity or unit and shows the vague note "a pinch".
7. **Given** the draft from scenario 5, **When** the member reads the onion line, **Then** it shows quantity 2, unit "unit" and size "large".
8. **Given** the pasted text gives no servings, **When** the draft appears, **Then** base servings show 4 with an "estimated" badge.
9. **Given** a draft is shown, **When** the member edits the title, servings, a category, an ingredient or a step, **Then** the edited value is shown in the draft and nothing is saved.
10. **Given** a draft is shown, **When** the member goes back, **Then** the text sheet shows the pasted text unchanged, the draft is gone, and nothing is saved.
11. **Given** the member has edited a draft, **When** they tap another bottom-bar tab, **Then** the app asks "Leave without saving? Your changes to this draft will be lost."; Stay keeps the edited draft, and Leave drops it without saving.
12. **Given** the member submits recipe text and a draft appears, **When** they look at the notebook, **Then** no new recipe, ingredient or category has been created.

---

### User Story 2 - Reject input that is not a recipe (Priority: P2)

A member pastes something that is not a recipe, such as a question about the weather, or a text with two complete recipes. The app explains why and keeps the pasted text in the box so they can correct it. Nothing is saved.

**Why this priority**: Without this, the draft screen would present junk as a recipe. It also protects the trust the product depends on.

**Independent Test**: Paste "What's the weather tomorrow?" and submit. The message "That doesn't look like a recipe." appears with a reason, the text is still in the box, and no draft or recipe is created.

**Acceptance Scenarios**:

1. **Given** the member pastes "What's the weather tomorrow?" and submits, **When** the app has analysed it, **Then** "That doesn't look like a recipe." appears with a short reason, no draft is shown, and nothing is saved (AC2.4).
2. **Given** the not-a-recipe message is shown, **When** the member looks at the input, **Then** the pasted text is still there and can be edited and submitted again.
3. **Given** the member pastes a text with two complete recipes, each with its own title and ingredient list, **When** the app has analysed it, **Then** "Upload only one recipe at a time" appears, no draft is shown, and nothing is saved.
4. **Given** the member pastes one recipe with sub-sections (for example "for the sauce"), **When** the app has analysed it, **Then** one draft is shown; the sub-sections are not treated as a second recipe.

---

### User Story 3 - Keep the pasted text when the assistant fails (Priority: P2)

The assistant is unavailable, too slow, at its usage limit, returns something unreadable, or is not set up. The app shows a plain message for that case and keeps the text in the box, so the member can try again without pasting again.

**Why this priority**: Failures are common for a slow external AI call. Losing the text would make members give up on capture.

**Independent Test**: Make the assistant fail in each way during submission. The matching message appears and the pasted text is still in the box.

**Acceptance Scenarios**:

1. **Given** the assistant does not answer in time, cannot be reached or returns a server error, **When** the member submits text, **Then** "The assistant isn't responding. Your text is kept — try again." appears and the text stays in the box (AC2.5).
2. **Given** the assistant reports its usage limit, **When** the member submits text, **Then** "We've hit the assistant's limit. Try again in a minute." appears and the text stays in the box.
3. **Given** the assistant returns a result that cannot be read as a valid recipe, **When** the member submits text, **Then** "We couldn't read that recipe. Try rephrasing or adding detail." appears and the text stays in the box.
4. **Given** the assistant is not set up for this deployment (missing key or model name), **When** the member submits text, **Then** "Assistant misconfigured. Your text is kept" appears, with no technical detail, and the text stays in the box.
5. **Given** any failure above, **When** the member submits again and the assistant succeeds, **Then** the draft appears as in User Story 1.

---

### User Story 4 - Discard a draft (Priority: P3)

After reviewing a draft, the member decides not to keep it. They choose Discard. The draft is gone and nothing is saved.

**Why this priority**: Discard is the counterpart to review and makes the draft-first rule visible.

**Independent Test**: Create a draft, choose Discard, and check that the notebook is unchanged and the text sheet is empty.

**Acceptance Scenarios**:

1. **Given** a draft is shown, **When** the member chooses Discard, **Then** the draft disappears, the text sheet returns with an empty input, and no recipe is created.
2. **Given** the member has discarded a draft, **When** they look at the notebook, **Then** it is the same as before the capture.

---

### Edge Cases

- Empty or whitespace-only input: the submit control is disabled and nothing is sent.
- Text longer than 5,000 characters (counted after trimming surrounding spaces): the submit control is disabled and the member sees "That text is too long. Paste up to 5,000 characters." The text stays in the box. If such text reaches the server anyway, it is refused with the same message and nothing is sent to the assistant.
- The member submits and, while waiting, tries to submit again: the second submission is blocked until the first one ends.
- Submitting the same text twice, one after the other, gives two independent drafts; nothing is shared between them.
- The text has no servings: base servings are 4 with the "estimated" badge.
- No cuisine matches: the cuisine chip reads "International". No main ingredient is identified: no main-ingredient chip is shown, and this is not an error.
- The text uses a written-out or misspelled unit ("tablespoon", "tablespon", "cucharada"): the draft shows the allowed unit ("tbsp") and the quantity is not converted.
- A vague phrase that is the whole amount ("to taste", "al gusto"): the line has no quantity or unit and shows the phrase as its note. A number word ("a dozen", "un par") becomes a number with unit "unit".
- The pasted text is in Spanish in an English kitchen (or the reverse): the draft's names and steps keep the pasted text's language; the category chips use the member's configured language.
- The text contains instructions such as "ignore previous instructions": they do not change how the draft is produced.
- The member edits a line so it breaks a line rule (for example a measured line with no quantity, or a size on a line whose unit is not "unit"): the problem is shown next to that line. Discard is always allowed.
- The member removes every step, or empties the title: the draft shows the problem next to that field.
- The member tries to add a third main ingredient or a third cuisine: the draft does not allow it.
- The member reloads the draft page or leaves it by another route than Back (for example a bottom-bar tab): if the draft was edited, they are asked first (FR-032); once they leave, the draft and the pasted text are gone. Nothing was saved.
- A member who is not in the kitchen tries to capture for it: the request is refused as not found, and the kitchen's existence is not revealed.
- The kitchen has no notebook yet (for example "My kitchen" after signup): opening its Notebook page creates the notebook first (spec 056 FR-008a), so the capture uses it. A capture that reaches a kitchen with none still works, and the save creates the notebook (spec 056 FR-009).
- The capture's notebook has an empty ingredient catalog: capture still works; every ingredient is a proposed new name.
- The member switches kitchen while a draft is shown: the draft stays tied to the notebook named in the text sheet.
- The kitchen is archived while its text sheet is open or a draft for it is shown: submitting for it is refused with "This kitchen is archived, so recipes can't be added.", and the pasted text stays in the box (FR-033).
- The member is removed from a kitchen while a draft for one of its notebooks is shown: submitting again for that notebook is refused as not found; the pasted text stays in the box.

## Requirements *(mandatory)*

### Functional Requirements

**Entry point**

- **FR-001**: A signed-in member MUST be able to start a capture from two places, each showing the add-recipe call to action below its header: (a) their own Notebook page, opened from a new Notebook tab in the app's bottom tab bar, next to Home; (b) a Notebook tab on the kitchen page, whose header shows the kitchen name. The call to action is a placeholder rectangle with standard rounded corners and a plus icon at its centre, and opens the add-recipe options. It is the one shared add-recipe call to action used by every page that lets a member add a recipe, not a page-specific control. The recipe lists on both pages are delivered by later stories (S-021, S-047); until then, each page shows the call to action and no list.
- **FR-001a**: Every capture MUST be for exactly one notebook. Outside a kitchen, the member picks one of the personal notebooks they own or belong to, with their default preselected; with one eligible notebook, it is used without a picker. In a kitchen, the member picks one of that kitchen's notebooks. The text sheet and the draft MUST name that notebook. The notebook does not change while the draft is shown, even if the member switches kitchen. A capture never creates a notebook. A kitchen's Notebook page creates the kitchen's notebook on its first open (spec 056 FR-008a), so a capture from that page always has one. If a kitchen has none, the capture still runs and the save creates it (spec 056 FR-009). When saving is built (S-020), the draft is saved into that notebook only: a kitchen capture writes nothing into a personal notebook, and the member is the kitchen recipe's author.- **FR-001b**: The bottom-bar Notebook tab MUST be marked as the current tab while the member is on their Notebook page. The kitchen page's other content (members, invites) MUST stay reachable from the kitchen page.
- **FR-023**: The add-recipe options dialog MUST have no confirm or cancel buttons. It MUST list, as a vertical list separated by dividers, in this order: (a) URL, shown but disabled and marked as not yet available; (b) Picture, shown but disabled and marked "coming soon" (its upload sheet is built with S-041); (c) Text, which opens the text sheet with the paste input and the submit control. Only Text works in this feature. Closing the dialog without a choice leaves the page unchanged.

**Submitting text**

- **FR-002**: The submit control MUST be disabled while the input is empty, contains only whitespace, or is longer than 5,000 characters after trimming surrounding spaces. Over the limit, the member MUST see "That text is too long. Paste up to 5,000 characters."
- **FR-003**: On submit, the system MUST send the pasted text to the recipe-extraction assistant together with the existing ingredient names of the capture's notebook, so that existing names can be reused. In a kitchen with no notebook yet, the member's own names are sent.
- **FR-004**: The system MUST show a visible progress state while the assistant is working, and MUST NOT accept a second submission until the first one ends.
- **FR-025**: The system MUST make one attempt per submission. It MUST NOT retry automatically; the member retries by submitting again.
- **FR-026**: Every member MUST see either a draft or a message within the assistant's configured wait plus two seconds of submitting (10 seconds by default for text).

**Draft review screen**

- **FR-005**: When the assistant returns a valid recipe, the system MUST open the draft review screen as its own full-screen page within the notebook the capture is for, with the title, base servings, categories as chips, an ingredient table and the steps. The names and steps are in the pasted text's language; the chips are in the member's configured language.
- **FR-006**: Base servings MUST show an "estimated" badge when they were not taken from the text. When the text gives none, they MUST be 4.
- **FR-007**: For each ingredient, the draft MUST show the name, quantity, unit and size when present, and the preparation when present. A vague amount ("to taste", "a pinch") MUST show no quantity or unit and MUST show the vague note.
- **FR-008**: Units in a draft MUST come from the allowed set: g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit. When the member edits a unit, they MUST choose from this set. Quantities are never converted between units.
- **FR-009**: Size MUST only be set when the unit is "unit", and MUST be one of small, medium or large.
- **FR-010**: Ingredient names in a draft MUST be lower-case and singular, with preparation in its own field (for example "onion" with preparation "chopped").
- **FR-011**: Categories in a draft MUST come only from the controlled lists: zero to two main ingredients (from `dev/docs/categories.yaml`) and zero to two cuisines (from `dev/docs/cuisine.yml`, scored by the app as in PRD §1.6). When no cuisine matches, the cuisine MUST be International. Chip labels MUST be in the member's configured language, or in the other language when a label is missing in it. A cuisine variant MUST be shown with its tag.
- **FR-012**: The member MUST be able to edit, in the draft: the title, base servings, each ingredient (name, quantity, unit, size, preparation, vague note), each step, and the categories. Ingredient lines and steps MUST be addable, removable and reorderable. Categories MUST be chosen from the controlled lists only, at most two main ingredients and at most two cuisines.
- **FR-013**: Every edit MUST be checked against the draft rules: a measured line has a quantity greater than zero and a unit; a vague line has neither; size only with unit "unit"; base servings a whole number of at least 1; a title that is not empty and has 200 characters or fewer; at least one step. A broken rule MUST be shown next to the field or line it concerns.
- **FR-024**: The draft MUST show each ingredient name exactly as the assistant returned it. It shows no list of name changes and no "matched" / "new ingredient" labels; both are delivered by S-018, which compares the text's names with the notebook's catalog.
- **FR-031**: Back on the draft review screen MUST return to the text sheet with the pasted text unchanged, so the member can edit it and submit again; the draft is dropped. Discard (FR-020) instead returns to an empty text sheet.
- **FR-032**: When the member has edited the draft and tries to leave it by any route other than Back or Discard (a bottom-bar tab, the kitchen switcher, a link, reloading or closing the page), the system MUST ask "Leave without saving? Your changes to this draft will be lost." with Leave and Stay. Stay keeps the draft as it was. For reloading or closing the page, the device's standard leave warning is enough. A draft with no edits leaves without asking. A draft counts as edited when its editable content differs from the draft as first shown: the title, servings, categories, every ingredient line field and every step, in order. Changing a value and then changing it back is not an edit.
- **FR-027**: The cuisine is scored once, when the draft is produced. Editing the title or steps afterwards MUST NOT change the categories on its own; the member changes them by hand.

**Not a recipe and failures**

- **FR-014**: Text the assistant reports as not a recipe MUST show "That doesn't look like a recipe." followed by the reason, MUST NOT show a draft, and MUST NOT create any data.
- **FR-015**: Text with two or more complete recipes, each with its own title and ingredient list, MUST show "Upload only one recipe at a time", MUST NOT show a draft, and MUST NOT create any data. Sub-sections of one recipe MUST NOT count as a second recipe.
- **FR-016**: When the assistant times out, cannot be reached or returns a server error, the system MUST show "The assistant isn't responding. Your text is kept — try again." and keep the input text unchanged.
- **FR-017**: When the assistant's usage limit is reached, the system MUST show "We've hit the assistant's limit. Try again in a minute." and keep the input text unchanged.
- **FR-018**: When the assistant's result cannot be read as a valid draft, the system MUST show "We couldn't read that recipe. Try rephrasing or adding detail." and keep the input text unchanged.
- **FR-028**: When the assistant is not set up for this deployment, the system MUST show "Assistant misconfigured. Your text is kept", with no technical detail, and keep the input text unchanged.
- **FR-029**: No message shown to the member MAY contain raw service error text, keys or technical traces.

**Data and access**

- **FR-019**: This feature MUST NOT save the draft. No recipe, ingredient, category, source, step or share record is created by capturing, editing or discarding a draft. The draft screen offers Discard only; Save is S-020. Storing unique vague amounts, which spec 015 assigned to S-016, moves to S-020 with Save.
- **FR-020**: A Discard control MUST be available on the draft at all times. Choosing it MUST remove the draft and return to the text sheet with an empty input, without saving anything.
- **FR-021**: The pasted text MUST be treated as data, not as instructions: text that tries to change the assistant's behaviour (for example "ignore previous instructions") MUST NOT change how the draft is produced.
- **FR-022**: A member MUST NOT be able to capture for a notebook they neither own nor belong to, or for a kitchen notebook of a kitchen they do not belong to; the request MUST be refused as not found. A capture for a personal notebook needs only that ownership or membership, and never reads another person's recipes or names.
- **FR-030**: Any member of the kitchen, owner or member role, MUST be able to capture, unless the kitchen is archived (FR-033).
- **FR-033**: An archived kitchen's Notebook tab MUST NOT show the add-recipe call to action. A capture sent for an archived kitchen MUST be refused before anything is sent to the assistant, with the message "This kitchen is archived, so recipes can't be added.", and the pasted text MUST stay in the box. The member's own notebook is never affected by a kitchen's archive state.
- **FR-034**: The UI text of this feature (text sheet, buttons, options dialog and messages) is English for now. Internationalization (English and Spanish, chosen by the account language setting, `users.language`) is a later story, after MVP. Chip labels follow the account language now (FR-011). The draft's names and steps keep the pasted text's language (FR-005).

### Key Entities *(include if feature involves data)*

- **Capture attempt**: One submission of pasted text by a member for one notebook. Holds the input text and the outcome: a draft, not a recipe (with its reason), or a failure class. Not stored.
- **Draft recipe**: The assistant's structured reading of the text, shown for review. Holds the title, base servings and whether they were estimated, main ingredients (zero to two), cuisines (zero to two, or International), ingredient lines and steps. Exists only on screen; gone on Discard, on leaving the page or on reload.
- **Draft ingredient line**: One ingredient in a draft: name, quantity, unit, size, preparation and vague note. Follows the line rules in PRD §1.6.
- **Notebook**: Where recipes are kept. Its own entity with an id. A personal notebook has one owner and any number of members; a kitchen notebook belongs to one kitchen, which can have several. Every capture is for one notebook. This feature reads notebooks and never changes them. Notebooks are created by spec 056-notebooks.
- **Ingredient catalog (read-only here)**: The set of normalized ingredient names of one notebook. The catalog of the capture's notebook is sent with the text so the draft can reuse its names. This feature reads it and never changes it.
- **Controlled category lists (read-only)**: The main-ingredient and cuisine lists, with English and Spanish labels. The only source of draft categories.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After submitting text of up to 5,000 characters, a member sees a draft or a message within 12 seconds in 100% of runs with default settings.
- **SC-002**: For the acceptance text with "a pinch of salt" and "2 large onions", the draft shows no main ingredient, the cuisine International, a salt line with a vague note and no quantity, and an onion line with quantity 2, unit "unit" and size "large", in all 10 runs of the manual evaluation.
- **SC-003**: For "What's the weather tomorrow?", the member sees "That doesn't look like a recipe." and the kitchen's recipe count is unchanged, in 100% of runs.
- **SC-004**: In every failure case (no answer in time, usage limit, unreadable result, assistant not set up), the pasted text is still in the box, so the member can retry without pasting again, in 100% of runs.
- **SC-005**: No capture, edit or discard creates or changes a recipe, ingredient, category, source, step or share record, in 100% of automated test runs.
- **SC-006**: Across the manual evaluation set of text inputs (at least one non-recipe and one with two recipes), at least 90% of drafts have the correct title, servings and ingredient lines when compared with the expected draft.
- **SC-007**: Each of the two household members completes a capture and a discard on the first attempt without help, in a short usability check.
- **SC-008**: A member who is not in a kitchen gets a not-found answer for a capture into one of that kitchen's notebooks, and a capture for an archived kitchen is refused without calling the assistant, in 100% of automated test runs.

## Assumptions

- The product is used by a small household (two to a few members); concurrent captures in the same kitchen are rare. Concurrent submissions of the same text share one assistant call (spec 015 FR-016).
- The pasted text is in English or Spanish. The draft keeps its language; no translation is done.
- The extraction rules (vague phrases, number words, the unit table and typo rule, sizes, servings, naming, category scoring) are those in spec 015 and PRD §2 J2 and Appendix B.1. This spec states them as visible behaviour only.
- The draft shape and the failure classes are those in `specs/015-gemini-recipe-extractor/data-model.md` and `contracts/recipe-extraction-port.md`. This feature is built and tested against the stand-in extractor from S-015, so tests need no network.
- Error wording follows the PRD §1.7 table exactly. The too-long message and "Assistant misconfigured. Your text is kept" are new and are recorded here. The wording is English in this feature; Spanish comes with the internationalization story after MVP (FR-034).
- There is no per-member capture limit (see Clarifications). One member's repeated captures can reach the assistant's shared usage limit for the whole deployment; FR-017 covers that case. Blocking a second submission while one is running (FR-004) is the only guard against repeated taps.
- The usage-limit message stays "Try again in a minute." even when the assistant gives a wait hint; showing the exact wait is not in this feature.
- Catalog matching (S-018), URL capture (S-026), photo capture (S-041) and saving a draft (S-020) are separate stories. Until S-018, the draft shows no "matched" / "new ingredient" labels and no list of name changes (FR-024); the assistant may still return an existing catalog name, but the draft does not mark it.
- Notebook creation and the notebook read routes are delivered by `specs/056-notebooks`, which is merged before this feature starts.
- The options dialog reuses the existing dialog component, with its confirm and cancel buttons made optional so existing dialogs stay unchanged. The text sheet reuses the existing sheet component (`AddRecipeCallToAction`, `ActionDialog`, `Sheet`; AGENTS.md "Shared UI components").
- A personal notebook's list shows its recipes, and a kitchen's Notebook tab lists the recipes of the kitchen's notebooks. Both lists come from later stories (S-021, S-047). The bottom bar's cart and chat tabs come with their own stories.
- Each notebook has its own ingredient catalog (PRD §1.6). Until S-020 saves recipes, a new notebook's catalog is empty or starts from its owner's names (flow H).
- Copying between notebooks (PRD §1.5 flow G) is not part of this feature: copying a recipe into another notebook is S-048, and adding a personal notebook to a kitchen as a snapshot is S-035. Names are normalized with the S-018 matcher, and the target's names win.
- Authorship is recorded when saving is built (S-020): the member who saves a kitchen draft is the kitchen recipe's author. This feature stores no authorship.
- Recipe preview images are not part of this feature.
- The AI evaluation set (S-034) is a manual, non-CI check; SC-002 and SC-006 are measured with it.
