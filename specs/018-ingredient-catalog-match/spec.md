# Feature Specification: Match Captured Ingredient Names to the Notebook's Catalog

**Feature Branch**: not created by this command

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "S-018 from dev/docs/backlog.yaml: Match captured ingredient names to the notebook's catalog"

**Related**: Builds on spec 016 (capture recipe text) and spec 017 (capture error messages). Spec 016 FR-024 moved the name-change list and the "matched" / "new ingredient" labels to this feature. The matching rule is reused by copying a recipe into another notebook (S-048) and by a new member joining a notebook (S-057).

## Clarifications

### Session 2026-10-26

- Q: Should the singular-form rule (for example "onions" → "onion") cover only English, or both English and Spanish? → A: English and Spanish plurals.
- Q: Should the app change how it matches names from the recipe text, or should the AI model propose the match and the fixed rule only confirm it? → A: The AI model proposes a catalog match for each line, and the fixed rule confirms or rejects each proposal.
- Q: What share of plural, letter-case and spacing name variants must match the right catalog entry before this feature ships? → A: 90%.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Member sees which ingredients already exist in the notebook (Priority: P1)

After a member captures a recipe from text, the draft shows each ingredient with a label. An ingredient whose name matches an entry in the notebook's catalog is labelled "matched" with that catalog name, for example "matched: onion". An ingredient with no match is labelled "new ingredient". The member can see, before saving, which names the notebook already knows and which ones will be new to it.

**Why this priority**: This is the core of the feature. Without the labels, the member cannot tell whether a name will extend the notebook's catalog or reuse an existing entry.

**Independent Test**: With a notebook whose catalog contains "onion", capture a recipe that lists "2 large onions" and "200 g flour" (flour not in the catalog). The draft labels onions as "matched: onion" and flour as "new ingredient".

**Acceptance Scenarios**:

1. **Given** a notebook whose catalog has "onion", **When** a member captures a recipe with "2 large onions", **Then** the draft shows that line as "matched: onion".
2. **Given** a notebook whose catalog has no "saffron", **When** a member captures a recipe with "a pinch of saffron", **Then** the draft shows that line as "new ingredient".
3. **Given** a notebook with an empty catalog, **When** a member captures any recipe, **Then** every ingredient line shows "new ingredient".
4. **Given** a draft with ingredient lines that have matches and lines that do not, **When** the member reads the draft, **Then** every ingredient line shows exactly one of the two labels.

---

### User Story 2 - Member sees and undoes each name change before saving (Priority: P1)

When the text's name for an ingredient differs from the catalog entry it matches, the draft lists that change, for example "onions" → "onion". The member sees every change in one list before saving. Each change can be undone on its own, and undoing it returns that line to "new ingredient" with the name it had before the match.

**Why this priority**: A matched name changes what the member is saving. The member must be able to see it and reverse it, or the feature silently rewrites their recipe.

**Independent Test**: Capture a recipe that says "onions" into a notebook whose catalog has "onion". The change list shows "onions" → "onion". Undo the change and the line reads "new ingredient" with "onions".

**Acceptance Scenarios**:

1. **Given** a draft with a line "onions" that matches the catalog entry "onion", **When** the member opens the draft, **Then** the change list shows "onions" → "onion".
2. **Given** that change is listed, **When** the member undoes it, **Then** the line is labelled "new ingredient" with the name "onions", and the change disappears from the list.
3. **Given** a line whose name is already the catalog entry (for example "onion" matches "onion"), **When** the draft is shown, **Then** no change is listed for that line.
4. **Given** several changes are listed, **When** the member undoes one, **Then** the others stay as they were.

---

### User Story 3 - Member changes a match they disagree with (Priority: P2)

The member can change the match of any ingredient line: pick another catalog entry from the notebook, or mark the line as a new ingredient. The label and the change list update at once.

**Why this priority**: The matcher can pick the wrong entry, for example when two catalog names are close. The member must be able to correct it, but the default match is already correct for most lines.

**Independent Test**: With catalog entries "onion" and "spring onion", capture "2 spring onions". The draft matches "onion" by default. The member changes the match to "spring onion" and the label reads "matched: spring onion".

**Acceptance Scenarios**:

1. **Given** a line with the label "matched: onion", **When** the member chooses another catalog entry, **Then** the label shows the new entry and the change list reflects it.
2. **Given** a line with a match, **When** the member chooses "new ingredient", **Then** the line is labelled "new ingredient" and no change is listed for it.
3. **Given** the member changed a match, **When** the member saves the draft, **Then** the saved recipe uses the entry the member chose. (Saving itself is S-020; this story only requires the draft to carry the choice.)

---

### Edge Cases

- What happens when a name in the text matches two catalog entries, for example "onion" and "onions" both exist? The exact normalized match wins. If no entry matches exactly, the line is labelled "new ingredient" and the member can pick one (User Story 3).
- What happens when the same ingredient appears on two lines of one recipe? Both lines match the same entry, and the change list shows each line's change.
- What happens when a name differs from the catalog only in letter case or spaces ("Onion" and "onion")? They are the same name. No change is listed.
- What happens with a vague amount line ("a pinch of salt")? The line is matched like any other ingredient line and keeps its vague note.
- What happens when the catalog holds a name in Spanish and the text is English, or the reverse? No cross-language matching. A name matches only a catalog entry in the same form. Translation is a later story.
- What happens when a name is already plural in the catalog ("cloves" as a catalog entry)? The catalog name is compared in its normalized singular form too, so the text "clove" matches it. The catalog stores the normalized form already, so this only affects the text side.
- What happens when the notebook's catalog changes while a draft is open (another member saves a recipe)? The draft keeps the labels it showed when it was opened. A new capture sees the new catalog.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The draft MUST show, on every ingredient line, exactly one of two labels: "matched: <catalog name>" when the line matches an entry in the capture notebook's catalog, or "new ingredient" when it does not.
- **FR-002**: Two names MUST be treated as the same when they are equal after the same normalization: trimmed, lower-case, runs of spaces collapsed to one, and in singular form. A plural name in the text matches its singular catalog entry (for example "onions" matches "onion", "tomatoes" matches "tomato", "cebollas" matches "cebolla").
- **FR-003**: When a line's name, as shown in the draft, differs from the catalog entry it matches, the draft MUST show that change as "<name in the text> → <catalog name>" in a row directly above that line's card (decided 2026-10-28; it was a separate list above the lines), before the member saves.
- **FR-004**: The member MUST be able to undo any one shown change, from its row. Undoing it MUST return that line to "new ingredient", with the name it had before the match, and remove only that change from the list.
- **FR-005**: The member MUST be able to change the match of any ingredient line: choose another entry of the capture notebook's catalog, or choose "new ingredient". The label and the change list MUST update to match the choice.
- **FR-006**: Matching MUST read the catalog and MUST NOT change it. Adding new names to the catalog is part of saving (S-020).
- **FR-007**: When the catalog has no entry that matches a line, or the notebook's catalog is empty, the line MUST be labelled "new ingredient" and no change MUST be listed for it.
- **FR-008**: When more than one catalog entry matches a line and one of them is exactly the normalized name, that entry MUST be chosen. When no single exact match exists, the line MUST be labelled "new ingredient" until the member chooses an entry.
- **FR-009**: Matching MUST apply only to ingredient names. Category chips, the title and the steps MUST NOT be matched or listed as changes.
- **FR-010**: The draft MUST know, for each ingredient, the name as it was written in the pasted text, so that a change can be listed as "<name in the text> → <catalog name>". The name shown on the line is the one the assistant returned (spec 016 FR-024).
- **FR-011**: The matching rule MUST be one shared rule. The copy to another notebook (S-048) and the joining of a new member (S-057) MUST use the same rule, so the same two names give the same result everywhere.
- **FR-012**: The AI model MAY propose, for each ingredient line, a catalog entry it matches. The fixed rule MUST confirm a proposal only when the line's name matches that entry under FR-002, and MUST reject it otherwise. A rejected proposal leaves the line "new ingredient". Labels and changes MUST follow the rule's result, so the same text, catalog and model proposals always give the same labels and changes.
- **FR-013**: Matching MUST NOT store anything. Labels, changes and member choices live only in the draft until it is saved or discarded.

### Key Entities *(include if feature involves data)*

- **Catalog entry**: One normalized ingredient name in the capture notebook's catalog (for example "onion"). It is a plain name with no id in this feature, and this feature only reads it.
- **Ingredient line**: One ingredient in the draft. It has the name as written in the text, the name shown on the line, and its match: either one catalog entry or "new ingredient".
- **Name change**: A listed difference between the name in the text and the catalog entry a line matches. It can be undone on its own, and it exists only in the draft.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every ingredient line in a draft shows a match label before the member saves, in 100% of captures.
- **SC-002**: A member can see every name change in the draft and undo any one of them in a single action.
- **SC-003**: For a recipe of up to 30 ingredient lines against a notebook catalog of up to 500 names, the labels and change list are shown with the draft, with no visible wait.
- **SC-004**: In a test set of plural, letter-case and spacing variants of catalog names, at least 90% are matched to the expected entry without the member changing the match.
- **SC-005**: Members change the match of a line in under 10 seconds when the default match is wrong.

## Assumptions

- The catalog sent with the text (spec 016 FR-003) is the capture notebook's catalog, so matching uses the same names the assistant was given.
- The singular form is found by a fixed set of English and Spanish plural rules (decided 2026-10-26; Spanish plurals are in scope). Irregular plurals and words whose singular is not obvious are labelled "new ingredient" rather than guessed. The exact rule set is decided in planning.
- The assistant returns each ingredient name as written in the text as well as its normalized name, so the change list can show the text's form (FR-010). Adding that field to the extraction result is part of this feature. Spec 016's rules for the names shown on the line still apply.
- The AI model may propose a catalog match for each line, and the fixed rule confirms or rejects it (FR-012). This matches the PRD's wording "Gemini may match a name", which needs no change.
- Labels and the change list are English-only for now. Spanish labels come with the account-language story, as spec 017 does for its messages.
- Matching for copies (S-048) and joins (S-057) reuse this rule. Those stories are not part of this feature.
- Saving the draft, and adding new names to the catalog on save, is S-020.
