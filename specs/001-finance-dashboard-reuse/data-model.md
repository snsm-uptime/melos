# Data Model: Finance-Dashboard Reuse Integration (Bootstrap)

**Source of truth:** Alembic revisions in `api/adapters/persistence/migrations/versions/`.
**Scope:** The tables this feature owns. Every other PRD §1.6 entity is listed under [Deferred entities](#deferred-entities) with the feature that owns it.

## Tables owned by this feature

### `users` (auth, reused unchanged — FR5.3 off-limits)

| Column | Type | Rules |
|--------|------|-------|
| `id` | UUID PK | |
| `email` | varchar(320) | unique. Normalized (trimmed, lower-cased) in `domain/signup.py` |
| `alias` | varchar(32)? | set once. Unique on `lower(alias)` |
| `photo_base64` | text? | size-capped and validated in `domain/photo.py` |
| `password_hash` | varchar(255) | argon2. Password is 8–256 characters (domain) |
| `email_verified_at` | timestamptz? | gates invite acceptance only when `EMAIL_VERIFICATION_REQUIRED=true` |
| `language` | varchar(8)? | kept from the finance schema. **Ignored by the UI** (English only, D3) |
| `theme` | varchar(16)? | `light` / `dark` / `system` |
| `last_opened_kitchen_id` | UUID? FK → kitchens (SET NULL) | the kitchen switcher remembers the last kitchen opened (PRD J1) |
| `created_at` | timestamptz | |

### `sessions`, `password_reset_tokens`, `email_verification_tokens` (auth, reused unchanged)

- `sessions(id, token unique, user_id → users CASCADE, created_at, expires_at)`: an opaque token that backs the httpOnly cookie (`SESSION_COOKIE_NAME`, see [configuration.md](contracts/configuration.md)).
- `*_tokens(id, user_id → users CASCADE, token_hash unique, expires_at, used_at?, created_at)`: single-use and stored hashed. A reset token is valid for 1 hour.

### `kitchens` (finance "lists", renamed)

| Column | Type | Rules |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | varchar(200) | required. The personal kitchen created at sign-up is named **"My kitchen"** |
| `owner_id` | UUID FK → users (CASCADE) | the creator. Roles are on memberships |
| `is_archived` | bool, default false | kept from finance |
| ➕ `content_language` | varchar(2), default `'en'`, CHECK in (`en`,`es`) | **added in `0002`** (D4). Sets the language of canonical ingredient and category names |
| `created_at` | timestamptz | |

**Rules:**
- Only an owner can rename the kitchen, change `content_language` or delete it.
- Changing `content_language` after recipes exist triggers a UI warning. That warning arrives with the recipes feature; the column only stores the value.

### `kitchen_memberships`

| Column | Type | Rules |
|--------|------|-------|
| `id` | UUID PK | |
| `kitchen_id` | UUID FK → kitchens (CASCADE) | unique with `user_id` (`uq_kitchen_membership`) |
| `user_id` | UUID FK → users (CASCADE) | |
| `role` | varchar(32) | `owner` / `member` |
| `is_hidden` | bool | kept from finance (per-user hide) |
| `created_at` | timestamptz | |

**Rules (domain/application):**
- The last owner can't leave or be demoted.
- A non-member gets **404**, not 403, for any kitchen-scoped resource (`application/kitchen_access.py`).

### `kitchen_invite_tokens`

| Column | Type | Rules |
|--------|------|-------|
| `id` | UUID PK | |
| `kitchen_id` | UUID FK → kitchens (CASCADE) | indexed with `email` |
| `email` | varchar(320) | normalized like sign-up |
| `token_hash` | varchar(64) unique | the raw token is only ever in the email link |
| `inviter_user_id` | UUID FK → users (CASCADE) | must be an owner |
| `locale` | varchar(8) | kept from finance. Always `en` (D3) |
| `expires_at`, `used_at?`, `created_at` | timestamptz | single use |

**State transitions:** `pending → accepted` (`used_at` set, membership created, user lands in that kitchen) or `pending → expired` (`now > expires_at`). Revoking deletes the row.

### Extension

- ➕ `vector` (pgvector), enabled in `0002` with `CREATE EXTENSION IF NOT EXISTS vector` (D4). No vector columns exist until the recipes/embeddings feature.

## Migration `0002_pgvector_kitchen_lang`

| Step | Upgrade | Downgrade |
|------|---------|-----------|
| 1 | `CREATE EXTENSION IF NOT EXISTS vector` | `DROP EXTENSION IF EXISTS vector` |
| 2 | `ALTER TABLE kitchens ADD COLUMN content_language varchar(2) NOT NULL DEFAULT 'en'` + `CHECK (content_language IN ('en','es'))` | drop the constraint and the column |

The entrypoint runs it automatically (`alembic upgrade head`). Existing rows get `en`.

## Deferred entities

These are PRD §1.6 tables that are **not** created by this feature. Each is added by an Alembic revision in the spec that owns it. Every one has a `kitchen_id` (directly or through its parent), and access is checked in `application/`.

| Entity | Owning feature (PRD) |
|--------|----------------------|
| `ingredient`, `category`, `source`, `recipe`, `recipe_ingredient`, `recipe_category`, `step` | J2 Capture + J3 Recipes |
| `recipe_embedding` (vector(768), strategy_used, input_tokens) | J2/J3 (embedding on save) |
| `cart`, `cart_item` | J4 Plan |
| `shopping_list`, `shopping_list_item` | J5 Shop |
| `conversation`, `message` | J6 Ask |
| `api_key` (hashed, per user; not yet in PRD §1.6) | MCP service (PRD §1.3.1) |

The dev seed grows with these features (D7).
