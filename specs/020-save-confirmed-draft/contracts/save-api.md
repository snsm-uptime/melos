# Contract: Save a recipe

Authenticated like the capture route (`require_user_alias`). The ui reaches it through the same-origin BFF `POST /api/recipes`, which passes status and body through unchanged.

## POST /recipes

Request body (JSON):

```json
{
  "save_key": "uuid",
  "notebook_id": "uuid | null",
  "kitchen_id": "uuid | null",
  "source_text": "string",
  "title": "string",
  "base_servings": 4,
  "servings_estimated": false,
  "ingredient_lines": [
    {
      "name": "onion",
      "vague": false,
      "quantity": 2,
      "unit": "unit",
      "size": "large",
      "preparation": "chopped",
      "note": null
    }
  ],
  "steps": ["Simmer them."]
}
```

- Exactly one of `notebook_id` (normal) or `kitchen_id` (the kitchen has no notebook) is required. Both null or both set: 422 `invalid_recipe`.
- `source_text` is the text the capture started from; limited by the capture text limit.
- Line fields are those of the draft response (spec 016). `note` is the vague note.

### Responses

| Status | `code` | When |
|---|---|---|
| 201 | none | Saved. Body below |
| 200 | none | Replay of an earlier save with the same `save_key`. Same body |
| 401 | | Not signed in |
| 404 | `notebook_not_found` | No such notebook, or the caller has no access (same body) |
| 409 | `kitchen_archived` | The notebook's kitchen is archived |
| 409 | `notebook_choice_required` | `kitchen_id` path, several notebooks |
| 422 | `draft_incomplete` | Missing title or steps, or line problems. Body has `missing` and `line_problems` as in capture |
| 422 | `ingredient_line_problem` | Line quantity or unit problems only. Body has `line_problems` |
| 422 | `invalid_recipe` | Any other broken rule, including more than 100 ingredient lines or 100 steps |
| 422 | `text_too_long` | `source_text` over the limit |

Success body:

```json
{
  "recipe": { "id": "uuid", "title": "Onion soup", "notebook_id": "uuid" },
  "notebook": { "id": "uuid", "kind": "personal|kitchen", "name": "string", "kitchen_id": "uuid|null" },
  "created_catalog_names": ["leek"]
}
```

On a replay `created_catalog_names` is `[]`.

### Guarantees

- Nothing is stored for any non-2xx answer, except a kitchen notebook created by the `kitchen_id` path.
- Catalog names are unique per notebook; names that differ from an entry only by letter case or spacing use the entry's spelling.
- The author is the signed-in user. The body cannot set it.
- Messages carry no service text, ids of other users or traces.
