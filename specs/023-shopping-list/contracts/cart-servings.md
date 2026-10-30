# Contract change: cart by servings (2026-10-30)

Applies to the cart routes of spec 022 and their BFF routes. Paths and status codes do not change.

## Cart responses

- Removed at the cart and draft levels: `people`, `people_is_default`.
- Each entry: `meals` is replaced by `servings` (whole, 1 to 99). `factor` is now `servings / base_servings`, formatted as before.

```json
{ "recipe_id": "…", "title": "Tomato rice", "base_servings": 4, "servings": 6, "factor": "1.5" }
```

## Replace draft (request)

```json
{ "items": [{ "recipe_id": "…", "servings": 6 }] }
```

`people` is no longer accepted as a meaningful field. A `servings` value outside 1 to 99 gets the same refusal `meals` got today, and a duplicate recipe is still refused.

## Add to draft

The request is unchanged. The new entry's `servings` is the recipe's base servings.

## Shopping list

`GET /kitchens/{id}/shopping-list`: the response shape is unchanged; only the factor behind the amounts changes.

## UI

- Cart row: `Servings` / `Porciones` field while editing, `Servings n` when read-only. No People field.
- Remove: icon button with `CloseIcon`, label `Remove {title}` / `Quitar {title}`, editing view only.
- Recipe card: selected background while `inCart`; the cart-icon button keeps `aria-pressed`.
