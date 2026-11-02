# Feature Specification: Share a notebook by email invite

**Feature Branch**: `057-notebook-invites`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml @dev/docs/prd.md S-057"

**Backlog story**: S-057 (Must). **PRD**: §1.5 flow H, §1.6, J1a, §3, Appendix A, AC1a.1, AC1a.3.

## Summary

A personal notebook is private to its owner and its members, but today nobody can become a member. With this feature the owner invites someone by email. The invited person accepts and becomes a notebook member, who can add, edit and delete its recipes. When they join, the ingredient names they already use are merged into the notebook's catalog, and the notebook's names win. A member can leave, and the owner can remove a member. Either way that person loses access at once, and everything they added stays in the notebook.

## Clarifications

### Session 2026-11-01

- Q: When someone with no account opens a notebook invite, how should they end up in the notebook? → A: They create an account as usual, set an alias, and return to the same link to join. Auth is unchanged.
- Q: Should opening an invite link join the person straight away, or should they first see the notebook's name and press a Join button? → A: Opening the link joins straight away, like a kitchen invite. Nothing is shown about the names.
- Q: Should the sharing view with open invites, cancel and resend (User Story 5) be built for tomorrow's delivery, or only part of it? → A: Build all of it: member list, open invites, cancel and resend.
- Q: Should there be a limit on how many notebook invite emails one person can send? → A: No limit, same as kitchen invites.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Invite someone who already has an account (Priority: P1)

Ana owns a personal notebook and wants Ben, who already uses Melos, to help keep it. She enters his email on the notebook's page. Ben gets an email, opens the link and lands in the notebook as a member. They now work on the same recipes.

**Why this priority**: This is the heart of the story. It is the only way two people can share a personal notebook, and it delivers value alone.

**Independent Test**: With two accounts, invite the second from the first's notebook, accept from the email link, then edit a recipe as the member and read it as the owner.

**Acceptance Scenarios**:

1. **Given** Ana owns a personal notebook, **When** she invites ben@example.test, **Then** an email with a link goes to that address, and she sees that the invite was sent.
2. **Given** Ben has an account with that email and is signed in, **When** he opens the link, **Then** he becomes a member of the notebook and lands on its page.
3. **Given** Ben has an account and is signed out, **When** he opens the link, **Then** he is asked to sign in and then joins as in scenario 2.
4. **Given** Ben is a member, **When** he edits a recipe, **Then** Ana sees the change in the same notebook (AC1a.1).
5. **Given** Ben is a member, **When** he adds, edits or deletes a recipe, or captures one into the notebook, **Then** it works as it does for the owner.
6. **Given** Ben is a member, **When** he opens his notebooks, **Then** the shared notebook is listed with his access as member and Ana's alias as owner.
7. **Given** Ben is a member, **When** he looks at the notebook's page, **Then** he has no controls to invite, remove members, rename or delete it.
8. **Given** Carla opens the link while signed in with a different email, **When** the link is used, **Then** she does not join, she sees that the invite is for another email, and the invite stays usable by Ben.

---

### User Story 2 - Names merge when someone joins (Priority: P1)

Ben has his own recipes, and he writes "onions" where Ana's notebook says "onion". When he joins, the notebook keeps its own name and gains only the names it does not have, so the two of them do not end up with two names for one ingredient.

**Why this priority**: The merge is what keeps a shared notebook's shopping lists and matching clean (AC1a.3). It happens once, at joining, so it cannot be added later for people who already joined.

**Independent Test**: Give the invited account a catalog that holds a plural of a notebook name and a name the notebook lacks. Accept the invite and compare the notebook's catalog with the expected result.

**Acceptance Scenarios**:

1. **Given** the notebook's catalog has "onion" and Ben's catalog has "onions", **When** Ben joins, **Then** no new name is added to the notebook's catalog (AC1a.3).
2. **Given** Ben's catalog has "saffron" and the notebook's does not, **When** Ben joins, **Then** "saffron" is added to the notebook's catalog.
3. **Given** Ben's catalog holds both "tomato" and "tomatoes" and the notebook has neither, **When** Ben joins, **Then** exactly one of them is added.
4. **Given** Ben has no personal notebook or an empty catalog, **When** he joins, **Then** the notebook's catalog does not change.
5. **Given** Ben joins, **When** the merge finishes, **Then** no recipe in the notebook or in Ben's other notebooks changes, and the catalogs of his other notebooks do not change.

---

### User Story 3 - Leave a notebook, or remove a member (Priority: P1)

Ben no longer wants to take part and leaves. Or Ana decides he should no longer have access and removes him. In both cases access ends at once, and the notebook keeps what he added.

**Why this priority**: Sharing has to be reversible, for privacy. Giving access with no way to take it back would not be safe to release.

**Independent Test**: Remove a member who is editing a recipe, then confirm that the person gets "not found" for the notebook and its recipes, that the lock has ended, and that their recipes are still there for the owner.

**Acceptance Scenarios**:

1. **Given** Ben is a member, **When** he leaves after confirming, **Then** he can no longer see the notebook or its recipes, and asking for them directly answers "not found".
2. **Given** Ben is a member, **When** Ana removes him after confirming, **Then** the same holds, and Ana sees he is no longer on the member list.
3. **Given** Ben added recipes and catalog names, **When** he leaves or is removed, **Then** they stay in the notebook, and his alias stays as their author.
4. **Given** Ben is editing a recipe of the notebook, **When** he leaves or is removed, **Then** his edit lock ends, his draft is dropped and anyone who can still write can edit the recipe (spec 022 FR-020b).
5. **Given** Ana owns the notebook, **When** she looks at its page, **Then** she has no way to leave it, and a direct attempt is refused (the owner can delete it instead, S-059).
6. **Given** Ben has left, **When** Ana invites him again and he accepts, **Then** he is a member again, with a new join date, and the merge runs again.

---

### User Story 4 - Invite someone new to Melos (Priority: P2)

Ana invites her sister, who has no account. The email takes her to create one. After that she joins the notebook.

**Why this priority**: The notebook works for people with accounts without this, but a family member with no account is a likely first invite.

**Independent Test**: Invite an address with no account, follow the link, create an account with that address and set an alias, then confirm the person lands in the notebook as a member.

**Acceptance Scenarios**:

1. **Given** no account has that email, **When** the person opens the link, **Then** they are offered to create an account or sign in, with the notebook's name and a masked form of the invited email shown.
2. **Given** they create an account with the invited email, **When** the account is ready and they have set their alias, **Then** they join the notebook and land on its page.
3. **Given** they create an account with a different email, **When** they reach the invite, **Then** they do not join and see that the invite is for another email.
4. **Given** email verification is required, **When** they have not verified, **Then** they are asked to verify and then join, and the invite stays usable until then.

---

### User Story 5 - See who is in the notebook and manage open invites (Priority: P2)

Ana opens the notebook's sharing view to see who has access and whose invites are still open. She typed one address wrong, so she cancels that invite. Another one expired, so she sends it again.

**Why this priority**: A mistyped address would otherwise hold a working link to a private notebook for days. The feature still works without this view, so it comes after the core flow.

**Independent Test**: Send two invites, cancel one and resend the other, then confirm that the cancelled link and the first resent link both fail and the newest link works.

**Acceptance Scenarios**:

1. **Given** a notebook with members, **When** the owner or a member opens its sharing view, **Then** they see the owner and every member by alias, and no email addresses.
2. **Given** open invites, **When** the owner opens the sharing view, **Then** she sees each invited email and when it expires, and a member sees no invites.
3. **Given** an open invite, **When** the owner cancels it, **Then** its link stops working and it leaves the list.
4. **Given** an open or expired invite, **When** the owner resends it, **Then** a new email goes out, a new 7-day period starts, and any earlier link for that address stops working.

---

### Edge Cases

- **Kitchen notebook**: cannot be shared by invite. Its people come from the kitchen. The control is not shown, and a direct attempt is refused.
- **Default notebook**: can be shared like any other personal notebook, and it stays its owner's default. It never becomes a member's default.
- **Inviting oneself, the owner or a current member**: refused with a plain message that the person is already in the notebook.
- **Invalid email**: refused with the same message as the kitchen invite, and nothing is sent.
- **Inviting the same address twice**: the newer invite replaces the older one, whose link stops working.
- **Used, expired, cancelled or replaced link**: shows one plain message that the invite is no longer valid, with no detail about why. It reveals nothing about the notebook.
- **Link opened by someone already in the notebook**: treated as a quiet success. They land on the notebook, and nothing changes.
- **Two presses or two tabs on one link**: one membership, and one merge.
- **Email cannot be sent**: the owner sees a clear error, and no usable invite remains (PRD §1.3, "fail loudly").
- **Notebook deleted while an invite is open** (S-059): the invite stops working.
- **Owner's account deleted while an invite is open** (S-058): the invite stays tied to the notebook, not to the person who sent it. It stays usable if the notebook passes to a new owner, and it ends if the notebook is deleted.
- **Person lacks an alias**: they set one first, as for any notebook page, then return to the invite.
- **Member removed during a capture**: the save is refused as "not found", no recipe is created, and their text stays on screen where the capture flow keeps it.
- **Member removed while viewing the notebook**: the next action answers "not found", and the app takes them back to their notebooks.
- **Leaving and the catalog**: names merged when a person joined stay in the notebook after they leave.
- **Personal catalog after leaving**: the notebook's names stop counting towards the person's own catalog, because that catalog is read from the notebooks they belong to.
- **Snapshots**: a member still cannot add the notebook to a kitchen, because that is owner only (spec 035 FR-002). Snapshots already taken do not change when people join or leave.
- **Capture**: a person with several personal notebooks picks one, as today, so joining a notebook adds a choice to that picker.
- **Merge failure**: joining is all or nothing. The person does not join, no name is added, the invite stays usable, and they can try again.
- **Merge is not reviewed**: nobody confirms the merge, since no recipe changes.

## Requirements *(mandatory)*

### Functional Requirements

**Inviting**

- **FR-001**: The owner of a personal notebook MUST be able to invite a person by email from the notebook's page.
- **FR-002**: A notebook member who tries to invite MUST be refused as an owner-only action, and a person who cannot see the notebook MUST get "not found" (AC1a.2).
- **FR-003**: Kitchen notebooks MUST NOT accept invites, and the control MUST NOT be shown on them.
- **FR-004**: The email address MUST be normalized and checked with the same rules as a kitchen invite. An invite to the owner or a current member MUST be refused.
- **FR-005**: The invite MUST be sent as an email in the inviter's account language, naming the notebook and the inviter's alias, with a link valid for 7 days. The notebook's name and the inviter's alias MUST be safe for email headers and HTML.
- **FR-006**: The link's token MUST be stored only in hashed form and MUST work once (PRD §1.6, same rules as a kitchen invite).
- **FR-007**: A new invite for the same notebook and email MUST end any earlier open invite for them.
- **FR-008**: If the email cannot be sent, the owner MUST see a clear error and no usable invite MUST remain.
- **FR-009**: The confirmation shown to the owner MUST NOT say whether the address has an account.

**Accepting**

- **FR-010**: A person who opens a valid link while signed in with the invited email MUST join as a notebook member and land on the notebook's page, with no Join button or other confirmation step.
- **FR-011**: The invited email MUST match the signed-in account, compared in normalized form. On a mismatch the person MUST NOT join and the invite MUST stay usable.
- **FR-012**: A person with no account MUST be able to create one and then join through the same link. Sign-up and the auth routes MUST NOT change: the join happens after the account exists and has an alias.
- **FR-013**: When email verification is required, joining MUST require a verified email, and the invite MUST stay usable until the person has verified.
- **FR-014**: A signed-out visitor who opens a link MUST see only the notebook's name, the inviter's alias and a masked form of the invited email. An invalid link MUST reveal nothing.
- **FR-015**: Accepting MUST be all or nothing, and repeated or simultaneous accepts MUST make one membership and one merge. Someone already in the notebook MUST land on it with nothing changed.
- **FR-016**: The membership MUST record the role of member and the join date, which S-058 uses to find the longest-standing member.

**Merging catalogs**

- **FR-017**: On joining, each name in the person's catalog (every name in the personal notebooks they belonged to just before joining) MUST be compared with the notebook's catalog using the fixed S-018 matching rule. Names that match MUST NOT be added, and names with no match MUST be added.
- **FR-018**: Names being added MUST also be matched against each other, so one ingredient is added once.
- **FR-019**: The merge MUST NOT use any AI step, change a recipe, change an existing catalog name, or change any other notebook. It MUST NOT ask for confirmation.

**Member access**

- **FR-020**: A notebook member MUST be able to read the notebook and add, edit and delete its recipes, and capture into it, as the owner can. Renaming and deleting it, inviting, and removing members MUST stay with the owner.
- **FR-021**: The owner and members MUST be able to see the owner and members of the notebook by alias. Emails MUST NOT be shown in this list.
- **FR-022**: Open invites, with their email and expiry, MUST be visible to the owner only.
- **FR-023**: The owner MUST be able to cancel an open invite, and to resend an open or expired one, which issues a new link under FR-005 to FR-007.

**Leaving and removal**

- **FR-024**: A member MUST be able to leave, and the owner MUST be able to remove a member. Both MUST ask for confirmation first.
- **FR-025**: The owner MUST NOT be able to leave or be removed, whether from the page or by a direct attempt.
- **FR-026**: Leaving or removal MUST delete the membership, and the person MUST lose all access at once: any later request answers "not found". Keeping an inactive membership is not allowed, because spec 022 FR-020b relies on the deletion to end the person's edit locks and drafts.
- **FR-027**: Recipes and catalog names the person added MUST stay in the notebook, with their authorship unchanged.
- **FR-028**: A person can be removed from a notebook only by its owner, and no email is sent on removal or on leaving.

**Language and access**

- **FR-029**: All new text, including the emails, MUST exist in English and Spanish, and MUST refer to a notebook.
- **FR-030**: The flows MUST work with a keyboard, at phone and desktop width, and announce their results to screen readers.

### Key Entities

- **Notebook invite**: an offer for one email address to join one personal notebook. It holds the hashed token, who sent it, when it expires, and when it was used. It is open until it is used, expires, is cancelled or is replaced.
- **Notebook membership**: a person's place in a personal notebook, with the role of owner or member and a join date. There is one owner, and leaving or removal deletes the membership.
- **Personal catalog**: every ingredient name in the personal notebooks a person belongs to. It is read, not stored.
- **Notebook catalog**: the notebook's set of unique names, which grows when someone joins.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An owner can send an invite in 3 steps or fewer from the notebook's page.
- **SC-002**: A signed-in person with an account joins from the email link in one step, and lands on the notebook within 3 seconds.
- **SC-003**: Joining with a personal catalog of 500 names and a notebook catalog of 500 names finishes in under 2 seconds.
- **SC-004**: For a sample of catalogs that includes plurals, accents and letter-case variants, 100% of names that match are left out, and 100% of names with no match are added once.
- **SC-005**: In access tests, 100% of attempts by people who are not the owner to invite, cancel, resend or remove are refused, and 100% of requests by a person who has left or been removed answer "not found".
- **SC-006**: 100% of used, expired, cancelled and replaced links fail, and none of them reveals the notebook.
- **SC-007**: A failure forced at any point of accepting leaves 0 new memberships and 0 new catalog names, and the invite stays usable.
- **SC-008**: After a person leaves or is removed, 100% of the recipes and catalog names they added are still in the notebook.

## Assumptions

- **Sign-up path** (FR-012, decided 2026-11-01): the kitchen invite joins during sign-up, inside the auth route, and that route takes kitchen tokens only. The constitution keeps the auth layer unchanged without explicit approval, and notebook routes need an alias, which a new account does not have yet. So a new person creates an account in the usual way and then comes back to the same link. They also still get their "My kitchen", as with any sign-up. Their personal catalog is empty at that point, so the merge adds nothing.
- **Reuse**: "reuses the kitchen invite flow" (PRD J1a) is read as the same token rules, 7-day life, email normalization, email binding, verification gate and safe preview. Notebook invites are stored separately (PRD §1.6 `notebook_invite`).
- **Inviter's name** (FR-005): the email names the inviter by alias, where the kitchen email uses their email address. A personal notebook always has an alias behind it, and an alias shares less.
- **Sent emails**: the existing Spanish kitchen emails say "lista" for a kitchen. The notebook emails must not copy that wording (FR-029). Fixing the kitchen emails is out of scope.
- **Open invites and cancel** (User Story 5): included in full (decided 2026-11-01), because PRD Appendix A lists them in the v1 UI.
- **Member list** (FR-021): the PRD lets members read memberships, but it does not say what they see. Aliases only, matching the kitchen's member list.
- **Rate limits** (decided 2026-11-01): kitchen invites have no rate limit on sending, and this feature adds none. Only the owner can send, and only for their own notebooks.
- **Merge is silent**: the PRD asks people to review name changes only when a recipe is copied or captured. Joining changes no recipe, so nothing is shown.
- **Removal and locks**: spec 022 already ends a person's locks when their membership row is deleted. This feature relies on that and tests it.
- **Access already built**: reading and writing by notebook members exists from specs 056, 020 and 027, but it could never be reached. This feature tests it end to end (AC1a.1).
- **Owner cannot leave**: the owner's way out is deleting the notebook (S-059), which is not built yet. Passing ownership on account deletion is S-058.
- **Schedule**: S-057 is a Must, and the delivery date is 02/11/2026.
- **Out of scope**: passing ownership (S-058), creating, renaming or deleting notebooks (S-059), leaving or removing members of a kitchen, reassigning a recipe's author, notifying the owner when someone joins or leaves, roles between member and owner, and sharing by link without an email.
