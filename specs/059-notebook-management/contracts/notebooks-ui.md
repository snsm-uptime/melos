# Contract: notebook management UI

All text comes from `lib/i18n/notebooks.ts`, in English and Spanish.

## Notebook page

An options button (dots icon) in the chrome header, after Share, shows when the person may manage:

`access === "owner" || (access === "kitchen_member" && kitchen_is_archived === false)`

It opens a menu with **Rename** and **Delete** (danger style). Keyboard: Enter opens, arrows move, Escape closes and returns focus, as in `IconButtonPopup`.

## Name dialog

`NotebookNameDialog`, used by rename and by both "New notebook" tiles.

| State | Behaviour |
|---|---|
| Open for rename | The input holds the current name, focused |
| Enter or confirm | Submits |
| `invalid_notebook_name`, or empty | Message under the input, text kept |
| Any other failure | Failure message, text kept, dialog stays open |
| `notebook_not_found` | "This notebook no longer exists." Closing goes to the gone address |
| `kitchen_not_found` | "This kitchen is no longer available." Closing goes to `/kitchens` |
| `kitchen_archived` | Plain archived message |
| `alias_required` | Redirect to `/alias` with a return address |
| Rename success | Dialog closes, the title updates |
| Create success | Goes to the new notebook. A kitchen notebook carries `?from=` to the kitchen's notebooks |

## Delete dialog

`NotebookDeleteDialog`. On open it reads the notebook and, for a personal notebook, its members. Confirm is disabled until both arrive.

Body, in order:

1. "Delete {name}?" as the title.
2. "This deletes {n} recipes. This can't be undone." Singular and zero forms included.
3. Personal notebook with members: "{m} people will lose access." Members exclude the owner.
4. Default notebook: "A new, empty notebook will take its place."

| State | Behaviour |
|---|---|
| Read fails, other than 404 | Error message, no confirm, Cancel stays |
| Delete pending | Buttons disabled, loader on confirm |
| Success | `requestSidePanelRefresh()`, then the gone address |
| 404 on a read or on the delete | "This notebook no longer exists." Closing goes to the gone address |
| Other failure | Failure message, the notebook is unchanged, dialog stays open |

## Gone address

With a loaded notebook: the kitchen's notebooks when it has a `kitchen_id`, otherwise `/notebooks`. With no loaded notebook: the page's `backHref`, which is `/notebooks` unless `?from=` says otherwise. The screen's existing 404 redirects use it too.

## Kitchen notebooks

A "New notebook" tile sits next to the add-snapshot tile, shown under the same `canAdd` condition.

## Client

`lib/notebooksClient.ts` gains `renameNotebook(id, name)`, `deleteNotebook(id)`, `createKitchenNotebook(kitchenId, name)` and `canManageNotebook(notebook)`.
