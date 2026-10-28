# Feature Specification: Save a Confirmed Draft into Its Notebook

**Feature Branch**: not created by this command

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml @dev/docs/prd.md S-20" (S-020: Save a confirmed draft into its notebook and create new catalog entries)

**Related**: Builds on spec 016 (capture recipe text, which offers Discard only and defers Save here), spec 018 (ingredient catalog matching, which only reads the catalog and defers adding names here) and spec 056 (notebooks, which owns the capture-notebook step). PRD 1.5 A, 1.6, J2 Save, AC3.5.

## Clarifications

### Session 2026-10-27

- Q: After a successful Save, where does the member land, given there is no recipe detail page yet? → A: Back on the notebook the recipe was saved into, with a "Recipe saved" message. The recipe is not listed there until S-021.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Member saves a reviewed draft into the notebook (Priority: P1)

A member has captured a recipe and corrected the draft. They choose Save. The recipe is stored once, in the notebook the capture started from, with the member as its author. The member returns to that notebook and sees a "Recipe saved" message.

**Why this priority**: Without Save, capture produces nothing lasting. Every later story (lists, cart, shopping list) depends on saved recipes.

**Independent Test**: Capture a recipe in a personal notebook, press Save, and check that one recipe exists in that notebook with the member as author and the title, servings, ingredient lines and steps shown in the draft.

**Acceptance Scenarios**:

1. **Given** a draft captured for a personal notebook the member owns, **When** the member saves it, **Then** exactly one recipe is created in that notebook, the member is its author, and its title, base servings, ingredient lines and steps equal what the draft showed.
2. **Given** a draft captured in a kitchen that has a notebook, **When** a kitchen member saves it, **Then** one recipe is created in the kitchen notebook chosen for the capture, with that member as author (AC3.5; listing it comes with S-021). Nothing is written to any personal notebook.
3. **Given** the member edited the title, an ingredient and a step in the draft, **When** they save, **Then** the saved recipe has the edited values, not the extracted ones.
4. **Given** a draft whose servings were estimated, **When** it is saved, **Then** the recipe keeps the "estimated" flag.
5. **Given** a save has succeeded, **When** the member presses Save again or reloads the page, **Then** no second recipe is created.

---

### User Story 2 - New ingredient names join the notebook's catalog (Priority: P1)

Ingredient lines the member confirmed as "new ingredient" add their names to the notebook's catalog, so the next capture in that notebook can match them. Lines matched to an existing entry add nothing.

**Why this priority**: Matching (spec 018) only works if the catalog grows with each saved recipe.

**Independent Test**: Save a draft with "onion" matched and "leek" new into a notebook whose catalog has "onion". The catalog then has "onion" once and "leek" once. Capturing "leeks" afterwards matches "leek".

**Acceptance Scenarios**:

1. **Given** a draft with one matched line ("onion") and one new line ("leek"), **When** it is saved, **Then** the catalog gains "leek" and "onion" is not duplicated.
2. **Given** a draft where the member undid a name change ("onions" back to a new ingredient), **When** it is saved, **Then** the recipe line keeps "onions" and the catalog gains "onions".
3. **Given** two lines in one draft with the same new name, **When** it is saved, **Then** the catalog gains that name once.
4. **Given** a notebook with an empty catalog, **When** a draft is saved, **Then** the catalog contains every distinct line name of the recipe.
5. **Given** the save fails, **When** the member looks at the notebook, **Then** neither the recipe nor any new catalog name exists (all or nothing).

---

### User Story 3 - Save target is checked and a failed save loses nothing (Priority: P2)

Between capture and Save, things can change: the notebook may be deleted, the kitchen archived, access removed, or the connection may fail. Save refuses with a plain message when the target is no longer valid, and the member's draft stays on screen so nothing they typed is lost.

**Why this priority**: Protects the member's edits and keeps access rules intact, but the happy path delivers value first.

**Independent Test**: Archive the kitchen after capturing a draft in it, press Save, and see a message that the kitchen is archived, with the draft still editable and no recipe stored.

**Acceptance Scenarios**:

1. **Given** the kitchen was archived after the draft was captured, **When** the member saves, **Then** nothing is stored, a message says no recipes can be added to an archived kitchen, and the draft stays on screen.
2. **Given** the notebook was deleted after capture, **When** the member saves, **Then** nothing is stored and a message says the notebook no longer exists.
3. **Given** the member lost access to the notebook (left the kitchen or was removed from the personal notebook), **When** they save, **Then** the app answers as if the notebook does not exist and stores nothing.
4. **Given** the kitchen had no notebook when the capture started, **When** the member saves, **Then** a kitchen notebook is created first (named as in PRD flow H) and the recipe is saved into it. If the save then fails, that notebook still exists and the draft stays on screen.
5. **Given** the connection drops while saving, **When** the member presses Save again, **Then** at most one recipe results.

---

### Edge Cases

- The draft has no title, no ingredient line or no step: Save is refused with a message naming what is missing, and nothing is stored (same rules as the capture rejects).
- A line breaks the line rules (a vague note together with a quantity, a size on a non-"unit" line, a non-vague line without quantity and unit): Save is refused and the line is named.
- A name with different letter case or spacing from an existing catalog entry: it is normalized to the same entry and no duplicate is made.
- Two members save drafts with the same new name into the same notebook at the same time: the catalog ends with that name once and both recipes are stored.
- The member's account is the only author reference; if the account is later deleted the alias reads "unknown" (PRD 1.6).
- The member discards instead of saving: nothing is stored, as in spec 016.
- A draft is very long: Save accepts up to 100 ingredient lines and 100 steps (FR-019). Beyond that it is refused with a message naming the limit, and nothing is stored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The draft review screen MUST offer Save next to Discard. Save MUST be disabled while the draft is invalid or while a save is in progress.
- **FR-002**: Saving MUST store exactly one recipe in exactly one notebook: the notebook the capture started from (outside a kitchen, a personal notebook the member owns or belongs to; in a kitchen, one of that kitchen's notebooks). A kitchen capture MUST NOT write into any personal notebook.
- **FR-003**: The saved recipe MUST record the saving member as its author.
- **FR-004**: The saved recipe MUST carry the title, base servings, the "estimated" flag, the ingredient lines (name, quantity, unit, size, preparation, vague note, position) and the steps (position, text) exactly as shown in the draft at the moment of Save, including every edit and every match choice the member made.
- **FR-005**: Before storing, the domain rules MUST be checked again (line rules, units, servings at least 1, title and at least one ingredient and one step). A draft that fails MUST NOT be stored, and the message MUST name the failing part.
- **FR-006**: Each ingredient line MUST store the name the member confirmed, trimmed and lower-cased, as a plain string. Save does not singularize or rename; singular forms are applied only when matching (spec 018). A name that differs from an existing catalog entry only by letter case or spacing takes that entry's spelling.
- **FR-007**: Names confirmed as "new ingredient" MUST be added to the notebook's catalog, each distinct normalized name once. Names matched to an existing entry MUST NOT add anything. Catalog names MUST stay unique per notebook.
- **FR-008**: Storing the recipe, its lines, its steps, its source record and the new catalog names MUST succeed or fail as one unit. A failed save MUST leave the notebook and its catalog as they were.
- **FR-009**: The saved recipe MUST keep its source record: type "text" and the pasted text. A recipe captured from text MUST show no source link. Captured source photos are never stored.
- **FR-010**: Vague amounts MUST be stored on their line as the vague note, with no quantity and no unit. Each distinct vague phrase MUST be kept as written so the line shows it unchanged.
- **FR-011**: When the draft names its notebook, Save MUST use exactly that notebook and check access to it; it MUST NOT pick another one. When the request names only a kitchen (the kitchen has no notebook), Save MUST run the capture-notebook step (spec 056) before storing anything and create the kitchen notebook; that notebook MUST remain if the rest of the save fails.
- **FR-012**: Save MUST refuse, store nothing and keep the draft on screen when: the kitchen is archived; the notebook choice is required but missing; the notebook does not exist; the member has no access to the notebook or kitchen. A member without access MUST get the same answer as for a notebook that does not exist.
- **FR-013**: Saving the same draft twice MUST NOT create two recipes. A repeated Save after success MUST return the already saved recipe.
- **FR-014**: After a successful Save, the member MUST be taken back to the notebook the recipe was saved into and see a "Recipe saved" message, and the draft MUST be gone. No recipe detail page is built here (S-027); the recipe is not listed in the notebook until S-021. After a failed Save, the draft and the pasted text MUST remain unchanged on screen.
- **FR-015**: The new recipe MUST be stored in its notebook right after Save (listing it is S-021). Embedding it for search is not part of this feature (S-019); a recipe saved before embeddings exist MUST be picked up when embeddings are built.
- **FR-016**: Saving MUST NOT change any other recipe, any other notebook or any copy elsewhere.
- **FR-017**: Cuisines and main ingredients MUST NOT be stored; they are out of the MVP (S-061).
- **FR-018**: All messages shown by Save MUST be in plain English, with no codes or technical terms.
- **FR-019**: Save MUST accept at most 100 ingredient lines and 100 steps, and the pasted text up to the capture text limit. A larger draft MUST be refused as invalid, with nothing stored.

### Key Entities *(include if feature involves data)*

- **Recipe**: A saved recipe in exactly one notebook, with title, base servings, estimated-servings flag, author, source and creation time.
- **Recipe ingredient line**: One ingredient of a recipe: a normalized name, optional quantity, unit, size, preparation, or a vague note, and its position.
- **Step**: One instruction of a recipe, with its position and text.
- **Source**: The record of where the recipe came from (here: pasted text). Deleting it never deletes the recipe.
- **Catalog entry**: One unique normalized ingredient name in a notebook's catalog. Save adds entries; it never removes or renames them.
- **Notebook**: The personal or kitchen notebook that receives the recipe. Save may create a kitchen notebook only when the kitchen has none.
- **Author**: The member who saved. Shown as an alias, or "unknown" if the account is gone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member can go from a reviewed draft to a saved recipe with one action, and the member is back on the notebook with the confirmation within 3 seconds in normal conditions.
- **SC-002**: In 100% of saves, the stored recipe equals the draft shown at the moment of Save (title, servings, lines, steps).
- **SC-003**: In 100% of saves, the notebook ends with exactly one new recipe and its catalog has no duplicate names.
- **SC-004**: In 100% of failed saves, no recipe, source or catalog name is left behind (except a kitchen notebook created by the capture step), and the draft remains on screen.
- **SC-005**: Pressing Save repeatedly or retrying after a dropped connection never produces more than one recipe from one draft.
- **SC-006**: A member without access to the target notebook cannot tell it exists: the response is identical to a missing notebook in 100% of cases.
- **SC-007**: After saving a recipe with a new ingredient, a later capture in the same notebook that mentions a plural or capitalized form of it labels the line "matched" (links to spec 018's 90% target).

## Assumptions

- The draft screen, the draft content, and the "matched" / "new ingredient" labels already exist (specs 016, 018); this feature adds Save and everything that happens at Save.
- Only text capture exists today (S-016); URL and photo captures (S-026, S-041) will reuse the same Save and set the source type and link.
- Normalization of names at Save reuses the shared catalog rule from spec 018; no new matching is done here.
- The PRD data model has no separate store for vague phrases. "Unique vague amounts" (moved here from spec 015) is read as: each vague phrase is saved as the line's vague note, unchanged. A separate list of distinct phrases is not built.
- Editing or deleting a saved recipe (S-027), recipe lists (S-021), embedding (S-019) and cart (S-022) are out of scope.
- A preview image is not set by Save; a recipe shows the default cooking-pot icon until an image story exists.
- Duplicate-save protection uses an identity for the draft created when the draft is shown; the draft itself is still never stored before Save.
- Mapping the refusal cases to the status codes of PRD 1.7 and the spec 056 contract is a planning detail.
