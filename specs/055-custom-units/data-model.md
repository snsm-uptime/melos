# Data Model: Custom Units and Admin Dashboard

All changes are in one migration, `0013_custom_units` (after `0012_notebook_invite`). See [research.md](research.md) for the reasons.

## New table: `unit`

| Column | Type | Rules |
|--------|------|-------|
| `name` | text, primary key | `name = lower(btrim(name))`, 1 to 32 characters |
| `user_references` | `uuid[]`, not null, default `{}` | Active accounts that kept the unit. No foreign key is possible. No duplicates, guaranteed by the one write statement (R2) |
| `reference_count` | integer, generated, stored | `cardinality(user_references)`. Never written |
| `is_default` | boolean, not null, default false | True for everyone's units |
| `created_at` | timestamptz, not null, default now | |

Seeded rows: `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`, default, no references.

**Rules**

- A person's list: every default plus every row that references them. A row can be both, which is how a later promotion shows once.
- A non-default row with no references does not exist (FR-020b).
- A default row is never deleted by the removal rule.

**State of one name**

```text
(no row) ── person keeps it ──▶ referenced ── more people ──▶ referenced (count grows)
                                    │
                                    └─ last reference removed ──▶ (no row)
referenced ── later promotion, out of scope ──▶ default, references kept
```

## New table: `cart_activity`

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid, primary key | `gen_random_uuid()` |
| `user_id` | uuid, not null | FK `users.id` `ON DELETE CASCADE`, indexed |
| `action` | text, not null | `created`, `edited` or `closed` (check) |
| `created_at` | timestamptz, not null, default now | |

Written only by `SaveCartService` and `CloseShoppingListService`, in their transaction. No cart behaviour reads it.

## Changed: `users`

Adds `is_admin boolean NOT NULL DEFAULT false`. Approved by the owner on 2026-11-01. No route or body writes it.

## Changed: `recipe_ingredient`

- Drops `ck_recipe_ingredient_unit`.
- Adds `ck_recipe_ingredient_unit_not_blank`: `unit IS NULL OR btrim(unit) <> ''`.
- `unit` stays plain text. It references nothing, so a recipe depends on no account (FR-012).
- `ck_recipe_ingredient_size` and `ck_recipe_ingredient_vague_or_measured` are unchanged.

## Changed: `shopping_list_item`

`ck_shopping_list_item_kind` allows `mass`, `volume`, `count`, `custom`. Amounts stay JSON, so a custom unit needs no other change.

## Domain values (not stored)

`domain/recipe_draft.py`:

| Value | Holds |
|-------|-------|
| `UnknownUnit` | `word` (normalized), `lines` (indexes). One per word per draft |
| `DraftRecipe.unknown_units` | Tuple of `UnknownUnit`, empty in the raw value and after an edit check |

`domain/cart.py`:

| Value | Holds |
|-------|-------|
| `Kind` | Adds `custom` |
| `CartAction` | `created`, `edited`, `closed` |

## Client-only state (`ui`)

| Field | On | Meaning |
|-------|----|---------|
| `keptUnits` | draft and edit state | Words the person said yes to, sent as `keep_units` at Save. Gone on discard |
| `declinedUnits` | draft and edit state | Words the person said no to on this screen. Not remembered (FR-006) |

Which questions show is derived: a word is asked about while a line uses it and it's in neither the allowed list nor these two fields.

## Rule changes by flow

| Flow | Reads the person's units | Writes the person's units | Accepts any stored unit |
|------|--------------------------|---------------------------|-------------------------|
| Capture | Yes | No | |
| Save new recipe | Yes | Kept words a line uses | |
| Update recipe | Yes | Kept words a line uses | Units already on the recipe |
| Vocabulary, unit check | Yes | No | |
| Read, scale, list, cart, shopping list | No | No | Yes |
| Snapshot copy | No | No | Yes (raw copy) |
| Hand-added list item | No | No | Default units only |
| Account deletion (S-054) | No | Removes the person | |
