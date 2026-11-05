# Data Model: Refused Site Registry

Migration `0016_refused_sites` (revises `0015_recipe_preview_image`).

## `refused_site`

| Column | Type | Rules |
|---|---|---|
| `domain` | text, PK | lower-case registrable domain (R3), ≤ 253 chars |
| `total_refusals` | integer, not null | ≥ 1; +1 per refusal |
| `distinct_members` | integer, not null | ≥ 1; +1 only when a new `refused_site_member` row is inserted |
| `first_seen_at` | timestamptz, not null | set on insert, never changed |
| `last_seen_at` | timestamptz, not null | now() on every refusal |
| `last_status` | smallint, not null | one of 401, 402, 403, 451 (CHECK) |
| `last_message` | text, not null, default `''` | plain text, ≤ 1,000 chars (CHECK `char_length`) |

Index: `(total_refusals DESC, domain)` is not needed at this scale. The admin query sorts in SQL.

## `refused_site_member`

| Column | Type | Rules |
|---|---|---|
| `domain` | text, FK → `refused_site.domain` ON DELETE CASCADE | |
| `member_key` | bytea(32), not null | HMAC fingerprint (R4); no user id |
| PK | (`domain`, `member_key`) | |

Neither table references `users`, so deleting an account changes nothing here (spec edge case).

## Write on refusal (one savepoint)

1. Upsert `refused_site` on `domain`: insert with total 1, distinct 0, first and last = now, status and message. On conflict, `total + 1`, last_seen, last_status, last_message.
2. `INSERT refused_site_member … ON CONFLICT DO NOTHING`. If one row was inserted, `distinct_members + 1`.

## Application types

- `PageFetchFailed(kind, status: int | None = None, message: str = "")`. Only `refused` sets `status` and `message`.
- `AdminRefusedSiteRow(domain, total_refusals, distinct_members, first_seen_at, last_seen_at, last_status, last_message)`.
