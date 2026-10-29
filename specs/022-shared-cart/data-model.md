# Data Model: Shared Kitchen Cart and Single-Editor Locks (S-022)

Migration `0007_cart_and_edit_locks` (upgrade and downgrade). All ids are UUID.

## New tables

### cart
| Column | Type | Rules |
|---|---|---|
| id | uuid pk | `gen_random_uuid()` |
| kitchen_id | uuid, unique, not null | FK `kitchens.id` ON DELETE CASCADE |
| people | int, null | NULL = follow member count (FR-002); else CHECK 1–99 |
| updated_at | timestamptz | set on save |
| updated_by | uuid, null | FK `users.id` ON DELETE SET NULL |

Created on first use (research R1).

### cart_item
| Column | Type | Rules |
|---|---|---|
| cart_id | uuid | FK `cart.id` ON DELETE CASCADE |
| recipe_id | uuid | FK `recipe.id` ON DELETE CASCADE |
| meals | int not null | CHECK 1–99, default 1 |
| added_at | timestamptz | |
| | | pk(cart_id, recipe_id) |

Invariant (checked in `application/carts.py`, not by FK): the recipe's notebook has `kitchen_id = cart.kitchen_id`.

### cart_edit_lock
| Column | Type | Rules |
|---|---|---|
| cart_id | uuid pk | FK `cart.id` ON DELETE CASCADE |
| session_id | uuid not null | FK `sessions.id` ON DELETE CASCADE |
| user_id | uuid not null | FK `users.id` ON DELETE CASCADE |
| membership_id | uuid not null | FK `kitchen_memberships.id` ON DELETE CASCADE (R11: removal ends the lock for good) |
| acquired_at | timestamptz | |
| last_active_at | timestamptz not null | idle limit 5 min (R10) |
| draft | jsonb not null | `{"people": int\|null, "items": [{"recipe_id": uuid, "meals": int}]}` |

### recipe_edit_lock
| Column | Type | Rules |
|---|---|---|
| recipe_id | uuid pk | FK `recipe.id` ON DELETE CASCADE |
| session_id | uuid not null | FK `sessions.id` ON DELETE CASCADE |
| user_id | uuid not null | FK `users.id` ON DELETE CASCADE |
| kitchen_membership_id | uuid null | FK `kitchen_memberships.id` ON DELETE CASCADE (kitchen notebook) |
| notebook_id | uuid null | with `user_id`: FK `notebook_membership(notebook_id, user_id)` ON DELETE CASCADE (personal notebook) |
| acquired_at | timestamptz | |
| last_active_at | timestamptz not null | idle limit 5 min (R10) |

CHECK: exactly one of `kitchen_membership_id`, `notebook_id` is set.

## Changed table

- `recipe.cart_add_count int not null default 0`, CHECK ≥ 0. Only raised by a cart save (FR-013); never lowered.

## Lock liveness (research R3, R4)

A lock row is **live** when all hold:
1. its `session_id` row exists and `expires_at > now()`;
1a. `now() - last_active_at < 5 minutes`;
2. cart: `user_id` is a member of the cart's kitchen and the kitchen is not archived;
   recipe: `can_write_recipes` holds for `user_id` on the recipe's notebook.

A non-live row is treated as absent and overwritten by the next acquire. Rows are **deleted** (not just ignored) when access is lost: membership removal cascades, and archiving a kitchen deletes its cart and recipe locks (R11), so restored access never brings a lock back.

```text
          acquire (no live lock)              save / discard / cancel
 FREE ───────────────────────────▶ HELD ─────────────────────────────▶ FREE
   ▲                                │
   └──── sign-out (row cascades), session expiry, 5 min idle (R10), ──┘
         access lost (row deleted, R11), resource or kitchen deleted (cascade)
```

## Domain values (`domain/cart.py`, pure)

- `PEOPLE_MIN = MEALS_MIN = 1`, `PEOPLE_MAX = MEALS_MAX = 99`.
- `effective_people(saved: int | None, member_count: int) -> int` = `saved` or `clamp(member_count, 1, 99)`.
- `scale_factor(people, meals, base_servings) -> Fraction` = `people * meals / base_servings`.
- `format_factor(f: Fraction) -> str`: half-up to 2 decimals, trailing zeros removed.
- `check_count(value) -> int`: whole number 1–99 or `CartValueError`.
- `LOCK_IDLE = timedelta(minutes=5)`, `LOCK_WARN = timedelta(minutes=1)`; `lock_is_idle(last_active_at, now) -> bool`.

## Application views

- `CartView`: kitchen_id, people (effective), people_is_default (bool), entries[`CartEntryView`: recipe_id, title, notebook_id, notebook_name, base_servings, meals, factor], editor (`EditorView | None`), my_draft (`CartDraftView | None`, only for the holder's session), can_edit (bool).
- `EditorView`: alias (or "unknown"), is_me, idle_expires_at (only when is_me).
- `CartDraftView`: same shape as the entries plus `dropped_recipe_ids` (recipes deleted since they were drafted).

## UI clarification (2026-10-29)

No data change. The icon button, the toasts and the Cart-page-only editing bar use the existing GET body (`editor`, `idle_expires_at`, `draft`) and the existing 409 `cart_locked` with `editor_alias`.
