# Contract: Side panel API

Session cookie required; otherwise `401`. The BFF exposes both routes at `/api/side-panel...`.

## GET /side-panel

Resolves the default (data-model.md), stores it if changed, and returns:

```json
{ "default_kitchen_id": "uuid-or-null", "recipes_added": 5, "notebooks": 2 }
```

## PUT /side-panel/default-kitchen

Body: `{ "kitchen_id": "uuid" }`

| Case | Status | Code |
|---|---|---|
| Member of an active kitchen | `200`, same body as GET | |
| Unknown kitchen, or not a member | `404` | `kitchen_not_found` |
| Archived kitchen | `409` | `kitchen_archived` |

## Unchanged

All `/auth/*` routes, and the kitchen create, rename, archive, unarchive, delete and invite routes.
