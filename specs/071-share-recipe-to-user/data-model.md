# Data Model: Share a recipe with a person from the recipe page

No new tables or columns (research R-2). The feature reads existing entities and creates one
recipe row per send.

## Entities

### Share candidate (read model, not stored)

A user who shares at least one kitchen or notebook with the caller.

| Field | Source | Notes |
|-------|--------|-------|
| `user_id` | users | Never the caller's id |
| `alias` | users / preferences | Shown in the select; the only personal field exposed |
| `shared_at` | membership join times | Max over shared contexts; used for order only; may be null (R-1) |

**Rules**
- Included only if a shared kitchen membership or a shared notebook membership exists (FR-003).
- The caller is excluded. A person in both a shared kitchen and a shared notebook appears once (edge case).
- Order: `shared_at` descending where present, then `alias` case-insensitive ascending (FR-004).
- The list is not paged; it is small.

### Share copy (created on send)

A new row in `recipes` with the same content as the source, plus:

| Field | Value |
|-------|-------|
| `notebook_id` | recipient's default notebook |
| `author_id` | recipient's user id (FR-008) |
| source link | none: the copy has no link to the original (FR-011, spec assumption) |
| ingredient lines | names normalized against the target notebook catalog (R-3) |

Ingredient catalog: new normalized names are added to the target notebook's catalog, as the kitchen
copy does.

The source recipe is read only; no field of it changes (FR-011, SC-003).

## Validation rules

- Caller must be able to read the source recipe. Otherwise 404, the same as a missing recipe.
- Recipient must be a share candidate of the caller at send time (server-side check, not only in
  the list). Otherwise 404 with no alias in the body (constitution principle 4).
- Recipient must have a resolvable default notebook. Otherwise 422-style refusal with a message and
  no copy (edge case).
- Recipient is not the caller. Sending to oneself is refused.
- A deleted recipient fails the send with a message; the popup stays open (edge case).

## State transitions (popup, UI only)

```text
closed --open--> listing --choose--> chosen --send--> sending
sending --ok--> success (list hidden until reopened, FR-009)
sending --error--> chosen (error shown, selection kept, FR-010)
success --close--> closed
```

Send is disabled in `listing` and `sending` (FR-007).
