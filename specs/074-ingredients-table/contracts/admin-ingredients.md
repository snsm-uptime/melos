# Contract: Admin ingredients and review list (spec 074)

Both endpoints are admin-only (`users.is_admin`, spec 055) and return 403 for other accounts, as the existing admin endpoints do.

## GET /api/admin/ingredients (changed)

Existing endpoint. The response gains three fields per item. Existing fields are unchanged.

```json
{
  "ingredients": [
    {
      "name": "tomate",
      "recipes": 4,
      "people": 2,
      "notebooks": 3,
      "standard_status": "checked",
      "sources": ["discovery", "ai"]
    }
  ]
}
```

| Field | Type | Values |
|---|---|---|
| `notebooks` | integer, 0 or more | distinct notebooks holding the name |
| `standard_status` | string | `checked`, `pending`, `rejected` |
| `sources` | array of strings | subset of `discovery`, `ai`, `admin`; empty when no standard row matches |

**Ordering**: the server keeps the existing order (`recipes` descending, then `name`). The browser applies sorting from spec 066.

**Compatibility**: clients that ignore unknown fields are unaffected. The UI reads the new fields only after this change ships.

## GET /api/admin/ingredient-reviews (new)

Lists flagged values awaiting a decision (spec 073 FR-022). Read only in this story.

```json
{
  "items": [
    {
      "id": "0b9f2c1e-7a3d-4c55-9d2e-1f6a2b3c4d5e",
      "replaces_name": "onion",
      "proposed_name": "cebolla",
      "proposed_language": "es",
      "proposed_by": "Ana",
      "created_at": "2026-11-07T18:20:00Z"
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | `standard_ingredient_review.id` |
| `replaces_name` | string | the AI-made entry it would replace |
| `proposed_name` | string | the value a person entered |
| `proposed_language` | `en` or `es` | |
| `proposed_by` | string or null | alias of the person who entered it; null when the account is deleted |
| `created_at` | ISO 8601 timestamp | |

**Ordering**: `created_at` descending.

**Out of scope here**: accept and reject actions (spec 073 FR-022). A later change adds them.

## Errors

| Status | When |
|---|---|
| 403 | Caller is not an admin. |
| 401 | Caller is not signed in (existing auth layer). |

No new error codes.
