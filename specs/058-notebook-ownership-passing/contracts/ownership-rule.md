# Contract: settling an owner's notebooks

This story adds no HTTP route. Its interface is one application service, for S-054 to call.

## `PassOwnedNotebooksService`

Module: `api/application/notebook_ownership.py`.

```python
PassOwnedNotebooksCommand(user_id: UUID)
PassOwnedNotebooksService(notebooks: NotebookRepository).execute(command) -> PassOwnedNotebooksResult
```

`PassOwnedNotebooksResult` holds `passed` (notebook id and new owner, one per notebook) and `deleted` (notebook ids). It is for logging and tests. Personal notebooks the person is only a member of, and kitchen notebooks, are left out.

## What the caller must do

1. Call `execute` in the same database session and transaction that deletes the user row.
2. Call it before deleting the user row. The foreign keys would otherwise remove the owner's membership, and the notebook could no longer be found.
3. Stop the person's activity first (end their sessions), so they can't create a notebook after the call. The user row should be locked before the call for the same reason.
4. Commit once, after the user row is deleted.
5. Roll back on every error branch, because `get_db` commits after a route returns an error response.

## What the service promises

- It never commits or rolls back.
- It raises nothing for a person with no notebooks, and a second run changes nothing.
- On any database error it lets the error rise, and the caller's rollback leaves everything as it was.
- It sends no email and keeps no record of past owners.

## Changed behaviour in existing routes

| Route | Change |
|-------|--------|
| `DELETE /notebooks/{id}/members/me` | A member who has just become owner gets the existing "owner stays" refusal instead of leaving. A notebook just deleted answers 404. |
| `POST /invites/notebook/accept` | If the notebook is deleted during the request, it answers as for an invalid link. |

No request or response shape changes.
