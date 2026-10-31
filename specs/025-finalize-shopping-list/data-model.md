# Data Model: Saved Shopping List

Migration `0010_shopping_lists`, down revision `0009_default_kitchen`.

## shopping_list

| Field | Type | Rules |
|---|---|---|
| id | uuid | Primary key |
| kitchen_id | uuid | FK `kitchen.id`, ON DELETE CASCADE |
| closing_date | date, null | Null: active |
| created_at | timestamptz | |

Partial unique index on `kitchen_id` where `closing_date IS NULL`. Index on `(kitchen_id, closing_date DESC)`.

## shopping_list_item

| Field | Type | Rules |
|---|---|---|
| id | uuid | Primary key |
| shopping_list_id | uuid | FK, ON DELETE CASCADE |
| origin | text | `cart` or `hand` |
| section | text | `measured` or `your_call`; hand items are `measured` |
| name | text | Not blank; hand names go through `normalize_name` |
| kind | text, null | `mass`, `volume`, `count`; null for your-call lines and hand items with no amount |
| size | text, null | `small`, `medium`, `large`, only with unit `unit` |
| amounts | jsonb | List of `{quantity, unit}`; at most one for a hand item |
| notes | jsonb | List of text; your-call only |
| recipes | jsonb | List of `{recipe_id, title}`; empty for hand items |
| position | int | Cart lines in S-023 order, then hand items by time added |

## State

```text
(none) → active → closed
```

- Created by a cart save with at least one recipe, or by a first hand item, which also takes the saved cart's lines.
- Closed by Done when the list has items. Closed lists never change.
- Refresh replaces rows with `origin = cart` only.

The kitchen delete cascades. Recipe, notebook and user deletes do not touch these tables.
