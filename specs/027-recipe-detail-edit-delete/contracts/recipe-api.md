# Contract: Recipe routes (api)

All routes require a signed-in user with an alias (`require_user_alias`), as the save route does. Bodies are JSON. Error bodies are `{"detail": string, "code": string}` plus the fields noted. Through the ui BFF the paths are the same under `/api`.

Access for every route: the caller must be able to read the recipe's notebook (spec 056), else **404 `recipe_not_found`**, identical to a missing recipe. Routes that change data also need write access, else **403 `recipe_read_only`**.

## GET /recipes/{recipe_id}

Read one recipe. Writes nothing.

**200**
```json
{
  "id": "uuid", "title": "Tomato rice", "base_servings": 4, "servings_estimated": false,
  "author_alias": "ana", "created_at": "2026-10-28T10:00:00Z", "version": "2026-10-28T10:05:00.123456Z",
  "notebook": {"id": "uuid", "name": "ana's Notebook", "kind": "personal", "kitchen_id": null},
  "can_write": true,
  "ingredient_lines": [
    {"name": "rice", "vague": false, "quantity": 1, "unit": "cup", "size": null, "preparation": null, "note": null},
    {"name": "salt", "vague": true, "quantity": null, "unit": null, "size": null, "preparation": null, "note": "to taste"}
  ],
  "steps": ["Fry the garlic.", "Add the rice."],
  "source": null
}
```
`author_alias` is null when the account is gone. `source` is `{"type": "url", "url": "https://…"}` or null; the pasted text is never returned.

**404** `recipe_not_found`.

## POST /recipes/{recipe_id}/name-matches

Read-only. For each typed name, the catalog entry of the recipe's notebook it matches under the S-018 rule. Needs write access (it only serves the edit screen).

**Request** `{"names": ["onions", "Garlic"]}` (1–100 names, each non-blank)

**200** `{"matches": [{"name": "onions", "entry": "onion"}, {"name": "Garlic", "entry": null}]}`
`entry` is null when nothing matches; a name that differs from an entry only by case or spacing is returned with that entry (the ui lists no change for it).

**404** `recipe_not_found` · **403** `recipe_read_only` · **422** `invalid_recipe`

## PUT /recipes/{recipe_id}

Replace the recipe's content. Same body shape as the save route minus `save_key`, `source_text`, `notebook_id` and `kitchen_id`, plus the `version` read earlier.

**Request**
```json
{
  "version": "2026-10-28T10:05:00.123456Z",
  "title": "Tomato rice", "base_servings": 4, "servings_estimated": false,
  "ingredient_lines": [{"name": "rice", "vague": false, "quantity": 2, "unit": "cup",
                        "size": null, "preparation": null, "note": null}],
  "steps": ["Fry the garlic.", "Add the rice."]
}
```

**200** the same body as GET (new `version`, `can_write`), plus `"created_catalog_names": ["…"]`.

| Status | `code` | When | Extra fields |
|---|---|---|---|
| 404 | `recipe_not_found` | no read access, or deleted | |
| 403 | `recipe_read_only` | read but not write (incl. archived kitchen) | |
| 409 | `recipe_changed` | `version` differs from the stored one | |
| 422 | `draft_incomplete` | title or steps missing | `missing[]`, `line_problems[]` |
| 422 | `ingredient_line_problem` | a line breaks a rule | `line_problems[]` |
| 422 | `invalid_recipe` | any other rule, or over 100 lines/steps | |

A refused update changes nothing. Author, notebook, source, `save_key` and `created_at` are never changed. New names are added to the notebook's catalog; none are removed.

## DELETE /recipes/{recipe_id}

Remove the recipe, its lines, steps and source record.

**204** no body. **404** `recipe_not_found` (also for a second delete). **403** `recipe_read_only`.

Copies and snapshots in other notebooks and the notebook's catalog are not touched.

## Logging

One info line per call with the outcome and counts (lines, steps, new names). Never titles, names, steps or source text.
