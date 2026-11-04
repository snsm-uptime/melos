# Contract: admin dashboard

## Access

Every `/admin/*` route answers the same `404 {"detail":"Not Found"}` to anyone signed out, and to any account without `is_admin`. That is the body FastAPI gives an unknown path. All routes are GET and write nothing, except `DELETE /admin/recipes/{id}` (below).

To set the flag, the owner runs this on the server:

```sql
UPDATE users SET is_admin = true WHERE email = '<address>';
```

No request can change it. `is_admin` is not in `/auth/me`.

## `GET /side-panel` (changed)

Gains `is_admin: boolean`, for the caller only. The entry to `/admin` shows only when it's true. `PUT /side-panel/default-kitchen` returns the same shape.

## `GET /admin/units`

Every row, by `reference_count` descending, then name.

```json
{ "units": [{ "name": "lata", "user_references": ["<uuid>"], "reference_count": 1,
              "is_default": false, "created_at": "2026-11-01T22:00:00Z" }] }
```

## `GET /admin/ingredients`

Each name once across all notebooks, by `recipes` descending, then name. A catalog name that no recipe uses shows 0.

```json
{ "ingredients": [{ "name": "tomate", "recipes": 4, "people": 2 }] }
```

## `GET /admin/recipes`

Every recipe, by `cart_adds` descending, then title.

```json
{ "recipes": [{ "id": "<uuid>", "title": "Sopa", "cart_adds": 5,
                "notebook_name": "Cuaderno de Ana", "notebook_kind": "personal",
                "people_with_access": 3, "people_aliases": ["ana", null, "ben"] }] }
```

`people_aliases` lists everyone who can read the recipe (notebook members, or kitchen members), by alias with null aliases last. Its length equals `people_with_access`.

## `DELETE /admin/recipes/{id}`

Removes the recipe in any notebook. `204` on success; `404 {"detail":"Not Found"}` for an unknown id or a non-admin. Added after this contract was approved as read-only; the owner must confirm it. The recipe's lines, steps, source, cart entries, locks and search data go with it.

## `GET /admin/users`

Every account, by alias, with null aliases last.

```json
{ "users": [{ "id": "<uuid>", "alias": "ana", "open_sessions": 2,
              "newest_session_at": "2026-11-01T20:00:00Z",
              "recipes_authored": 7, "latest_recipe_at": "2026-10-30T09:00:00Z",
              "carts_created": 1, "carts_edited": 1, "carts_closed": 1,
              "latest_cart_action_at": "2026-11-01T21:00:00Z" }] }
```

Dates are null when there's nothing to show.

## Never in any answer (FR-019)

Conversations, recipe ingredients or steps, password data, session tokens, emails. An integration test compares the response keys to the lists above, so a new field must be added on purpose.

## UI

- Page: `/admin`, server-rendered. A 404 from the api renders the app's not-found page.
- Four tabs: Units, Ingredients, Recipes, Users. A tab loads its section when opened.
- BFF: `app/api/admin/[section]/route.ts` passes the four sections through and answers 404 to anything else. `app/api/admin/recipes/[recipeId]/route.ts` passes the delete through.
- Recipes tab: a delete column (trash button, confirmed in a dialog through the shared `DeleteItemButton`). The people column shows the count, then the aliases as a scrolling row of chips.
- All text exists in English and Spanish, and the page works at 360px.
