# Contract changes: shopping list (S-025 routes)

All routes keep S-025's membership rules: non-member 404, archived kitchen refuses writes as today.

## GET /kitchens/{kitchen_id}/shopping-list  and  GET /kitchens/{kitchen_id}/shopping-lists/{list_id}

Added to every cart line (`lines[]`), `your_call[]` entry and `hand_items[]` entry:

```json
{
  "id": "uuid | null",          // null when status is live or draft (no stored row)
  "bought": false,
  "place": {"kind": "default", "key": "farmers_market"}
        // or {"kind": "custom", "id": "uuid", "name": "Asian market"}
}
```

`place` is resolved for the caller (the viewer), not for the list, also on closed lists (places are not saved with a list). Added at top level:

```json
{ "custom_places": [{"id": "uuid", "name": "Asian market"}] }
```

## PATCH /kitchens/{kitchen_id}/shopping-list/items/{item_id}   (new)

Body `{"bought": true}` → 200 with the whole list, like the other list writes (S-025). Works for cart and hand items of the **active** list. The value sent is set, never flipped (research R10).

| Case | Answer |
|---|---|
| not a member / unknown item | 404 |
| item on a closed list | 409 `list_closed` |
| kitchen archived | 403 `kitchen_archived` |

## POST /kitchens/{kitchen_id}/shopping-list/items   (changed)

Body gains optional `"place": {"kind": "default", "key": "..."} | {"kind": "custom", "id": "uuid"}`. When present, it is saved as the caller's place for the normalized name (FR-016a) in the same transaction. An unknown key or a custom id not owned by the caller → 422 `invalid_place`.

## BFF

`ui/app/api/kitchens/[kitchenId]/shopping-list/items/[itemId]/route.ts` gains `PATCH`, forwarding as the other routes do.
