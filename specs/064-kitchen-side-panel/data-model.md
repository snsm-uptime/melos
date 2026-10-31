# Data Model: Kitchen Side Panel

## users (changed)

| Field | Type | Rule |
|---|---|---|
| `default_kitchen_id` | UUID, nullable, FK `kitchens.id`, `ON DELETE SET NULL` | Kitchen that Home opens. Null until first resolved, or after that kitchen is deleted. |

Migration `0009_default_kitchen` adds the column and drops it on downgrade. No backfill (research R2).

## Default kitchen resolution (derived)

Inputs: the stored id, and the person's kitchens with `is_archived`, `role`, kitchen `created_at`, membership `created_at`.

1. The stored id, if the person belongs to it and it is active.
2. Else their earliest-created active kitchen with role owner.
3. Else their earliest-joined active kitchen.
4. Else none.

A result that differs from the stored id is stored, except that "none" clears it.

## Recipe count (derived, not stored)

Recipes with `author_id` = person, whose notebook is in a kitchen they belong to, or is a personal notebook where they have a `notebook_membership` row. A deleted recipe stops counting.

## Panel state (browser only)

`localStorage["melos_side_panel_open"]`: `"true"` or `"false"`, absent means closed. Per device. Larger screens only.
