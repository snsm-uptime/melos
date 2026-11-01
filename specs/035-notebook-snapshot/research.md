# Research: Notebook snapshots

## R1. How a notebook is marked as a snapshot

- **Decision**: Add a nullable `notebook.snapshot_key` (uuid). Set on every snapshot, never cleared, and unique per kitchen.
- **Rationale**: The label can't mark a snapshot, because `source_notebook_id` is cleared when the original is deleted, and FR-017 must still hold after that. The same column gives repeated requests a safe answer (R3).
- **Alternatives considered**: `is_snapshot` boolean: needs a second column for R3. Filter on `source_notebook_id`: fails as above.

## R2. Keeping captures away from snapshots (FR-017)

- **Decision**: `user_kitchen_notebook` adds `snapshot_key IS NULL`.
- **Rationale**: It looks up `owner_user_id`, and a snapshot records its adder as owner (spec 056 FR-002), so without the filter a snapshot would become that person's capture notebook.

## R3. Double press and retries (FR-008)

- **Decision**: The ui makes one key for each notebook chosen in an opening of the dialog, reuses it when retrying or confirming that notebook, and disables the action while it runs. The api returns the existing snapshot when the key was already used in that kitchen. A concurrent duplicate is stopped by the kitchen lock and the unique index.
- **Rationale**: Same pattern as `save_key` (spec 020). A retry after a lost answer is safe, and choosing a different notebook after a lost answer can't return the first notebook's snapshot.

## R4. Copy method and consistency (FR-006, FR-009)

- **Decision**: One transaction under `lock_kitchen`. Lock the source recipes `FOR SHARE`, read recipes, sources, lines and steps, then bulk insert with new ids. Copy the catalog with one `INSERT … SELECT`.
- **Rationale**: `get_db` already commits or rolls back as one unit, which gives all or nothing. Row locks make the copy wait for an edit being saved, so a recipe's lines and steps can't come from two versions. Unsaved edits live in the ui, so the last saved version is what gets copied, and edit locks are not touched. Bulk inserts keep 100 recipes well inside SC-002.
- **Alternatives considered**: `SaveRecipeDraft` per recipe: re-runs validation and name matching that must not change anything, and one statement set per recipe. Repeatable-read isolation: differs from the rest of the app for little gain.

## R5. Sources, preview images and dates

- **Decision**: Copy the `source` row for each recipe. Keep each recipe's `created_at`; `updated_at` is the copy time; `save_key` is null; `cart_add_count` is 0.
- **Rationale**: Deleting a recipe deletes its source row (`recipes.py`), so a shared row would break the other side's link (FR-015). The kitchen list sorts by `created_at`, so identical timestamps would lose the original order.
- **Note**: `preview_image_base64` is in the PRD but not in the schema, so FR-009 defers preview images; whoever adds the column must add it to `copy_all`. A schema guard test should not be needed, as no table is added.

## R6. Capture default in the ui (FR-017, clarification 2)

- **Finding**: The api creates a member's own notebook only when no notebook is picked, but the ui always sends one: `KitchenNotebooksSection` preselects `notebooks[0]` and the capture route needs a notebook id. So a second member's captures already go to the first notebook, and a snapshot could be offered as the default. This predates S-035.
- **Decision**: Add `is_own_capture_notebook` to kitchen notebook answers and `POST /notebooks/kitchens/{id}/capture-notebook`, which runs `ResolveCaptureNotebookService`. The picker preselects the member's own notebook; when they have none, it shows "My own notebook (new)", and submitting calls the route first. An explicit pick works as today. The "new" row is a ui-only `CaptureNotebook` with the sentinel id `own-new`, which never reaches the api. It counts as a candidate, so the picker shows when the kitchen has one other notebook.
- **Rationale**: It is the smallest change that makes clarification 2 true in the app. The notebook is created on submit, before extraction, and stays if no recipe is saved. This amends spec 056 FR-009 ("nothing created before the recipe save"), FR-013 ("no route") and SC-011, which AGENTS.md's capture rule already outgrew.
- **Alternatives considered**: Create the notebook when the kitchen page opens: contradicts "first capture". Create it at recipe save: leaves no empty notebooks, but needs a kitchen-scoped capture route and drafts with no notebook.

## R7. Repeat warning (FR-008a)

- **Decision**: The api answers `409 snapshot_exists` unless `confirm_repeat` is true. The ui then shows the warning and resends with the same key.
- **Rationale**: The check runs under the kitchen lock, so it can't be stale, and kitchen members aren't sent the origin ids.

## R8. Who sees what for the label (FR-019, FR-020)

- **Decision**: Add `origin_notebook_name` to the notebook answer, from a join on `source_notebook_id`, and show it as plain text on the notebook page. The origin id is not returned.

## R9. Recipe count in the side panel

- **Decision**: `count_recipes_added` leaves out recipes in snapshot notebooks.
- **Rationale**: Copies keep their author, so a snapshot would otherwise double the count of "recipes added" for no new recipe (FR-025). Nothing marks a recipe as a copy, so recipes later captured into a snapshot aren't counted either. That undercount is accepted.

## R10. Default personal notebook in the choice

- **Decision**: The dialog loads `GET /notebooks/default` before `GET /notebooks`, as the Notebook tab does, and offers rows with `kind = personal` and `access = owner`.
- **Rationale**: A person who never opened their notebook has no default yet. This corrects the spec's Picker assumption without changing a requirement.

## R11. Finding a snapshot in the kitchen (FR-007, FR-007a)

- **Decision**: Add a route, `/kitchens/{id}/notebooks`, opened by a notebooks icon beside the share icon in `KitchenDetailChrome`, the same way `cartHref` opens the cart. The page renders the Notebook tab's `styles.grid` and `NotebookCard` with `href={/notebooks/{id}}` and no `access` chip. Its first cell starts adding a notebook, hidden when the kitchen is archived, as the Notebook tab's first cell adds a recipe. The grid reloads after a snapshot is added.
- **Rationale**: Recipe cards were the only path to a notebook, so an empty snapshot couldn't be reached. Copies keep their `created_at` and the list sorts newest first, so they can also land past page one. A route keeps the back button working and leaves `KitchenNotebooksSection` as it is, which respects the 2026-10-28 one-column redesign (commit a5d0d30) and its "no notebook cards" test.
- **Alternatives considered**: A link in the success message: an empty snapshot can't be reached once the message closes. Cards on the recipe page: reverses the redesign. A view toggle in `KitchenNotebooksSection`: no address to return to.
