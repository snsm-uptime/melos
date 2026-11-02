# Research: Notebook ownership passes on

Checked against the code on `main` at `84203e1`.

## R1. Where the rule lives and what triggers it

**Decision**: An application service, `PassOwnedNotebooksService`, with no route. S-054 calls it in the same transaction, just before it deletes the user row.

**Rationale**: No account deletion exists: nothing in `api/` deletes a user, and the PRD lines saying `DELETE /auth/me` exists are out of date (backlog S-054 records this). The auth layer can't change without approval, and the backlog puts S-054 after this story.

**Alternatives**: A database trigger on user deletion would also cover deletions by hand, but it puts a domain rule in SQL, out of reach of the fake-port tests. Building the route here is S-054's scope.

## R2. Atomicity

**Decision**: The service never commits. It works in the session it is given, and the caller commits.

**Rationale**: FR-011 needs the notebooks and the account to succeed or fail together. `get_db` commits after a route returns a response, even an error one, so S-054 must roll back on its error branches, as the invite accept route does (spec 057 research R4). This goes in the contract.

## R3. Who inherits

**Decision**: A pure function in `domain/notebook.py` takes the memberships and returns the member with the lowest `(joined_at, user_id)`, ignoring the owner. `None` means no members. `NotebookMemberRecord` gains `joined_at`, from `notebook_membership.created_at`.

**Rationale**: `members_of` already sorts this way, so the next row after the owner would do, but that hides a product rule in an adapter's sort order and can't be tested without Postgres. `created_at` is a transaction timestamp, so ties are possible, and `user_id` makes the outcome repeatable (FR-003, SC-005). Rejoining counts from the new row, because leaving deletes the old one.

## R4. Moving the role

**Decision**: Delete the old owner's membership first, then update the heir's role.

**Rationale**: `notebook_membership` has a partial unique index allowing one `owner` per notebook, so promoting first fails. The index stays as the guard for FR-010. Deleting through `delete_membership` ends the old owner's edit locks through their foreign key. The heir's row keeps its key, so their own edit locks and `created_at` survive (FR-004). The lock in R6 means nobody sees the gap, and the transaction undoes it on failure.

## R5. Deleting a notebook

**Decision**: A new `delete_personal` on the notebook repository deletes the notebook row, then deletes the `source` rows its recipes pointed at, unless another recipe still points at them.

**Rationale**: Foreign keys handle almost everything: recipes, ingredients, memberships and invites cascade, a snapshot's `source_notebook_id` and `users.default_notebook_id` are set null (FR-007, FR-008). The exception is `source`: the recipe holds the reference, so deleting the recipe leaves the row behind with its `raw_text`, and `source.user_id` is then set null by the account deletion. That would keep a deleted person's captured text with no owner, which is why `RecipeRepository.delete` removes the source by hand. Snapshots are safe: `copy_all` gives each copy new source rows. The "still referenced" check keeps that safe if a future copy shares a source.

## R6. Locking and races

**Decision**: Read the person's owned notebook ids, sort them, and take `lock_notebook` on each in that order. Under the lock, read the role again and skip the notebook if the person no longer owns it.

**Rationale**: Inviting, accepting and removing already take this lock, so a join is either seen in full or waits. Sorted order prevents deadlock if two owners' deletions overlap, and nothing else holds two notebook locks. The re-read makes a repeated run harmless.

**Leaving must change**: `LeaveNotebookService` takes no lock, trusts the access read before it, and `delete_membership` deletes by key whatever the role. If Ben is promoted while his leave is in flight, his delete waits for the row and then removes the new owner. Nothing would stop it: the unique index allows zero owners. Leave now takes the lock and checks `role_of` after it, as `RemoveNotebookMemberService` does, so Ben gets the existing "owner stays" refusal.

**Alternative**: A `role = 'member'` condition on the delete. It would close this race but leaves leave as the one membership change outside the lock.

## R7. A notebook that vanishes under a lock

**Decision**: `lock_notebook` raises `NotebookNotFoundError` when the row is gone, instead of SQLAlchemy's `NoResultFound`. Accepting catches it and answers as for any invalid link. The other callers already answer 404 for that error.

**Rationale**: Notebooks can't be deleted today, so this path is new. An accept that read its invite before the deletion would otherwise wait on the lock and return 500. FR-007 and User Story 2 scenario 4 want the usual invalid-link message. S-059 needs the same fix.

## R8. Kitchen notebooks

**Decision**: Nothing to do.

**Rationale**: The spec says a kitchen notebook has no owner, and that holds for access. The code does store the creator in `notebook.owner_user_id`, used to find a member's own notebook for capture. Its foreign key sets it null when the user is deleted, and the rule only reads `notebook_membership`, which kitchen notebooks don't use.

## R9. Open invites after a passing

**Decision**: No change.

**Rationale**: `notebook_invite.invited_by` is nullable and set null with the user, the preview already returns no alias in that case, and resending sets the sender to whoever resends. The ui's handling of a missing alias gets a test. Only the owner can send invites, so every open invite on a passed notebook has this sender.

## R10. Ui

**Decision**: No change.

**Rationale**: Owner controls and the owner's alias come from the membership role on each read, so the new owner gets them on their next load (FR-006, SC-006).
