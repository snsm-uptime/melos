# Contract: Save in the draft screen

## Controls

- **Save** sits beside **Discard** on the draft review screen. It is disabled while a save is in progress and while the draft has no title, no ingredient line or no step.
- While saving, the control shows a busy state and the draft fields are not editable.

## State (client-only, `captureStore`)

- `saveKey`: made when a draft is shown (`crypto.randomUUID()`), kept while that draft is on screen, cleared on Discard, Back or success.
- `saving`: true while the request runs.
- `savedNotice`: `{ notebookId }` set on success, cleared when shown.

## Flow

1. Save sends `POST /api/recipes` with the edited draft (current title, servings, flag, lines and steps), `source_text` (the pasted text), `save_key` and `notebook_id`.
2. 201 or 200: clear the draft and the pasted text, set `savedNotice`, go to the notebook's `returnPath`. No leave prompt (the draft is gone).
3. Any other answer: stay on the draft, keep every edit, show the message below at the top of the draft, re-enable Save.
4. A network failure or timeout shows the "could not save" message; pressing Save again reuses the same `saveKey`.

## Messages (English only, no codes shown)

| Code | Message |
|---|---|
| `kitchen_archived` | This kitchen is archived, so recipes can't be added. |
| `notebook_not_found` | This notebook no longer exists or you no longer have access. |
| `draft_incomplete`, `ingredient_line_problem` | Same wording as the capture messages (spec 017), naming the missing part or line. |
| `invalid_recipe` | The recipe breaks a rule. Check the ingredient lines and try again. |
| network or unknown | We couldn't save the recipe. Your changes are kept. Try again. |

## Notebook page

`NotebookTabScreen` shows "Recipe saved" at the top once when `savedNotice.notebookId` equals the page's notebook, then clears it. It lists no recipes (S-021).
