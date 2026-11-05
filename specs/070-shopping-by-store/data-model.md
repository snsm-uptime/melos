# Data Model: Shopping by Store (S-070)

Migration `0018_shopping_places` (down revision `0017_merge_0016_heads`), with a full downgrade.

## shopping_list_item (changed)

| Column | Type | Rule |
|---|---|---|
| bought | boolean, not null, default false | Set only while the list's `closing_date` is null (FR-001, FR-004) |

Domain: `SavedLine.bought: bool = False`. Carry-over rule in research R2.

## place (new)

A person's custom place. Default places are not rows (research R4).

| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| user_id | uuid, FK `users.id` ON DELETE CASCADE, not null | owner |
| name | text, not null | 1–40 chars after trim and space collapse |
| name_key | text, not null | folded name (lower case, no accents); unique `(user_id, name_key)` |
| created_at | timestamptz, default now() | |

Application rules: at most 30 rows per user; `name_key` must not equal the folded English or Spanish name of a default place (FR-007).

## ingredient_place (new)

One person's place for one ingredient name.

| Column | Type | Rule |
|---|---|---|
| user_id | uuid, FK `users.id` ON DELETE CASCADE | PK part |
| name | text | normalized ingredient name (`normalize_name`); PK part |
| default_key | text, null | one of the seven keys (check constraint) |
| place_id | uuid, null, FK `place.id` ON DELETE CASCADE | custom place of the same user |
| updated_at | timestamptz, default now() | |

Check: exactly one of `default_key`, `place_id` is not null. A missing row means `supermarket` (FR-008). Deleting a custom place deletes its rows, so those names fall back to Supermarket.

## Resolved place (read model, not stored)

`PlaceRef = {kind: "default", key} | {kind: "custom", id, name}`. `domain/places.resolve_place(name, choices)` returns the person's choice for `normalize_name(name)` or `{default, supermarket}`.

## Lifecycles

- **Bought**: not bought ⇄ bought while active; frozen at Done. A cart refresh carries it per research R2; hand items keep theirs.
- **Places**: created, renamed, deleted by their owner. Copy from member replaces all of the caller's `place` and `ingredient_place` rows in one transaction.
- **Account deletion** (S-054, later): rows go by cascade.
