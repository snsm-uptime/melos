# Contract: notebook management API

Reached by the ui through same-origin BFF routes at `/api/notebooks/...`, which forward the cookie, status and body. All three need a signed-in person with an alias (`require_user_alias`). The notebook object is the one spec 056 defines. Errors are `{ "detail", "code" }`.

## PATCH /notebooks/{notebook_id}

Renames a notebook.

Body: `{ "name": string }`

| Status | Code | When |
|---|---|---|
| 200 | | The notebook object. Also for an unchanged name. |
| 403 | `notebook_owner_only` | The caller is a member of the personal notebook, not its owner |
| 403 | `kitchen_archived` | The notebook's kitchen is archived |
| 404 | `notebook_not_found` | Missing, deleted, or not visible to the caller |
| 422 | `invalid_notebook_name` | Empty after trimming, or over 200 characters |

Access is checked before the name, so a person who cannot see the notebook always gets 404.

## DELETE /notebooks/{notebook_id}

Deletes a notebook and what it holds, as one step. The request carries no counts: confirming is the ui's job.

| Status | Code | When |
|---|---|---|
| 204 | | Deleted |
| 403 | `notebook_owner_only` | As above |
| 403 | `kitchen_archived` | As above |
| 404 | `notebook_not_found` | As above, including a second delete |

## POST /notebooks/kitchens/{kitchen_id}

Adds an empty kitchen notebook. The caller is its recorded owner, and its catalog starts from theirs.

Body: `{ "name": string }`

| Status | Code | When |
|---|---|---|
| 201 | | The notebook object |
| 403 | `kitchen_archived` | The kitchen is archived |
| 404 | `kitchen_not_found` | Missing, or the caller is not a member |
| 422 | `invalid_notebook_name` | As above |

## Changed behaviour

`POST /notebooks/kitchens/{id}/snapshots` answers 404 `notebook_not_found`, not 500, when the original is deleted during the request.

The recipe save route answers 404 `notebook_not_found`, not 500, when its notebook is deleted during the request.
