# Feature Specification: Add a personal notebook to a kitchen as a snapshot

**Feature Branch**: `035-notebook-snapshot`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "@../dev/docs/backlog.yaml @../dev/docs/prd.md S-035"

**Backlog story**: S-035 (Must). **PRD**: §1.5 flow H, §1.6, J1a, J3 "Add to a kitchen", AC1a.4.

## Summary

A personal notebook is private and is never shown in a kitchen. A kitchen member who wants to bring their recipes into a kitchen adds one of their personal notebooks to it as a **snapshot**: a new kitchen notebook holding independent copies of its recipes and its ingredient catalog, labelled with the notebook it came from. Every member of the kitchen can then use those recipes. From that moment the two notebooks never sync.

## Clarifications

### Session 2026-11-01

- Q: Who can add a personal notebook to a kitchen as a snapshot: only its owner, or also the people who joined it as members? → A: Only the notebook's owner.
- Q: When someone adds a snapshot to a kitchen where they don't yet have their own kitchen notebook, where should their next capture go by default? → A: A kitchen notebook of their own is created on first capture, as today; the snapshot is used only if they pick it.
- Q: What should happen when someone adds a personal notebook to a kitchen that already has a snapshot of it? → A: It is allowed, after a warning that the kitchen already has a snapshot of that notebook and a confirmation.
- Q: Should choosing a notebook add it straight away, or should the person first confirm that everyone in the kitchen will see a copy? → A: Choosing a notebook adds it straight away; a confirmation appears only for the repeat warning.
- Q: When is a member's own kitchen notebook created on first capture? → A: When they submit the capture, before extraction. It stays even if no recipe is saved.
- Q: How does a member find a new snapshot? → A: A notebooks icon next to the share icon in the kitchen's chrome replaces the recipe body with the kitchen's notebook cards, using the same ui as the Notebook tab. The recipe page stays free of notebook cards.
- Q: Does the side panel's recipe count include snapshot notebooks? → A: No. A snapshot doesn't raise the count, and recipes later captured into a snapshot aren't counted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bring my notebook into a kitchen (Priority: P1)

Ana keeps recipes in her personal notebook and shares a kitchen with Ben. From the kitchen, she picks her notebook and adds it. The kitchen now has a new notebook with copies of all her recipes, and Ben can see and use them.

**Why this priority**: This is the only way a whole personal notebook reaches a kitchen. Without it, Ana must capture every recipe again. It delivers the story's value alone.

**Independent Test**: With two accounts in one kitchen, add a personal notebook holding several recipes. Sign in as the other member and confirm the recipes appear in the kitchen, open fully, and can go into the cart.

**Acceptance Scenarios**:

1. **Given** Ana is a member of kitchen Home and owns a personal notebook with 3 recipes, **When** she adds it to Home, **Then** Home has one new kitchen notebook with the same name and copies of all 3 recipes, and she sees that it was added.
2. **Given** that snapshot exists, **When** Ben, another member of Home, opens the kitchen, **Then** he sees the copied recipes, each with its original author, ingredients, steps, servings and source link.
3. **Given** that snapshot exists, **When** any member of Home adds a copied recipe to the cart, edits it, deletes it, renames the snapshot or deletes it, **Then** it works as for any other kitchen notebook.
4. **Given** Ana's personal notebook has a catalog with names no recipe uses, **When** she adds it, **Then** the snapshot's catalog holds every name of the original's catalog, unchanged, and no recipe's ingredient names change.
5. **Given** Ana owns two personal notebooks, **When** she opens the choice of notebooks in Home, **Then** she sees those two and no others.
6. **Given** a snapshot with no recipes, **When** any member of Home opens the kitchen's notebooks view, **Then** the notebook appears as a card that links to its page.

---

### User Story 2 - The two notebooks stay independent (Priority: P1)

After the snapshot, Ana keeps changing her personal recipes and the kitchen changes its copies. Neither change reaches the other side.

**Why this priority**: Independence is the defining rule of a snapshot (AC1a.4) and protects each side from the other's edits.

**Independent Test**: Edit one recipe in the original and a different one in the snapshot, add and delete recipes on both sides, then compare both notebooks.

**Acceptance Scenarios**:

1. **Given** a snapshot, **When** a recipe is edited in the original, **Then** its copy in the snapshot does not change, and the same holds the other way round.
2. **Given** a snapshot, **When** a recipe is added to or deleted from either notebook, **Then** the other notebook does not change.
3. **Given** a snapshot, **When** a name is added to either catalog, **Then** the other catalog does not change.
4. **Given** a snapshot, **When** the kitchen is deleted, **Then** the snapshot goes with it and the original is not touched.
5. **Given** a snapshot, **When** Ana leaves the kitchen, **Then** she loses access to the snapshot, the snapshot stays in the kitchen unchanged, and her personal notebook is not touched.

---

### User Story 3 - See where a snapshot came from (Priority: P2)

Members of the kitchen can tell that a notebook is a snapshot and which notebook it came from.

**Why this priority**: The label helps people understand why a notebook exists, but the recipes are usable without it.

**Independent Test**: Open a snapshot as a kitchen member who has no access to the original and check the label. Delete the original and check that the label is gone and the recipes stay.

**Acceptance Scenarios**:

1. **Given** a snapshot of "Ana's Notebook", **When** a kitchen member opens that notebook's page, **Then** it is labelled as coming from "Ana's Notebook".
2. **Given** Ben cannot access the original, **When** he sees the label, **Then** he sees only the name, with no way to open the original, and asking for the original directly answers "not found".
3. **Given** a snapshot, **When** the original is deleted, **Then** the label disappears and the snapshot keeps its recipes and catalog.
4. **Given** a kitchen notebook that is not a snapshot, **When** a member sees it, **Then** it shows no origin label.

---

### Edge Cases

- **Empty notebook**: a personal notebook with no recipes can be added. The snapshot has no recipes and has a copy of the catalog.
- **Adding the same notebook twice**: allowed after a warning and a confirmation (FR-008a). Each time makes a new, separate snapshot of the notebook as it is then. An earlier snapshot is not refreshed or replaced. If the earlier snapshot was deleted, or its label was cleared, no warning is shown.
- **Same name**: notebook names are not unique, so a snapshot can share its name with another notebook in the kitchen.
- **Language**: the snapshot keeps the original's name as written. It is not translated.
- **Archived kitchen**: no notebook can be added. The action is not shown, and a direct attempt is refused.
- **Not a member of the kitchen**: answered "not found", so the answer does not reveal that the kitchen exists.
- **Someone else's personal notebook, or a kitchen notebook, as the source**: refused, answered "not found" where the person cannot see it. This includes a personal notebook the person only joined as a member. A snapshot cannot be made from a kitchen notebook, so a kitchen cannot copy another kitchen's notebook this way.
- **Original deleted, or kitchen left, while choosing**: the add fails with a clear message and nothing is created.
- **Recipe being edited**: the snapshot copies the last saved version. Unsaved edits are not copied and the editor's lock is not affected.
- **Deleted author**: a recipe whose author reads "unknown" still reads "unknown" in the copy.
- **Failure part way**: nothing is created. The kitchen never holds a partial snapshot, and the person can try again.
- **Double press**: one press makes one snapshot. The action cannot be pressed again while it runs.
- **Original renamed**: the label shows the original's current name; the snapshot's own name does not change.

## Requirements *(mandatory)*

### Functional Requirements

**Adding a snapshot**

- **FR-001**: A member of a kitchen, of any role, MUST be able to start adding a notebook from the kitchen's notebooks view (FR-007a).
- **FR-002**: The person MUST choose from the personal notebooks they own. Personal notebooks they only joined as a member, kitchen notebooks and other people's notebooks MUST NOT be offered or accepted (spec 056 FR-003).
- **FR-002a**: Choosing a notebook MUST add it straight away, with no confirmation step unless the repeat warning applies (FR-008a).
- **FR-003**: Adding MUST create one new kitchen notebook in that kitchen, named exactly as the original at that moment. The person who added it is recorded as the notebook's owner (spec 056 FR-002).
- **FR-004**: The action MUST be refused in an archived kitchen, and the control MUST NOT be shown there.
- **FR-005**: A person who is not a member of the kitchen, or who cannot see the source notebook, MUST get "not found", and nothing about either may be revealed.
- **FR-006**: Adding MUST be all or nothing. On any failure, nothing is created and the person sees a plain message and can try again.
- **FR-007**: The person MUST see that the action is running, and on success MUST see that the notebook was added and find it in the kitchen without reloading.
- **FR-007a**: A notebooks icon next to the share icon in the kitchen's chrome MUST open a view that replaces the recipe body with the kitchen's notebooks as cards, in the same ui as the Notebook tab. It MUST include empty notebooks, work in archived kitchens, and link each card to the notebook's page. The kitchen's recipe page MUST keep showing no notebook cards.
- **FR-008**: Two presses of the same action MUST NOT make two snapshots. Adding the same notebook again as a separate, later action MUST make a new snapshot, subject to FR-008a.
- **FR-008a**: When the kitchen already has a snapshot labelled as coming from the chosen notebook, the person MUST see a warning saying so and MUST confirm before a new snapshot is made. Cancelling MUST create nothing.

**What is copied**

- **FR-009**: Every recipe of the original MUST be copied as last saved: title, base servings, the "estimated" flag, ingredient lines in order (name, quantity, unit, size, preparation, vague note), steps in order and source link. Preview images are deferred: recipes have no preview image yet (see Assumptions).
- **FR-010**: Each copy MUST keep the original recipe's author, including an "unknown" author.
- **FR-011**: The whole catalog of the original MUST be copied, including names no recipe uses. Recipe ingredient names MUST stay exactly as they are; no name is changed and no confirmation is asked (PRD flow G).
- **FR-012**: A copied recipe MUST start with a cart count of zero and MUST NOT be added to any cart.
- **FR-013**: The copy MUST be a recipe of the kitchen like any other: readable and writable by every kitchen member while they belong to the kitchen, and part of the kitchen's lists and cart. When recipe search and the assistant exist (S-019, S-030), copied recipes MUST be part of them.
- **FR-014**: No AI step may run as part of adding a snapshot.

**Independence**

- **FR-015**: After the snapshot, no change to the original (its name, recipes or catalog) may change the snapshot's recipes, catalog or name, and no change to the snapshot may change the original.
- **FR-016**: The original MUST NOT show that it has been snapshotted, and its members MUST NOT gain any access to the kitchen. Kitchen members MUST NOT gain any access to the original.
- **FR-017**: A snapshot MUST NOT change where a member's captures go by default. A person's own kitchen notebook stays their default capture target, and it is created when they submit their first capture, even if they have added a snapshot. It is kept even if extraction fails or the draft is abandoned. A snapshot is used for capture only when explicitly picked.
- **FR-018**: A snapshot MUST behave as any other kitchen notebook for rename, delete and the end of kitchen membership, and MUST be deleted with its kitchen. The original MUST NOT be touched by any of these.

**Origin label**

- **FR-019**: A snapshot MUST record the notebook it came from as a label only, and MUST show that label, with the original's current name, to kitchen members wherever the kitchen's notebook is shown by name on its own page.
- **FR-020**: The label MUST NOT link to the original or give any access to it.
- **FR-021**: When the original is deleted, the label MUST be cleared and the snapshot MUST keep its recipes and catalog.
- **FR-022**: A kitchen notebook that is not a snapshot MUST show no label.

**Side panel**

- **FR-025**: The side panel's count of recipes a person added MUST leave out every recipe in a snapshot notebook, so adding a snapshot does not raise it. This includes recipes later captured into a snapshot, because nothing marks a recipe as a copy.

**Language and access**

- **FR-023**: All new text MUST exist in English and Spanish, following the account's language.
- **FR-024**: The flow MUST work with a keyboard, at phone and desktop width, and announce its result to screen readers.

### Key Entities

- **Personal notebook (the original)**: the source. Read, never changed.
- **Snapshot**: a kitchen notebook made from an original. Same as any kitchen notebook, plus an optional origin label naming the original. Not stored as a separate kind of thing.
- **Origin label**: a reference from the snapshot to the original, for display only, cleared when the original is deleted.
- **Copied recipe**: a full, independent recipe in the snapshot that keeps its author and has no link to the recipe it came from.
- **Catalog**: the snapshot's own set of ingredient names, starting as a copy of the original's.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A kitchen member can add a personal notebook in 4 steps or fewer from the kitchen: open the notebooks view, start, choose, see the result. One more step is added only when a repeat warning applies.
- **SC-002**: A notebook of 100 recipes is added in under 5 seconds on the deployed server.
- **SC-003**: For a sample of notebooks, including one with vague amounts, sizes and source links, 100% of the recipes and catalog names match the original when compared field by field.
- **SC-004**: In a test that edits, adds and deletes on both sides, 0 changes reach the other notebook (AC1a.4).
- **SC-005**: A failure forced at any point of the add leaves 0 new notebooks, recipes or catalog names.
- **SC-006**: In access tests, 100% of attempts by non-members, from archived kitchens, or from notebooks the person does not own are refused and create nothing.

## Assumptions

- **Owner only** (FR-002, decided 2026-11-01): a snapshot exposes the whole notebook to a kitchen, so the decision stays with the owner, as in spec 056 FR-003. The PRD's "their personal notebooks" is read this way. Notebook members can't be added yet (S-057), so nobody is affected today.
- **Name**: the snapshot takes the original's name. The PRD gives no name for snapshots, and the origin label plus a later rename cover the rest. The generated "{alias}'s ({kitchen name}) Notebook" name is only for notebooks made with a kitchen or on a first capture.
- **Capture default** (FR-017): a snapshot records the person who added it as its owner, so implementation must make sure it isn't taken for that person's own kitchen notebook.
- **Repeat snapshots** (FR-008a, decided 2026-11-01) are how a kitchen gets newer recipes, because the two sides never sync, so they are allowed with a warning rather than refused.
- **Archived kitchens** refuse snapshots, matching the rule for capture.
- **Label name**: the label reads the original's current name, since only a reference is stored. Kitchen members see it only while the snapshot exists, and it reveals nothing but the name.
- **Picker**: the choice loads the person's default notebook before their list, as the Notebook tab does, because someone who never opened that tab has no default yet. It then offers the rows of kind personal that they own (research R10).
- **Reuse**: copying uses the same steps planned for recipe copy (S-048, flow G). Since S-048 isn't built, this feature delivers the shared copy step.
- **Search**: recipe embeddings (S-019) don't exist yet. S-019 must include copied recipes.
- **Rename and delete** of kitchen notebooks by hand come from S-059. Until then, FR-018 covers what the app offers. The label is cleared by deletion of the original, which reaches users through S-059 as well.
- **Leaving a kitchen**: no route lets a member leave yet, so US2 scenario 5 and that part of FR-018 are checked by removing the membership row in an integration test.
- **Preview images**: `recipe` has no preview image column yet, so there is nothing to copy. Whoever adds the column must add it to the copy step and to SC-003's comparison.
- **Same names in lists**: repeat snapshots share a name, so they look alike in the notebooks view, the capture picker and recipe cards. The label appears only on the notebook's own page in v1.
- **Schedule**: S-035 is a Must and the delivery date is 02/11/2026.
- **Out of scope**: refreshing a snapshot from its original, choosing some recipes only (S-048 copies one), snapshots of kitchen notebooks, moving a kitchen notebook back to a personal one, telling the original's owner or members about a snapshot, and notebook invites (S-057).
