# Feature Specification: Catalog Management (rename and merge ingredient names)

**Feature Branch**: `043-catalog-rename-merge` (story S-043)

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Backlog S-043, PRD. I want bilingual users to be able to merge ingredient names that are written in different languages."

**Related**: Backlog S-043. PRD J3 "Catalog management" (*Should*), Appendix A (Ingredient: rename, merge, delete only if unused, `409` if used), 1.6 (one catalog per notebook). Builds on spec 018 (catalog matching), spec 056 (notebooks and access), spec 070 (the "Ingredients" catalog page and each person's places, whose FR-013 left rename, merge and delete to this story), spec 025 (saved shopping list) and spec 027 (recipe edit and its edit lock). Out of this feature: copying a recipe (S-048), automatic translation of names, and categories (S-061).

## Clarifications

### Session 2026-11-06

- Q: When "cebolla" is merged into "onion", what does a Spanish recipe that said "cebolla" show? → A: A recipe's language is part of its metadata; each line shows the name variant in the recipe's language ("cebolla" in a Spanish recipe, "onion" in an English one).
- Q: Does one merge apply to every notebook the person can write to that has both names, or only to the picked notebook? → A: Every notebook the person can write to that has both names, all at once.
- Q: Which name does the shopping list show for an ingredient with an English and a Spanish name? → A: The name in the viewer's interface language, or the kept name when there is none.
- Q: Should the app suggest likely cross-language pairs for the person to confirm? → A: Yes: a "Suggest pairs" action on the Ingredients page asks the model for likely pairs; the person accepts or dismisses each, and nothing changes without that.
- Q: How do recipes saved before this story get a language? → A: The AI model detects each existing recipe's language once, when the story ships; anyone who can edit the recipe can correct it. (Refined in /speckit-analyze, 2026-11-06: the model only proposes; a person applies the proposal, constitution principle 5.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge two names, also across languages (Priority: P1)

A bilingual couple captures some recipes in Spanish and some in English, so one notebook's catalog has both "cebolla" and "onion", and the shopping list shows two lines for the same thing. A member who can write to the notebook opens the Ingredients page, picks "cebolla", chooses Merge and picks "onion" as the name to keep. After a confirmation that says how many recipes use "cebolla", the two names are one ingredient: the shopping list adds them up on one "onion" line, "cebolla" no longer shows as a separate entry, and a later Spanish capture that says "cebollas" is matched to the same ingredient instead of adding "cebolla" back.

**Why this priority**: It is the reason for the story. Names in two languages split the shopping list, and the fixed matching rule of S-018 never joins "cebolla" and "onion" on its own.

**Independent Test**: In a notebook whose recipes use "cebolla" (one recipe) and "onion" (another), merge "cebolla" into "onion"; add both recipes to the cart and see one "onion" line with the summed amount; capture a Spanish recipe with "cebollas" and see it matched, listed as a change, with no new name proposed.

**Acceptance Scenarios**:

1. **Given** a notebook the member can write to whose catalog has "cebolla" and "onion", **When** the member merges "cebolla" into "onion" and confirms, **Then** the catalog shows one ingredient with two name variants, "onion" (English) and "cebolla" (Spanish).
2. **Given** that merge, **When** the confirmation is shown, **Then** it names both names and lists every notebook the member can write to that has both, with the number of recipes in each that use the name being merged, before anything changes.
3. **Given** that merge, **When** recipes that used "cebolla" and "onion" are in the cart, **Then** the shopping list shows one line for the ingredient, with the amounts added up by the existing consolidation rules, named "onion" for a member whose interface is English and "cebolla" for one whose interface is Spanish.
4. **Given** that merge, **When** a member captures, edits or copies a recipe into the notebook with "cebolla" or "cebollas", **Then** the line is matched to the onion ingredient and the change "cebollas → cebolla" (in a Spanish recipe) is listed for the member before save, as other catalog matches are (S-018).
5. **Given** that merge, **When** someone opens a Spanish recipe, **Then** the line reads "cebolla"; in an English recipe it reads "onion", even if that recipe was captured with "cebolla".
6. **Given** a merge, **When** the confirmation is shown, **Then** it shows the language of each name (prefilled from the recipes that use it) and the person can correct it before confirming.
7. **Given** a member who can only read the notebook, **When** they open the Ingredients page, **Then** they see the names but no rename, merge or delete action for that notebook.

---

### User Story 2 - Rename a name (Priority: P1)

A member finds a typo, "tomatoe", or wants a clearer name, "red pepper" to "red bell pepper". They rename it; every recipe line in the notebook that used it now shows the new name, and the shopping list follows.

**Why this priority**: The most common clean-up, and the simplest; it shares the confirmation and the recipe update with merge.

**Independent Test**: Rename "tomatoe" to "tomato" in a notebook where two recipes use it and "tomato" is not yet in the catalog; open both recipes and the cart and see "tomato".

**Acceptance Scenarios**:

1. **Given** a name in a notebook the member can write to, **When** they rename it to a name not in the catalog, **Then** the catalog has the new name, every recipe line in that notebook that used the old name uses the new one, and the old name is gone.
2. **Given** a new name that is already in the catalog, or is the same name under the S-018 rules (for example "tomatoes" when "tomato" exists), **When** the member renames, **Then** the app tells them the name exists and offers to merge into it instead.
3. **Given** a new name that is empty or only spaces after trimming, **When** the member saves, **Then** it is refused with a message and nothing changes.
4. **Given** a rename, **When** saved, **Then** the new name is stored normalized (trimmed, lower-case, singular when the S-018 rules give a singular) and the member sees the stored form.
5. **Given** "garlic" with no language, **When** the member sets it to English, **Then** it is saved and later merges prefill English.

---

### User Story 3 - Delete an unused name (Priority: P2)

A name was added by a recipe that was later deleted, so no recipe uses it. A member deletes it to keep the list short. A name that is still used cannot be deleted; the app says how many recipes use it and offers merge instead.

**Why this priority**: Clean-up that matters less than merging; spec 027 left unused names in the catalog on purpose for this story.

**Independent Test**: Delete a recipe that was the only user of "saffron", then delete "saffron" from the catalog; try to delete "onion", which two recipes use, and see it refused with the count and a merge offer.

**Acceptance Scenarios**:

1. **Given** a name no recipe in the notebook uses, **When** the member deletes it and confirms, **Then** it is removed from the catalog.
2. **Given** a name that recipes in the notebook use, **When** the member tries to delete it, **Then** it is refused, the number of recipes using it is shown, and merge is offered.

---

### User Story 4 - See other names and split one back out (Priority: P3)

A member opens an ingredient and sees its other names: its name variant per language ("onion" English, "cebolla" Spanish) and any alternative spellings. If a merge was a mistake, they split one other name back out into its own ingredient.

**Why this priority**: Recovery from a wrong merge; useful, but the first stories work without it.

**Independent Test**: After merging "cebolla" into "onion", split "cebolla" back out; the Spanish recipe still reads "cebolla", the shopping list shows two lines again, and a new capture with "cebolla" matches the split-out ingredient.

**Acceptance Scenarios**:

1. **Given** an ingredient with other names, **When** the member opens it, **Then** each name variant is listed with its language, and each alternative spelling is listed.
2. **Given** a name variant, **When** the member splits it out and confirms, **Then** it becomes its own catalog ingredient again, and the lines of recipes in that variant's language that showed it now refer to the new ingredient; no recipe shows different text than before the split.
3. **Given** an alternative spelling, **When** the member splits it out, **Then** it becomes its own catalog ingredient and saved recipe lines are not changed.

---

### User Story 5 - Suggested cross-language pairs (Priority: P2)

A bilingual member has a long catalog with names in both languages. On the Ingredients page they press "Suggest pairs". The app lists likely pairs of the same ingredient in English and Spanish ("ajo" and "garlic", "harina" and "flour"). For each pair the member accepts, picks the name to keep and goes through the normal merge confirmation, or dismisses it.

**Why this priority**: Finding the pairs is the slow part of cleaning a bilingual catalog; merging (User Story 1) works without it.

**Independent Test**: In a notebook with "ajo", "garlic", "harina" and "flour", press "Suggest pairs" and see both pairs; accept one and see the merge confirmation; dismiss the other, press "Suggest pairs" again and see it not offered.

**Acceptance Scenarios**:

1. **Given** the chosen notebook's catalog, **When** the member presses "Suggest pairs", **Then** the app lists likely pairs of one English and one Spanish name of that catalog, each with accept and dismiss.
2. **Given** a suggested pair, **When** the member accepts it, **Then** the merge confirmation of User Story 1 opens with the pair prefilled; nothing changes until they confirm there.
3. **Given** a suggested pair, **When** the member dismisses it, **Then** it is not suggested again for that notebook.
4. **Given** the model is unavailable or returns nothing usable, **When** the member presses "Suggest pairs", **Then** the app says no suggestions could be made and manual merge still works.

---

### Edge Cases

- Merging a name into itself, or into one of its own other names, is not offered.
- Merging A into B when A already has other names: each joins B as a variant of its language; when B already has a variant in that language, the incoming name becomes an alternative spelling of B.
- Two members merge or rename the same name at the same time: the second action finds the name gone and is told to reload; nothing is half done.
- A recipe is open in edit (spec 027 edit lock) during a merge or rename: the merge goes ahead; when the editor saves a line with the old name, it is matched to the kept name like any other line, and the change is listed before save. If the save lands at the same moment as the merge, it may add the merged name back as its own catalog entry; a second merge fixes it, and nothing else is lost.
- A name is renamed to a name that is an other name of another ingredient: treated as that entry already existing (User Story 2, scenario 2).
- The person's place for the merged name (spec 070) differs from their place for the kept name: the kept name's place stays; when the person had set a place only for the merged name, it moves to the kept name, for each person, so nobody loses a choice.
- Active shopping list (spec 025): its cart-based lines follow the change on the next cart save; hand-added items and closed lists keep the text they had (history is not rewritten), so they are not shown in the viewer's language.
- The same pair ("cebolla", "onion") in several notebooks: one merge applies to every notebook the person can write to whose catalog has both names (FR-002a). Notebooks they can only read, and notebooks with only one of the two names, are not changed.
- A notebook in the set loses one of the two names between the confirmation and the save (someone else renamed it): that notebook is skipped and the result says so; the others are merged.
- A recipe whose fallback or applied language is wrong: anyone who can edit it changes the language, and its lines show the other variants at once; no name is changed.
- A snapshot (spec 035) copies the catalog with its other names; a later merge in the original or the copy does not reach the other.
- A person joins a personal notebook (spec 057): names in their catalog that match an other name of the notebook's catalog are not added.

## Requirements *(mandatory)*

### Functional Requirements

#### Who and where

- **FR-001**: A person who can write to a notebook (its owner or members for a personal notebook, any member of the kitchen for a kitchen notebook) MUST be able to rename, merge and delete names in that notebook's catalog. A person who can only read MUST NOT; a person with no access gets a not-found answer, as elsewhere.
- **FR-002**: A rename and a delete MUST act on one notebook's catalog and that notebook's recipes only. The Ingredients page (spec 070) MUST let the person choose a notebook they can read and show its catalog; rename, merge, delete, split and Suggest pairs appear only for notebooks they can write to.
- **FR-002a**: A merge MUST apply to every notebook the person can write to whose catalog has both names (the same names under the S-018 rules), personal and kitchen notebooks alike. The confirmation lists them (FR-004). Each notebook's merge is complete or not done at all (FR-015); the result lists any notebook that was skipped and why.

#### Merge

- **FR-003**: A merge MUST start from one name to merge and one name to keep in the chosen notebook's catalog, with no rule about language: any two names may be merged. It then applies to every notebook in FR-002a.
- **FR-004**: Before a merge, the app MUST show both names and, per notebook in the set (FR-002a), the number of recipes that use the merged name, and MUST change nothing until the person confirms.
- **FR-005**: After a merge, the two names MUST be one catalog ingredient. When their languages differ, each becomes that ingredient's name variant for its language (at most one variant per language). When they share a language, the kept name is the variant and the merged name is recorded as an alternative spelling.
- **FR-005a**: Every recipe MUST have a language (English or Spanish) in its metadata, set at capture from the text, shown on the recipe and editable by anyone who can edit the recipe. Recipes saved before this story MUST get a fallback language: the kitchen's content language for a kitchen notebook, or the author's account language for a personal one (Spanish when neither is set). The AI model then proposes a language for each one once; when the proposal differs from the stored language, the recipe page shows "Detected: {language}. Apply?" to anyone who can edit the recipe. Nothing changes until they apply it, and dismissing it removes the proposal.
- **FR-006**: A recipe line MUST show the ingredient's name variant in the recipe's language. When the ingredient has no variant in that language, the line shows the kept name. Changing a recipe's language changes which variant its lines show.
- **FR-007**: The shopping list (spec 023 and 025) MUST add up lines of an ingredient's names as one ingredient. Each viewer MUST see the line under the ingredient's name variant in their interface language, or the kept name when there is none; two members may see the same line under different words. Sorting follows the name each viewer sees.
- **FR-007a**: A person's place for an ingredient (spec 070) MUST apply under any of its names, so the store tabs put the line in the same place whichever name the viewer sees.
- **FR-008**: Catalog matching at capture, edit, copy and notebook join (S-018, spec 027, S-048, spec 057) MUST treat an other name (name variant or alternative spelling), and its singular and plural forms under the S-018 rules, as the ingredient it belongs to, and MUST list each such match for the person before save, as other matches are. The listed change MUST show the name the line will show in the recipe's language ("cebollas → cebolla" in a Spanish recipe, "cebollas → onion" in an English one), not the kept name, unless the two are the same.
- **FR-009**: Each person's place for a name (spec 070) MUST carry over in a merge: a person who set a place for the merged name and none for the kept name gets that place for the kept name; any other choice is unchanged.

#### Suggested pairs

- **FR-009a**: The Ingredients page MUST offer a "Suggest pairs" action for the chosen notebook to a person who can write to it. It asks the AI model for likely pairs of one English and one Spanish name of that catalog that are the same ingredient, and lists them.
- **FR-009b**: The app MUST drop any suggested pair whose names are not both in the catalog, are already one ingredient, or were dismissed in that notebook, before showing the list.
- **FR-009c**: Accepting a pair MUST open the merge confirmation (FR-002a, FR-004) prefilled with the pair; a suggestion MUST NOT change anything by itself (constitution principle 5).
- **FR-009d**: Dismissing a pair MUST be remembered for that notebook so the pair is not suggested again.

#### Rename

- **FR-010**: A rename MUST store the new name normalized (trimmed, lower-case, singular when the S-018 rules give one) and change every recipe line in the notebook that used the old name to the new name.
- **FR-011**: A rename to a name that is already in the catalog, or is an other name there, or is the same name under the S-018 rules, MUST be refused with an offer to merge into that name.
- **FR-012**: A rename MUST keep the ingredient's other names and each person's place for it (spec 070 places move to the new name). The person MAY also set or change the language of a kept name (English, Spanish or none) without renaming it; this changes no recipe line.

#### Delete and other names

- **FR-013**: Deleting a name that any recipe in the notebook uses (under any of its names) MUST be refused with the number of recipes and an offer to merge. Deleting an unused name MUST ask for confirmation and then remove it with its other names.
- **FR-014**: The person MUST be able to see an ingredient's other names and split one back out into its own ingredient after a confirmation (User Story 4). A split MUST change no recipe's shown text.

#### Integrity and display

- **FR-015**: Every rename, merge and delete MUST either finish completely or change nothing; when the name was changed by someone else first, the person MUST be told to reload.
- **FR-016**: Closed shopping lists and hand-added shopping list items MUST keep the text they had; the active list's cart-based lines follow the change on the next cart save.
- **FR-017**: Every action MUST be in English and Spanish, usable by keyboard and announced by screen readers, at 360 px and 1280 px.

### Key Entities

- **Catalog ingredient** (existing `ingredient`, extended): one ingredient in one notebook's catalog, with a kept name and at most one name variant per language.
- **Name variant** (new): the ingredient's name in one language (English or Spanish), unique in the catalog.
- **Other names**: an ingredient's name variants and alternative spellings, apart from its kept name.
- **Alternative spelling** (new): another name in the same language recorded under an ingredient, from a same-language merge; unique in the catalog and only used for matching.
- **Recipe** (existing, extended): gains a language (English or Spanish).
- **Recipe line** (existing): refers to a catalog ingredient and shows its variant in the recipe's language (FR-006); a rename changes what it shows.
- **Dismissed pair** (new): a pair of names in one notebook's catalog that a person marked as not the same ingredient, so it is not suggested again.
- **Ingredient place** (existing, spec 070): one person's place for one name; carried over by rename and merge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member merges two names in at most 4 taps from the Ingredients page, confirmation included.
- **SC-002**: After merging two names in different languages, adding recipes that use either name gives one shopping list line in every test case.
- **SC-003**: After a merge, a new capture that uses the merged name (singular or plural) proposes no new catalog name in every test case.
- **SC-004**: A rename in a notebook with 200 recipes, or a merge across 10 notebooks with 200 recipes in all, finishes and shows its result in under 2 s on the dev stack.
- **SC-005**: No rename, merge or delete leaves a recipe line that does not refer to an ingredient of the notebook's catalog.
- **SC-006**: For a catalog of 300 names, the suggested pairs appear in under 10 s on the dev stack, and in the AI evaluation set at least 8 of 10 suggested pairs are real pairs.

## Assumptions

- The app never merges names on its own: the model only suggests pairs (User Story 5) and the person decides. Suggestions cover English and Spanish only, the two languages the app supports. Suggesting a pair at capture time is out of scope.
- The kept name is the one the person picks; it is the name shown where no language applies (the catalog list, and a recipe whose language has no variant).
- The one-time language proposal for existing recipes (FR-005a) runs once per recipe and is not repeated; a recipe written in both languages gets the one most of its text is in.
- The fixed S-018 singular and plural rules still apply; other names add to them, they do not replace them.
- Other names are kept per notebook catalog and travel with snapshots (spec 035), like the catalog itself.
- The Ingredients page of spec 070 is the place for these actions; its per-person places are unchanged by this story except as FR-009 and FR-012 say.
- The recipe embeddings (S-019) are refreshed for recipes whose lines change, when embeddings exist.
- This story lifts no MVP-era rule.
