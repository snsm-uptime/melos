# Data model: Notebook ownership passes on

No schema change and no migration.

## Rows the rule changes

| Row | Notebook with members | Notebook with no members |
|-----|-----------------------|--------------------------|
| `notebook_membership`, old owner | deleted | deleted by cascade |
| `notebook_membership`, heir | `role` becomes `owner`; `created_at` kept | none |
| `notebook_membership`, others | unchanged | none |
| `notebook` | unchanged | deleted |
| `recipe`, its lines and steps, `ingredient` | unchanged | deleted by cascade |
| `source` of those recipes | unchanged | deleted unless another recipe uses it (research R5) |
| `notebook_invite` | unchanged, `invited_by` set null later with the user | deleted by cascade |
| `notebook.source_notebook_id` on snapshots | unchanged | set null by its foreign key |
| `recipe_edit_lock` | the old owner's end, others kept | deleted by cascade |

Deleting the user row afterwards is S-054's step. Its existing foreign keys then set `recipe.author_id` to null, which reads "unknown", remove the person's plain memberships, and set `source.user_id` and `notebook.owner_user_id` to null.

## Invariant

A personal notebook has exactly one `owner` row once the rule's transaction has committed. The partial unique index `role = 'owner'` refuses a second one. The notebook lock and the checks in research R6 refuse zero.

## Application records

`NotebookMemberRecord` gains `joined_at: datetime`, from `notebook_membership.created_at`.

## New port methods on `NotebookRepository`

| Method | Purpose |
|--------|---------|
| `owned_personal_ids(user_id) -> list[UUID]` | Personal notebooks where this person's role is `owner` |
| `make_owner(notebook_id, user_id) -> None` | Sets that membership's role to `owner` |
| `delete_personal(notebook_id) -> None` | Deletes the notebook and its unshared sources |

`lock_notebook` keeps its signature and now raises `NotebookNotFoundError` for a missing row.

## State of a personal notebook

```text
owned by A
  ├─ A's account deleted, members remain → owned by the longest-standing member
  └─ A's account deleted, no members     → deleted
```

Nothing else changes the owner.
