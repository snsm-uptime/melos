# Implementation Plan: Share a notebook by email invite

**Branch**: `057-notebook-invites` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/057-notebook-invites/spec.md`

## Summary

The owner of a personal notebook invites someone by email, and opening the link makes that person a notebook member. One new table, `notebook_invite`, holds the hashed token, with the kitchen invite's token rules reused from `domain/kitchen_invite.py`. Accepting runs in one transaction: claim the token, merge the catalogs with a new pure rule, add the membership. Leaving and removal delete the membership row, and the existing foreign key ends the person's edit locks. The ui adds one link page and a sharing page for the notebook. Sign-up and the auth routes don't change. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Tailwind 4. No new libraries.

**Storage**: PostgreSQL 16. One migration, `0012_notebook_invite`.

**Testing**: pytest (domain, application with fake ports, integration in the Compose test overlay), vitest (ui), browser walk ([quickstart.md](quickstart.md)).

**Target Platform**: The four existing Compose services. `mcp` and `db` images are unchanged.

**Project Type**: Web application (api plus BFF ui).

**Performance Goals**: Joining with 500 personal names and 500 notebook names takes under 2 seconds (SC-003). A signed-in person lands on the notebook within 3 seconds (SC-002).

**Constraints**: Accepting is all or nothing (FR-015, SC-007). No AI step in the merge (FR-019). The email goes out inside the request, as with kitchen invites, because there is no queue or worker.

**Scale/Scope**: A home cookbook: a few members per notebook, and hundreds of catalog names.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| 1. Simplicity and reuse | Pass | No new service. Reuses the token rules, the single-use claim, `EmailSender`, `EnsureEmailVerifiedService` and `ActionDialog`. The auth routes and the sign-up page are untouched (R8). |
| 2. Tech stack | Pass | No new library. |
| 3. Hexagonal | Pass | The merge and the owner-only rules are pure and live in `domain/`. Email goes through the `EmailSender` port. SQL stays in `adapters/persistence/`. |
| 4. Security and privacy | Pass | Tokens are stored hashed. 404 for anyone who can't see the notebook. The preview shows a masked email only, and no response says whether an address has an account (R5). Logs hold ids and outcomes, never addresses. |
| 5. No AI shortcuts | Pass | The merge is a fixed rule, and it changes no recipe. |
| 6. Testing | Pass | All layers planned, including a browser walk. |
| 7. Deployment | Pass | Migration only. SMTP settings already exist. |
| 8. Git discipline | Pass | Schema change through Alembic. Work starts on branch `057-notebook-invites`; this plan was written on `main`. |
| 9. Scope | Pass | S-057 is a Must. |

Re-check after Phase 1: all pass. One PRD wording change is needed: §1.6 names the column `accepted_at`, and this plan uses `used_at` so the shared claim helper works (R2).

## Project Structure

### Documentation (this feature)

```text
specs/057-notebook-invites/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/notebook-sharing-api.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── ingredient_catalog.py            # names_to_add: the merge rule
│   ├── notebook_invite.py               # link path, owner-only and shareable rules
│   └── errors.py                        # new sharing errors
├── application/
│   ├── notebook_invites.py              # send, resend, cancel, list, preview, accept
│   ├── notebook_members.py              # list, leave, remove
│   └── ports.py                         # notebook and invite port methods
├── adapters/persistence/
│   ├── models.py                        # NotebookInviteModel
│   ├── migrations/versions/0012_notebook_invite.py
│   ├── notebook_invites.py              # invite repository
│   └── notebooks.py                     # lock, members, add and delete membership
├── api/routes/notebooks.py              # members and invites of a notebook
├── api/routes/invites.py                # notebook preview and accept
├── api/schemas/notebook_invites.py
└── tests/

ui/
├── app/invites/notebook/page.tsx        # the emailed link
├── app/invites/notebook/AcceptNotebookInvitePanel.tsx
├── app/invites/notebookInviteClient.ts
├── app/notebooks/[notebookId]/sharing/page.tsx
├── app/notebooks/[notebookId]/NotebookSharingScreen.tsx
├── app/notebooks/[notebookId]/NotebookRecipesScreen.tsx  # sharing link; leaves on 404
├── app/api/invites/notebook/{preview,accept}/route.ts
├── app/api/notebooks/[notebookId]/members/...            # BFF routes
├── app/api/notebooks/[notebookId]/invites/...            # BFF routes
├── lib/appChrome.ts                     # language switch on the link page
├── lib/notebooksClient.ts
└── lib/i18n/{invite,notebooks}.ts
```

**Structure Decision**: The existing `api/` and `ui/` layout. The kitchen invite modules are left as they are: their names, tables and message text are kitchen-specific, and only their pure rules are imported.

## Complexity Tracking

No violations.
