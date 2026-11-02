# Feature Specification: Create, rename and delete notebooks

**Feature Branch**: `worktree-059-notebook-rename`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "@dev/docs/prd.md @dev/docs/backlog.yaml 059"

**Related**: Backlog S-059. PRD 1.5 flow H, 1.6 (`notebook`), J1a, section 3 (roles), Appendix A (Notebook). Builds on spec 056 (notebooks), spec 035 (snapshots), spec 057 (notebook invites and creating a personal notebook) and spec 022 (a cart entry and an edit lock go with their recipe). Out of this feature: copying a recipe (S-048), renaming or merging catalog names (S-043), changing which notebook is the default.

## User Scenarios & Testing *(mandatory)*

Creating a personal notebook already works (spec 057). This feature adds the rest of notebook management: renaming, deleting, and adding an empty kitchen notebook.

### User Story 1 - Rename a notebook (Priority: P1)

Generated names such as "Ana's (Home) Notebook" are long and do not say what is inside. The person who manages a notebook gives it a name that does. The owner of a personal notebook can rename it. Any member of a kitchen can rename any of that kitchen's notebooks, snapshots included.

**Why this priority**: It is the most frequent need and the smallest change. It also fixes names that still carry a former owner's alias (spec 058).

**Independent Test**: Rename a personal notebook as its owner and a kitchen notebook as a kitchen member. Check that the new name shows wherever the notebook is listed, for every person who can see it, and that its recipes are unchanged.

**Acceptance Scenarios**:

1. **Given** Ana owns a personal notebook, **When** Ana renames it from its page, **Then** the new name shows on its page and in the notebook lists of Ana and its members.
2. **Given** Ben is a member of a kitchen, **When** Ben renames one of its notebooks, **Then** every member of the kitchen sees the new name.
3. **Given** Ben is a member of Ana's personal notebook but not its owner, **When** Ben opens it, **Then** Ben has no rename action, and a direct attempt is refused and changes nothing.
4. **Given** a name that is empty or only spaces, **When** the person saves it, **Then** they see a plain message, what they typed stays in the box, and the notebook keeps its name. The name box stops at the limit, so a name over it reaches only a direct request, which is refused and changes nothing.
5. **Given** a personal notebook that has a snapshot in a kitchen, **When** the owner renames it, **Then** the snapshot's label shows the new name and the snapshot's own name does not change.
6. **Given** an archived kitchen, **When** a member opens one of its notebooks, **Then** there is no rename action, and a direct attempt is refused.

---

### User Story 2 - Delete a notebook (Priority: P2)

A person clears out a notebook that is no longer needed. The owner of a personal notebook can delete it, which is also the only way for an owner to step away from it. Any member of a kitchen can delete any of that kitchen's notebooks. Deleting removes the notebook, its recipes and its catalog, so the person first sees what will be lost and confirms.

**Why this priority**: It destroys data, so it needs more care than renaming, and it depends on the cases below being right. It comes after rename because rename delivers value without it.

**Independent Test**: Put recipes from a kitchen notebook in the cart and on the active shopping list, delete the notebook, and check the kitchen's lists, cart and shopping list. Delete a personal notebook that has a member, a pending invite and a snapshot, and check each of them.

**Acceptance Scenarios**:

1. **Given** Ana owns a notebook with 12 recipes and 2 members, **When** Ana chooses Delete, **Then** a confirmation names the notebook, the 12 recipes and the 2 members who will lose access, and nothing is deleted until Ana confirms.
2. **Given** that confirmation, **When** Ana cancels, **Then** nothing changes.
3. **Given** Ana confirms, **When** the deletion finishes, **Then** the notebook, its recipes and its catalog are gone, Ana lands on their notebooks list, and the members get "not found" for it.
4. **Given** a kitchen notebook with recipes in the cart, **When** any kitchen member deletes it, **Then** those recipes leave the kitchen's list, cart and search, and the rest of the cart is unchanged (spec 022).
5. **Given** a notebook that has been snapshotted into a kitchen, **When** the owner deletes it, **Then** the snapshot keeps its recipes and catalog and loses its label (spec 035 FR-021).
6. **Given** a snapshot in a kitchen, **When** a kitchen member deletes it, **Then** the original personal notebook is not touched, and adding that original again gives no repeat warning (spec 035).
7. **Given** Ben is a member of Ana's notebook but not its owner, **When** Ben opens it, **Then** Ben has no delete action, and a direct attempt is refused and changes nothing.
8. **Given** Ana deletes their default notebook, **When** Ana next opens their notebooks, **Then** a new, empty default notebook is there, and the confirmation said so before the deletion.
9. **Given** a kitchen's only notebook, **When** a member deletes it, **Then** it is deleted, and the next member who opens the kitchen's notebooks gets a new, empty one named after them (spec 056 FR-008a).
10. **Given** an archived kitchen, **When** a member opens one of its notebooks, **Then** there is no delete action, and a direct attempt is refused.

---

### User Story 3 - Add an empty kitchen notebook (Priority: P3)

A kitchen wants separate notebooks, such as "Weeknight" and "Holidays", without copying anything in. Any member of the kitchen adds an empty kitchen notebook by giving it a name. The way to create a personal notebook does not change.

**Why this priority**: A kitchen already gets notebooks through first capture and snapshots, so this is a convenience.

**Independent Test**: As a kitchen member, add a notebook from the kitchen's notebook list, and check that every member sees it and can capture into it.

**Acceptance Scenarios**:

1. **Given** Ben is a member of an active kitchen, **When** Ben adds a notebook named "Holidays", **Then** it is listed for every member of the kitchen, with no recipes, and Ben lands on its page.
2. **Given** a person who is not a member of the kitchen, **When** they try to add a notebook to it, **Then** they get "not found" and nothing is created.
3. **Given** an archived kitchen, **When** a member opens its notebooks, **Then** there is no add action, and a direct attempt is refused.
4. **Given** an invalid name, **When** the member saves, **Then** they see the same message as for a rename, what they typed stays in the box, and nothing is created.
5. **Given** Ben has no own kitchen notebook in this kitchen, **When** Ben adds "Holidays" and later captures in the kitchen, **Then** the capture goes into "Holidays" unless Ben picks another notebook.

---

### Edge Cases

- **Name unchanged**: saving the current name changes nothing and shows no error, even if an older generated name is over the limit.
- **Two people with the same name**: duplicate names are allowed, within a person's notebooks and within a kitchen, as they are for created notebooks today.
- **Two people rename at once**: the last save wins.
- **Two people delete at once, or one renames while the other deletes**: the deletion wins. The second person sees that the notebook is gone, and no error page.
- **Someone is viewing a notebook when it is deleted**: a rename or delete tells them it is gone. Closing that message sends them to their notebooks list, or to the kitchen's notebooks for a kitchen notebook. A reload can no longer tell which kitchen the notebook was in, so it sends them to the list they opened it from, or to their notebooks list if there is none.
- **A person is editing a recipe in the notebook**: the lock does not block the deletion. Their edit is discarded and they are told the recipe is gone (spec 022 User Story 3, scenario 6).
- **A deleted recipe is in someone's unsaved cart draft**: it drops out of the draft and the editor is told in plain words when they next view or save it (spec 022).
- **Shopping lists**: the active list and closed lists keep their lines, with the recipe titles shown as they were. A later refresh of the active list from the cart no longer includes the deleted recipes. Items added by hand stay.
- **A capture draft is open for a deleted notebook**: saving tells the person the notebook is gone and nothing is saved. The draft stays on screen.
- **A pending invite to a deleted notebook**: it stops working and shows the usual invalid-link message, including when someone accepts it at the same moment as the deletion.
- **A snapshot of the notebook is being added when it is deleted**: the add fails with a clear message and nothing is created (spec 035).
- **A person deletes the kitchen notebook captures go to**: their next capture uses their next oldest own notebook in that kitchen. If they have none, a new one is created for them. Snapshots do not count as their own.
- **A person's units**: deleting a notebook does not change the units they kept (spec 055).
- **Language**: a chosen name is stored as typed and is never translated. A notebook recreated after deletion is named in the language of the person who causes it (spec 063).

## Requirements *(mandatory)*

### Functional Requirements

**Rename**

- **FR-001**: The owner of a personal notebook MUST be able to rename it. Its members MUST NOT.
- **FR-002**: Any member of a kitchen MUST be able to rename any of the kitchen's notebooks, snapshots included, while the kitchen is active.
- **FR-003**: A notebook name MUST follow the rules for creating a notebook: surrounding spaces are trimmed, it is not empty, and it is at most 200 characters.
- **FR-004**: A new name MUST show everywhere the notebook's name appears, including the origin label of its snapshots, the next time each person reads it. Recipes, catalog, members, access and whether it is the default MUST NOT change.

**Delete**

- **FR-005**: The owner of a personal notebook MUST be able to delete it, including their default notebook and a notebook that has members. Its members MUST NOT.
- **FR-006**: Any member of a kitchen MUST be able to delete any of the kitchen's notebooks, snapshots included, while the kitchen is active, including the kitchen's only notebook.
- **FR-007**: Deleting MUST require an explicit confirmation that names the notebook and states how many recipes will be deleted and that this cannot be undone. For a personal notebook with members it MUST also state how many will lose access. For a default notebook it MUST also state that a new, empty one will replace it.
- **FR-008**: Deleting a notebook MUST delete, as one step, the notebook, its recipes with their lines and steps, its catalog, its memberships, its pending invites, and the captured source text of its recipes that no other recipe uses. Either all of it happens or none of it does.
- **FR-009**: Deleting a notebook MUST remove its recipes from the kitchen's lists, cart and search, and MUST end any edit lock on them. An edit lock MUST NOT block the deletion. Past shopping list lines and the rest of the cart MUST NOT change.
- **FR-010**: Deleting a notebook MUST leave copies and snapshots made from it unchanged, except that a snapshot's origin label is cleared. Deleting a snapshot MUST NOT touch its original.
- **FR-011**: After a default notebook is deleted, the person MUST get a new, empty default on their next visit (spec 056). After a kitchen's last notebook is deleted, the next member to open its notebooks MUST get a new, empty one (spec 056 FR-008a). The catalog of a recreated notebook starts from the person's catalog, as for any new notebook, and the deleted recipes do not come back.
- **FR-012**: After a deletion, the person MUST land on their notebooks list for a personal notebook, or on the kitchen's notebooks for a kitchen notebook.

**Add a kitchen notebook**

- **FR-013**: Any member of an active kitchen MUST be able to add a kitchen notebook by giving it a name that follows FR-003.
- **FR-014**: The new notebook MUST start with no recipes and with the creator's personal catalog. The creator MUST be recorded as its owner in the same sense as a kitchen notebook made on first capture, which does not change who can read or write it.

**Access and behaviour on error**

- **FR-015**: A person who cannot see a notebook or kitchen MUST get "not found" for all of these actions. A person who can see it but may not perform the action MUST be refused, and nothing changes. The rules MUST be enforced by the system, not only by hiding controls.
- **FR-016**: Rename, delete and add MUST NOT be offered in an archived kitchen, and direct attempts MUST be refused. Personal notebooks do not depend on any kitchen's state.
- **FR-017**: Rename and delete actions MUST be on the notebook's own page and shown only to those who may use them. The add action MUST be on the kitchen's notebooks list and shown only in an active kitchen.
- **FR-018**: A failed rename or add MUST keep what the person typed. A failed delete MUST leave the notebook as it was and tell the person in plain words.
- **FR-019**: A notebook deleted by someone else, during any of these actions or while accepting an invite, saving a capture or adding a snapshot, MUST lead to a plain message, never an error page or a server failure.
- **FR-020**: All new text MUST be available in Spanish and English, and the actions MUST work by keyboard and at phone and desktop width.

### Key Entities

- **Notebook**: gains a changeable name. Its kind, its kitchen and its origin label do not change on rename.
- **Recipe and catalog**: belong to one notebook and are deleted with it.
- **Personal notebook membership and notebook invite**: belong to one personal notebook and are deleted with it.
- **Snapshot origin label**: a display-only reference to the original, cleared when the original is deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person can rename a notebook in under 20 seconds from its page.
- **SC-002**: A person can add an empty kitchen notebook in under 20 seconds from the kitchen's notebooks.
- **SC-003**: In 100% of tests, a person without the right to an action changes nothing, across every role: notebook owner, notebook member, kitchen member, non-member, and archived kitchen.
- **SC-004**: In 100% of tests, a deletion leaves nothing of the notebook behind: no recipe, catalog name, cart entry, membership, invite, edit lock or unused source text, and no change to its copies and snapshots other than the cleared label.
- **SC-005**: No notebook is deleted without a confirmation that states what will be lost.
- **SC-006**: A partly failed deletion leaves the notebook complete in every tested failure.
- **SC-007**: No tested race (two deletions, rename against delete, invite or capture against delete) shows an error page.

## Assumptions

- **Scope of this story**: the backlog's "create" part is already built for personal notebooks. This feature keeps that behaviour and adds only the kitchen case.
- **Name limit**: 200 characters, the limit built with spec 057. Spec 056 FR-001 says 70, which was not what shipped. No stored name is shortened.
- **Who is told**: members who lose access to a deleted notebook get no email or notification. They find it gone from their list, as when they are removed.
- **Confirmation**: one confirmation step, as for deleting a recipe. No typing the name, no recycle bin and no undo.
- **Deletion permanence**: nothing is soft-deleted, and no record of deleted notebooks is kept.
- **Default notebook**: it can be renamed and stays the default. Choosing another notebook as default is out of scope.
- **Archived kitchens**: read-only, as for recipes (spec 027).
- **Later stories**: a chat citation to a recipe deleted this way follows the same "recipe removed" rule as a single recipe deletion once S-030 exists. Embeddings go with their recipe once S-019 exists.
