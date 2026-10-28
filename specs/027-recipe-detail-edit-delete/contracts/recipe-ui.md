# Contract: Recipe detail, edit and delete (ui)

Plain English messages (FR-019). Copy lives in `lib/i18n/recipeDetail.ts`, in the same locale shape as `recipeLists.ts`.

## BFF routes (same-origin)

| Route | Forwards to | Notes |
|---|---|---|
| `GET /api/recipes/[recipeId]` | `GET /recipes/{id}` | status and body pass through |
| `PUT /api/recipes/[recipeId]` | `PUT /recipes/{id}` | 15 s deadline; timeout → 503 `save_unavailable`, as the save route |
| `DELETE /api/recipes/[recipeId]` | `DELETE /recipes/{id}` | 204 passes through |
| `POST /api/recipes/[recipeId]/name-matches` | `POST /recipes/{id}/name-matches` | |

## Pages

### `/recipes/[recipeId]?from=<path>` (detail)

- The layout of the draft review page, display only (2026-10-28): title, notebook name and author in the header; an Ingredients column of cards (name and amount on the top line, then "Preparation:" and "Note:" rows only when the line has them) with the servings and an "estimated" badge on the heading row; a Steps column of numbered cards. No fields, dropdowns, match control, or move and remove controls.
- Source link below the columns, only when `source.url`.
- **Back** (an icon link in the header, as on the draft page) goes to `from` when it starts with `/notebooks/` or `/kitchens/`, else `/notebooks/{notebook.id}`.
- **Edit** and **Delete** show only when `can_write`.
- 404 from the api → "That recipe isn't available." with a link back; no other detail is given.

### `/recipes/[recipeId]/edit?from=<path>`

- Loads the recipe; fields: title, servings, ingredient rows (name, amount, unit, size, preparation, vague toggle + note), steps; add, remove, reorder rows and steps.
- On leaving a name field, calls name-matches; a proposed entry shows as a name change with **Undo** (`NameChangeNotice`). Undo keeps the typed name. Pressing **Save** first checks any typed name not yet checked; if that finds a proposal, nothing is saved yet: the change is listed and the member presses Save again.
- **Save** sends `version` and the final names. On 200 → detail page. On 422 → message naming the field or line, edits kept. On 409 `recipe_changed` → "This recipe was changed after you opened it. Reload to see the latest version." with a **Reload** action; typed edits stay on screen until reload. On 404 → "That recipe is no longer available." and a link to the list. On 403 → "You can only read this recipe."
- **Cancel** or leaving with unsaved changes asks for confirmation (`LeaveDraftGuard`); cancel without changes goes straight back to the detail.

### Delete dialog (`ActionDialog` on the detail)

- Text names the recipe: "Delete “{title}”? This can't be undone."; buttons **Delete** and **Cancel**.
- While deleting, the button is disabled, so a double press sends one request. 204 or 404 → go to `from` (FR-017). 403 → "You can only read this recipe." Network failure → "The recipe wasn't deleted. Try again."

## Existing screens that change

- `RecipeCard`: becomes a link to `/recipes/{id}?from=<current path>`; still no checkbox, no category chips (spec 021 FR-014 otherwise unchanged).
- After deleting the last recipe the list shows its empty-list message (spec 021).
