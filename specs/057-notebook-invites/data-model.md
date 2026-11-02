# Data model: Share a notebook by email invite

**Feature**: [spec.md](spec.md) | **Decisions**: [research.md](research.md)

## New table: `notebook_invite`

Migration `0012_notebook_invite`, after `0011_notebook_snapshot_key`.

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid | Primary key |
| `notebook_id` | uuid | Not null, FK `notebook.id`, `ON DELETE CASCADE` |
| `email` | varchar(320) | Not null, normalized |
| `token_hash` | varchar(64) | Not null, unique. SHA-256 of the raw token |
| `invited_by` | uuid | Nullable, FK `users.id`, `ON DELETE SET NULL` (R3) |
| `expires_at` | timestamptz | Not null. Sent or resent time plus 7 days |
| `used_at` | timestamptz | Nullable. Set when the invite is accepted |
| `created_at` | timestamptz | Not null, default `now()` |

Index: `uq_notebook_invite_open`, unique on `(notebook_id, email)` where `used_at IS NULL`.

Only personal notebooks get rows. The application enforces that, because a check constraint can't read the `notebook` table.

## Invite states

| State | Stored as | Link | On the owner's list |
|-------|-----------|------|---------------------|
| Open | `used_at` null, `expires_at` in the future | Works | Yes |
| Expired | `used_at` null, `expires_at` passed | Invalid | Yes, marked expired |
| Accepted | `used_at` set | Quiet success for someone in the notebook, otherwise invalid | No |
| Cancelled or replaced | Row deleted | Invalid | No |

| Action | Effect |
|--------|--------|
| Send | Deletes any unused row for that notebook and email, then inserts one |
| Resend | Same row: new `token_hash`, `expires_at` and `invited_by` |
| Cancel | Deletes an unused row |
| Accept | Sets `used_at` once |

## Changed behaviour on existing tables

`notebook_membership` has no schema change. Its `created_at` is the join date (FR-016).

- Accepting inserts a row with `role = 'member'`.
- Leaving or removal deletes the row. The foreign key removes the person's `recipe_edit_lock` rows in that notebook.
- A person who rejoins gets a new row, and so a new join date.

`ingredient` has no schema change. Joining inserts the result of `names_to_add` into the notebook's catalog. No other notebook's catalog changes.

## Validation

| Rule | Source |
|------|--------|
| Email passes `validate_invite_email` | FR-004 |
| The invitee isn't the owner or a current member | FR-004 |
| The notebook is personal | FR-003 |
| The caller's access is `owner` for send, resend, cancel, listing invites and removing | FR-002, FR-022, FR-023 |
| A person with role `owner` can't leave or be removed | FR-025 |

## Domain additions

| Name | Module | Purpose |
|------|--------|---------|
| `names_to_add(incoming, existing)` | `domain/ingredient_catalog.py` | The merge (R6) |
| `NOTEBOOK_INVITE_PATH`, `build_notebook_invite_link` | `domain/notebook_invite.py` | The one link (R5) |
| `assert_can_manage_sharing(kind, access)` | `domain/notebook_invite.py` | Refuses kitchen notebooks and members |
| `NotebookNotShareableError`, `NotebookOwnerOnlyError`, `AlreadyInNotebookError`, `NotebookOwnerStaysError`, `NotebookInviteNotFoundError`, `NotebookMemberNotFoundError` | `domain/errors.py` | See the contract |

## Port additions

| Port | Methods |
|------|---------|
| `NotebookRepository` | `lock_notebook`, `members_of`, `role_of`, `add_member`, `delete_membership` |
| `NotebookInviteRepository` (new) | `create`, `delete_open_for_email`, `list_unused`, `get`, `get_by_token_hash`, `rotate`, `delete`, `claim` |
