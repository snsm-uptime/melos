# Feature Specification: Notebooks That Belong to People and Are Linked to Kitchens

**Feature Branch**: `s55-notebooks`

**Created**: 2026-10-22

**Updated**: 2026-10-23 (re-specified to the 2026-10-23 notebook model; replaces the kitchen-owned notebook of 2026-10-22)

**Status**: Draft. The code on `s55-notebooks` implements the replaced model and must be reworked to this spec before merge.

**Input**: Backlog story S-055, "Notebooks that belong to people and are linked to kitchens (entity, default notebook, read routes)" (`dev/docs/backlog.yaml`), and PRD §1.4, §1.5 flow H, §1.6 (notebook, notebook_membership, notebook_kitchen, `users.default_notebook_id`, design choices), J1a, AC1a.2. Prerequisite for `specs/016-capture-recipe-text` (S-016). Build order: this spec first, then S-016.

## Summary

Recipes are kept in notebooks, and a notebook belongs to people, never to a kitchen. The person who creates a notebook is its owner; other people join it later as notebook members (S-056). A kitchen sees a notebook only when the notebook is linked to it. This feature creates the notebook, membership, kitchen link and ingredient catalog data. It gives every person a default notebook on first use. It creates the member's notebook for a kitchen, linked to it, the first time the member captures there. It also provides the read routes that capture (S-016) and the Notebook tabs need: a person's notebooks, one notebook, and a kitchen's notebooks. It does not capture, save or show recipes. It does not invite people, link or unlink notebooks by hand, or keep copies when a link ends: those are S-056, S-034 and S-057.

## Clarifications

### Session 2026-10-22 (still valid)

- The auth routes (signup, alias claim, sign-in) are not changed. The user gains one column, a nullable default notebook reference (`users.default_notebook_id`). The owner approved this on 2026-10-22 as a constitution exception, and it still applies.
- A person's default notebook is created silently the first time they ask for it, and it is named "{alias}'s Notebook", using the alias at creation time. The name does not follow later alias changes.
- Deleting the default notebook clears the person's default (`ON DELETE SET NULL`), and the next request creates a new default notebook silently.
- The default notebook answer has the same shape and status whether the notebook was just created or already existed.

### Session 2026-10-22 (replaced on 2026-10-23)

- The rules "each kitchen has one shared notebook, created with the kitchen", "a member's notebooks are the notebooks with their user id" and "a member's notebook is private to them" are replaced by the 2026-10-23 model below. The answers "signup kitchen gets its notebook on first read" (FR-001a) and "member notebook answer `{ id, kind: "member", user_id, name }`" are withdrawn with them.

### Session 2026-10-23 (re-specification)

- A notebook has one owner, its creator, and any number of notebook members. Ownership and membership are recorded the same way for both (owner or member role). Nothing in this feature adds members; S-056 does.
- A kitchen sees a notebook only through a link. A link records who made it. This feature creates links only for the default notebook (to the signup kitchen) and the first-capture notebook; linking by hand is S-034.
- The kitchen notebook (one per kitchen, no owner, holds kept copies) is allowed by the data model here but is created and managed only by S-057.
- The notebook created on a member's first capture in a kitchen is named "{alias}'s Notebook ({kitchen name})" (PRD Appendix D, decided 2026-10-23).
- The notebook routes keep the existing alias check: a signed-in user without an alias gets the existing "alias required" answer, and no notebook is created.
- Q: When is the notebook for a member's first capture in a kitchen created? → A: When the capture is saved (option A). This feature provides the "find or create and link" step and S-016's save calls it. Opening and discarding a capture creates nothing. A draft made before the notebook exists is matched against the member's own catalog.
- Q: Does a notebook the member joined (not owns) count as their notebook in a kitchen? → A: Yes (option A). Notebooks the member owns or is a member of, linked to the kitchen, count. A couple sharing one notebook capture into it from their shared kitchen.
- Q: Is the default notebook linked to the person's signup kitchen ("My kitchen")? → A: Yes (option B). When the default notebook is created, it is linked to the kitchen made for the person at signup, if they still belong to it. A capture there goes into the default notebook, and anyone who later joins that kitchen can read it.
- Checklist review (requirements-quality CHK001, CHK003): no route today deletes a user, removes a kitchen member or lets one leave. S-057 (ownership passing, links ending, kept copies) must be built before or together with any of them, so a notebook is never left without an owner and a link never outlives its owner's membership.
- Checklist review (CHK002): when a user is deleted, the links they made stay, and who made them reads "unknown", as a deleted author does.
- Checklist review (CHK020): no capture happens in an archived kitchen. The capture notebook step refuses it even when the member already has a notebook there, and creates nothing.
- Checklist review (CHK024): a notebook created by the capture notebook step is kept even if the recipe save that called it then fails.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every person has a default notebook on first use (Priority: P1)

A signed-in person with an alias opens their Notebook tab. The first time, the app creates their notebook, named "{alias}'s Notebook", with them as its owner, and links it to the kitchen made for them at signup ("My kitchen"), without saying so. Every later visit shows the same notebook. Nobody else can see it, except members of a kitchen it is linked to.

**Why this priority**: A personal capture (S-016) saves into this notebook, and the Notebook tab learns which notebook to show from this answer.

**Independent Test**: As a person with no default notebook, ask for the default notebook twice. Check that exactly one notebook exists, named after the alias, owned by the person, and recorded as their default.

**Acceptance Scenarios**:

1. **Given** Ana, alias "ana", with no default notebook, **When** she asks for her default notebook, **Then** a notebook named "ana's Notebook" is created with Ana as its owner, recorded as her default, linked by Ana to her signup kitchen "My kitchen", and returned.
2. **Given** Ana already has a default notebook, **When** she asks again, **Then** the same notebook is returned with the same answer shape and status as the first time.
3. **Given** Ana has no default notebook, **When** two requests for it arrive at the same time, **Then** exactly one notebook exists afterwards and it is her default.
4. **Given** Ana's default notebook has been deleted, **When** she asks for her default notebook, **Then** a new "ana's Notebook" is created and set as her default, with no error shown.
5. **Given** Ana owns other notebooks whose catalogs hold "onion" and "garlic", **When** a new default notebook is created for her, **Then** its catalog starts with "onion" and "garlic".
6. **Given** Ana has left (or deleted) her signup kitchen, **When** her default notebook is created, **Then** it is created and linked to no kitchen.
7. **Given** Ana's default notebook is linked to "My kitchen", **When** she saves her first capture in "My kitchen", **Then** it goes into her default notebook and no new notebook is created (User Story 2, scenario 2).

---

### User Story 2 - A capture in a kitchen has a notebook to go into (Priority: P1)

Ana captures a recipe from the Notebook tab of a kitchen she belongs to. When she saves it, the recipe must go once into her notebook linked to that kitchen: one she owns or is a member of. If she has none, the app creates "ana's Notebook ({kitchen name})", makes her its owner and links it to the kitchen, then uses it. If she has several, she picks one.

**Why this priority**: A capture started in a kitchen (S-016, AC3.5) cannot be saved without this notebook. It is the only way a kitchen gets notebooks before S-034.

**Independent Test**: As a member of kitchen "Home" with no notebook linked to it, run the capture notebook step for "Home" twice, as S-016's save will. Check that one notebook named "{alias}'s Notebook (Home)" exists, that you own it, and that it is linked to "Home". Then check that a person who is not a member of "Home" gets the not-found answer and that nothing is created.

**Acceptance Scenarios**:

1. **Given** Ana is a member of kitchen "Home" and has no notebook linked to it, **When** she saves her first capture there, **Then** a notebook named "ana's Notebook (Home)" is created with Ana as its owner, linked to "Home" by Ana, and returned as the capture notebook.
2. **Given** Ana already has exactly one notebook linked to "Home", **When** she saves another capture there, **Then** that notebook is used and no new notebook is created.
3. **Given** Ana has two notebooks linked to "Home", **When** she captures there, **Then** she is offered both and the recipe goes into the one she picks; a pick that is not one of them is refused, and no new notebook is created.
4. **Given** Ben is a member, not the owner, of Ana's notebook linked to "Home", and Ben has no notebook of his own linked there, **When** Ben saves a capture in "Home", **Then** it goes into Ana's shared notebook and no "ben's Notebook (Home)" is created.
5. **Given** two first captures by Ana in "Home" arrive at the same time, **When** both ask for the capture notebook, **Then** exactly one notebook is created and linked.
6. **Given** Carl is not a member of "Home", **When** he asks for a capture notebook in "Home", **Then** he gets the same not-found answer as for a kitchen that does not exist, and no notebook is created.
7. **Given** Ana's catalog (her other notebooks) holds "onion", **When** her first-capture notebook is created, **Then** its catalog starts with "onion".
8. **Given** Ana opens a capture in "Home" and discards it, **When** nothing is saved, **Then** no notebook is created or linked.
9. **Given** Ana has never opened her Notebook tab (no default notebook yet), **When** she saves her first capture in her signup kitchen "My kitchen", **Then** her default notebook "ana's Notebook" is created, linked to "My kitchen" and used; no "ana's Notebook (My kitchen)" is created (FR-020).
10. **Given** "Home" is archived, **When** Ana saves a capture there, **Then** it is refused and no notebook is created or used, even if she already has one linked to "Home".
11. **Given** Ana's first capture in "Home" creates "ana's Notebook (Home)", **When** the recipe save then fails, **Then** the notebook and its link stay.

---

### User Story 3 - People and kitchen members read the notebooks they may see (Priority: P1)

Ana opens her Notebook tab and sees the notebooks she owns or is a member of. Ana and Ben open the Notebook tab of their shared kitchen and see the notebooks linked to it, with who owns each one. Anyone else gets the not-found answer, as if the notebook did not exist.

**Why this priority**: Every recipe screen (S-016 onwards) needs to know which notebooks a person may read or write, and the kitchen's recipe list is built from its linked notebooks.

**Independent Test**: Make Ana the owner of two notebooks, one of them linked to kitchen "Home", where Ben is also a member. Read Ana's list, each notebook, and Home's list as Ana, as Ben and as Carl (no access), and check what each one sees.

**Acceptance Scenarios**:

1. **Given** Ana owns "ana's Notebook" and "ana's Notebook (Home)" (the second created by her first capture in "Home"), **When** she lists her notebooks, **Then** she gets both, each with its name, her access "owner", and the default one marked as her default.
2. **Given** "ana's Notebook (Home)" is linked to "Home" and Ben is a member of "Home", **When** Ben lists Home's notebooks, **Then** he gets "ana's Notebook (Home)" with owner alias "ana" and his access "reader"; **When** Ana lists them, her access is "owner".
3. **Given** the same setup, **When** Ben reads "ana's Notebook (Home)" by id, **Then** he gets it with access "reader"; **When** he reads "ana's Notebook" (linked only to Ana's "My kitchen", which Ben has not joined) by id, **Then** he gets the not-found answer.
4. **Given** Carl is neither a member of a notebook nor of any kitchen it is linked to, **When** he reads it by id, **Then** he gets the same not-found answer as for a notebook id that does not exist (AC1a.2).
5. **Given** Carl is not a member of "Home", **When** he lists Home's notebooks, **Then** he gets the same not-found answer as for a kitchen that does not exist.
6. **Given** Ben is not a member of any notebook, **When** he lists his notebooks, **Then** the notebooks he can only read through "Home" are not in his list.
7. **Given** a kitchen has no linked notebooks, **When** a member lists its notebooks, **Then** the list is empty, not an error.

---

### User Story 4 - The upgrade keeps existing data working (Priority: P2)

The owner upgrades a database that already has users and kitchens. After the upgrade, nothing about the existing users and kitchens has changed, and each person gets their default notebook the first time they open their Notebook tab. The upgrade can be undone and redone.

**Why this priority**: The deployed v0 has users and kitchens. The upgrade must not break them, but no notebook is needed before first use.

**Independent Test**: Upgrade a database with existing users and kitchens, check that the data is unchanged and that a first default request works. Then downgrade and upgrade again.

**Acceptance Scenarios**:

1. **Given** a database with users and kitchens from the released version, **When** it is upgraded, **Then** the notebook, membership, kitchen link and ingredient data exist and are empty, every user's default notebook is empty (none yet), and the users and kitchens are unchanged.
2. **Given** the upgraded database, **When** an existing user with an alias asks for their default notebook, **Then** it is created as in User Story 1.
3. **Given** the upgraded database, **When** it is downgraded, **Then** the notebook data and the default notebook column are gone and the rest of the data is unchanged; **When** it is upgraded again, **Then** scenario 1 holds again.

---

### Edge Cases

- A signed-in user without an alias asks for any notebook route: they get the existing "alias required" answer, and no notebook is created.
- A person changes their alias after a notebook exists: the notebook keeps its original name. A kitchen renamed after a first-capture notebook exists: the notebook keeps its original name.
- A kitchen is archived: its members can still list and read its notebooks. No capture happens in an archived kitchen, so no notebook is created or used for one.
- A kitchen is deleted: its links and its kitchen notebook (if any) are deleted with it. The notebooks that were linked to it, and their catalogs, are not touched.
- A notebook is deleted: its memberships, links and catalog go with it. If it was someone's default, their default is cleared and recreated on the next visit.
- A user is deleted: their memberships are removed. Links they made stay, and who made them reads "unknown". Passing their notebooks to another member, ending their links and the kept copies are S-057. No route deletes a user, removes a kitchen member or lets one leave today; S-057 must be built before or with any of them (backlog order), so a notebook is never left without an owner.
- A second owner for one notebook, a person listed twice in one notebook, the same notebook linked twice to one kitchen, or a second kitchen notebook for one kitchen are all rejected.
- A kitchen notebook has no owner and is never anyone's default or capture notebook in this feature.
- A person joins Ana's "My kitchen": they can read Ana's default notebook through its link, but it is not in their own notebook list.
- Ana renames her signup kitchen: her default notebook stays linked to it. The default notebook is linked only when it is created, never later.
- A notebook's catalog never lists another notebook's names, and holds each name once.

## Requirements *(mandatory)*

### Functional Requirements

**Data**

- **FR-001**: The system MUST store notebooks with a name (null only for a kitchen notebook, which shows its kitchen's name), an optional kitchen reference that is set only on a kitchen notebook and unique per kitchen, and a creation date (PRD §1.6 `notebook`).
- **FR-002**: The system MUST store notebook memberships: a person, a notebook, a role (owner or member) and a join date, one per person and notebook. Every notebook except a kitchen notebook MUST have exactly one owner; a kitchen notebook MUST have none (PRD §1.6 `notebook_membership`).
- **FR-003**: The system MUST store kitchen links: a notebook, a kitchen, who linked it and when, at most one per notebook and kitchen (PRD §1.6 `notebook_kitchen`).
- **FR-004**: The system MUST store each notebook's ingredient catalog as a set of unique normalized names per notebook, with a creation date (PRD §1.6 `ingredient`).
- **FR-005**: The user MUST gain a nullable default notebook reference that is cleared when that notebook is deleted. No other change to the user, signup, sign-in, alias claim or session is allowed.
- **FR-006**: Deleting a kitchen MUST delete its links and its kitchen notebook, and MUST NOT delete the notebooks linked to it. Deleting a notebook MUST delete its memberships, links and catalog. Deleting a user MUST delete their memberships and MUST keep the links they made, with who made them cleared (shown as "unknown").

**Creating notebooks**

- **FR-007**: Asking for one's default notebook MUST return it, and when the person has none, MUST first create "{alias}'s Notebook" with the person as owner, record it as their default, and link it to the person's signup kitchen when they still belong to it (FR-020). Repeated and simultaneous requests MUST leave exactly one default notebook. The answer MUST have the same shape and status whether the notebook was created or not.
- **FR-008**: The capture notebook step, called by S-016 when a capture in a kitchen is saved, MUST find the notebooks linked to that kitchen that the member owns or is a member of (not the kitchen notebook). With none, the system MUST create "{alias}'s Notebook ({kitchen name})" with the member as owner and link it to the kitchen, made by the member. With one, it MUST use it. With several, it MUST use the one the member picked, and MUST refuse a pick that is not among them. Simultaneous first requests MUST create exactly one notebook. Nothing MUST be created before a capture is saved. A notebook the step creates MUST be kept even if the recipe save that called it then fails. Before the step runs, the member picks among the kitchen's notebooks where their access is owner or member (FR-013).
- **FR-009**: The capture notebook step MUST be available only to members of the kitchen. A missing kitchen and a non-member MUST get the same not-found answer. In an archived kitchen the step MUST refuse every capture, whether or not the member already has a notebook there, and MUST create nothing (spec 016 FR-033).
- **FR-010**: A notebook created by this feature MUST start with its owner's catalog: every name in the catalogs of the notebooks the owner already owns or is a member of, each name once.

**Reading notebooks**

- **FR-011**: A person MUST be able to list the notebooks they own or are a member of. Each item MUST give the notebook's id and name, the person's access (owner or member), the owner's alias, and whether it is the person's default. Notebooks the person can only read through a kitchen MUST NOT be in this list.
- **FR-012**: A person MUST be able to read one notebook by id when they own it, are a member of it, or are a member of a kitchen it is linked to. The answer MUST have the same fields as FR-011, with access "reader" in the last case. Anyone else, and a missing notebook, MUST get the same not-found answer.
- **FR-013**: A member of a kitchen MUST be able to list the notebooks linked to it, and its kitchen notebook when one exists, each with the same fields as FR-012 and the member's access. A missing kitchen and a non-member MUST get the same not-found answer. Archived kitchens MUST still be listed for their members.
- **FR-014**: The system MUST offer an internal reader that returns one notebook's catalog names, and one that returns a person's catalog (every name in the notebooks they own or are a member of), for capture (S-016) and the matcher (S-017). A draft made in a kitchen where the member has no notebook yet uses the person's catalog. No route exposes these readers in this feature.
- **FR-015**: Lists MUST be ordered by creation date, oldest first.

**Access and boundaries**

- **FR-016**: Every notebook route MUST require a signed-in user with an alias, as the kitchen routes do. A user without an alias MUST get the existing "alias required" answer and MUST NOT get a notebook.
- **FR-017**: The UI MUST reach every notebook route through same-origin routes that forward the person's session, as the existing kitchen routes do.
- **FR-018**: No code in this feature MUST write recipe, step, category, source, invite or cart data, add notebook members, or link notebooks other than the default notebook (FR-007) and the first-capture notebook (FR-008).
- **FR-019**: The upgrade MUST create the data in FR-001 to FR-005 empty, MUST NOT change existing users or kitchens, and MUST have a working downgrade.
- **FR-020**: A person's signup kitchen is the kitchen made for them at signup. When their default notebook is created and they still belong to that kitchen, it MUST be linked to it, made by the person. If they no longer belong to it, the default notebook MUST be linked to no kitchen. When a first capture is saved in the signup kitchen and the person has no default notebook yet, the capture notebook step (FR-008) MUST create the default notebook (linked as above) and use it, instead of a "{alias}'s Notebook ({kitchen name})".
- **FR-021**: The capture notebook step (FR-008) is an internal step for S-016's save. It MUST NOT be reachable by a read route.

### Key Entities

- **Notebook**: a container for recipes and an ingredient catalog. It has a name, set when it is created and not changed by this feature, and a creation date. A kitchen notebook has no name, shows its kitchen's name, and belongs to exactly one kitchen.
- **Notebook membership**: a person's place in a notebook, as owner or member, with the date they joined. Exactly one owner per notebook, except the kitchen notebook, which has none.
- **Kitchen link**: a notebook made visible, read-only, to the members of one kitchen. It records who linked it and when.
- **Ingredient (catalog entry)**: one normalized name in one notebook's catalog, unique within that notebook.
- **User (changed)**: gains a default notebook reference, empty until the person first asks for their default notebook and empty again after that notebook is deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeated and simultaneous first requests leave exactly one default notebook for the person, recorded as their default and owned by them, in 100% of automated runs.
- **SC-002**: Repeated and simultaneous first capture-notebook requests in one kitchen leave exactly one new notebook, owned by the member and linked to that kitchen, in 100% of automated runs.
- **SC-003**: For every read route, a person with no access gets an answer identical to the answer for a notebook or kitchen that does not exist, in 100% of automated runs.
- **SC-004**: A kitchen member who is not a member of a linked notebook can read it, and never sees it in their own notebook list, in 100% of automated runs.
- **SC-005**: After the default notebook is deleted, the next request creates a new one named "{alias}'s Notebook" with the same answer shape, in 100% of automated runs.
- **SC-006**: The upgrade, downgrade and second upgrade all succeed on a copy of the released data, and existing users and kitchens are unchanged.
- **SC-007**: Deleting a kitchen leaves every notebook that was linked to it, with its catalog, in 100% of automated runs.
- **SC-008**: A capture opened and discarded in a kitchen creates no notebook and no link, and a first default notebook is linked to the signup kitchen whenever the person still belongs to it, in 100% of automated runs.

## Assumptions

- The PRD (§1.4, §1.5 flow H, §1.6, J1a, Appendix A and D) and AGENTS.md describe the 2026-10-23 model. Where this spec and the PRD differ, the PRD wins and this spec is fixed.
- Data names follow PRD §1.6 because S-016, S-034, S-056 and S-057 build on them. Route paths and answer shapes are set in the plan's contracts.
- No backfill: existing users get their default notebook on first use (FR-007), and kitchens get notebooks only through captures and links. The unmerged 2026-10-22 migration on this branch is replaced, not stacked on.
- The kitchen notebook is created and its members kept equal to the kitchen's members only by S-057. Until then, no kitchen notebook exists, and the kitchen list (FR-013) holds only linked notebooks.
- The kitchen notebook is never offered as a capture notebook in this feature.
- The signup kitchen is not marked in the data today. The plan decides how to find it (for example, the oldest kitchen the person owns), without changing signup.
- A person's access in a notebook is the strongest one they have: owner, then member, then reader.
- Unit and integration tests run in Compose against Postgres, as in spec 016.
- This feature adds no env var and no library.
- Out of scope: creating, renaming or deleting notebooks from the UI; invites and members (S-056); linking and unlinking by hand (S-034); kept copies, kitchen notebook management and ownership passing (S-057); copying recipes (S-047); writing catalog names other than the seed in FR-010 (S-017, S-019); recipes (S-016 onwards).
