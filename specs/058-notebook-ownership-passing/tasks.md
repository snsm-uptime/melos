---

description: "Task list for notebook ownership passing on account deletion"
---

# Tasks: Notebook ownership passes on when an owner's account is deleted

**Input**: Design documents from `specs/058-notebook-ownership-passing/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/ownership-rule.md](contracts/ownership-rule.md), [quickstart.md](quickstart.md)

**Tests**: Included, because constitution principle 6 requires them at the domain, application and integration layers. There are no ui tasks except T021: nothing changes in the ui (research R10).

**Organization**: Tasks are grouped by user story so each can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Start from the right branch and a known test baseline

- [ ] T001 Create branch `058-notebook-ownership-passing` from the current `main`, keeping `specs/058-notebook-ownership-passing/`, `.specify/feature.json`, and the changes to `dev/docs/backlog.yaml` and `dev/memory/011126.md`
- [ ] T002 Record the baseline in `specs/058-notebook-ownership-passing/notes.md`: run `uv run pytest -q` in `api/` against a throwaway tmpfs `pgvector/pgvector:pg16` container on its own port with the CI environment, the working setup in [quickstart.md](quickstart.md); the Compose overlay is the final check in T023

---

## Phase 2: Foundational

**Purpose**: The port surface and the service skeleton every story uses

**⚠️ CRITICAL**: No story can start until this phase is done

- [ ] T003 Add `joined_at: datetime` to `NotebookMemberRecord`, and the protocol methods `owned_personal_ids(user_id) -> list[UUID]`, `make_owner(notebook_id, user_id) -> None` and `delete_personal(notebook_id) -> None` to `NotebookRepository`, in `api/application/ports.py`; note on `lock_notebook` that it raises `NotebookNotFoundError` for a missing row
- [ ] T004 In `api/adapters/persistence/notebooks.py`, select `NotebookMembershipModel.created_at` as `joined_at` in `members_of`, and add `owned_personal_ids` (rows with `role = 'owner'` joined to notebooks with `kitchen_id IS NULL`) and `make_owner` (updates `role` only, so `created_at` is kept)
- [ ] T005 Add the same methods and `joined_at` to `FakeNotebooks` in `api/tests/notebook_sharing_fakes.py`, keeping the `log` of calls in order, make its `lock_notebook` raise `NotebookNotFoundError` for an unknown notebook, and fix any test that builds a `NotebookMemberRecord` without it

**Checkpoint**: `uv run pytest -q` passes as at the baseline

---

## Phase 3: User Story 1 - A shared notebook passes to its longest-standing member (Priority: P1) 🎯 MVP

**Goal**: The longest-standing member becomes owner, and everything else in the notebook stays.

**Independent Test**: Make a notebook with an owner and two members who joined on different dates, run the service, and check who owns it, who belongs to it and what it holds.

### Tests for User Story 1

- [ ] T006 [P] [US1] In `api/tests/test_notebook_domain.py`, test `longest_standing`: earliest `joined_at` wins, the owner is ignored, a tie on `joined_at` goes to the lowest `user_id` in any input order, and no members gives `None` (FR-002, FR-003)
- [ ] T007 [P] [US1] In `api/tests/test_notebook_ownership_application.py` (new), test against `FakeNotebooks`: locks come in sorted id order, each lock comes before the role re-read, the old owner's membership is deleted before `make_owner` (research R4), a notebook no longer owned after the lock is skipped, a second run changes nothing, a person with no notebooks gets an empty result, several notebooks can go to different heirs, and the service makes no commit
- [ ] T008 [P] [US1] In `api/tests/test_notebook_members_application.py`, test that leaving takes `lock_notebook` and that a caller whose `role_of` reads `owner` after the lock gets `NotebookOwnerStaysError` with no membership deleted (research R6)
- [ ] T009 [US1] In `api/tests/test_notebook_ownership_integration.py` (new), against Postgres, run the service then delete the user row as S-054 will, and check: the heir is owner, others and all joining times are unchanged, a rejoined member counts from the rejoining, recipes stay with the old owner's author reading "unknown", the catalog and notebook name are unchanged, the owner appears nowhere in `/notebooks` or the members list, the new owner can invite and remove through the existing routes, the heir's existing edit lock and default notebook survive, and two identical notebooks whose members share a joining time pass to the same person (SC-005)
- [ ] T010 [US1] In `api/tests/test_notebook_ownership_integration.py`, check that after the rule and the user row deletion an open invite still joins through `POST /invites/notebook/accept`, the preview gives `inviter_alias` null (`invited_by` clears only with the user row), and a resend by the new owner sets them as sender
- [ ] T011 [US1] In `api/tests/test_notebook_ownership_integration.py`, check FR-011: for a person with one notebook that passes and one with no members, run the service, fail before commit, roll back, and find memberships and both notebooks as they were
- [ ] T012 [US1] In `api/tests/test_notebook_ownership_integration.py`, with two sessions from the `engine` fixture, committing for real and cleaning up after, not the shared `db_session`: the heir's leave and the rule overlap, in both orders, and an invite accept and the rule overlap, in both orders, and each time exactly one owner remains (FR-010)

### Implementation for User Story 1

- [ ] T013 [P] [US1] In `api/domain/notebook.py`, add a frozen dataclass `JoinedMember(user_id: UUID, role: NotebookRole, joined_at: datetime)` and `longest_standing(members: Iterable[JoinedMember]) -> UUID | None`, skipping `role == "owner"` and taking the lowest `(joined_at, user_id)`
- [ ] T014 [US1] Create `api/application/notebook_ownership.py` with `PassOwnedNotebooksCommand`, `PassOwnedNotebooksResult` and `PassOwnedNotebooksService` as in [the contract](contracts/ownership-rule.md): take `owned_personal_ids`, sort, and for each take `lock_notebook`, re-read `role_of` and skip unless `owner`, call `longest_standing`, then `delete_membership` and `make_owner`. Never commit, never send email, log ids only. Leave the no-heir branch for T018
- [ ] T015 [US1] In `api/application/notebook_members.py`, make `LeaveNotebookService.execute` call `lock_notebook` after the access check and then `role_of`: `owner` raises `NotebookOwnerStaysError`, `None` raises `NotebookNotFoundError`, as `RemoveNotebookMemberService` reads its role after the lock

**Checkpoint**: A notebook with members passes correctly; T006 to T012 pass

---

## Phase 4: User Story 2 - A notebook with no members is deleted (Priority: P1)

**Goal**: A notebook nobody else can reach goes, without touching anything made from it.

**Independent Test**: Make a notebook with an owner, no members, recipes, a catalog and a snapshot in a kitchen. Run the service and check that the notebook is gone and the snapshot remains.

### Tests for User Story 2

- [ ] T016 [P] [US2] In `api/tests/test_notebook_ownership_application.py`, test that a notebook with no members goes to `delete_personal` and into `result.deleted`, and that a pending invite does not change this. In `api/tests/test_notebook_invites_application.py`, test that accepting raises `InvalidInviteTokenError` when `lock_notebook` raises `NotebookNotFoundError`
- [ ] T017 [US2] In `api/tests/test_notebook_ownership_integration.py`, check: notebook, recipes, ingredients and invites are gone; `source` rows and their `raw_text` are gone, but one another recipe still uses is kept; a snapshot stays with its recipes and its own sources, with `source_notebook_id` null; the deleted invite's link gives the usual invalid answer (410). With two sessions, an accept waiting on the lock while the notebook is deleted answers as an invalid link, not 500

### Implementation for User Story 2

- [ ] T018 [US2] In `api/adapters/persistence/notebooks.py`, add `delete_personal`: read the notebook's recipes' `source_id`s, delete the notebook row, then delete those `source` rows no remaining recipe references (research R5). Add the no-heir branch to the service in `api/application/notebook_ownership.py`
- [ ] T019 [US2] In `api/adapters/persistence/notebooks.py`, make `lock_notebook` use `.one_or_none()` and raise `NotebookNotFoundError` when the row is gone (research R7), and in `api/application/notebook_invites.py` have the accept service turn that error into `InvalidInviteTokenError` around its `lock_notebook` call. Confirm the other callers reach their route's 404 handling, in `api/api/routes/notebooks.py`

**Checkpoint**: Both P1 stories pass, and the rule is complete

---

## Phase 5: User Story 3 - People and places that are not the owner's are left alone (Priority: P2)

**Goal**: Prove where the rule stops. No new code is expected; a failure here is a bug in T014.

**Independent Test**: Give a person a mix of owned notebooks, notebooks they are a member of and kitchen notebooks. Run the service and check that only the owned ones changed.

- [ ] T020 [US3] In `api/tests/test_notebook_ownership_integration.py`, check after the service and the user row deletion: a notebook where the person was a member keeps its owner and what they added, with the author reading "unknown"; a kitchen notebook they created keeps its access, recipes and members, and only its stored creator, `owner_user_id`, becomes null; a snapshot of a notebook that passed keeps its origin label

**Checkpoint**: All stories pass

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 [P] Confirm `ui/app/invites/notebook/AcceptNotebookInvitePanel.test.tsx` covers a preview with no `inviter_alias` and add the case if it is missing (research R9)
- [ ] T022 [P] Add to S-054's notes in `dev/docs/backlog.yaml` that it must call `PassOwnedNotebooksService` under the conditions in `specs/058-notebook-ownership-passing/contracts/ownership-rule.md`
- [ ] T023 Run the full checks and record them in `specs/058-notebook-ownership-passing/notes.md`: the Compose test overlay as in [quickstart.md](quickstart.md) (`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, in this checkout's usual Compose project), `uv run ruff check .`, `uv run ruff format --check .`, and `cd ui && npm test && npm run lint && npm run typecheck`
- [ ] T024 Walk the table in `specs/058-notebook-ownership-passing/quickstart.md` and confirm each row has a passing test, then set S-058's `status` and `verification` in `dev/docs/backlog.yaml`, saying the browser walk belongs to S-054, and move S-058 out of the "Ownership passing" row in `README.md`

---

## Dependencies & Execution Order

- **Setup (Phase 1)** comes first, then **Foundational (Phase 2)**, which blocks every story.
- **US1 (Phase 3)** creates the service.
- **US2 (Phase 4)** extends the service, so it follows T014. T019 can start earlier, since it touches only the lock.
- **US3 (Phase 5)** needs T014 and the user row deletion test setup from T009.
- **Polish (Phase 6)** comes last. T021 and T022 can run at any time.

Within a story, tests come first and fail, then the implementation. T014 needs T013.

## Parallel Opportunities

- US1 tests: T006, T007 and T008 touch different files.
- US1 implementation: T013 can run beside T015.
- T016 can run beside T018.
- T021 and T022.

Tasks in `api/tests/test_notebook_ownership_integration.py` share one file, so they run in order. T004, T018 and T019 share `api/adapters/persistence/notebooks.py`.

```bash
# US1 tests together
T006 api/tests/test_notebook_domain.py
T007 api/tests/test_notebook_ownership_application.py
T008 api/tests/test_notebook_members_application.py
```

## Implementation Strategy

**First cut**: US1 and US2 together. The story is not usable until both branches of the rule exist, because S-054 needs every owned notebook settled. US3 adds proof, not code.

Nothing here ships to a person until S-054. The fix in T015 is safe to land alone if the rest waits.

## Notes

- No migration. If a task seems to need one, stop and check [data-model.md](data-model.md).
- The auth layer and its routes are not touched (FR-014).
- Do not add a route for the rule. That is S-054.
