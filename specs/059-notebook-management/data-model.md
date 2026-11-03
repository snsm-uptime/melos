# Data model: Create, rename and delete notebooks

No tables, columns or migrations change.

## Notebook

| Field | Rule in this feature |
|---|---|
| `name` | Changeable. Trimmed, not empty, at most 200 characters (`validate_notebook_name`). An unchanged name is not validated (research R6). Duplicates allowed. |
| `kitchen_id`, `source_notebook_id`, `snapshot_key` | Not changed by a rename. |
| `owner_user_id` | Set to the creator on a kitchen notebook added here. Gives no extra access. |

## What a deletion does

| Data | How it goes | Effect |
|---|---|---|
| `recipe`, `ingredient` | Cascade from `notebook` | Gone |
| `recipe_ingredient`, `step` | Cascade from `recipe` | Gone |
| `cart_item` | Cascade from `recipe` | Leaves the cart, other entries stay |
| `recipe_edit_lock` | Cascade from `recipe` | Edit ends |
| `notebook_membership`, `notebook_invite` | Cascade from `notebook` | Access and links end |
| `source` | Deleted by the repository when no remaining recipe uses it | Captured text goes |
| `notebook.source_notebook_id` on snapshots | Set null | Label clears, snapshot stays |
| `users.default_notebook_id` | Set null | Recreated on next visit |
| `shopping_list_item` | Not linked by a foreign key | Lines and titles stay |
| Cart draft | Items are checked on read | Reported as `dropped_recipe_ids` |
| `cart_edit_lock` | Not touched | The cart editor keeps editing |

## Permission rule

| Access | Kitchen state | Rename and delete |
|---|---|---|
| `owner` | n/a | Allowed |
| `member` | n/a | Refused: `notebook_owner_only` |
| `kitchen_member` | Active | Allowed |
| `kitchen_member` | Archived | Refused: `kitchen_archived` |
| none | any | `notebook_not_found` |

## Port changes

`NotebookRepository`:

- `rename(notebook_id, name)`: new.
- `delete(notebook_id)`: replaces `delete_personal`, for both kinds, and takes the full row lock first (research R1).
- `lock_kitchen(kitchen_id)`: raises `KitchenNotFoundError` on a missing row (research R2).

`RecipeRepository`:

- `add(recipe)`: raises `NotebookNotFoundError` when the notebook is gone at insert (research R4).
