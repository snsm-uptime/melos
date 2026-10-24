# Feature Specification: Personal and Kitchen Notebooks

**Feature Branch**: `s55-notebooks`

**Created**: 2026-10-22

**Updated**: 2026-10-23 (re-specified to the snapshot model; replaces the kitchen-owned notebook of 2026-10-22 and the kitchen-link model of earlier on 2026-10-23)

**Status**: Draft. The code on `s55-notebooks` implements the 2026-10-22 model and must be reworked to this spec before merge (`tasks.md`).

**Input**: Backlog story S-055, "Personal and kitchen notebooks (entity, default notebook, kitchen notebook at kitchen creation, capture notebook, read routes)" (`dev/docs/backlog.yaml`), and PRD §1.4, §1.5 flow H, §1.6 (`notebook`, `notebook_membership`, `ingredient`, `users.default_notebook_id`, design choices), J1, J1a, AC1.3, AC1a.2, Appendix A and D. Prerequisite for `specs/016-capture-recipe-text` (S-016). Build order: this spec first, then S-016.

## Summary

Recipes are kept in notebooks, and there are two kinds. A **personal notebook** belongs to people: one owner, who created it, and members who join later by invite (S-056). Only they can see it, and it is never shown in a kitchen. A **kitchen notebook** belongs to one kitchen. Every member of that kitchen reads and writes it while they belong to the kitchen; its owner is the kitchen's owner (`kitchens.owner_id`), and it has no member list. A personal notebook reaches a kitchen only as a snapshot, an independent copy (S-034).

This feature creates the notebook, membership and ingredient catalog data, with room for a snapshot's origin label. It gives every person a default personal notebook on first use. It gives every kitchen made from the kitchen page a kitchen notebook, and it gives a capture a notebook to go into: in a kitchen with no notebook (for example signup's "My kitchen"), the first saved capture creates one. It also provides the read routes that capture (S-016) and the Notebook tabs need: a person's notebooks, one notebook, and a kitchen's notebooks. It also removes the per-member kitchen hide, which archive already covers. It does not capture, save or show recipes. It does not invite people (S-056), make snapshots (S-034), pass ownership (S-057), or create, rename or delete notebooks by hand (S-058).

## Clarifications

### Session 2026-10-22 (still valid)

- The auth routes (signup, alias claim, sign-in) are not changed. The user gains one column, a nullable default notebook reference (`users.default_notebook_id`). The owner approved this on 2026-10-22 as a constitution exception, and it still applies.
- A person's default notebook is created silently the first time they ask for it, and it is named "{alias}'s Notebook", using the alias at creation time. The name does not follow later alias changes.
- Deleting the default notebook clears the person's default, and the next request creates a new default notebook silently.
- The default notebook answer has the same shape and status whether the notebook was just created or already existed.

### Replaced decisions

- 2026-10-22: "each kitchen has one shared notebook", "a member's notebooks are the notebooks with their user id", "a member's notebook is private to them", "signup kitchen gets its notebook on first read" and the member notebook answer `{ id, kind: "member", user_id, name }` are withdrawn.
- Earlier on 2026-10-23: kitchen links (`notebook_kitchen`), the ownerless kitchen notebook holding kept copies, the first-capture notebook "{alias}'s Notebook ({kitchen name})", linking the default notebook to the signup kitchen (old FR-020), "a notebook the member joined counts as theirs in a kitchen", and the "reader" access are withdrawn. The checklist answers about links (CHK002, CHK005) are moot.

### Session 2026-10-23 (snapshot model)

- A personal notebook has exactly one owner and any number of members, recorded the same way (owner or member role). Nothing in this feature adds members; S-056 does.
- A kitchen notebook belongs to one kitchen, which can have several. Access to it comes only from kitchen membership: there are no owner or member rows (its owner is the kitchen's owner, read from the kitchen), and leaving the kitchen ends access at once, with nothing copied.
- A kitchen made through the kitchen service starts with one kitchen notebook, "{alias}'s ({kitchen name}) Notebook", named after its creator, made in the same step as the kitchen (decision of 13:52, renamed at 13:56). Signup's "My kitchen" and the kitchen made when an invitee signs up are made by the auth code, which is not changed, so they start with none.
- A capture saved in a kitchen with no notebook creates "{alias}'s ({kitchen name}) Notebook", named after the capturing member, and saves into it. It is created when the capture is saved, never when a capture is opened (the 2026-10-23 answer to "when is it created" still holds). A draft made before it exists is matched against the member's personal catalog.
- The capture picker in a kitchen offers the kitchen's notebooks. Outside a kitchen it offers the personal notebooks the person owns or is a member of.
- A snapshot keeps an origin label (`source_notebook_id`), cleared when the original is deleted. This feature only stores the field; S-034 sets it and decides how it is shown.
- The notebook routes keep the existing alias check: a signed-in user without an alias gets the existing "alias required" answer, and no notebook is created.
- Still valid from the checklist review: no capture happens in an archived kitchen, and the capture notebook step refuses it even when the kitchen has notebooks (CHK020). A notebook created by the capture step is kept even if the recipe save that called it then fails (CHK024). No route today deletes a user; S-057 (ownership passing) must be built before or together with any route that does, so a personal notebook is never left without an owner (CHK001, CHK003).

### Session 2026-10-23 (requirements-quality review)

- Q: Does a kitchen notebook have an owner? → A: Yes, the kitchen's owner, read from `kitchens.owner_id`, not stored on the notebook. Access stays "any current kitchen member". Passing kitchen ownership to the longest-standing member when the owner leaves or is deleted, and deleting a kitchen with no people left, belong to the story that adds leaving, removal and user deletion (S-053/S-057). No creator is stored; the name says who made it (CHK004, CHK011).
- Q: Which notebooks make up a person's catalog? → A: Unchanged: the personal notebooks they own or are a member of, never kitchen notebooks (CHK005).
- Q: Should a kitchen made at signup start with a notebook? → A: No. Auth stays unchanged; "My kitchen" gets its notebook on the first saved capture, and S-016 shows an empty state in its Notebook tab until then (CHK009).
- Q: Keep `GET /notebooks/default` creating on first use? → A: Yes, the accepted risk stands (CHK035).

- Q: When a capture's picked notebook is no longer among the options, is the save always refused? → A: No. A pick is checked only when there are several notebooks; with none the step creates one, with one it uses it, and a stale pick is ignored (CHK018, CHK019; replaces research R6's "refused even when the kitchen has none").
- Q: Does a non-member capturing in an archived kitchen get the not-found answer? → A: Yes. Membership is checked first, then the archived state, so only members learn a kitchen is archived (CHK020).
- Q: Does a kitchen notebook's answer say whether its kitchen is archived? → A: Yes, `kitchen_is_archived` on every notebook answer: true/false for a kitchen notebook, null for a personal one, so the ui can hide "add recipe" without another call (CHK014).
- Q: Can a member capture into a kitchen they have hidden? → A: The per-member hide is removed in this feature (owner decision: archive already covers it). A kitchen membership is either there or not; archived is the only kitchen state notebooks look at (CHK022).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every person has a default personal notebook on first use (Priority: P1)

A signed-in person with an alias opens their own Notebook tab. The first time, the app creates their notebook, named "{alias}'s Notebook", with them as its owner, without saying so. Every later visit shows the same notebook. Nobody else can see it, and no kitchen shows it.

**Why this priority**: A capture outside a kitchen (S-016) saves into a personal notebook, and the Notebook tab learns which notebook to show from this answer.

**Independent Test**: As a person with no default notebook, ask for the default notebook twice. Check that exactly one notebook exists, named after the alias, personal, owned by the person, recorded as their default, and absent from every kitchen's notebook list.

**Acceptance Scenarios**:

1. **Given** Ana, alias "ana", with no default notebook, **When** she asks for her default notebook, **Then** a personal notebook named "ana's Notebook" is created with Ana as its owner, recorded as her default, and returned.
2. **Given** Ana already has a default notebook, **When** she asks again, **Then** the same notebook is returned with the same answer shape and status as the first time.
3. **Given** Ana has no default notebook, **When** two requests for it arrive at the same time, **Then** exactly one notebook exists afterwards and it is her default.
4. **Given** Ana's default notebook has been deleted, **When** she asks for her default notebook, **Then** a new "ana's Notebook" is created and set as her default, with no error shown.
5. **Given** Ana owns or is a member of personal notebooks whose catalogs hold "onion" and "garlic", **When** a new default notebook is created for her, **Then** its catalog starts with "onion" and "garlic".
6. **Given** Ana belongs to kitchen "Home", **When** her default notebook is created, **Then** it does not appear in Home's notebooks, and Ben, another member of Home, gets the not-found answer when he reads it.

---

### User Story 2 - A kitchen made from the kitchen page starts with a kitchen notebook (Priority: P1)

Ana creates the kitchen "Home" from the kitchen page. Home starts with one notebook, "ana's (Home) Notebook", that belongs to Home. When Ben joins Home, he reads and writes that notebook too, because he belongs to the kitchen.

**Why this priority**: A kitchen's recipe list, cart and chat are built from its notebooks, and a capture in a kitchen needs one to save into.

**Independent Test**: As Ana, create a kitchen named "Home". Check that exactly one notebook exists for Home, named "ana's (Home) Notebook", owned by Ana as the kitchen's owner, with no membership rows, and that its catalog starts from Ana's personal catalog.

**Acceptance Scenarios**:

1. **Given** Ana, alias "ana", **When** she creates the kitchen "Home" from the kitchen page, **Then** Home has exactly one kitchen notebook, "ana's (Home) Notebook", whose owner is Ana as the kitchen's owner, with no membership rows.
2. **Given** Ana's personal catalog holds "onion", **When** she creates "Home", **Then** the notebook's catalog starts with "onion".
3. **Given** creating "Home" fails, **When** the failure happens after the kitchen was started, **Then** neither the kitchen nor its notebook exists.
4. **Given** Ana signs up and gets "My kitchen", **When** signup finishes, **Then** "My kitchen" has no notebook, and signup works as before.
5. **Given** Ana renames "Home" to "Casa", **When** she lists Home's notebooks, **Then** the notebook is still named "ana's (Home) Notebook".

---

### User Story 3 - A capture has a notebook to go into (Priority: P1)

Ana saves a captured recipe. In a kitchen, it goes once into one of that kitchen's notebooks: the only one, the one she picked when there are several, or, when there are none, a new "ana's ({kitchen name}) Notebook" made for it. Outside a kitchen, it goes into one of the personal notebooks she owns or is a member of. No capture happens in an archived kitchen.

**Why this priority**: A capture (S-016) cannot be saved without a target notebook. It is the only way signup's "My kitchen" and kitchens from before this feature get a notebook.

**Independent Test**: As a member of kitchen "My kitchen" with no notebook, run the capture notebook step twice, as the recipe save (S-019) will. Check that one kitchen notebook named "{alias}'s (My kitchen) Notebook" exists and is used both times. Then check that a person who is not a member gets the not-found answer, and that an archived kitchen refuses the step, with nothing created.

**Acceptance Scenarios**:

1. **Given** Ana is a member of "My kitchen", which has no notebook, **When** she saves her first capture there, **Then** a kitchen notebook "ana's (My kitchen) Notebook" is created for "My kitchen" and returned as the capture notebook.
2. **Given** "Home" has exactly one notebook, **When** Ben, a member, saves a capture there, **Then** that notebook is used and none is created.
3. **Given** "Home" has two notebooks, **When** Ana saves a capture there, **Then** the recipe goes into the one she picked; a missing pick or a pick that is not one of Home's notebooks is refused, and nothing is created.
4. **Given** "My kitchen" has no notebook, **When** two first captures by Ana and Ben arrive at the same time, **Then** exactly one notebook is created, and both use it.
5. **Given** Carl is not a member of "Home", **When** he asks for a capture notebook in "Home", **Then** he gets the same not-found answer as for a kitchen that does not exist, and nothing is created.
6. **Given** Ana's personal catalog holds "onion", **When** her first capture in "My kitchen" creates its notebook, **Then** its catalog starts with "onion".
7. **Given** Ana opens a capture in "My kitchen" and discards it, **When** nothing is saved, **Then** no notebook is created.
8. **Given** "Home" is archived, **When** Ana saves a capture there, **Then** it is refused and no notebook is created or used, even though Home has notebooks.
9. **Given** Ana's first capture in "My kitchen" creates its notebook, **When** the recipe save then fails, **Then** the notebook stays.
10. **Given** Ana owns only her default notebook, **When** she saves a capture outside a kitchen, **Then** it goes into her default notebook; **Given** she has none yet, **Then** her default notebook is created as in User Story 1 and used.
11. **Given** Ana owns "ana's Notebook" and is a member of Ben's "Family" notebook, **When** she saves a capture outside a kitchen, **Then** it goes into the one she picked; a missing pick or a pick of a notebook she does not own or belong to (including any kitchen notebook) is refused.

---

### User Story 4 - People and kitchen members read the notebooks they may see (Priority: P1)

Ana opens her own Notebook tab and sees the personal notebooks she owns or is a member of. Ana and Ben open the Notebook tab of their shared kitchen and see its notebooks. Anyone else gets the not-found answer, as if the notebook did not exist.

**Why this priority**: Every recipe screen (S-016 onwards) needs to know which notebooks a person may read and write, and a kitchen's recipe list is built from its notebooks.

**Independent Test**: Give Ana a default notebook and make her and Ben members of kitchen "Home", which has one notebook. Read Ana's list, each notebook, and Home's list as Ana, as Ben and as Carl (no access), and check what each one sees.

**Acceptance Scenarios**:

1. **Given** Ana owns "ana's Notebook" and is a member of Ben's personal notebook "Family", **When** she lists her notebooks, **Then** she gets both, each with its name, kind "personal", her access ("owner" or "member"), the owner's alias, and "ana's Notebook" marked as her default.
2. **Given** Ana and Ben are members of "Home", which has "ana's (Home) Notebook", **When** Ben lists Home's notebooks, **Then** he gets that notebook with kind "kitchen" and his access "kitchen member"; **When** Ana lists them, her access is the same.
3. **Given** the same setup, **When** Ben reads "ana's (Home) Notebook" by id, **Then** he gets it with access "kitchen member"; **When** he reads "ana's Notebook" by id, **Then** he gets the not-found answer.
4. **Given** Carl belongs to neither a personal notebook nor the kitchen of a kitchen notebook, **When** he reads it by id, **Then** he gets the same not-found answer as for a notebook id that does not exist (AC1a.2).
5. **Given** Carl is not a member of "Home", **When** he lists Home's notebooks, **Then** he gets the same not-found answer as for a kitchen that does not exist.
6. **Given** Ana belongs to "Home", **When** she lists her notebooks, **Then** Home's notebooks are not in the list; **When** anyone lists Home's notebooks, **Then** Ana's personal notebooks are not in it.
7. **Given** "My kitchen" has no notebook yet, **When** a member lists its notebooks, **Then** the list is empty, not an error.
8. **Given** Ben has stopped being a member of "Home", **When** he reads or lists Home's notebooks, **Then** he gets the not-found answer, and Home's notebooks are unchanged (AC1.3).

---

### User Story 5 - The upgrade keeps existing data working (Priority: P2)

The owner upgrades a database that already has users and kitchens. Nothing about the existing users and kitchens changes. Each person gets their default notebook the first time they open their Notebook tab, and each existing kitchen gets its notebook on its first saved capture. The upgrade can be undone and redone.

**Why this priority**: The deployed v0 has users and kitchens. The upgrade must not break them, but no notebook is needed before first use.

**Independent Test**: Upgrade a database with existing users and kitchens, check that the data is unchanged and that a first default request and a first kitchen capture work. Then downgrade and upgrade again.

**Acceptance Scenarios**:

1. **Given** a database with users and kitchens from the released version, **When** it is upgraded, **Then** the notebook, membership and ingredient data exist and are empty, every user's default notebook is empty (none yet), and the users and kitchens are unchanged.
2. **Given** the upgraded database, **When** an existing user with an alias asks for their default notebook, **Then** it is created as in User Story 1; **When** a member saves the first capture in an existing kitchen, **Then** its notebook is created as in User Story 3.
3. **Given** the upgraded database, **When** it is downgraded, **Then** the notebook data and the default notebook column are gone and the rest of the data is unchanged; **When** it is upgraded again, **Then** scenario 1 holds again.

---

### Edge Cases

- A signed-in user without an alias asks for any notebook route: they get the existing "alias required" answer, and no notebook is created. Kitchen creation already requires an alias, so a kitchen notebook always has one to be named after.
- A person changes their alias, or a kitchen is renamed, after a notebook exists: the notebook keeps its original name.
- Two notebooks may have the same name (for example when Ana creates two kitchens both named "Home"). Names are not unique.
- A kitchen is archived: its members can still list and read its notebooks. No capture happens in it, so no notebook is created or used for one.
- A kitchen is deleted: its kitchen notebooks and their catalogs are deleted with it. Personal notebooks are not touched.
- A kitchen notebook's creator later leaves the kitchen: nothing changes. The catalog seed was a one-time copy, and the notebook stays with the kitchen.
- A personal notebook is deleted: its memberships and catalog go with it. If it was someone's default, their default is cleared and recreated on the next visit. A snapshot made from it keeps its recipes, and its origin label is cleared.
- A person stops being a member of a kitchen (no route does this today): they lose access to its notebooks at once, nothing is copied, and their personal notebooks are not touched.
- A kitchen's owner leaves or is deleted (no route does this today): the story that adds it (S-053/S-057) passes kitchen ownership to the longest-standing member, which also makes them the owner of its notebooks, and deletes the kitchen when nobody is left. Until a new owner exists, a kitchen notebook's owner shows as "unknown".
- A user is deleted: their notebook memberships are removed. Passing their personal notebooks to another member is S-057, which must be built before or with any route that deletes a user (S-053 depends on it).
- A personal notebook with no owner or two owners, a person listed twice in one notebook, a membership in a kitchen notebook, a kitchen notebook as anyone's default, and an origin label on a personal notebook are all rejected.
- An invitee who signs up through a kitchen invite gets their own "My kitchen" from the auth code, with no notebook, like any signup; the inviting kitchen keeps its notebooks.
- A notebook's catalog never lists another notebook's names, and holds each name once.

## Requirements *(mandatory)*

### Functional Requirements

**Data**

- **FR-001**: The system MUST store notebooks with a non-empty name, an optional kitchen reference, an optional origin reference and a creation date (PRD §1.6 `notebook`). A notebook with a kitchen reference is a kitchen notebook, and a kitchen can have several; one without is a personal notebook.
- **FR-002**: The system MUST store personal notebook memberships: a person, a notebook, a role (owner or member) and a join date, one per person and notebook (PRD §1.6 `notebook_membership`). Every personal notebook MUST have exactly one owner. The one exception is a deleted owner: until ownership passing (S-057) exists, deleting a user (FR-006) can leave a notebook with no owner, and its answer then gives `owner_alias: null`, which the ui shows as "unknown". No route deletes a user today. A kitchen notebook MUST have no memberships.
- **FR-003**: The origin reference (`source_notebook_id`) MUST be allowed only on a kitchen notebook, MUST point at another notebook, which MUST be a personal notebook owned by the person making the snapshot (PRD §1.5 flow H; S-034 enforces this when it sets the label), so the origin is never a kitchen notebook, and MUST be cleared when that notebook is deleted. No code in this feature sets it (S-034 does).
- **FR-004**: The system MUST store each notebook's ingredient catalog as a set of unique normalized names per notebook, with a creation date (PRD §1.6 `ingredient`).
- **FR-005**: The user MUST gain a nullable default notebook reference that can only point at a personal notebook the person owns and is cleared when that notebook is deleted. No other change to the user, signup, sign-in, alias claim or session is allowed.
- **FR-006**: Deleting a kitchen MUST delete its kitchen notebooks and their catalogs, and MUST NOT touch personal notebooks. Everything that belongs to the kitchen goes with it: its notebooks with their recipes and catalogs, its cart and its chats. The stories that add recipes, carts and chats (S-016 onwards) MUST keep this cascade. Deleting a notebook MUST delete its memberships and catalog. Deleting a user MUST delete their notebook memberships.

**Creating notebooks**

- **FR-007**: Asking for one's default notebook MUST return it, and when the person has none, MUST first create the personal notebook "{alias}'s Notebook" with the person as owner and record it as their default. Repeated and simultaneous requests MUST leave exactly one default notebook. The answer MUST have the same shape and status whether the notebook was created or not.
- **FR-008**: Creating a kitchen through the kitchen service (api `POST /kitchens`, which the kitchen page calls through the BFF route `POST /api/kitchens`, and the dev seed, which uses the same service) MUST also create one kitchen notebook for it, "{alias}'s ({kitchen name}) Notebook", named after the creator, in the same step: the kitchen, the creator's kitchen membership, the notebook and its catalog seed (FR-012) are all kept or, on any failure, none of them is. Signup and the other auth flows MUST NOT be changed and create no notebook.
- **FR-009**: The capture notebook step, called by the recipe save (S-019) when a capture is saved in a kitchen (the save calls it first, before the recipe is written), MUST look at the kitchen's notebooks. With none, it MUST create the kitchen notebook "{alias}'s ({kitchen name}) Notebook", named after the capturing member, and use it. With one, it MUST use it. With several, it MUST use the one the member picked, and MUST refuse a missing pick or a pick that is not among them. With none or one, a pick MUST be ignored, even when it is not among them. Simultaneous first requests MUST create exactly one notebook. Nothing MUST be created before the recipe save calls the step. A notebook the step creates MUST be kept even if the recipe save that called it then fails.
- **FR-010**: The capture notebook step in a kitchen MUST be available only to members of the kitchen. A missing kitchen and a non-member MUST get the same not-found answer. Membership MUST be checked before the archived state, so a non-member of an archived kitchen gets the not-found answer. In an archived kitchen it MUST refuse every member's capture, whether or not the kitchen has notebooks, and MUST create nothing (spec 016 FR-033).
- **FR-011**: The capture notebook step, called by the recipe save (S-019) when a capture is saved outside a kitchen, MUST look at the personal notebooks the person owns or is a member of. With none, it MUST create and use their default notebook (FR-007). With one, it MUST use it. With several, it MUST use the one the person picked, and MUST refuse a missing pick or a pick that is not among them. With none or one, a pick MUST be ignored, even when it is not among them.
- **FR-012**: A notebook created by this feature MUST start with its creator's personal catalog: every name in the catalogs of the personal notebooks the creator owns or is a member of, each name once. For a kitchen notebook, the creator is the person who created the kitchen (FR-008) or made the capture (FR-009).
- **FR-013**: The capture notebook step is an internal step for the recipe save (S-019). It MUST NOT be reachable by a route in this feature.

**Reading notebooks**

- **FR-014**: A person MUST be able to list the personal notebooks they own or are a member of. Each item MUST give the notebook's id and name, its kind (personal), the person's access (owner or member), the owner's alias, and whether it is the person's default. Kitchen notebooks MUST NOT be in this list. Listing MUST NOT create a default notebook.
- **FR-015**: A person MUST be able to read one notebook by id when it is a personal notebook they own or are a member of, or a kitchen notebook of a kitchen they are a member of. A personal notebook's answer MUST have the fields of FR-014; a kitchen notebook's answer MUST give its id, name, kind (kitchen), its kitchen's id, whether that kitchen is archived, the kitchen owner's alias as its owner, and the access "kitchen member"; a personal notebook's answer gives no archived state. Anyone else, and a missing notebook, MUST get the same not-found answer.
- **FR-016**: A member of a kitchen MUST be able to list the kitchen's notebooks, each with the fields of a kitchen notebook in FR-015. Personal notebooks MUST NOT be in this list. A missing kitchen and a non-member MUST get the same not-found answer. Archived kitchens MUST still be listed for their members.
- **FR-017**: Access to a kitchen notebook MUST be decided only by current membership of its kitchen, at the moment of each request.
- **FR-018**: The system MUST offer an internal reader that returns one notebook's catalog names, and one that returns a person's personal catalog (every name in the personal notebooks they own or are a member of), for capture (S-016) and the matcher (S-017). A draft made in a kitchen with no notebook yet uses the person's personal catalog. No route exposes these readers in this feature.
- **FR-019**: Lists MUST be ordered by creation date, oldest first.

**Access and boundaries**

- **FR-020**: Every notebook route MUST require a signed-in user with an alias, as the kitchen routes do. A user without an alias MUST get the existing "alias required" answer and MUST NOT get a notebook.
- **FR-021**: The UI MUST reach every notebook route through same-origin routes that forward the person's session, as the existing kitchen routes do.
- **FR-022**: Code in this feature MUST NOT write recipe, step, category, source, invite or cart data, add notebook members, set an origin label, or create notebooks other than the default notebook (FR-007), the kitchen notebook made with a kitchen (FR-008) and the capture notebook (FR-009, FR-011).
- **FR-023**: The upgrade MUST create the data in FR-001 to FR-005 empty, with no backfill, MUST NOT change existing users or kitchens, and MUST have a working downgrade. It replaces the unmerged notebook upgrade on this branch rather than adding to it.
- **FR-024**: The per-member kitchen hide MUST be removed: the hide and unhide routes and their BFF routes, the hide control in the kitchen page, the hide services, port methods and error, and the `kitchen_memberships.is_hidden` column (dropped by an upgrade with a working downgrade that restores it as `false`). A member's archived view MUST then follow `kitchens.is_archived` alone. Archive and unarchive are not changed.

### Key Entities

- **Notebook**: a container for recipes and an ingredient catalog. It has a name, set when it is created and not changed by this feature, and a creation date. A personal notebook has no kitchen. A kitchen notebook belongs to exactly one kitchen and may carry an origin label naming the notebook it was snapshotted from.
- **Notebook membership**: a person's place in a personal notebook, as owner or member, with the date they joined. Exactly one owner per personal notebook; none for a kitchen notebook.
- **Ingredient (catalog entry)**: one normalized name in one notebook's catalog, unique within that notebook.
- **Personal catalog** (derived, not stored): every name in the personal notebooks a person owns or is a member of.
- **User (changed)**: gains a default notebook reference, empty until the person first asks for their default notebook and empty again after that notebook is deleted.
- **Kitchen notebook owner** (derived, not stored): the owner of the notebook's kitchen.
- **Kitchen (behavior changed)**: creating one from the kitchen page also creates its first kitchen notebook; deleting one deletes its notebooks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeated and simultaneous first requests for the default notebook, first personal captures, or a mix of both, leave exactly one default notebook for the person, personal, recorded as their default and owned by them, in 100% of automated runs.
- **SC-002**: Every kitchen created from the kitchen page has exactly one notebook right after creation, named after its creator, and a failed creation leaves neither kitchen nor notebook, in 100% of automated runs.
- **SC-003**: Repeated and simultaneous first captures in a kitchen with no notebook, by the same member or by different members, leave exactly one new kitchen notebook, used by all of them, in 100% of automated runs.
- **SC-004**: For every read route and the capture step, a person with no access gets an answer identical to the answer for a notebook or kitchen that does not exist, in 100% of automated runs.
- **SC-005**: A personal notebook never appears in a kitchen's list or to a non-member, and a kitchen notebook never appears in a person's own list, in 100% of automated runs.
- **SC-006**: A person who stops being a member of a kitchen gets the not-found answer for its notebooks on their next request, and the notebooks are unchanged, in 100% of automated runs.
- **SC-007**: After the default notebook is deleted, the next request creates a new one named "{alias}'s Notebook" with the same answer shape, in 100% of automated runs.
- **SC-008**: Deleting a kitchen deletes all of its notebooks and none of its members' personal notebooks, in 100% of automated runs.
- **SC-009**: A capture opened and discarded creates no notebook, and a capture in an archived kitchen is refused with nothing created, in 100% of automated runs.
- **SC-010**: The upgrade, downgrade and second upgrade all succeed on a database at the released revision (`0002`) seeded with synthetic users and kitchens (no real personal data, constitution §4), and those users and kitchens are unchanged.
- **SC-011**: Automated tests show that no route reaches the capture notebook step (FR-013), that the catalog readers return one notebook's names and a person's personal catalog (FR-018), that each BFF route forwards the session and returns the api's status and body (FR-021), and that this feature's code writes no data outside FR-022's list, in 100% of runs.

## Assumptions

- The PRD (§1.4, §1.5 flow H, §1.6, J1, J1a, Appendix A and D) and AGENTS.md describe the snapshot model. Where this spec and the PRD differ, the PRD wins and this spec is fixed.
- Data names follow PRD §1.6 because S-016, S-034, S-056 and S-057 build on them. Route paths and answer shapes are set in the plan's contracts.
- No backfill: existing users get their default notebook on first use (FR-007), and existing kitchens get a notebook on their first saved capture (FR-009). The unmerged 2026-10-22 upgrade on this branch is replaced, not stacked on.
- The access label "kitchen member" and the kinds "personal" and "kitchen" are working names; the plan's contracts fix the exact values.
- The capture picker's preselection (for example, the default notebook outside a kitchen) is S-016's choice; the step itself always needs a pick when there are several notebooks.
- A kitchen notebook does not record who created it; only its name says so.
- No route today removes a kitchen member, lets one leave or deletes a user. Access rules (FR-017) make leaving work without further changes when such a route is built. The story that adds member removal or leaving (S-053 or later) must keep FR-017, and the story that adds user deletion (S-053) must come with or after S-057.
- Until S-016 adds it, nothing shows a kitchen with no notebook; S-016's kitchen Notebook tab shows an empty state for it.
- No backfill means an existing kitchen shows an empty notebook list until its first saved capture (US4 scenario 7). This is accepted for the deployed v0 users: the Notebook tab shows an empty state, and the first capture fixes it.
- `GET /notebooks/default` creates data on first use. This is an accepted risk (research R4): it is idempotent, so a cross-site navigation can at most create the notebook the person would get on their next visit.
- The user-facing messages for `notebook_choice_required` (choose a notebook) and a stale pick (`notebook_not_found`) belong to S-019, which maps the step's errors on its save route; S-016's picker avoids them in normal use. Only the archived message is fixed here (spec 016 FR-033).
- Spec 016 FR-001a ("also saved into the member's notebook", "a kitchen's shared notebook") conflicts with this model. It must be re-synced to this spec before S-016 is built (plan Follow-ups, backlog S-016 note).
- No maximum notebook name length is set: names are built from an alias and a kitchen name, which already have limits. S-058 sets a limit when it adds renaming, and only a personal notebook's owner may rename it.
- No response-time target is set for the capture step. The kitchen-row lock is taken only for the first capture in a kitchen with no notebook, and held until that notebook is committed (research R6, R8). A capture that arrives during that time waits for the lock, then uses the new notebook; it is never refused because of the race.
- Unit and integration tests run in Compose against Postgres, as in spec 016.
- This feature adds no env var and no library.
- Out of scope: creating more personal notebooks, adding more kitchen notebooks, and renaming or deleting notebooks (S-058); notebook invites and members (S-056); snapshots and showing the origin label (S-034); ownership passing (S-057); copying recipes (S-047); writing catalog names other than the seed in FR-012 (S-017, S-019); recipes (S-016 onwards).
