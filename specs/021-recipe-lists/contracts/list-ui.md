# Contract: Recipe lists in the ui

## Same-origin BFF routes

`GET /api/notebooks/{notebookId}/recipes` and `GET /api/notebooks/kitchens/{kitchenId}/recipes` forward `page` and `q` and the session cookie to the api and return its status and body unchanged (pattern of the existing notebook BFF routes).

## Pages

| Page | Shows |
|---|---|
| `/notebooks/{notebookId}` | Notebook name, "Recipe saved" notice (once), the list of that notebook |
| `/kitchens/{kitchenId}` | Existing sections, plus the combined list of the kitchen's notebooks |

Both pages read `?page=` and `?q=`. Typing in the filter updates `q` after a 300 ms pause, returns to page 1 and replaces the history entry.

## Recipe card (display only)

Default cooking-pot icon, title (one line, shortened with an ellipsis, full title as the tooltip), author chip ("unknown" if no alias), "N ingredients" ("1 ingredient" for one), and on the kitchen list the notebook name. No link, no checkbox, no category chips (FR-014).

## List states

| State | Shown |
|---|---|
| Loading | Placeholder cards; the filter box stays usable |
| Cards | Grid, then the pager |
| Empty (no `q`) | "No recipes in this notebook yet." plus the add-recipe action when the kitchen is not archived |
| No match (`q` set) | "No recipes match "…"." and a "Clear filter" action |
| Not found | Same message as a missing notebook or kitchen |
| Error | Plain message and a Retry action (as in spec 060) |

## Pager

Previous, next and numbered page buttons, "Page 2 of 5". Hidden when there is one page. The current page is marked (`aria-current="page"`).

## Links

- `NotebookCard` takes an optional `href`. The Notebook tab and the kitchen notebooks section pass `/notebooks/{id}`; the card is then a link. Without `href` it stays inert (spec 060 FR-014 no longer applies to the two screens that pass it).
- Capture return path: personal → `/notebooks/{notebookId}`; kitchen → `/kitchens/{kitchenId}`.

## Messages

English only, in `lib/i18n/recipeLists.ts`; no codes shown (FR-015).
