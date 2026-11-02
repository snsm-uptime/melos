# Feature Specification: Notebook ownership passes on when an owner's account is deleted

**Feature Branch**: `058-notebook-ownership-passing`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml @dev/docs/prd.md S-058"

**Backlog story**: S-058 (Must). **PRD**: §1.5 flow H, §1.6, J1a edge cases, §3, Appendix A (User).

## Summary

A personal notebook has exactly one owner, and only the owner can invite and remove people, and the owner cannot leave. If the owner's account is deleted, the people still using the notebook must not be left with one that nobody runs, and a notebook nobody else uses must not linger with no one able to reach it.

With this feature, when an owner's account is deleted, each personal notebook they own passes to its longest-standing member. A notebook with no members is deleted.

No way to delete an account exists yet. This story delivers the rule that account deletion (S-054) will call, and S-054 must not ship without it. Nobody sees a change until then.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A shared notebook passes to its longest-standing member (Priority: P1)

Ana owns a notebook she shares with Ben, who joined in March, and Carla, who joined in June. Ana deletes her account. Ben becomes the owner, Carla stays a member, and all the recipes are still there.

**Why this priority**: This is the reason for the story. Without it, deleting an account would leave people in a notebook with no owner, or take their shared recipes from them.

**Independent Test**: Make a notebook with an owner and two members who joined on different dates, run the rule for the owner, and check who owns it, who belongs to it and what it holds.

**Acceptance Scenarios**:

1. **Given** Ana owns a notebook with members Ben (joined first) and Carla, **When** Ana's account is deleted, **Then** Ben is its owner and Carla is still a member.
2. **Given** Ben has become the owner, **When** he opens the notebook, **Then** he can invite and remove members, as any owner can, and Ana is no longer listed.
3. **Given** Carla is still a member, **When** she opens her notebooks, **Then** the notebook shows Ben's alias as owner, and her access is unchanged.
4. **Given** the notebook has recipes by Ana, Ben and Carla, **When** Ana's account is deleted, **Then** every recipe stays, Ana's read "unknown" as author, and the others keep their authors.
5. **Given** the notebook has a catalog of ingredient names, **When** it passes to Ben, **Then** the catalog is unchanged.
6. **Given** the notebook is called "Ana's Notebook", **When** it passes to Ben, **Then** its name is unchanged.
7. **Given** Ana owns several notebooks with different members, **When** her account is deleted, **Then** each one is decided on its own and may pass to a different person.

---

### User Story 2 - A notebook with no members is deleted (Priority: P1)

Ana also owns a notebook she never shared. When she deletes her account, nobody else can reach it, so it is deleted with its recipes.

**Why this priority**: A notebook with no people in it can never be opened again. It is the other half of the same rule, and an account deletion must handle both.

**Independent Test**: Make a notebook with an owner and no members, with recipes, an ingredient catalog and a snapshot in a kitchen. Run the rule and check that the notebook is gone and the snapshot remains.

**Acceptance Scenarios**:

1. **Given** Ana owns a notebook with no members, **When** her account is deleted, **Then** the notebook, its recipes and its catalog are deleted.
2. **Given** a kitchen holds a snapshot of that notebook, **When** the notebook is deleted, **Then** the snapshot stays with all its recipes and no longer names where it came from.
3. **Given** that notebook has an open invite, **When** it is deleted, **Then** the invite link no longer works, and it says so as for any invite that is no longer valid.

---

### User Story 3 - People and places that are not the owner's are left alone (Priority: P2)

Ana is also a plain member of Dana's notebook and belongs to a kitchen. The rule does not touch what Ana does not own.

**Why this priority**: The rule changes who holds a notebook, so it must be clear where it stops. A mistake here would take a notebook away from someone who still owns it.

**Independent Test**: Give a person a mix of owned notebooks, notebooks they are a member of and kitchen notebooks. Run the rule and check that only the owned personal notebooks changed hands.

**Acceptance Scenarios**:

1. **Given** Ana is a member of Dana's notebook, **When** Ana's account is deleted, **Then** Dana still owns it, Ana is no longer a member, and what Ana added stays.
2. **Given** Ana's kitchen has a kitchen notebook, **When** the rule runs, **Then** everyone in the kitchen keeps the same access and its recipes stay, because a kitchen notebook belongs to the kitchen. Only the record of who created it is cleared.
3. **Given** Ana's notebook has a snapshot in a kitchen, **When** the notebook passes to Ben, **Then** the snapshot does not change and keeps its origin label.

---

### Edge Cases

- **Joined at the same moment**: two members with the same joining time are put in a fixed order, so running the rule twice on the same data picks the same person.
- **Left and came back**: a member who left or was removed and later rejoined counts from their latest joining, because the earlier membership no longer exists.
- **Open invites on a notebook that passes**: they stay open and the link still joins the notebook. A person opening one sees no sender's name, as for any invite whose sender is gone. The new owner sees them and can cancel or resend them, and a resend goes out in the new owner's name.
- **The new owner wants out**: an owner cannot leave. Until notebook deletion is built (S-059), a person who inherits a notebook they do not want has no way out of it, the same as any owner today.
- **The new owner's default notebook**: it stays the one they already had. An inherited notebook does not replace it.
- **The new owner's account is deleted later**: the same rule applies again, from the members remaining at that time.
- **A member joins or leaves while the rule runs**: the outcome is one that could have happened in either order, and the notebook ends up with exactly one owner.
- **A failed deletion**: if the account deletion does not complete, no notebook has changed hands and none has been deleted.
- **A notebook with an open invite but no members**: an invited person is not a member, so the notebook is deleted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When an account is deleted, the system MUST settle every personal notebook that account owns, each on its own, by passing it on or deleting it.
- **FR-002**: A personal notebook with at least one member MUST pass to its longest-standing member: the one with the earliest current joining time. The role of that person becomes owner.
- **FR-003**: When members share the same joining time, the system MUST pick among them by a fixed order, so the result is repeatable.
- **FR-004**: The other members of a notebook that passes MUST keep their membership and their original joining times, and the new owner's joining time MUST not change.
- **FR-005**: A notebook that passes MUST keep its name, recipes, recipe authors, ingredient catalog, open invites and snapshot links, apart from the deleted person's authorship, which reads "unknown".
- **FR-006**: From the moment it passes, the new owner MUST have everything an owner has, and the deleted person MUST no longer appear as owner or member anywhere.
- **FR-007**: A personal notebook with no members MUST be deleted, with its recipes, catalog and invites. Open invites do not count as members.
- **FR-008**: Deleting a notebook this way MUST leave snapshots made from it in place, and clear the snapshot's origin label.
- **FR-009**: Personal notebooks the person is only a member of, and all kitchen notebooks, MUST not change owner. Recipes they added stay, with the author reading "unknown".
- **FR-010**: A personal notebook MUST have exactly one owner once the rule has finished, under simultaneous joins and departures too.
- **FR-011**: Settling the notebooks and deleting the account MUST succeed or fail together. If either fails, nothing changes.
- **FR-012**: The system MUST NOT keep a record of past owners. The notebook shows only its current owner.
- **FR-013**: The rule MUST be available for the account deletion in S-054 to use.
- **FR-014**: This story MUST NOT change the sign-in, session or account routes.

### Key Entities

- **Personal notebook**: has one owner and any number of members. Its owner may change through this rule; nothing else changes that.
- **Notebook membership**: a person's place in a notebook, with a role (owner or member) and the time they joined, which decides who inherits.
- **Notebook invite**: an offer to join a notebook. It belongs to the notebook, so it outlives its sender. It is not a membership.
- **Snapshot**: an independent kitchen copy of a personal notebook, with a label naming where it came from. It is not affected unless the original is deleted, and then only the label goes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an owner's account is deleted, 100% of the personal notebooks they owned that had members have exactly one owner, and it is the longest-standing member.
- **SC-002**: After an owner's account is deleted, none of the personal notebooks they owned without members remains.
- **SC-003**: No recipe, ingredient name or member of a notebook that passes is lost, other than the deleted person's own membership.
- **SC-004**: No personal notebook without an owner exists after any account deletion, including one that fails midway.
- **SC-005**: Running the rule twice on identical data gives the same new owner every time.
- **SC-006**: The new owner can invite someone to the inherited notebook on their next visit, with no step on their part.

## Assumptions

- **Scope**: this story is the rule alone. The account deletion itself (the route, the confirmation, removing memberships and conversations, deleting kitchens the person alone owns) stays in S-054. The backlog sets this order: S-054 depends on S-058. Until S-054 ships, the rule runs only in tests.
- **No notice to the new owner**: neither the PRD nor the backlog asks for one, so the new owner is not told by email or in the app. They see themselves as owner in their notebooks. The deleted person's members are not told either.
- **S-054 must use the rule**: S-054 must not ship without it. The backlog records this as a condition on that story.
- **Copies**: "Copy to notebook" (flow G) is not built yet. When it is, a copy has no link to the original, so deleting a notebook will leave its copies in place.
- **Kitchen notebooks**: they belong to the kitchen and have no owner in the sense of this rule. The app stores who created one, to find a member's own notebook for capture, and that record is cleared with the account.
- **Accounts are removed only through the rule**: an account removed by hand in the database is outside this story.
- **Kept as is**: a notebook's name is fixed when made and is not translated or changed, including "{alias}'s Notebook" names that still carry the old owner's alias. Renaming comes with S-059.
- **Joining time**: the time on the current membership decides. The owner's own creation of the notebook plays no part, as the owner is leaving.
- **Author "unknown"**: already how recipes behave when an author's account is gone (PRD §3), so this story adds nothing there.
