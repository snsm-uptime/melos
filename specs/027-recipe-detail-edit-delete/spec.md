# Feature Specification: Recipe Detail, Edit and Delete

**Feature Branch**: not created by this command

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "S-027" (Recipe detail, edit and delete with confirmation; deletion removes it from cart and search)

**Related**: Builds on spec 020 (save a confirmed draft, which stores recipes), spec 021 (recipe lists, whose cards are display-only) and spec 056 (notebooks and their access rules). PRD J3 "Detail", AC3.2 and Appendix D (who may edit and delete a recipe). Out of this feature: the recipe PDF (S-028), copy to notebook (S-048), the cart (S-022), semantic search and embeddings (S-019, S-044), the chat and its citations (S-030), catalog management (S-043), categories (S-061) and creating or editing a recipe's preview image.

## Clarifications

### Session 2026-10-28

- Q: Should edited ingredient names only be trimmed and lower-cased, or also matched against the notebook's catalog? → A: Also matched (S-018 matcher); each change is shown and can be undone before saving.
- Q: When a recipe is deleted, is its source record deleted or kept? → A: Deleted together with the recipe.
- Q: After saving an edit, where does the member land? → A: On the recipe's detail page, showing the saved changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a recipe and read it (Priority: P1)

A member taps a recipe card in a notebook or kitchen list and sees the whole recipe: title, base servings (with an "estimated" badge when the number was guessed), the author's alias, the notebook it is in, every ingredient line, the steps in order and, when the recipe came from a web page, a link to its source. The member can go back to the list they came from.

**Why this priority**: Lists (spec 021) show only a summary. Without a detail page nobody can read the saved recipe, so edit and delete have nowhere to live.

**Independent Test**: Save a recipe, open its card from the list, and check that every ingredient line, every step, the servings and the author appear exactly as saved.

**Acceptance Scenarios**:

1. **Given** a saved recipe with three ingredients and four steps, **When** a member who can read its notebook opens its card, **Then** the title, servings, author alias, notebook name, all three ingredient lines and all four steps appear, steps in order.
2. **Given** a recipe whose servings were estimated, **When** it is opened, **Then** the servings show an "estimated" badge.
3. **Given** an ingredient line with a vague amount ("to taste"), a counted item with a size ("2 large onion") and a measured line ("1 cup rice"), **When** the recipe is opened, **Then** each line shows its amount the way it was saved, with the preparation note when there is one.
4. **Given** a recipe saved from a URL, **When** it is opened, **Then** a link to the source page is shown; a recipe saved from pasted text shows no source link.
5. **Given** a recipe whose author's account is gone, **When** it is opened, **Then** the author reads "unknown".
6. **Given** a person with no access to the recipe's notebook, **When** they try to open the recipe, **Then** the answer is the same as for a recipe that does not exist.
7. **Given** a member of a personal notebook or a kitchen that holds the recipe, **When** they open it from the list, **Then** they can return to that same list in one action.

---

### User Story 2 - Correct a saved recipe (Priority: P1)

A member who can write to the recipe's notebook chooses Edit, changes the title, the base servings, any ingredient line (name, amount, unit, size, preparation, vague note) or any step, adds or removes ingredient lines and steps, reorders them, and saves. The recipe shows the new content right away in its notebook and kitchen list. Cancelling leaves the recipe untouched.

**Why this priority**: A captured recipe is rarely perfect after the first save. Without edit, the only fix is to capture it again, which duplicates it.

**Independent Test**: Open a recipe as its author, change the title, one amount and one step, save, reload, and check that the detail page and the list card show the new values and nothing else changed.

**Acceptance Scenarios**:

1. **Given** a recipe in a personal notebook, **When** the owner or a notebook member edits the title and saves, **Then** the detail page and the list card show the new title.
2. **Given** a recipe in a kitchen notebook, **When** any member of the kitchen edits it, **Then** the change is saved, whoever the author is, and the author stays the original author.
3. **Given** the edit form, **When** the member changes "1 cup" to "2 cups", adds a new ingredient line and removes a step, **Then** after saving the recipe has the new amount, the extra line and one step fewer, and the remaining steps stay in order.
4. **Given** the edit form with unsaved changes, **When** the member cancels or leaves the page, **Then** the recipe is unchanged; leaving with unsaved changes asks for confirmation first.
5. **Given** an edit that breaks a line rule (a measured line with no amount or no unit, a vague note together with an amount, a blank title, no ingredients, no steps, servings below 1), **When** the member tries to save, **Then** nothing is saved and a plain message names the line or field to fix, with the member's other edits kept on screen.
6. **Given** an edit that introduces an ingredient name not yet in the notebook's catalog, **When** it is saved, **Then** the name is added to that notebook's catalog, as at the first save.
   6a. **Given** an edit that types "onions" in a notebook whose catalog has "onion", **When** the member finishes the line, **Then** the change "onions" → "onion" is shown and can be undone before saving; if undone, "onions" is kept and added to the catalog.
7. **Given** a member who can only read the recipe (for example, a member of an archived kitchen), **When** they open it, **Then** no Edit action is offered, and a direct attempt to save a change is refused with the same answer as for a person without write access.
8. **Given** two members editing the same recipe, **When** the second one saves after the first, **Then** the second is told the recipe changed since they opened it and is not allowed to overwrite it silently; their edits stay on screen so they can reload and redo them.

---

### User Story 3 - Delete a recipe with confirmation (Priority: P1)

A member who can write to the recipe's notebook chooses Delete and is asked to confirm, naming the recipe. On confirming, the recipe is gone from its notebook, from the kitchen's list and, once they exist, from the kitchen's cart and search. Copies and snapshots of it in other notebooks are not touched.

**Why this priority**: Mistaken or duplicate recipes must be removable, and the PRD makes deletion a Must with explicit consequences (AC3.2).

**Independent Test**: Delete a recipe from a kitchen notebook, then check that it is absent from the kitchen list and from its notebook, and that a copy of the same recipe in another notebook is still there with its content unchanged.

**Acceptance Scenarios**:

1. **Given** a recipe the member can write to, **When** they choose Delete, **Then** a confirmation names the recipe and offers Delete and Cancel; nothing is deleted yet.
2. **Given** the confirmation, **When** the member confirms, **Then** the recipe is removed, the member returns to the list they came from, and the list no longer shows it.
3. **Given** the confirmation, **When** the member cancels, **Then** the recipe is unchanged and still open.
4. **Given** a recipe in a kitchen notebook, **When** it is deleted, **Then** it no longer appears in the kitchen's list for any member.
5. **Given** a recipe that has copies or snapshots in other notebooks, **When** it is deleted, **Then** those copies remain with the same content (AC3.2).
6. **Given** a recipe deleted by another member while this member has it open, **When** this member opens or saves it, **Then** they see that the recipe no longer exists and are taken back to the list; nothing breaks.
7. **Given** a member who can only read the recipe, **When** they open it, **Then** no Delete action is offered, and a direct attempt to delete is refused with the same answer as for a person without write access.
8. **Given** a recipe in the middle of being deleted, **When** the member presses Confirm twice, **Then** the recipe is deleted once and no error is shown for the second press.

---

### User Story 4 - A deleted recipe leaves nothing dangling (Priority: P2)

Whatever refers to a recipe stops showing it when it is deleted: the kitchen's cart, the search, and a past chat citation. A past citation keeps its text and shows "recipe removed" in place of the link. This story fixes the rule now, so the later stories that create these references (cart S-022, embeddings S-019, chat S-030) honour it.

**Why this priority**: The PRD asks for it, but the cart, search and chat do not exist yet, so today it can only be checked as a rule on the stored data, not on screen.

**Independent Test**: Delete a recipe and check that no stored record still points to it and that nothing a person can open lists it. When the cart, search or chat exist, the same check is repeated on each.

**Acceptance Scenarios**:

1. **Given** a recipe that is deleted, **When** any list, detail or lookup by its identity is requested, **Then** it is reported as missing.
2. **Given** a recipe with a stored embedding or cart entry (once those exist), **When** the recipe is deleted, **Then** the embedding and the cart entry are removed with it and the rest of the cart is unchanged.
3. **Given** a past chat citation to a deleted recipe (once chat exists), **When** the conversation is shown, **Then** the citation text is kept and "recipe removed" appears in place of the link.

---

### Edge Cases

- Deleting the last recipe of a notebook leaves an empty notebook that shows the empty-list message from spec 021; the notebook itself is not deleted.
- Deleting a recipe never removes ingredient names from the notebook's catalog, even when no other recipe uses the name; cleaning the catalog belongs to S-043.
- Editing an ingredient name to one that differs only by case or spacing (" Onion ") stores the normalized name and does not create a second catalog entry. Names left untouched in an edit are not changed by the matcher.
- Editing changes only the recipe's content; its author, notebook, source and creation time stay the same. Its last-updated time changes.
- A recipe from a snapshot or copy edits independently of its original: editing either one never changes the other (AC3.3).
- Titles, ingredient names and steps with accents, ñ, ¿, ¡ or fractions are kept unchanged through edit.
- A recipe with 100 ingredient lines or very long steps can still be opened, edited and saved.
- The member loses access (leaves the kitchen, is removed from the notebook, the kitchen is archived) while on the detail or edit page: the next action gets the same answer as for a recipe that does not exist, or as for read-only access in the archived case; nothing is changed.
- A direct link to a recipe the person can read opens the detail page without going through a list.
- A recipe captured before this feature has no `updated` history; it shows and edits like any other.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A member MUST be able to open a recipe from its card in a personal notebook list or a kitchen list, and to reach it by direct link, when they can read its notebook.
- **FR-002**: The recipe detail MUST show the title, base servings (with an "estimated" badge when estimated), the author's alias ("unknown" if the account is gone), the name of the notebook it is in, every ingredient line with its amount, unit, size, preparation and vague note as saved, and every step in order.
- **FR-003**: The detail MUST show a link to the source page when the recipe came from a URL, and no source section otherwise.
- **FR-004**: The detail MUST offer a way back to the list the member came from. The cards of spec 021 MUST become links to this detail; this replaces the "display-only cards" behavior of spec 021 FR-014 for the detail link only. Cart checkbox, category chips and the other controls named there stay out.
- **FR-005**: Edit and Delete MUST be offered only to people who can write to the recipe's notebook: the owner and members of a personal notebook, or any member of the kitchen for a kitchen notebook. They MUST NOT be offered in an archived kitchen.
- **FR-006**: The system MUST enforce FR-005 on every attempt to change or delete, not only by hiding the actions. A person who can read but not write MUST be refused; a person who cannot read MUST get the same answer as for a missing recipe.
- **FR-007**: Edit MUST allow changing the title, base servings, each ingredient line (name, quantity, unit, size, preparation, vague note), and each step; adding and removing ingredient lines and steps; and reordering both.
- **FR-008**: Saving an edit MUST apply the same recipe rules as the first save: a title is required; base servings are at least 1; at least one ingredient line and one step; a vague note excludes quantity and unit; a measured line needs a quantity above 0 and a unit; a size is kept only on a counted item (on any other line it is not stored, as at the first save); units come from the allowed set. A recipe failing any rule MUST NOT be saved, and the message MUST name what to fix in plain words.
- **FR-009**: Ingredient names typed in an edit MUST be normalized the same way as at capture (trimmed, lower-cased) and matched against the recipe's notebook catalog with the S-018 matcher. Every name change the match proposes MUST be shown to the member and be undoable before saving. Any name not yet in the recipe's notebook catalog MUST be added to that catalog when the edit is saved. Saving an edit MUST NOT remove names from the catalog.
- **FR-010**: Edit MUST keep the recipe's author, notebook, source and creation time, and MUST update its last-updated time.
- **FR-011**: If the recipe was changed or deleted by someone else after the member opened it, saving MUST NOT overwrite it silently. The member MUST be told what happened in plain words and MUST keep their typed edits on screen.
- **FR-011a**: After a successful save the member MUST land on the recipe's detail page showing the saved changes, with the way back to the original list still available.
- **FR-012**: Cancelling an edit, or leaving it, MUST leave the recipe unchanged; leaving with unsaved changes MUST ask for confirmation.
- **FR-013**: Delete MUST ask for confirmation that names the recipe and offers Delete and Cancel. The recipe MUST be removed only after the member confirms.
- **FR-014**: Deleting a recipe MUST remove it, with its ingredient lines and steps, from its notebook and from the kitchen's list when it was in a kitchen notebook. The recipe's source record (pasted text or page link) MUST be deleted with it, and this MUST NOT affect any other recipe.
- **FR-015**: Deleting or editing a recipe MUST NOT change any copy or snapshot of it in other notebooks, nor the notebook's other recipes.
- **FR-016**: Deleting a recipe MUST remove any cart entry and any stored search data that refers to it, and a past chat citation to it MUST keep its text and show "recipe removed" in place of the link. Where the cart, search or chat do not exist yet, this MUST be satisfied by those stories when they are built; this feature MUST NOT leave any reference of its own that outlives the recipe.
- **FR-017**: After a delete the member MUST land on the list they came from, with the recipe absent. A second delete of the same recipe (double press, another tab) MUST end without an error screen.
- **FR-018**: Opening a detail MUST NOT create, change or delete anything.
- **FR-019**: All messages shown by the detail, edit and delete MUST be in plain English, with no codes or technical terms.

### Key Entities *(include if feature involves data)*

- **Recipe**: A saved recipe in exactly one notebook (spec 020), with title, base servings, whether servings were estimated, ingredient lines, steps, author, source and times. This feature reads, changes and removes it.
- **Ingredient line**: One row of a recipe: a normalized name, and either a measured amount with unit (and a size for counted items) or a vague note, plus an optional preparation. Order is kept.
- **Step**: One short instruction, in order.
- **Notebook**: The personal or kitchen notebook that holds the recipe. It decides who can read and who can write (spec 056). Its catalog gains names on edit and loses none.
- **Source**: Where a recipe came from (pasted text or a web page link). Shown on the detail when it is a link.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member opens a recipe from its list card in one tap and sees every saved ingredient line and step, in 100% of checks, with the first content visible within 2 seconds in normal conditions.
- **SC-002**: A member corrects a recipe's title, one amount and one step and sees the result on the list in under 1 minute, with no other field changed in 100% of checks.
- **SC-003**: In 100% of checks, an edit that breaks a recipe rule saves nothing and tells the member which field or line to fix.
- **SC-004**: In 100% of checks, a person who can read but not write cannot change or delete the recipe, and a person who cannot read it cannot tell whether it exists.
- **SC-005**: In 100% of checks, deleting a recipe leaves its copies and snapshots in other notebooks and every other recipe of its notebook unchanged (AC3.2).
- **SC-006**: No recipe is deleted without a confirmation step, in 100% of checks, and a cancelled delete changes nothing.
- **SC-007**: When two members change the same recipe, none of the first member's saved edits is lost without the second member being told, in 100% of checks.

## Assumptions

- The detail page is a screen reachable from the lists and by direct link; it uses the same notebook and kitchen access rules as spec 056 and spec 021, so reading follows notebook readers and writing follows notebook writers (PRD Appendix D).
- Edit reuses the field set and rules of the draft review screen from spec 016 and spec 020; it is not a new way to author recipes. Main ingredients and cuisines are out of the MVP (S-061), so the edit has none.
- Preview images are not edited here; a recipe keeps whatever image it has (none today), and the card keeps the default cooking-pot icon.
- There is no recipe history or undo: a deleted recipe cannot be restored, which is why deletion asks for confirmation.
- Embeddings (S-019), the cart (S-022) and the chat (S-030) do not exist yet. This feature does not create their data. PRD says that editing re-embeds and that deleting removes cart and search entries and shows "recipe removed" on past citations; those behaviors are delivered by the stories that create the data, against FR-016 here.
- The conflict check on save (FR-011) is the minimum protection against silent overwrites; it does not merge two people's edits.
- Deleting a recipe keeps the notebook's catalog as is; renaming and merging ingredient names belong to S-043.
- The PDF button, "Copy to notebook" and "Add to cart" shown on the PRD's detail are separate stories (S-028, S-048, S-022) and are not part of this detail page until they are built.
