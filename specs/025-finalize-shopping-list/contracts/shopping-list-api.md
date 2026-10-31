# Contract: Shopping List API

All routes need a session. Non-members, unknown kitchens and lists of another kitchen get 404 `kitchen_not_found` or `list_not_found`. Writes in an archived kitchen get 403 `kitchen_archived`.

## GET /kitchens/{id}/shopping-list (extended, fields added)

```json
{
  "is_empty": false,
  "status": "live",
  "list_id": null,
  "lines": [],
  "your_call": [],
  "hand_items": [{"id": "uuid", "name": "dish soap", "quantity": null, "unit": null, "size": null}]
}
```

`status`: `live` (no active list), `active` (stored), `draft` (the caller's unsaved cart plus hand items). `list_id` is set for `active` and `draft` when a list exists. Reads take no lock.

`is_empty` is true only when the cart has no recipes and the list has no items.

Each recipe ref in a stored line also has `exists: boolean`, computed on read.

## POST /kitchens/{id}/shopping-list/items

Body: `{"name": "dish soap", "quantity": "2", "unit": "unit", "size": null}`. Only `name` is required; `quantity` and `unit` come together, and units are the PRD set. 201 with the read shape. 422 `invalid_item`.

## DELETE /kitchens/{id}/shopping-list/items/{item_id}

Hand items of the active list. 200 with the read shape. 404 `item_not_found`, also for a cart line or a closed list's item.

## POST /kitchens/{id}/shopping-list/done

Body: `{"list_id": "uuid"}`. 200 with the closed list. 409 `list_not_active` if already closed; 409 `list_empty` if it has no items.

## GET /kitchens/{id}/shopping-lists

Closed lists, newest first: `{"items": [{"id", "closing_date", "recipe_titles": []}]}`.

## GET /kitchens/{id}/shopping-lists/{list_id}

`{"id", "closing_date", "lines", "your_call", "hand_items"}`.

## POST /kitchens/{id}/cart/save (behaviour only)

The response does not change. The save also creates or refreshes the active list.

The BFF mirrors these routes under `/api/kitchens/{id}/...`.
