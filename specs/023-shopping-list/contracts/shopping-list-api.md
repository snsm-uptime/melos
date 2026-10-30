# Contract: Shopping List API (api and BFF)

The BFF exposes the same path under `/api/…` and forwards cookies, as for the cart routes (spec 022). The route needs a signed-in user with an alias. Errors use the existing `{ "code": "...", "detail": "..." }` body.

| Code | HTTP | When |
|---|---|---|
| `kitchen_not_found` | 404 | not a member / no such kitchen (FR-012) |

There is no other error: the route does not write, so it has no lock, archive or value errors. An archived kitchen answers 200.

## GET /kitchens/{kitchen_id}/shopping-list

Builds the list on this request; nothing is stored. It does not take, renew or release the cart lock and does not change the cart, recipes, catalog or any add count (FR-014).

Which cart it reads (FR-001): if the caller's session holds the live cart lock and has a draft, the draft (its People, recipes and Meals). Otherwise the saved cart. Recipes that no longer exist, or are not in this kitchen's notebooks, are skipped.

200:
```json
{
  "is_empty": false,
  "lines": [
    {
      "name": "flour",
      "kind": "volume",
      "size": null,
      "amounts": [
        {"quantity": "1", "unit": "cup"},
        {"quantity": "3", "unit": "tbsp"}
      ],
      "recipes": [
        {"recipe_id": "uuid", "title": "Bread"},
        {"recipe_id": "uuid", "title": "Pancakes"}
      ]
    },
    {
      "name": "onion",
      "kind": "count",
      "size": "large",
      "amounts": [{"quantity": "2", "unit": "unit"}],
      "recipes": [{"recipe_id": "uuid", "title": "Stew"}]
    }
  ],
  "your_call": [
    {
      "name": "salt",
      "notes": ["a pinch", "to taste"],
      "recipes": [
        {"recipe_id": "uuid", "title": "Bread"},
        {"recipe_id": "uuid", "title": "Stew"}
      ]
    }
  ]
}
```

Field rules:
- `is_empty` is true when the cart (or the editor's draft) has no recipes; then `lines` and `your_call` are empty (FR-011). A non-empty cart whose recipes have no ingredient lines also returns empty arrays with `is_empty: false`.
- `kind` is `mass`, `volume` or `count`, derived from the unit (FR-004).
- `size` is `small`, `medium`, `large` or null; non-null only for `count` (FR-005).
- `amounts` is ordered largest unit first within the kind: mass `kg, lb, oz, g`; volume `l, cup, tbsp, tsp, ml` (FR-006). A `count` line has exactly one amount with `unit: "unit"`.
- `quantity` is a string: a whole number for counts (rounded up after summing); for mass and volume at most 2 decimals, half up, trailing zeros removed (`"0.33"`, `"1.5"`, `"2"`). A string so no precision is lost in JSON.
- `lines` is sorted by name (accents and case ignored), then mass < volume < count, then for counts large < medium < small < no size (FR-010). `your_call` is sorted by name.
- `recipes` lists each recipe once, in cart order, by `recipe_id` (two recipes with the same title give two entries) (FR-008).
- `notes` lists each distinct vague note once, in the order first met (FR-007).
- Names, notes and titles are as stored, untranslated (FR-013).

## Examples that fix the contract (from the spec)

| Case | Result |
|---|---|
| A: 3 tbsp flour, B: 1 cup flour, factor 1 (AC5.1) | one `volume` line, amounts `1 cup`, `3 tbsp`, recipes A, B |
| base servings 4, 2 eggs, People 3, Meals 1 (AC5.2) | one `count` line, `quantity: "2"` |
| rice 200 g in one recipe, 1 cup in another (AC5.3) | two lines: `mass` and `volume` |
| 1 large onion in two recipes, 1 small in a third (AC5.4) | `onion` large `"2"`, `onion` small `"1"` |
| chopped onion + sliced onion | one line |
| salt "a pinch" in A, "to taste" in B | `your_call` entry `salt`, notes both, recipes A, B |
| butter vague in A, 100 g in B | `lines` has `butter` 100 g (B); `your_call` has `butter` (A) |
