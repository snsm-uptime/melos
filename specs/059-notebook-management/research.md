# Research: Create, rename and delete notebooks

No open unknowns came from the Technical Context. These are the decisions, checked against the code at 83adc09.

## R1. One delete for both kinds of notebook

**Decision**: rename `delete_personal` to `delete` on the notebook repository and use it for both kinds. It first takes `FOR UPDATE` on the notebook row, then reads the source ids, then deletes.

**Rationale**: the method already removes the notebook and the captured source text that no other recipe uses, and nothing in it depends on the kind. Foreign keys do the rest. `recipe`, `ingredient`, `notebook_membership` and `notebook_invite` cascade from the notebook. `recipe_ingredient`, `step`, `cart_item` and `recipe_edit_lock` cascade from the recipe. `notebook.source_notebook_id` and `users.default_notebook_id` are set to null.

The full row lock is new. A recipe save holds `FOR KEY SHARE`, which `lock_notebook` does not block. Without the lock, a save could commit between reading the source ids and the delete, and leave its source row behind with no recipe.

**Alternatives**: a second method for kitchen notebooks repeats the same lines. Deleting recipes one at a time through `DeleteRecipeService` adds a query per recipe and nothing else, since its cleanup is the same cascade.

## R2. Lock order and the check under the lock

**Decision**: rename and delete run in this order.

1. Read the facts for the caller, with no lock. No notebook, or no access: 404. An outsider takes no lock.
2. A kitchen notebook: `lock_kitchen`. Kitchen gone: 404.
3. `lock_notebook`. Gone: 404.
4. Read the facts again and apply `assert_can_manage`.
5. Act and commit.

**Rationale**: the kitchen lock conflicts with archiving, so the archived check in step 4 is exact, and it serializes a last-notebook delete against the first-notebook creation of spec 056, which takes the same lock. Step 4 also catches ownership passing or leaving a kitchen while the request waited. Kitchen before notebook is the order the snapshot path takes (R3), so these cannot deadlock.

`lock_kitchen` uses `.one()` today, so a kitchen deleted after step 1 raises a database error. It changes to raise `KitchenNotFoundError` on a missing row, as `lock_notebook` does for its own, and the helper turns that into `NotebookNotFoundError`, since the notebook went with the kitchen.

A second delete waits at step 3, finds no row and answers 404. A rename that waits behind a delete does the same. Two renames run one after the other, and the last wins.

## R3. Snapshot against deletion of its original

**Decision**: `AddNotebookSnapshotService` takes `lock_notebook` on the source after the kitchen lock and after the first ownership check, and reads the source facts again.

**Rationale**: today the source is read with no lock, so a delete that commits before the new row's foreign key is checked gives an `IntegrityError` and a 500. Spec 035 and FR-019 want the clear message the ui already has for `notebook_not_found`. With the lock, the delete waits for the snapshot, or the snapshot finds the notebook gone.

## R4. Invite and capture races

**Decision**: the invite race needs only tests. The capture race needs one change: `RecipeRepository.add` turns a failed foreign key on `recipe.notebook_id` into `NotebookNotFoundError`, in the `except IntegrityError` that already handles the save key.

**Rationale**: `AcceptNotebookInviteService` already turns a notebook gone at `lock_notebook` into `InvalidInviteTokenError` (spec 058). `SaveRecipeService` reads the notebook with no lock and then inserts, so a delete that commits between the two fails the foreign key, and `add` re-raises it as a 500. The full row lock of R1 makes the insert wait for the delete, and it then fails the same way. Once `add` raises the domain error, the save route's existing mapping gives 404 `notebook_not_found`, `lib/i18n/capture.ts` has the message, and the draft stays on screen.

**Alternatives**: `lock_notebook` in the save service would also work, but it makes saves into one notebook wait for each other, to handle a rare race.

## R5. Who may manage: one domain rule

**Decision**: `assert_can_manage(access, kitchen_is_archived)` in `domain/notebook.py`. `owner`: allowed. `member`: `NotebookOwnerOnlyError`. `kitchen_member` in an archived kitchen: `KitchenArchivedError`. `kitchen_member` otherwise: allowed. The ui has a one-line mirror for showing the menu. The api remains the rule.

**Rationale**: rename and delete have the same rule (FR-001, 002, 005, 006, 016). `NotebookOwnerOnlyError` already answers 403 `notebook_owner_only`.

`KitchenArchivedError` is reused with its code, though its message speaks of adding recipes. The ui shows its own text for the code, and the menu is hidden there, so only a direct caller reads it.

## R6. A rename that changes nothing

**Decision**: when the trimmed name equals the stored one, the service returns the current view without validating or writing.

**Rationale**: generated names can pass 200 characters, since aliases allow 32 and kitchen names 200. Without this, opening rename on such a notebook and saving would be refused for a name the person did not type (spec edge case).

## R7. Member count for the confirmation

**Decision**: when the delete dialog opens, it reads the notebook and, for a personal notebook, `GET /notebooks/{id}/members`. Confirm stays disabled until both answer. If a read answers 404, the dialog shows the gone message of R10. If a read fails any other way, it shows the error and offers no confirm.

**Rationale**: FR-007 must state real numbers, and the page's recipe count can be old. Adding `member_count` to every notebook answer costs a subquery on every list for one dialog.

## R8. Actions in one options menu

**Decision**: a dots button in the chrome header opens `IconButtonPopup` with Rename and Delete. Share stays its own button. People who may not manage see no dots button.

**Rationale**: the header already holds back, title and Share at 360px, and two more icons do not fit. Delete in a menu is one step further from a mis-tap.

## R9. Rename and create share a dialog

**Decision**: extract `NotebookNameDialog` from `NewNotebookCard`. It takes a title, a start value and a submit function, and keeps the text on failure (FR-018). `NewNotebookCard` takes an optional `kitchenId`.

**Rationale**: one set of name rules and messages. A third copy on the kitchen page would drift.

## R10. Where people go when the notebook is gone

**Decision**: a screen computes `goneHref`. With a loaded notebook it is the kitchen's notebooks when the notebook has a `kitchen_id`, otherwise `/notebooks`. With no loaded notebook, as on a first load that answers 404, it is `backHref`. Both dialogs show "This notebook no longer exists." on a 404, and closing them goes to `goneHref`. The existing 404 redirects use `goneHref` in place of `/notebooks`.

**Rationale**: a kitchen member has no reason to land on their personal list after a kitchen notebook goes. A first load has no notebook to read a kitchen from, and `?from=` doesn't always name the kitchen's notebooks: from a recipe list or the cart it names that list, and a recipe's fallback Back link carries none. So a reload lands on the list it came from, or on `/notebooks`.

## R11. New kitchen notebooks

**Decision**: `CreateKitchenNotebookService`, using the existing `_create_kitchen_notebook` with the name made a parameter. Order: kitchen access (404), kitchen lock, kitchen access and record read again (404), archived (403), name validation (422), create, seed the catalog, commit. Owner is the caller. `snapshot_key` stays null, so it counts as their own capture notebook (US3 scenario 5).

**Rationale**: access comes first, so a non-member learns nothing from a bad name. The archived check sits under the kitchen lock for the reason in R2: checked before it, a kitchen archived in the gap would still gain a notebook.

## R12. After a change

**Decision**: the ui calls `requestSidePanelRefresh()` after a delete, since the recipe count in the panel changes. After a rename, the page sets its own state, which updates the chrome title.

**Rationale**: both are existing paths. Notebook names are read fresh on each page, and the snapshot label is a join, so nothing else needs updating.
