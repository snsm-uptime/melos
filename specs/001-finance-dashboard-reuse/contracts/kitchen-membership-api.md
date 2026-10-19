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
| `name` | String | Human-readable name (e.g., "Weeknight Dinners") |
| `owner_id` | UUID | Foreign key to user; cannot be changed |
| `description` | String | Optional; kitchen metadata |
| `created_at` | Timestamp | Creation time |
| `updated_at` | Timestamp | Last modification time |

### Membership

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `kitchen_id` | UUID | Foreign key to kitchen |
| `user_id` | UUID | Foreign key to user |
| `role` | Enum | "owner" or "member" |
| `joined_at` | Timestamp | When user joined |

**Constraint:** One membership per (kitchen_id, user_id) pair.

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
      "description": "Quick meals for work nights",
      "owner_id": "uuid-owner",
      "role": "owner",
      "member_count": 3,
      "created_at": "2026-10-01T10:00:00Z"
    },
    {
      "id": "uuid-2",
      "name": "Sunday Brunch",
      "description": "Shared brunch recipes",
      "owner_id": "uuid-other",
      "role": "member",
      "member_count": 2,
      "created_at": "2026-10-05T14:30:00Z"
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

Create a new kitchen.

**Request:**
```json
{
  "name": "Holiday Recipes",
  "description": "Recipes for holiday meals"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "Holiday Recipes",
  "description": "Recipes for holiday meals",
  "owner_id": "<authenticated_user_id>",
  "role": "owner",
  "member_count": 1,
  "created_at": "2026-10-19T12:00:00Z"
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
  "description": "Quick meals",
  "owner_id": "uuid-owner",
  "role": "member",
  "members": [
    {
      "user_id": "uuid-owner",
      "alias": "John Doe",
      "role": "owner",
      "joined_at": "2026-10-01T10:00:00Z"
    },
    {
      "user_id": "uuid-member",
      "alias": "Jane Smith",
      "role": "member",
      "joined_at": "2026-10-15T14:30:00Z"
    }
  ],
  "created_at": "2026-10-01T10:00:00Z"
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

Update kitchen details (owner only).

**Request:**
```json
{
  "name": "Weeknight Dinners (Updated)",
  "description": "Easy recipes for busy weeknights"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Weeknight Dinners (Updated)",
  "description": "Easy recipes for busy weeknights",
  "owner_id": "uuid-owner",
  "role": "owner",
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-19T15:45:00Z"
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
      "email": "john@example.com",
      "role": "owner",
      "joined_at": "2026-10-01T10:00:00Z"
    },
    {
      "user_id": "uuid-member",
      "alias": "Jane Smith",
      "email": "jane@example.com",
      "role": "member",
      "joined_at": "2026-10-15T14:30:00Z"
    }
  ]
}
```

---

### DELETE /kitchens/{kitchen_id}/members/{user_id}

Remove a member from a kitchen (owner only).

**Request:** (uses session cookie)

**Response (204 No Content)**

**Error (403 Forbidden):**
```json
{
  "detail": "Only the owner can remove members"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Cannot remove the owner"
}
```

**Note:** Owner cannot remove self via this endpoint (use kitchen deletion instead).

---

## Invitations

### POST /kitchens/{kitchen_id}/invites

Create an invite link (owner only).

**Request:**
```json
{
  "email": "guest@example.com"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "kitchen_id": "uuid",
  "email": "guest@example.com",
  "token": "<random_invite_token>",
  "invite_url": "http://localhost:3000/invites/accept?token=<token>",
  "created_at": "2026-10-19T12:00:00Z",
  "expires_at": "2026-10-26T12:00:00Z"
}
```

**Email:** If guest's email is in the system, an invitation email is sent automatically.

**Error (403 Forbidden):**
```json
{
  "detail": "Only the owner can create invites"
}
```

---

### GET /kitchens/{kitchen_id}/invites

List pending invites (owner only).

**Response (200 OK):**
```json
{
  "invites": [
    {
      "id": "uuid",
      "email": "guest@example.com",
      "created_at": "2026-10-19T12:00:00Z",
      "expires_at": "2026-10-26T12:00:00Z",
      "status": "pending"
    }
  ]
}
```

---

### POST /invites/accept

Accept an invite (any user, or anonymous if invitation creates account).

**Request:**
```json
{
  "token": "<invite_token>"
}
```

**Response (200 OK):**
```json
{
  "kitchen_id": "uuid",
  "kitchen_name": "Weeknight Dinners",
  "detail": "Invitation accepted"
}
```

**Behavior:** If user is authenticated, adds them to the kitchen. If not authenticated, redirects to sign-up (which then adds them on completion).

**Error (400 Bad Request):**
```json
{
  "detail": "Invitation invalid or expired"
}
```

**Token Expiry:** 7 days from creation.

---

## Access Control

**Kitchen Ownership:**
- Kitchen owner can: view, update, delete kitchen; manage members; create invites
- Kitchen member can: view kitchen; view/create recipes, carts, shopping lists, conversations
- Non-member: receives 404 on all kitchen endpoints (no permission distinction)

**Application Layer Enforcement:**
All endpoints check membership in `application/kitchens.py` and `application/invites.py` before returning data. No endpoint returns 403; non-members always see 404.

---

## Configuration & Defaults

```bash
# Invite Expiry (not configurable, hardcoded)
INVITE_EXPIRY_DAYS=7

# Email Templates
INVITE_EMAIL_SUBJECT="You're invited to join {kitchen_name} on Melos"
INVITE_EMAIL_TEMPLATE=<based_on PUBLIC_APP_URL>
```

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

