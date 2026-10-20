# Kitchen & Membership API Contract (Reused Pattern from finance-dashboard)

**Status:** Stable (pattern reused; endpoints new for Melos)  
**Basis:** finance-dashboard kitchen/"list" pattern  
**Naming:** "list" → "kitchen" in all Melos code and UI

---

## Overview

Kitchens are shared spaces where users collaborate on recipes, shopping lists, and carts. Each user can own or be a member of multiple kitchens. Access control is enforced at the application layer: non-members receive 404 (not 403) for any kitchen resource.

---

## Data Model

### Kitchen

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `name` | varchar(200) | Required; human-readable name (e.g., "Weeknight Dinners") |
| `owner_id` | UUID | Foreign key to user; cannot be changed |
| `is_archived` | Boolean | Default false; hides kitchen from owner's list |
| `content_language` | varchar(2) | Default `'en'`; CHECK constraint: `'en'` or `'es'`. Sets canonical ingredient/category language |
| `created_at` | Timestamp | Creation time |

### Membership

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `kitchen_id` | UUID | Foreign key to kitchen |
| `user_id` | UUID | Foreign key to user |
| `role` | Enum | `'owner'` or `'member'` |
| `is_hidden` | Boolean | Per-user hide (member-only; owner cannot hide their own kitchen) |
| `created_at` | Timestamp | When user joined |

**Constraint:** Unique (kitchen_id, user_id) pair.

---

## Endpoints

### GET /kitchens

List all kitchens where the authenticated user is a member or owner.

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "kitchens": [
    {
      "id": "uuid-1",
      "name": "Weeknight Dinners",
      "owner_id": "uuid-owner",
      "role": "owner",
      "is_archived": false,
      "content_language": "en",
      "members": [
        {
          "user_id": "uuid-owner",
          "alias": "John Doe",
          "photo_base64": null
        }
      ]
    },
    {
      "id": "uuid-2",
      "name": "Sunday Brunch",
      "owner_id": "uuid-other",
      "role": "member",
      "is_archived": false,
      "content_language": "en",
      "members": [
        {
          "user_id": "uuid-other",
          "alias": "Jane Smith",
          "photo_base64": null
        }
      ]
    }
  ]
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

---

### POST /kitchens

Create a new kitchen owned by the authenticated user.

**Request:**
```json
{
  "name": "Holiday Recipes",
  "content_language": "en"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "Holiday Recipes",
  "owner_id": "<authenticated_user_id>",
  "is_archived": false,
  "content_language": "en"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Kitchen name is required"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

---

### GET /kitchens/{kitchen_id}

Get kitchen details (only if user is a member or owner).

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Weeknight Dinners",
  "owner_id": "uuid-owner",
  "is_archived": false
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

**Note:** Returns 404 even if the kitchen exists but the user is not a member (security: no kitchen enumeration).

---

### PATCH /kitchens/{kitchen_id}

Update kitchen name or content_language (owner only).

**Request:**
```json
{
  "name": "Weeknight Dinners (Updated)",
  "content_language": "es"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Weeknight Dinners (Updated)",
  "owner_id": "uuid-owner",
  "is_archived": false,
  "content_language": "es"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

**Error (403 Forbidden):**
```json
{
  "detail": "Only the kitchen owner can update settings"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

---

### POST /kitchens/{kitchen_id}/archive

Archive a kitchen (owner only). Archived kitchens are hidden from the owner's list.

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Weeknight Dinners",
  "owner_id": "uuid-owner",
  "is_archived": true,
  "content_language": "en"
}
```

**Error (403 Forbidden):**
```json
{
  "detail": "Only the kitchen owner can archive the kitchen",
  "code": "not_kitchen_owner"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

---

### POST /kitchens/{kitchen_id}/unarchive

Unarchive a kitchen (owner only).

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Weeknight Dinners",
  "owner_id": "uuid-owner",
  "is_archived": false,
  "content_language": "en"
}
```

**Error (403 Forbidden):**
```json
{
  "detail": "Only the kitchen owner can unarchive the kitchen",
  "code": "not_kitchen_owner"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

---

### POST /kitchens/{kitchen_id}/hide

Hide a kitchen from the authenticated user's list (member only; owner cannot hide their own kitchen).

**Request:** (uses session cookie)

**Response (204 No Content)**

**Error (403 Forbidden):**
```json
{
  "detail": "Kitchen owner cannot hide their own kitchen",
  "code": "cannot_hide_owned_kitchen"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

---

### POST /kitchens/{kitchen_id}/unhide

Unhide a kitchen in the authenticated user's list.

**Request:** (uses session cookie)

**Response (204 No Content)**

**Error (403 Forbidden):**
```json
{
  "detail": "Kitchen owner cannot hide their own kitchen",
  "code": "cannot_hide_owned_kitchen"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

---

### DELETE /kitchens/{kitchen_id}

Delete a kitchen (owner only).

**Request:** (uses session cookie)

**Response (204 No Content)**

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

**Error (403 Forbidden):**
```json
{
  "detail": "Only the kitchen owner can delete the kitchen"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Kitchen not found"
}
```

**Note:** Cascades delete all associated recipes, carts, shopping lists, conversations, and memberships.

---

## Member Management

### GET /kitchens/{kitchen_id}/members

List all members of a kitchen (any member can view).

**Response (200 OK):**
```json
{
  "members": [
    {
      "user_id": "uuid-owner",
      "alias": "John Doe",
      "photo_base64": null
    },
    {
      "user_id": "uuid-member",
      "alias": "Jane Smith",
      "photo_base64": null
    }
  ]
}
```

---

### DELETE /kitchens/{kitchen_id}/members/{user_id}

**Status:** Not in bootstrap scope. Will be added in a future phase.

---

## Invitations

Invites are bound to one email address. The raw token is only ever in the email link; the database stores its SHA-256 hash. A token is single-use and expires **7 days** after creation (`INVITE_TOKEN_TTL` in `domain/kitchen_invite.py`; not configurable).

### POST /kitchens/{kitchen_id}/invites

Invite someone by email (owner only). Sends one of two emails:

| Invitee | `template_kind` | Link in the email |
|---------|-----------------|-------------------|
| Already has an account | `join` | `{PUBLIC_APP_URL}/invites/accept?token=<raw>` |
| No account yet | `signup` | `{PUBLIC_APP_URL}/signup?invite=<raw>` |

**Request:**
```json
{ "email": "guest@example.com" }
```

**Response (201 Created):**
```json
{ "status": "sent", "template_kind": "join", "invite_id": "uuid" }
```

The response never contains the raw token or the link.

**Errors:**

| Status | `code` | When |
|--------|--------|------|
| 401 | — | No session |
| 404 | `kitchen_not_found` | Kitchen missing, or caller is not a member |
| 403 | `not_kitchen_owner` | Caller is a member but not the owner |
| 409 | `already_kitchen_member` | Invitee is already a member |
| 422 | `invalid_invite_email` | Email is not a valid address |
| 503 | `smtp_config_error` / `smtp_send_error` | SMTP misconfigured or send failed (logged; see [error-responses.md](error-responses.md)) |

Listing or revoking pending invites is not part of the bootstrap.

### GET /invites/preview?token=<raw>

Public (no session). Lets the UI show the invite before the user signs in or signs up.

**Response (200 OK):**
```json
{ "kitchen_name": "Dev Kitchen", "email_hint": "g***t@example.com", "path": "join" }
```

`path` is `"join"` when the invited email has an account, otherwise `"signup"`.

**Error (410 Gone):** `{"detail": "...", "code": "invalid_invite_token"}` when the token is empty, unknown, expired or already used.

### POST /invites/accept

Accept an invite as a signed-in user (`path` = `join`).

**Request:**
```json
{ "token": "<raw>" }
```

**Response (200 OK):**
```json
{ "kitchen_id": "uuid" }
```

Accepting again when already a member returns 200 with the same body (idempotent).

**Errors:**

| Status | `code` | When |
|--------|--------|------|
| 401 | — | No session. The API never redirects |
| 410 | `invalid_invite_token` | Token unknown, expired or already used |
| 403 | `invite_email_mismatch` | Signed in with a different email than the one invited |
| 403 | `email_not_verified` | `EMAIL_VERIFICATION_REQUIRED=true` and the caller's email is not verified |

### POST /auth/register with `invite_token` (new invitees)

Someone without an account (`path` = `signup`) signs up and joins in one call: the usual `/auth/register` body plus `"invite_token": "<raw>"` ([auth-api.md](auth-api.md)). The user gets their personal "My kitchen" and a `member` membership in the inviting kitchen. When `EMAIL_VERIFICATION_REQUIRED=true`, the account and personal kitchen are created but joining waits until the email is verified and the invite is accepted.

Extra errors: `410 invalid_invite_token`, `403 invite_email_mismatch` (sign-up email differs from the invited email).

### Invite flow (UI)

The API never redirects; the UI routes the user:

1. **Existing account** (`join` email) → `/invites/accept?token=…`. Signed out: the page offers **Sign in**, which returns to the same URL. Signed in: the page calls `POST /invites/accept`, then lands in the kitchen. `email_not_verified` sends the user to `/verify` and back.
2. **New account** (`signup` email) → `/signup?invite=…`. The form calls `/invites/preview`, shows the kitchen name, and submits `/auth/register` with `invite_token`. If the preview says `join` (the person registered meanwhile), the page redirects to `/invites/accept`. A signed-in visitor is redirected to `/invites/accept` too.
3. Invalid or expired token → the page shows the "invite expired" message (from the `410`).

---

## Access Control

One rule for every kitchen-scoped endpoint, reads and writes alike (spec FR7, constitution §3), checked in order:

| Order | Condition | Response |
|-------|-----------|----------|
| 1 | No session | `401` |
| 2 | Kitchen missing **or** caller not a member | `404 {"code": "kitchen_not_found"}`. Same body in both cases, so nobody can tell whether a kitchen exists |
| 3 | Member, but the action is owner-only | `403 {"code": "not_kitchen_owner"}` |
| 4 | Request problems | `409` / `422` |

- Owner-only actions: rename (incl. `content_language`), archive/unarchive, delete, invite.
- Member actions: view the kitchen and its members, hide/unhide it for themselves, and (later features) work with recipes, carts, lists and conversations.
- `403` is never used for non-members. The only other `403`s are invite-specific (`invite_email_mismatch`, `email_not_verified`).
- Setting `last_opened_kitchen_id` (`PATCH /auth/me`) to a kitchen the user is not a member of follows the same rule: `404 kitchen_not_found`.

Enforcement lives in `application/kitchen_access.py`.

---

## Configuration & Defaults

- Invite token lifetime: 7 days, a domain constant (not an environment variable).
- Invite emails use `PUBLIC_APP_URL` for links and are sent over SMTP, which is configured in every environment, dev included.

---

## Testing

Kitchen and membership endpoints are tested via:
1. **Unit tests** (domain/): Kitchen creation, membership validation
2. **Integration tests** (api/tests/test_kitchens.py, test_members.py, test_invites.py):
   - Kitchen CRUD, member list, member removal
   - Invite creation, acceptance, expiry
   - Access control (non-members receive 404)
3. **BFF tests** (ui/__tests__/api/kitchen-proxy.tsx): Kitchen proxy routing

Test database: Uses `docker-compose.test.yml` with isolated Postgres.

