# Contract: Cart API (api and BFF)

The BFF exposes the same paths under `/api/…` and forwards cookies, as for existing kitchen routes. All routes need a signed-in user with an alias. Kitchen access: a non-member, or an unknown kitchen, gets **404** on every route.

Errors use the existing `{ "code": "...", "detail": "..." }` body.

| Code | HTTP | When |
|---|---|---|
| `kitchen_not_found` | 404 | not a member / no such kitchen |
| `recipe_not_found` | 404 | recipe missing, not in this kitchen's notebooks, or personal |
| `kitchen_archived` | 403 | any write in an archived kitchen |
| `cart_locked` | 409 | another live session edits the cart; body adds `editor_alias` |
| `not_editing` | 409 | draft write/save/discard without holding the lock |
| `invalid_value` | 422 | people or meals not a whole number 1–99; duplicate recipe; body adds `field` |

## GET /kitchens/{kitchen_id}/cart

200:
```json
{
  "kitchen_id": "uuid",
  "people": 2,
  "people_is_default": true,
  "entries": [
    {"recipe_id": "uuid", "title": "Tomato rice", "notebook_id": "uuid", "notebook_name": "Ana's (Home) Notebook",
     "base_servings": 4, "meals": 1, "factor": "0.5"}
  ],
  "editor": {"alias": "Ana", "is_me": false, "idle_expires_at": null},
  "draft": null,
  "can_edit": false
}
```
- `entries` is the saved cart, ordered by `added_at`.
- `editor` is null when no live lock. For my own lock, `idle_expires_at` is when it ends without activity (5 min after the last activity). `can_edit` is false when archived or someone else edits.
- `draft` is present only when the caller's session holds the lock: same shape as the top level (`people`, `people_is_default`, `entries`) plus `dropped_recipe_ids`.

## POST /kitchens/{kitchen_id}/cart/edit

Take the lock, or for the holder: keep-alive (sets `last_active_at`, research R10). A new draft starts as a copy of the saved cart. 200 → the GET body with `draft`. 409 `cart_locked`.

## PUT /kitchens/{kitchen_id}/cart/draft

Body: `{"people": 3 | null, "items": [{"recipe_id": "uuid", "meals": 2}]}`. `people: null` keeps the default (follow members). Replaces the whole draft and counts as activity. 200 → GET body. 409 `not_editing`, 422 `invalid_value`, 404 `recipe_not_found`.

## POST /kitchens/{kitchen_id}/cart/draft/items

Body: `{"recipe_id": "uuid"}`. Takes the lock if free, then adds the recipe with meals 1 (no-op if already in the draft). 200 → GET body. 409 `cart_locked`, 404 `recipe_not_found`.

## DELETE /kitchens/{kitchen_id}/cart/draft/items/{recipe_id}

Takes the lock if free, removes the recipe from the draft. 200 → GET body. 409 `cart_locked`.

## POST /kitchens/{kitchen_id}/cart/save

Applies the draft in one transaction, raises `recipe.cart_add_count` for newly added recipes, releases the lock. 200 → GET body (no draft) plus `dropped_recipe_ids`. 409 `not_editing`.

## DELETE /kitchens/{kitchen_id}/cart/edit

Discards the draft and releases the lock. 204. Idempotent (204 when not holding).

Clearing the cart is `PUT …/draft` with `items: []` followed by save; the ui asks for confirmation first.

All draft writes and `POST …/cart/edit` by the holder renew the idle limit. After 5 minutes without activity the lock is gone: the holder's next draft write or save answers 409 `not_editing`, and the draft is deleted.
