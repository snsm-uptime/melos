---

description: "Task list for sharing a notebook by email invite"
---

# Tasks: Share a notebook by email invite

**Input**: Design documents from `specs/057-notebook-invites/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/notebook-sharing-api.md](contracts/notebook-sharing-api.md), [quickstart.md](quickstart.md)

**Tests**: Included, because constitution principle 6 requires them at the domain, application, integration and ui layers.

**Organization**: Tasks are grouped by user story so each can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Start from the right branch and a known test baseline

- [X] T001 Create branch `057-notebook-invites` from the current `main`, keeping `specs/057-notebook-invites/`, `.specify/feature.json`, and the changes to `dev/docs/backlog.yaml` and `dev/memory/011126.md`
- [X] T002 Record the baseline in `specs/057-notebook-invites/notes.md`: api failures from `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, and the ui result of `npm test`, so failures that predate this story are known

---

## Phase 2: Foundational

**Purpose**: The table, errors, rules and ports every story needs

**CRITICAL**: No user story work starts until this phase is complete

- [X] T003 Add `NotebookInviteModel` (table `notebook_invite`) in `api/adapters/persistence/models.py`: `id` uuid primary key; `notebook_id` uuid not null, FK `notebook.id` `ON DELETE CASCADE`; `email` varchar(320) not null, normalized; `token_hash` varchar(64) not null, unique; `invited_by` uuid nullable, FK `users.id` `ON DELETE SET NULL`; `expires_at` timestamptz not null; `used_at` timestamptz nullable; `created_at` timestamptz not null, default `now()`; and index `uq_notebook_invite_open`, unique on `(notebook_id, email)` where `used_at IS NULL`
- [X] T004 Create migration `0012_notebook_invite`, with `down_revision` `0011_notebook_snapshot_key`, creating the table and index on upgrade and dropping them on downgrade, in `api/adapters/persistence/migrations/versions/0012_notebook_invite.py`
- [X] T005 [P] Add to `api/domain/errors.py`, each with `MESSAGE` and `CODE`: `NotebookNotShareableError` (`notebook_not_shareable`), `NotebookOwnerOnlyError` (`notebook_owner_only`), `AlreadyInNotebookError` (`already_in_notebook`), `NotebookOwnerStaysError` (`notebook_owner_stays`), `NotebookInviteNotFoundError` (`notebook_invite_not_found`), `NotebookMemberNotFoundError` (`notebook_member_not_found`)
- [X] T006 Create `api/domain/notebook_invite.py` with `NOTEBOOK_INVITE_PATH = "/invites/notebook"`, `build_notebook_invite_link(public_app_url, raw_token)`, `assert_shareable(kind)` (raises `NotebookNotShareableError` for a kitchen notebook) and `assert_can_manage_sharing(kind, access)` (also raises `NotebookOwnerOnlyError` unless access is `owner`), with tests in `api/tests/test_notebook_invite_domain.py`
- [X] T007 Add to `api/application/ports.py`: `NotebookInviteRecord` (id, notebook_id, email, token_hash, invited_by, expires_at, used_at); a `NotebookInviteRepository` protocol with `create`, `delete_open_for_email`, `list_unused`, `get`, `get_by_token_hash`, `rotate`, `delete`, `claim`; `NotebookMemberRecord` (user_id, alias, role); and on `NotebookRepository`: `lock_notebook`, `members_of`, `role_of`, `add_member`, `delete_membership`
- [X] T008 Create `SqlAlchemyNotebookInviteRepository` in `api/adapters/persistence/notebook_invites.py`; `claim` calls `claim_single_use_email_token`, `list_unused` returns rows with `used_at IS NULL` newest first, and `delete` and `get` are scoped to the notebook id
- [X] T009 Implement in `api/adapters/persistence/notebooks.py`: `lock_notebook` (`with_for_update(key_share=True)`, as `lock_kitchen`), `members_of` (owner first, then `created_at`, with the alias), `role_of`, `add_member` (role `member`) and `delete_membership` (a SQL delete, so the foreign key ends the locks; returns whether a row went)
- [X] T010 Add shared fakes for the two ports and an email sender in `api/tests/notebook_sharing_fakes.py`
- [X] T011 Test upgrade, downgrade and upgrade on a scratch database with invented rows, and record the result in `specs/057-notebook-invites/notes.md`

**Checkpoint**: The stack runs and existing tests still pass

---

## Phase 3: User Story 1 - Invite someone who already has an account (Priority: P1) 🎯 MVP

**Goal**: The owner invites by email, and a signed-in person with that email joins by opening the link.

**Independent Test**: With two accounts, invite the second from the first's notebook, accept from the email link, then edit a recipe as the member and read it as the owner.

### Tests for User Story 1

- [X] T012 [P] [US1] Application tests with fakes for sending in `api/tests/test_notebook_invites_application.py`: owner sends; member gets `NotebookOwnerOnlyError`; stranger gets `NotebookNotFoundError`; kitchen notebook gets `NotebookNotShareableError`; bad email; owner or member as invitee gets `AlreadyInNotebookError`; a repeat deletes the earlier row; the result has no sign of whether the address has an account; Spanish email says "cuaderno" and never "lista"; line breaks in the name and alias are stripped from the subject and HTML is escaped
- [X] T013 [P] [US1] Application tests with fakes for accepting and preview in the same file: join; quiet success when already in; a live link for another email is a mismatch and stays usable; a dead link for another email is invalid, not a mismatch; used, expired and unknown tokens are invalid; a lost claim with a membership succeeds; the service commits once
- [X] T014 [P] [US1] Integration tests in `api/tests/test_notebook_invites_integration.py`: both routes per the contract; every dead-link kind returns an identical 410 body (SC-006); a failed email stores nothing and leaves an earlier invite working (FR-008, research R7); an invited member reads, adds, edits and deletes recipes and captures (AC1a.1, FR-020); a member gets 404 on snapshot of it as a source (spec 035 FR-002); a default notebook stays the owner's and `is_default` is false for the member
- [X] T015 [P] [US1] Vitest tests for the panel in `ui/app/invites/notebook/AcceptNotebookInvitePanel.test.tsx` and the client in `ui/app/invites/notebookInviteClient.test.ts`: join and land, `alias_required`, `email_not_verified`, mismatch, invalid

### Implementation for User Story 1

- [X] T016 [US1] In `api/application/notebook_invites.py`, add `build_notebook_invite_email` (EN and ES, inviter's alias and notebook name, 7 days, one link, "cuaderno" in Spanish) reusing `_safe_header_text` from `application/kitchen_invite.py`, and `SendNotebookInviteService`: validate the email, load `facts_for` (none or no access gives `NotebookNotFoundError`), `assert_can_manage_sharing`, refuse a person already in the notebook, `lock_notebook`, `delete_open_for_email`, `create`, send. Locale comes from `resolve_invite_locale`
- [X] T017 [US1] Add `PreviewNotebookInviteService` in `api/application/notebook_invites.py`, returning `notebook_name`, `inviter_alias` (null with no sender) and `email_hint`, with no `path` field
- [X] T018 [US1] Add `AcceptNotebookInviteService` in `api/application/notebook_invites.py`, in the exact order of research R4, with a `TransactionCommitter` commit before returning
- [X] T019 [US1] Add request and response models in `api/api/schemas/notebook_invites.py`
- [X] T020 [US1] Add `POST /notebooks/{id}/invites` in `api/api/routes/notebooks.py`, mapping errors per the contract, reusing the SMTP response of `api/api/routes/kitchens.py` (move `_smtp_error_response` somewhere shared or call an equal helper), with `db.rollback()` on SMTP errors; log ids and outcomes, never the address
- [X] T021 [US1] Add `GET /invites/notebook/preview` and `POST /invites/notebook/accept` in `api/api/routes/invites.py`; accept depends on `require_user_alias`, the 410 detail speaks of a notebook, and **every** error branch calls `db.rollback()` (research R4)
- [X] T022 [P] [US1] Add BFF routes in `ui/app/api/invites/notebook/preview/route.ts` and `ui/app/api/invites/notebook/accept/route.ts`, and `ui/app/api/notebooks/[notebookId]/invites/route.ts` (POST), following `ui/app/api/invites/accept/route.ts`, with tests in `ui/app/api/notebooks.bff.test.ts`
- [X] T023 [P] [US1] Add `notebookInvite` messages (EN and ES, parity test passing, "notebook" and "cuaderno") in `ui/lib/i18n/invite.ts`, and sharing page messages in `ui/lib/i18n/notebooks.ts`
- [X] T024 [US1] Add `fetchNotebookInvitePreview` and `acceptNotebookInvite` in `ui/app/invites/notebookInviteClient.ts`
- [X] T025 [US1] Add `ui/app/invites/notebook/page.tsx` and `ui/app/invites/notebook/AcceptNotebookInvitePanel.tsx`: signed in, join on open with no button, then go to `/notebooks/{id}`; handle `alias_required` with `aliasSetupHref`, and `email_not_verified` with `/verify?returnTo=`; signed out, show the preview with Sign in (`returnTo`). Add `/invites/notebook` to `LANGUAGE_SWITCH_PREFIXES` in `ui/lib/appChrome.ts`
- [X] T026 [US1] Add `inviteToNotebook` in `ui/lib/notebooksClient.ts`, and `ui/app/notebooks/[notebookId]/sharing/page.tsx` with `NotebookSharingScreen.tsx` holding the invite form for the owner, with a `role="status"` result and test `NotebookSharingScreen.test.tsx`
- [X] T027 [US1] Link to the sharing page from `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.tsx`, on personal notebooks only, and test that it's absent on a kitchen notebook in `NotebookRecipesScreen.test.tsx`

**Checkpoint**: Two people share a notebook. Names don't merge yet

---

## Phase 4: User Story 2 - Names merge when someone joins (Priority: P1)

**Goal**: Joining adds only the names the notebook lacks, and the notebook's names win.

**Independent Test**: Give the invited account a catalog with a plural of a notebook name and a name the notebook lacks. Accept the invite and compare the notebook's catalog with the expected result.

### Tests for User Story 2

- [X] T028 [P] [US2] Domain tests in `api/tests/test_ingredient_catalog_domain.py`: "onions" against "onion" adds nothing; "saffron" is added; "tomato" and "tomatoes" add one; accents and letter case; empty input; agreement with `match_line` on a sample; 500 by 500 names under 2 seconds (SC-003, SC-004)
- [X] T029 [P] [US2] Integration tests in `api/tests/test_notebook_invites_integration.py`: AC1a.3; a person with no notebook; no recipe and no other catalog changes (FR-019); simultaneous accepts make one membership and one merge (FR-015); a failure forced at each step after the claim leaves 0 memberships and 0 names, and the invite usable (SC-007); after joining, the names of the target notebook were not counted as the person's

### Implementation for User Story 2

- [X] T030 [US2] Add `names_to_add(incoming, existing)` in `api/domain/ingredient_catalog.py`, linear, per research R6: sorted input; sets of keys and of all `singular_forms`; each accepted name joins both sets
- [X] T031 [US2] In `AcceptNotebookInviteService`, after the claim and before `add_member`, call `names_for_person`, `names_for_notebook`, `names_to_add` and `add_names`, in `api/application/notebook_invites.py`

**Checkpoint**: US1 and US2 together meet AC1a.1 and AC1a.3

---

## Phase 5: User Story 3 - Leave a notebook, or remove a member (Priority: P1)

**Goal**: A member leaves or the owner removes them, access ends at once, and their work stays.

**Independent Test**: Remove a member who is editing a recipe, then confirm that the person gets "not found" for the notebook and its recipes, that the lock has ended, and that their recipes are still there for the owner.

### Tests for User Story 3

- [X] T032 [P] [US3] Application tests with fakes in `api/tests/test_notebook_members_application.py`: list as owner and as member; leave; owner can't leave; remove; member can't remove; owner can't be removed; missing target; kitchen notebook refused
- [X] T033 [P] [US3] Integration tests in `api/tests/test_notebook_members_integration.py`: after leaving or removal, notebook, recipes and capture answer 404 (SC-005); the person's `recipe_edit_lock` row is gone and someone else can edit (FR-026); recipes, authors and names stay (SC-008); a rejoin gets a new join date and merges again; the member list has no email (FR-021)
- [X] T034 [P] [US3] Vitest tests in `ui/app/notebooks/[notebookId]/NotebookSharingScreen.test.tsx`: confirm dialogs for leave and remove, owner sees no Leave, member sees no Remove; and in `NotebookRecipesScreen.test.tsx` a 404 goes to `/notebooks`

### Implementation for User Story 3

- [X] T035 [US3] Create `api/application/notebook_members.py` with `ListNotebookMembersService`, `LeaveNotebookService` and `RemoveNotebookMemberService`, with checks in the contract's order; remove takes `lock_notebook`; no email goes out (FR-028)
- [X] T036 [US3] Add `GET /notebooks/{id}/members`, `DELETE /notebooks/{id}/members/me` and `DELETE /notebooks/{id}/members/{user_id}` in `api/api/routes/notebooks.py`, declaring `me` before `{user_id}`, with schemas in `api/api/schemas/notebook_invites.py`
- [X] T037 [P] [US3] Add BFF routes `ui/app/api/notebooks/[notebookId]/members/route.ts`, `members/me/route.ts` and `members/[userId]/route.ts`, with tests in `ui/app/api/notebooks.bff.test.ts`
- [X] T038 [US3] Add `fetchNotebookMembers`, `leaveNotebook` and `removeNotebookMember` in `ui/lib/notebooksClient.ts`
- [X] T039 [US3] Add the member list, with "unknown" for a null alias, plus Leave and Remove through `ActionDialog`, in `NotebookSharingScreen.tsx`; after leaving, go to `/notebooks`
- [X] T040 [US3] Send a 404 to `/notebooks` in `NotebookRecipesScreen.tsx` and `NotebookSharingScreen.tsx`

**Checkpoint**: All P1 stories work; this is shippable

---

## Phase 6: User Story 4 - Invite someone new to Melos (Priority: P2)

**Goal**: A person with no account creates one, then joins through the same link.

**Independent Test**: Invite an address with no account, follow the link, create an account with that address and set an alias, then confirm the person joins as a member.

### Tests for User Story 4

- [X] T041 [P] [US4] Integration tests in `api/tests/test_notebook_invites_integration.py`: no account means a preview with the same fields as for an existing account (research R5); a new account with the invited email joins and adds no names; a different email is a mismatch; with verification required, `email_not_verified` leaves the invite usable until verified, and the auth routes get no notebook token
- [X] T042 [P] [US4] Vitest tests in `AcceptNotebookInvitePanel.test.tsx`: signed out shows the name, alias, masked email, Sign in and Create account, and the note to reopen the link

### Implementation for User Story 4

- [X] T043 [US4] Add the Create account link to plain `/signup` and the reopen note in `ui/app/invites/notebook/AcceptNotebookInvitePanel.tsx`, with EN and ES text in `ui/lib/i18n/invite.ts`. Do not change `ui/app/signup/` or `api/api/routes/auth.py` (FR-012, research R8)

**Checkpoint**: A new person can join

---

## Phase 7: User Story 5 - See who is in the notebook and manage open invites (Priority: P2)

**Goal**: The owner sees open and expired invites, cancels and resends them.

**Independent Test**: Send two invites, cancel one and resend the other, then confirm that the cancelled link and the first resent link both fail and the newest link works.

### Tests for User Story 5

- [X] T044 [P] [US5] Application tests with fakes in `api/tests/test_notebook_invites_application.py`: list as owner with `expired` set; member refused; resend open and expired; cancel; accepted invite gives `NotebookInviteNotFoundError`; another notebook's invite id gives the same error
- [X] T045 [P] [US5] Integration tests in `api/tests/test_notebook_invites_integration.py`: cancelled and earlier resent links fail with the identical 410; resend starts a new 7 days; failed resend keeps the previous link (research R7); non-owners refused (SC-005); an invite outlives its sender with `invited_by` null, and ends with the notebook
- [X] T046 [P] [US5] Vitest tests in `NotebookSharingScreen.test.tsx`: invites listed for the owner, none for a member, expired marked, resend, cancel with confirmation

### Implementation for User Story 5

- [X] T047 [US5] Add `ListNotebookInvitesService`, `ResendNotebookInviteService` (same email builder; refuses a person now in the notebook; `rotate` sets a new `token_hash`, `expires_at` and `invited_by`) and `CancelNotebookInviteService` in `api/application/notebook_invites.py`
- [X] T048 [US5] Add `GET /notebooks/{id}/invites`, `POST /notebooks/{id}/invites/{invite_id}/resend` and `DELETE /notebooks/{id}/invites/{invite_id}` in `api/api/routes/notebooks.py`, with `db.rollback()` on SMTP errors
- [X] T049 [P] [US5] Add GET to `ui/app/api/notebooks/[notebookId]/invites/route.ts`, and `invites/[inviteId]/route.ts` and `invites/[inviteId]/resend/route.ts`, with tests in `ui/app/api/notebooks.bff.test.ts`
- [X] T050 [US5] Add `fetchNotebookInvites`, `resendNotebookInvite` and `cancelNotebookInvite` in `ui/lib/notebooksClient.ts`
- [X] T051 [US5] Add the owner's invite list with expiry, Resend and Cancel (through `ActionDialog`) in `NotebookSharingScreen.tsx`, refreshing after a send

**Checkpoint**: All five stories work

---

## Phase 8: Polish

**Purpose**: Whole-feature checks and records

- [X] T052 Change `accepted_at` to `used_at` in the `notebook_invite` line of `dev/docs/prd.md` §1.6 (research R2)
- [X] T053 [P] Check `ui/lib/i18n/parity.test.ts` passes and that no new Spanish text says "lista" for a notebook (FR-029)
- [X] T054 Run the automated checks in `specs/057-notebook-invites/quickstart.md`: the api suite in Compose, `uv run ruff check .` and `npm test && npm run lint && npm run typecheck`, and record the results in `specs/057-notebook-invites/notes.md`
- [X] T055 Walk the browser steps of `specs/057-notebook-invites/quickstart.md` at 360px and 1280px, in both languages and with a keyboard only (FR-030), on an isolated stack, and record the results and step 10's capture finding (research R12) in `specs/057-notebook-invites/notes.md`
- [X] T056 Update S-057's status and verification in `dev/docs/backlog.yaml`, from the recorded results only

---

## Dependencies & Execution Order

- **Setup, then Foundational**: both come before any story.
- **US1**: needs Foundational.
- **US2**: needs the accept service from US1 (T018). T028 and T030 can start earlier.
- **US3**: needs Foundational and the sharing page from US1 (T026). Its integration tests need members, so they also need US1.
- **US4**: needs the link page from US1 (T025).
- **US5**: needs the send service and sharing page from US1.
- **Polish**: after the stories that will ship.

Order within a story: tests, then domain, application, routes, BFF, client, screens. Write each test first and see it fail.

`NotebookSharingScreen.tsx`, `api/application/notebook_invites.py`, `api/api/routes/notebooks.py` and `ui/lib/notebooksClient.ts` are shared by several stories, so tasks on them run one at a time.

## Parallel Examples

```text
Foundational: T005 alongside the start of T003
US1 tests:    T012, T013, T014, T015
US1 ui:       T022, T023
US2 tests:    T028, T029
US3 tests:    T032, T033, T034
US5 tests:    T044, T045, T046
```

## Implementation Strategy

1. **First cut**: Phases 1 to 5 (US1, US2, US3). This is the safe minimum to release: sharing, the merge, and a way to end sharing. US1 alone isn't releasable, because access couldn't be taken back and the merge can't be added later for people who already joined.
2. **Next**: US4, one small task, then US5.
3. **Last**: Polish, including the browser walk. Stop and report if the walk finds a failure.
