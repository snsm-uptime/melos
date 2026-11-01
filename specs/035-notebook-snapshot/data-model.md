# Data Model: Notebook snapshots

## Changed: `notebook`

| Column | Type | Rule |
|--------|------|------|
| `snapshot_key` (new) | uuid, nullable | Set when the notebook is made as a snapshot, never changed. Null on every other notebook. |

- New check `ck_notebook_snapshot_is_kitchen`: `snapshot_key IS NULL OR kitchen_id IS NOT NULL`.
- New unique index `uq_notebook_kitchen_snapshot_key` on `(kitchen_id, snapshot_key)` where `snapshot_key IS NOT NULL`.
- `source_notebook_id` is unchanged, and this feature is the first to set it. It must point at a personal notebook the adder owns. It is cleared by `ON DELETE SET NULL`.

Migration `0011_notebook_snapshot_key` adds the column, check and index. Existing rows stay null, and downgrade drops them.

## What a snapshot holds

| Target row | Copied from the original | Set new |
|------------|--------------------------|---------|
| `notebook` | `name` | `id`, `kitchen_id`, `owner_user_id` = adder, `source_notebook_id`, `snapshot_key`, `created_at` |
| `ingredient` | `name` (every row) | `id`, `notebook_id`, `created_at` |
| `source` | `user_id`, `type`, `url`, `raw_text`, `created_at` | `id` |
| `recipe` | `author_id`, `title`, `base_servings`, `servings_estimated`, `created_at` | `id`, `notebook_id`, `source_id`, `updated_at`; `save_key` null; `cart_add_count` 0 |
| `recipe_ingredient` | `position`, `name`, `quantity`, `unit`, `size`, `preparation`, `vague_note` | `id`, `recipe_id` |
| `step` | `position`, `text` | `id`, `recipe_id` |

No `notebook_membership` rows are made, as for any kitchen notebook. Nothing links a copied recipe to its original.

## Lifecycle

| Event | Result |
|-------|--------|
| Added | Exists with label and key |
| Original renamed | The label shows the new name; the snapshot's name stays |
| Original deleted | `source_notebook_id` null, so no label and no repeat warning; `snapshot_key` stays, so it is still not a capture default |
| Adder leaves the kitchen, or is deleted | Same as any kitchen notebook |
| Kitchen deleted | Deleted with the kitchen; the original isn't touched |

## Read model

`NotebookFacts` and `NotebookResponse` gain:

- `origin_notebook_name: string | null`: the original's current name.
- `is_snapshot: boolean`.
- `is_own_capture_notebook: boolean`: true on the notebook `user_kitchen_notebook` returns for the caller.
