# Feature Specification: Capture a Recipe from Pasted Text

**Feature Branch**: `s20`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Capture a recipe from pasted text into a draft review screen" (backlog S-016, journey J2; PRD `dev/docs/prd.md` §1.5A, §2 J2, Appendix B.1)

## Clarifications

### Session 2026-10-20

- Q: Should S-016 build the Gemini extraction adapter itself (port, `google-genai` implementation, fake, error mapping), or depend on a separate prerequisite story? → A: Separate prerequisite story. S-016 consumes the `RecipeExtractor` port and its error mapping; the adapter is delivered first by its own backlog story.
- Q: Should the capture screen be its own page, a panel on the recipe list, or an overlay? → A: Entry point on the kitchen's recipes page. A placeholder image rectangle (standard rounded corners) sits below the page header and shows a plus icon at its centre. Activating it opens an options dialog with no confirm or cancel buttons: a vertical list of options separated by dividers, in this order: URL (not implemented yet), Picture (opens an upload sheet), Text.
- Q: In this feature, should the Picture option be shown but disabled until photo capture is built, hidden, or functional now? → A: Shown but disabled, marked "coming soon", same as URL. Photo capture is S-040.
- Q: On the kitchen's recipes page, what should the header show? → A: The kitchen name. The page header uses the kitchen name in the app chrome; recipe names appear on the cards and the recipe detail page, not in the header.
- Q: Should a recipe stay owned by the kitchen (PRD §1.6, author as a separate field), or belong to the user who created it and be shared with the kitchen? → A: Belongs to the user. A kitchen sees a recipe only when its owner shares it there. The kitchen shows the owner's alias as the author. If the owner removes the recipe from their account, it stays in the kitchen with the author alias "unknown". Out of scope: author history. Cloning a shared recipe into one's own account is a separate story (S-047).
- Q: Open item: how are names and categories of a shared recipe stored? → A: The recipe stores its names as confirmed when it enters a kitchen. Gemini normalizes each name against the kitchen's existing ingredients and categories, and the app tells the member which changes were made.
- Q: Open item: how are recipe preview images stored? → A: Saved as base64 text on the recipe. Captured source photos are still not stored.
- Q: Open item: does removing a recipe from the cart lower its cart frequency? → A: No. The count is the number of additions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn typed recipe text into a reviewable draft (Priority: P1)

A member of a kitchen has a recipe written in a message, a note or a cookbook transcription. They open the kitchen's recipes page, tap the plus icon in the placeholder rectangle, choose Text from the options, paste the text into the text sheet, and submit it. After a short wait, they see a draft review screen with the recipe's title, base servings, categories, ingredients and steps, all ready to read. Nothing is saved to the kitchen yet.

**Why this priority**: This is the core value of the product. Every later step (saving, cart, shopping list, chat) depends on having a correct draft from text. It is the smallest slice that delivers a usable result.

**Independent Test**: Sign in, open the capture screen in a kitchen, paste text containing "a pinch of salt" and "2 large onions", submit, and check the draft screen. The kitchen's recipe list stays unchanged.

**Acceptance Scenarios**:

1. **Given** a signed-in member is in a kitchen and the capture screen is open on the Text input, **When** they paste a recipe text that contains "a pinch of salt" and "2 large onions" and submit, **Then** a draft review screen appears showing a title, base servings, between 3 and 5 category chips, and an ingredient table that contains both ingredients.
2. **Given** the draft from scenario 1 is shown, **When** the member reads the salt line, **Then** the salt line has no quantity or unit and shows a vague note taken from the text ("a pinch").
3. **Given** the draft from scenario 1 is shown, **When** the member reads the onion line, **Then** it shows quantity 2, unit "unit" and size "large".
4. **Given** the member submits recipe text, **When** the draft appears, **Then** no new recipe appears in the kitchen's recipe list.
5. **Given** a draft is shown, **When** the member edits the title, servings, a category, an ingredient or a step, **Then** the edited value is shown in the draft and nothing is saved.

---

### User Story 2 - Reject input that is not a recipe (Priority: P2)

A member pastes something that is not a recipe, such as a question about the weather. The app explains that it is not a recipe, shows the reason, and keeps the pasted text in the box so they can correct it. Nothing is saved.

**Why this priority**: Without this, the draft screen would present junk as a recipe and the kitchen would fill with wrong entries. It also protects the trust the product depends on.

**Independent Test**: Paste "What's the weather tomorrow?" into the Text input and submit. The message "That doesn't look like a recipe." appears, the text is still in the box, and no draft or recipe is created.

**Acceptance Scenarios**:

1. **Given** the member pastes "What's the weather tomorrow?" and submits, **When** the app analyses it, **Then** the message "That doesn't look like a recipe." appears with a short reason, no draft is shown, and nothing is saved.
2. **Given** the not-a-recipe message is shown, **When** the member looks at the input, **Then** the pasted text is still there and can be edited and resubmitted.
3. **Given** the member pastes text with two separate recipes and submits, **When** the app analyses it, **Then** the message says the app handles one recipe at a time, no draft is shown, and nothing is saved.

---

### User Story 3 - Keep the typed text when the assistant fails (Priority: P2)

The assistant is temporarily unavailable, times out, or hits its usage limit while the member is waiting. The app shows a plain message for that situation and keeps the text in the box, so the member can try again without retyping.

**Why this priority**: Failures are common for a slow external AI call. Losing typed text would frustrate users and cause them to abandon capture.

**Independent Test**: Simulate an assistant outage during submission. The matching message appears and the pasted text is still in the box.

**Acceptance Scenarios**:

1. **Given** the assistant does not respond in time or returns a server error, **When** the member submits text, **Then** the message "The assistant isn't responding. Your text is kept — try again." appears and the text stays in the box.
2. **Given** the assistant reports its usage limit has been reached, **When** the member submits text, **Then** the message "We've hit the assistant's limit. Try again in a minute." appears and the text stays in the box.
3. **Given** the assistant returns a result that cannot be read as a valid recipe, **When** the member submits text, **Then** the message "We couldn't read that recipe. Try rephrasing or adding detail." appears and the text stays in the box.
4. **Given** any failure above, **When** the member retries and the assistant succeeds, **Then** the draft appears as in User Story 1.

---

### User Story 4 - Discard a draft (Priority: P3)

After reviewing a draft, the member decides not to keep it. They choose Discard and return to an empty capture screen. Nothing is saved, and the draft is gone.

**Why this priority**: Discard is the counterpart to review and makes the draft-first rule visible. Saving the draft belongs to a later story, so this is the only exit for now.

**Independent Test**: Create a draft, choose Discard, and confirm the recipe list is unchanged and the capture screen is empty.

**Acceptance Scenarios**:

1. **Given** a draft is shown, **When** the member chooses Discard, **Then** the draft disappears, the capture screen returns to an empty Text input, and no recipe is created.
2. **Given** the member has discarded a draft, **When** they open the recipe list, **Then** the list is the same as before the capture.

---

### Edge Cases

- Empty or whitespace-only input: the submit button is disabled and no request is sent.
- Very long text: the app accepts text up to a reasonable limit and shows a plain message when the limit is exceeded, without saving anything.
- The assistant returns a recipe with no servings in the text: base servings are estimated, and the draft marks them as estimated.
- The assistant returns more than 5 or fewer than 3 categories: the draft keeps the valid categories and the rule (3 to 5, no duplicates) is enforced before the draft is shown.
- The assistant returns a unit outside the allowed set (e.g., "tablespoon"): the draft shows the mapped unit (e.g., "tbsp"); the quantity is not converted.
- The member edits the draft so that an ingredient breaks a line rule (e.g., a non-vague line without a quantity): the draft shows the problem next to the line and does not allow it to be discarded silently.
- A member who is not in the kitchen cannot run a capture for that kitchen.
- Submitting the same text twice produces two independent drafts; nothing is shared between them.
- A shared recipe whose owner removed it from their account: the kitchen keeps it, and its author alias reads "unknown". Conflict to resolve before planning: PRD J3 and AC3.2 say deleting a recipe removes it from the cart and search; this rule keeps it in the kitchen (see Clarifications).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signed-in kitchen member MUST be able to start a capture from the kitchen's recipes page: a placeholder image rectangle with standard rounded corners, placed below the page header, shows a plus icon at its centre and opens the add-recipe options. This is the shared add-recipe call to action (`AddRecipeCallToAction`, AGENTS.md "Shared UI components"), not a page-specific control.
- **FR-002**: The submit control MUST be disabled while the input is empty or contains only whitespace.
- **FR-003**: On submit, the system MUST send the pasted text to the recipe-extraction assistant together with the kitchen's existing ingredient and category names, so that names can be reused.
- **FR-004**: The system MUST show a visible progress state while the assistant is working, and the submit control MUST NOT allow a second submission of the same text at the same time.
- **FR-005**: When the assistant returns a valid recipe, the system MUST show a draft review screen with: title, base servings, categories as chips, an ingredient table, and steps.
- **FR-006**: Base servings MUST be shown with an "estimated" badge when the assistant estimated them rather than reading them from the text.
- **FR-007**: For each ingredient, the draft MUST show quantity, unit and size when present; when the text gives a vague amount ("to taste", "a pinch"), the line MUST have no quantity or unit and MUST show the vague note.
- **FR-008**: Units in a draft MUST come from the allowed set: g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit. A unit outside this set MUST be mapped to the closest allowed unit without converting between units (e.g., "tablespoon" → "tbsp"; "1 cup" stays "1 cup").
- **FR-009**: Size MUST only be set when the unit is "unit" and MUST be one of small, medium or large.
- **FR-010**: Ingredient names in a draft MUST be lower-case and singular, and preparation MUST be stored in its own field (e.g., "onion" with preparation "chopped").
- **FR-011**: Every draft MUST have between 3 and 5 unique categories, preferring categories already in the kitchen.
- **FR-012**: The member MUST be able to edit, in the draft, the title, base servings, categories, each ingredient (name, quantity, unit, size, preparation, vague note) and each step.
- **FR-013**: Edits in the draft MUST be validated against the ingredient line rules before the draft is shown as valid, and invalid lines MUST be marked next to the line.
- **FR-014**: Submitting text that the assistant reports as not a recipe MUST show "That doesn't look like a recipe." followed by the reason, MUST NOT show a draft, and MUST NOT create any recipe or other data in the kitchen.
- **FR-015**: Submitting text that contains two or more recipes MUST show the same not-a-recipe response with the reason "one recipe at a time".
- **FR-016**: When the assistant times out, is unreachable or returns a server error, the system MUST show "The assistant isn't responding. Your text is kept — try again." and MUST keep the input text unchanged.
- **FR-017**: When the assistant's usage limit is reached, the system MUST show "We've hit the assistant's limit. Try again in a minute." and MUST keep the input text unchanged.
- **FR-018**: When the assistant's result cannot be read as a valid draft, the system MUST show "We couldn't read that recipe. Try rephrasing or adding detail." and MUST keep the input text unchanged.
- **FR-019**: The draft MUST NOT be saved as a recipe during this feature. No recipe, ingredient, category, source or step record is created by capture or by discarding a draft.
- **FR-020**: A "Discard" control MUST be available on the draft. Choosing it MUST remove the draft from the screen and return to an empty Text input, without saving anything.
- **FR-021**: The pasted text MUST be treated as data, not as instructions: text that tries to change the assistant's behaviour (e.g., "ignore previous instructions") MUST NOT change how the draft is produced.
- **FR-022**: A member MUST NOT be able to capture text for a kitchen they do not belong to; the request MUST be refused as not found.
- **FR-023**: The add-recipe options dialog MUST have no confirm or cancel buttons. It MUST list, as a vertical list separated by dividers: (a) URL, shown but disabled and marked as not yet available; (b) Picture, shown but disabled and marked "coming soon", the same treatment as URL; its upload sheet (inner dashed border about 2rem thick, text "Upload file or drag and drop") is built with S-040, not here; (c) Text, which opens a text sheet with the paste input and submit control. Only Text is functional in this feature.
- **FR-024**: When the draft's names or categories are matched to existing kitchen entries, the draft screen MUST list each change (for example "onions" → "onion"), so the member can see it and undo it before save. The matching itself is delivered by S-017; this feature displays its result.

### Key Entities *(include if feature involves data)*

- **Capture attempt**: One submission of pasted text by a member for a kitchen. Holds the input text and the outcome (draft, not a recipe, or a failure). Not stored as a recipe.
- **Draft recipe**: The assistant's structured reading of the text, shown for review. Holds title, base servings (and whether estimated), categories, ingredient lines, and steps. Exists only on screen and is discarded when the member leaves or discards it.
- **Draft ingredient line**: One ingredient in a draft. Holds name, quantity, unit, size, preparation, and vague note. Follows the line rules in the PRD (§1.6).
- **Recipe ownership (for context, set by the clarification above)**: A recipe belongs to one user and is shared into kitchens. The kitchen's view of a shared recipe shows the owner's alias as the author; when the owner removes the recipe, the alias reads "unknown" and the recipe stays in the kitchen.
- **Kitchen catalog (read-only here)**: The kitchen's existing ingredient and category names, used to prefer existing names. This feature reads it and never changes it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member can go from pasting a typical recipe to seeing a draft review screen in under 15 seconds for a recipe of up to 500 words, on a normal connection.
- **SC-002**: For the acceptance text "a pinch of salt" and "2 large onions", the draft shows 3 to 5 categories, a salt line with a vague note, and an onion line with quantity 2, unit "unit" and size "large", on every attempt in the manual evaluation set.
- **SC-003**: For the not-a-recipe input "What's the weather tomorrow?", the member sees the "That doesn't look like a recipe." message, and the recipe count in the kitchen is unchanged, in 100% of runs.
- **SC-004**: In every failure case (timeout, usage limit, unreadable result), the pasted text is still in the input, so the member can retry without retyping, in 100% of runs.
- **SC-005**: No capture attempt, draft or discard creates a recipe, ingredient, category or step record in the kitchen.
- **SC-006**: Across the manual evaluation set of text inputs (including at least one non-recipe and one with two recipes), at least 90% of drafts have the correct title, servings and ingredient lines when compared with the expected draft.
- **SC-007**: A member can complete a capture and discard it without assistance from the team on the first attempt, as observed in a short usability check with the two household users.

## Assumptions

- The product is used by a small household (two to a few members) with one kitchen per household; concurrent capture for the same kitchen is rare.
- Capture is available to any kitchen member (owner or member role), as stated in PRD §3.
- The pasted text is in English or Spanish, matching the kitchen's `content_language`; no translation is performed.
- "Save" is out of scope for this feature (it belongs to the "Save a confirmed draft" story). Until that story is built, the draft screen offers Discard only, and drafts are not persisted between page reloads.
- URL and photo capture logic, the catalog match display ("matched: onion" / "new ingredient") and the ingredient-matching behaviour belong to other backlog stories (S-025, S-040, S-017) and are not part of this feature.
- The extraction rules (vague amounts, units, sizes, servings, categories, naming) are those in PRD §2 J2 and Appendix B.1; this spec states them as user-visible behaviour only.
- The maximum input length is a reasonable product limit chosen during planning, not a value fixed by the PRD.
- Error wording follows the PRD §1.7 table exactly, so the user-facing messages match the rest of the product.
- The entry rectangle lives on the kitchen's recipes page. That page is not built yet (its list is S-020 and its card view is the new story S-046), so S-016 depends on the recipes page existing before the entry point can be shown.
- A captured draft becomes owned by the member who submitted it when it is saved (S-019). Authorship is not stored in this feature.
- Author history (who owned a recipe before) is out of scope for the whole product.
- Recipe preview images, when the feature that adds them is built (S-046 and its owner-side upload), are stored as base64 text on the recipe. This feature does not store images.
- The options dialog reuses the existing `ActionDialog` component. Its confirm and cancel props become optional so a dialog with no footer buttons is possible; existing callers stay unchanged. The upload sheet reuses the existing `Sheet` component, with its dashed border added as new styling.
- Dependency: the Gemini extraction adapter (the `RecipeExtractor` port implementation, its `google-genai` SDK wiring and its error mapping to the PRD §1.7 domain errors) is a prerequisite delivered by a separate backlog story, not by this feature. This feature is built and tested against a fake extractor until that story is done.
- The AI evaluation set (S-033) is a manual, non-CI check; this spec only requires that the set exists for the success criterion SC-006 to be measured.
