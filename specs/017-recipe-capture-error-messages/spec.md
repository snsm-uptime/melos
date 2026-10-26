# Feature Specification: Clear Recipe Capture Error Messages

**Feature Branch**: not created by this command

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "I want the error message for capturing a recipe to be clear to the user what information was missing or how they can improve the message. The message should be crafted based on language."

**Related**: Builds on spec 016 (capture recipe text). Where this spec gives new wording for a message, it replaces the wording in 016 for that message only.

## Clarifications

### Session 2026-10-25

- Q: Which parts must a pasted recipe have before the app builds a draft from it? → A: Title and steps only, as the app enforces today; a recipe with no ingredient list still gets a draft.
- Q: When a recipe breaks a rule that is not about a missing part (for example, an unknown unit or a bad quantity on one ingredient), should the message name that ingredient? → A: Tell the member which problem applies: quantity missing, unit missing, or unit not recognized. Other rule breaks keep the generic message.
- Q: Reason for text that is a question or request? → A: Keep the "question or request" reason. The message tells the member to clarify the text by pasting the full recipe, with its ingredients and steps.
- Q: Should the message name the ingredient? → A: Yes. A line problem names its ingredient, so "1/4 butter" with no unit says the unit is missing for butter. A question about one ingredient (for example, "what's the total grams of a bar of butter?") names that ingredient too.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Member learns which part of the recipe is missing (Priority: P1)

A member pastes text that looks like a recipe but does not have enough to build a draft, such as no title or no steps. The message names the missing part in plain words and says what to add. The pasted text stays in the box so the member can add the part and submit again.

**Why this priority**: This is the most common way a capture fails for a real recipe, and a generic message leaves the member guessing what to change.

**Independent Test**: Paste a recipe with ingredients and steps but no title, then submit. The message names the title as missing and the text is still in the box.

**Acceptance Scenarios**:

1. **Given** a pasted text with no title, **When** the member submits it, **Then** the message says the title is missing and asks them to add it, and the text stays in the box.
2. **Given** a pasted text with ingredients but no steps, **When** the member submits it, **Then** the message says the steps are missing and asks them to add them, and the text stays in the box.
3. **Given** a pasted text missing more than one part, **When** the member submits it, **Then** the message names every missing part, not only the first one found.
4. **Given** an ingredient line with no quantity, no unit, or a unit the app does not recognize, **When** the member submits the text, **Then** the message names the ingredient, says which of these applies (quantity missing, unit missing, or unit not recognized), suggests how to fix it, and the text stays in the box. For example, "1/4 butter" gives "Add a unit to butter."

---

### User Story 2 - Member learns why the text is not a recipe (Priority: P1)

A member pastes something that is not a recipe, such as a question about the weather, or a text with two complete recipes. The message says that it does not look like a recipe, gives the reason in plain words, and says how to fix it: paste the full recipe, or paste one recipe at a time. Nothing is saved.

**Why this priority**: The current message can show an unclear reason and gives no next step. This is the other common failure.

**Independent Test**: Paste "What's the weather tomorrow?" and submit. The message says the text does not look like a recipe, gives a reason, and suggests pasting a full recipe. The text is still in the box.

**Acceptance Scenarios**:

1. **Given** a pasted text that is not a recipe, **When** the member submits it, **Then** the message says it does not look like a recipe, gives the reason, and suggests pasting the full recipe with its ingredients and steps.
2. **Given** a pasted text with two recipes, **When** the member submits it, **Then** the message says only one recipe can be added at a time and suggests pasting them one by one.
3. **Given** any not-a-recipe message, **When** the member reads it, **Then** the pasted text is still in the box and can be edited and submitted again.

---

### User Story 3 - Member knows what to do when the app cannot build a draft (Priority: P2)

The assistant answers, but the app cannot turn the answer into a recipe. The message says the app could not build a recipe from this text and tells the member what to try: submit again, or shorten the text to one recipe. It does not show technical details.

**Why this priority**: This case happens less often than the two above, but the current message gives no next step.

**Independent Test**: Make the assistant's answer unreadable in a test run. The message shows the new wording with a next step and the text is still in the box.

**Acceptance Scenarios**:

1. **Given** the assistant's answer cannot be turned into a recipe, **When** the member submits text, **Then** the message says the app could not build a recipe from this text, suggests trying again or shortening the text, and the text stays in the box.
2. **Given** that message is shown, **When** the member reads it, **Then** it contains no technical detail, error code or raw assistant text.

---

### User Story 4 - Messages are written in one language now and can be translated later (Priority: P2)

All capture messages are written in English for this feature. Each message is defined once, with its own wording, so a Spanish version (and later, the member's account language) can be added without changing when or why a message appears.

**Why this priority**: The product will need Spanish messages after MVP. Setting up the wording this way now avoids rework.

**Independent Test**: Review every capture message in the product. Each one comes from a single definition, and none is written inline in a screen or a rule.

**Acceptance Scenarios**:

1. **Given** the feature is delivered, **When** a member sees any capture message, **Then** it is in English.
2. **Given** a future translation of the messages, **When** it is added, **Then** the situations in which each message appears do not change.

---

### Edge Cases

- A text is missing several parts at once: every missing part is named.
- A text is long and missing a part: the message names the missing part and does not repeat the whole text.
- The assistant gives a reason that is long or technical: the member sees a short plain-language version from the fixed wording, never the raw reason.
- The text is at the length limit and is also missing a part: the length message is shown first, as in spec 016.
- Availability, usage-limit, and not-set-up messages: unchanged from spec 016.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every refused or failed capture MUST show a message that says in plain words what went wrong.
- **FR-002**: Where the member can act on the message, it MUST also give one concrete next step.
- **FR-003**: When a draft cannot be built because a required part of the recipe is missing, the message MUST name each missing part (the title or the steps) and ask the member to add it. The ingredient list is not a required part.
- **FR-004**: When the text is not a recipe, the message MUST say so, give the reason in plain words, and suggest pasting the full recipe with its ingredients and steps.
- **FR-005**: When the text holds more than one recipe, the message MUST say that only one recipe can be added at a time and suggest pasting them one by one.
- **FR-006**: When the assistant's answer cannot be turned into a recipe for any reason other than those in FR-012, the message MUST say that the app could not build a recipe from the text and suggest trying again or shortening the text to one recipe.
- **FR-012**: When an ingredient line has no quantity, no unit, or a unit the app does not recognize, the message MUST name that ingredient, say which of these applies (quantity missing, unit missing, or unit not recognized) and suggest how to fix it. If a line lacks both quantity and unit, the message MUST name both.
- **FR-013**: When the text is a question or request about one ingredient, the message MUST name that ingredient.
- **FR-007**: The message MUST NOT show raw assistant text, service errors, keys, codes or technical traces. Any reason shown MUST come from fixed wording chosen by the app.
- **FR-008**: The pasted text MUST stay in the box after every refused or failed capture.
- **FR-009**: Capture messages MUST be in English for this feature.
- **FR-010**: Each capture message MUST be defined in one place, so a translation can be added later without changing when a message appears.
- **FR-011**: The too-long, availability, usage-limit and not-set-up messages MUST keep their wording from spec 016.

### Key Entities

Not applicable. This feature changes wording and the choice of message only; it stores nothing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test set covering every refusal and failure case, 100% of the messages name the reason and, where the member can act, a next step.
- **SC-002**: In a check with five members, at least four out of five can say what to change after reading a missing-part or not-a-recipe message, on their first read.
- **SC-003**: In 100% of test runs, no capture message shows raw assistant text, service errors, keys or technical traces.
- **SC-004**: In 100% of refused or failed captures, the pasted text is still in the box.
- **SC-005**: Every capture message is in English and is defined in one place, so a second language can be added without changing when messages appear.

## Assumptions

- The required parts of a recipe are its title and its steps, as the recipe rules enforce them today (clarified 2026-10-25). A recipe with no ingredient list still gets a draft.
- Language is English only for this feature. Choosing the language from the member's account setting is a later story, as set in spec 016 (FR-034). The message wording is kept in one place so that story is simple.
- The new wording replaces the wording of spec 016 for the not-a-recipe and unreadable-answer messages only. Spec 016's other messages stay as they are.
- The current change in the recipe extraction code, which logs the name of the broken recipe rule on the server, stays server-side. The member never sees it.
- Members see the pasted text only in the box, as in spec 016. No new screen or saved draft is added.

## Out of Scope

- Spanish or any other translation of the messages.
- Changes to the assistant's instructions or to how it reads recipes.
- Saving, retrying automatically, or editing the text for the member.
