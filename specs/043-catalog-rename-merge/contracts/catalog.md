# Contract: Catalog management API

Routes in `api/api/routes/catalog.py`, mounted under `/notebooks` like `routes/notebooks.py`; the ui
BFF proxies them as `/api/notebooks/...` (`ui/app/api/notebooks/[id]/catalog/...`). Every route
needs a session. A notebook the person cannot read gives `404`; read but not write gives `403`
on writes only (the existing notebook rule); errors use the existing `{"detail": {"code": ...}}`
shape. Names in requests are normalized by the api (trimmed, lower-case, singular); responses
return the stored form.

## GET /notebooks/{notebook_id}/catalog

Readable notebooks. The catalog with other names and use counts.

```json
{
  "notebook_id": "uuid",
  "can_write": true,
  "ingredients": [
    {
      "name": "onion",
      "language": "en",
      "recipe_count": 4,
      "variants": [{"name": "cebolla", "language": "es"}],
      "spellings": ["yellow onion"]
    }
  ]
}
```

## PATCH /notebooks/{notebook_id}/catalog/{name}

Rename (FR-010 to FR-012). Body `{"new_name": "tomato", "language": "en" | "es" | null}`
(`language` optional: sets the kept name's language without renaming when `new_name` equals the
current name).

- `200` the updated ingredient (shape above) plus `"recipes_changed": 2`.
- `409 {"code": "name_exists", "existing": "tomato"}`: the new name is a kept or other name, or the
  same name under S-018 rules; the ui offers merge into `existing`.
- `409 {"code": "name_changed"}`: the old name is gone (FR-015).
- `422 {"code": "name_blank"}`.

## DELETE /notebooks/{notebook_id}/catalog/{name}

FR-013. `204`, or `409 {"code": "name_in_use", "recipe_count": 3}`, or `409 name_changed`.

## POST /catalog/merge-preview

Body `{"from_notebook_id": "uuid", "merged": "cebolla", "kept": "onion"}`. Both names must be in
that notebook's catalog (FR-003), else `422 {"code": "unknown_name"}`; the preview then reaches
every writable notebook with both names (FR-002a).

```json
{
  "merged": "cebolla",
  "kept": "onion",
  "merged_language": "es",
  "kept_language": "en",
  "notebooks": [
    {"notebook_id": "uuid", "name": "Cuaderno de Ana", "recipe_count": 3}
  ]
}
```

Languages are prefilled from the recipes using each name (most common recipe language), or the
stored `ingredient.language`. `422 {"code": "same_ingredient"}` when the two are already one
ingredient everywhere; `notebooks: []` when no writable notebook has both.

## POST /catalog/merge

Body `{"merged", "kept", "merged_language", "kept_language", "notebook_ids": [...]}`
(`notebook_ids` as returned by the preview; the api merges only those that still qualify).

```json
{
  "merged": [{"notebook_id": "uuid", "recipes_changed": 3}],
  "skipped": [{"notebook_id": "uuid", "reason": "name_changed" | "no_access"}]
}
```

## POST /notebooks/{notebook_id}/catalog/{name}/split

Body `{"other_name": "cebolla"}`. FR-014, User Story 4. `200` with both ingredients and
`"recipes_changed"`; `409 name_changed`.

## POST /notebooks/{notebook_id}/catalog/pair-suggestions

FR-009a, b. Writable notebooks. `200 {"pairs": [{"en": "garlic", "es": "ajo"}]}`;
`503 {"code": "ai_unavailable"}` mapped from the adapter (constitution 3). Rate limited like
capture (the existing per-user limit).

## POST /notebooks/{notebook_id}/catalog/pair-dismissals

Body `{"en": "garlic", "es": "ajo"}`. `204`. FR-009d.

## Changed routes

- `GET /recipes/{id}`: adds `"language"` and `"proposed_language"` (null or `en`/`es`); each line adds `"shown_name"` (FR-006).
- `PUT /recipes/{id}`: accepts `"language"` (setting it clears the proposal) and `"proposed_language": null` (dismiss). The edit form sends `language`.
- `PATCH /recipes/{id}/language` (added 2026-11-06, owner choice for T062): body `{"language": "en" | "es" | null}`. The recipe page's "Detected: {language}. Apply? / Dismiss" banner uses it: a language applies it and clears the proposal, null dismisses the proposal. It needs no edit lock or recipe body, only write access. It is `409 recipe_locked` while another person edits the recipe, `403` read-only, `404` not found. It returns the recipe as `GET /recipes/{id}` does.
- Capture draft responses: add `"language"` (detected offline from the text, else the interface language); save requests accept it.
- `GET /kitchens/{id}/shopping-list` and closed lists: each item's `name` is the name shown to the
  viewer (FR-007); adds `"kept_name"` for places and keys.
