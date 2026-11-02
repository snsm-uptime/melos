# Implementation Plan: Notebook ownership passes on when an owner's account is deleted

**Branch**: `058-notebook-ownership-passing` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/058-notebook-ownership-passing/spec.md`

## Summary

A new application service settles every personal notebook a person owns, in the caller's transaction. It locks each notebook, picks the longest-standing member with a pure domain rule, and either moves the owner role to that person or deletes the notebook. It has no route and no ui. S-054 calls it just before deleting the user row.

Two existing weak spots become real once owners can change and notebooks can vanish. Leaving takes no lock and deletes by key alone, so a member who leaves at the moment they inherit would leave the notebook with no owner. `lock_notebook` fails with an unmapped error if the notebook is gone, so an invite accepted during a deletion would answer 500. Both are fixed here. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (api). No ui change.

**Primary Dependencies**: FastAPI, SQLAlchemy. No new libraries.

**Storage**: PostgreSQL 16. No migration: the role column, the one-owner index and the foreign keys already do what is needed.

**Testing**: pytest (domain, application with fake ports, integration in the Compose test overlay). A throwaway Postgres is fine while working, but the Compose run is the final check. No browser walk, because nothing a person sees can trigger the rule until S-054.

**Target Platform**: The existing `api` service.

**Project Type**: Web application (api plus BFF ui); this story touches `api/` only.

**Performance Goals**: None beyond a normal request. A person owns a handful of notebooks with a few members each.

**Constraints**: All or nothing with the account deletion (FR-011), so the service never commits. No record of past owners (FR-012). No change to auth routes (FR-014).

**Scale/Scope**: A home cookbook.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| 1. Simplicity and reuse | Pass | No new service or table. Reuses `lock_notebook`, `delete_membership` and the foreign keys. The auth layer is untouched. |
| 2. Tech stack | Pass | No new library. |
| 3. Hexagonal | Pass | Who inherits is a pure rule in `domain/notebook.py`. SQL stays in `adapters/persistence/`. |
| 4. Security and privacy | Pass | Deleting a notebook also deletes its captured source text (R5). Logs hold ids only. |
| 5. No AI shortcuts | Pass | No AI step. |
| 6. Testing | Pass | Domain, application and integration tests, including the races, with the integration suite run in the Compose test overlay (T023). The browser check does not apply until S-054 gives the rule a trigger; S-054 owns that walk. |
| 7. Deployment | Pass | Code only. |
| 8. Git discipline | Pass | No schema change. Work starts on branch `058-notebook-ownership-passing`; this plan was written on `main`, and that branch does not exist yet. |
| 9. Scope | Pass | S-058 is a Must, and S-054 cannot ship without it. |

Re-check after Phase 1: all pass.

## Project Structure

### Documentation (this feature)

```text
specs/058-notebook-ownership-passing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ownership-rule.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── notebook.py                      # longest_standing: who inherits
├── application/
│   ├── notebook_ownership.py            # new: PassOwnedNotebooksService
│   ├── notebook_members.py              # leave takes the lock, reads the role after it
│   ├── notebook_invites.py              # accept treats a vanished notebook as an invalid link
│   └── ports.py                         # joined_at, owned_personal_ids, make_owner, delete_personal
├── adapters/persistence/
│   └── notebooks.py                     # the three port methods; lock_notebook on a missing row
└── tests/
    ├── notebook_sharing_fakes.py        # the new port methods
    ├── test_notebook_domain.py
    ├── test_notebook_ownership_application.py
    ├── test_notebook_ownership_integration.py
    ├── test_notebook_members_application.py
    └── test_notebook_invites_application.py

ui/
└── app/invites/notebook/AcceptNotebookInvitePanel.test.tsx  # only if the no-sender case is missing
```

**Structure Decision**: The existing `api/` layout. One new application module, because the rule belongs to no existing use case and S-054 will import it.

## Complexity Tracking

No violations.
