# Contract: copy a personal recipe into a kitchen

`POST /api/notebooks/kitchens/{kitchen_id}/recipe-copies` (ui proxies `/api/*`; session cookie)

Request
```json
{ "source_recipe_id": "uuid", "on_repeat": "ask" | "add" | "overwrite" }
```

Responses
| Status | Body | When |
|---|---|---|
| 201 | `{ "recipe_id", "notebook_id", "notebook_name", "overwritten": false }` | New copy |
| 200 | same, `"overwritten": true` | Overwrite done |
| 409 | `{ "code": "recipe_already_in_kitchen", "detail", "existing_recipe_id", "notebook_name" }` | `on_repeat=ask` and a copy exists |
| 409 | `{ "code": "recipe_locked", "detail" }` | Overwrite target is being edited |
| 404 | `kitchen_not_found` | Not an active member / no kitchen |
| 404 | `recipe_not_found` | Source missing, unreadable, or not in a personal notebook |
| 409 | `kitchen_archived` | Archived kitchen |
| 422 | validation | bad body |

## UI contract
- `AddRecipeOptionsDialog` gets optional `onChooseFromNotebook` and `fromNotebookDisabledReason`; when the prop is absent the option is not rendered (personal notebook pages).
- Option order: URL, Picture, Text, Recipe from another notebook.
- Strings (en/es): `optionFromNotebook` "Recipe from another notebook" / "Receta de otro cuaderno"; quick add label "Add recipe" / "Añadir receta"; repeat dialog title, "Add another copy", "Overwrite", "Cancel"; empty states.
