# Contract: Share recipe API

Served by `api` under `/api`, reached from the browser through the `ui` BFF proxy unchanged. Session
cookie auth, as for the other recipe routes. Errors use the existing `{ "code", "detail" }` shape.

## GET /api/recipes/share-candidates

Lists the people the caller can share with (FR-002 to FR-005).

**Response 200**

```json
{
  "candidates": [
    { "user_id": "uuid", "alias": "Ben" }
  ]
}
```

- Order is the one defined in data-model.md (recent shared activity, then alias).
- Empty list is a valid response (edge case: no shared kitchen or notebook).

## POST /api/recipes/{recipe_id}/share

Copies the recipe into the recipient's default notebook (FR-008, FR-011).

**Request**

```json
{ "recipient_user_id": "uuid" }
```

**Response 201**

```json
{
  "recipe_id": "uuid",
  "recipient_alias": "Ben",
  "notebook_id": "uuid"
}
```

The response does not include the recipe body.

**Errors**

| Status | `code` | When |
|--------|--------|------|
| 404 | `recipe_not_found` | Caller cannot read the recipe, or it does not exist |
| 404 | `recipient_not_found` | Recipient is not a share candidate of the caller, or does not exist (same body for both: no alias leak) |
| 409 | `share_self` | Recipient is the caller |
| 422 | `recipient_no_default_notebook` | Recipient's default notebook cannot be resolved; no copy made |
| 500 | `share_failed` | Unexpected failure; the transaction rolls back and nothing is copied |

The popup maps each code to a message in English and Spanish (FR-010, FR-012). On any error the
chosen recipient stays selected.

## Security notes

- Both routes require a session; unauthenticated calls get the existing 401.
- The recipient check runs on the server for every send; the list is never trusted.
- No email is sent by either route (spec assumption).
