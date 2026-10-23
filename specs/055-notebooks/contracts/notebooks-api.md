# Contract: Notebook routes and the capture notebook step

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md) | **Status**: designed 2026-10-23; replaces the 2026-10-22 routes `/notebooks/kitchens/{id}` (single kitchen notebook) and `/notebooks/members/{user_id}[/{notebook_id}]`

All routes are `GET`. They need a session cookie (`melos_session`) and a claimed alias (`require_user_alias`). The ui calls them through same-origin BFF routes on the same paths under `/api` (for example `/api/notebooks/default`). The BFF forwards the `cookie` header and returns the api's status and body unchanged, or 502 `{ "detail": "Upstream unavailable.", "code": "bad_gateway" }` when the api is unreachable (FR-017).

## The notebook object

Every answer uses this shape (`NotebookResponse`):

```json
{
  "id": "9a41…",
  "name": "ana's Notebook",
  "kind": "personal",
  "access": "owner",
  "owner_alias": "ana",
  "is_default": true
}
```

| Field | Values |
|---|---|
| `kind` | `"personal"`, or `"kitchen"` for a kitchen notebook (none exist until S-057) |
| `name` | The stored name; for a kitchen notebook, the kitchen's current name |
| `access` | The caller's access: `"owner"`, `"member"` or `"reader"` (read-only through a kitchen) |
| `owner_alias` | `null` for a kitchen notebook, or when no owner remains |
| `is_default` | `true` only on the caller's default notebook |

Lists are `{ "notebooks": [NotebookResponse, …] }`, ordered by creation, oldest first.

## Common errors

| Status | Body | When |
|---|---|---|
| 401 | existing unauthenticated body | No valid session |
| 403 | `{ "detail": "Choose an alias before using kitchens.", "code": "alias_required" }` | Signed in without an alias. No notebook is created |
| 422 | FastAPI validation body | A path id is not a UUID |

## GET /notebooks

BFF: `GET /api/notebooks`. The notebooks the caller owns or is a member of (FR-011). `access` is `"owner"` or `"member"`, never `"reader"`. Notebooks the caller can only read through a kitchen are not listed. Never creates anything; the list may be empty.

**200** `{ "notebooks": [ … ] }`

## GET /notebooks/default

BFF: `GET /api/notebooks/default`. The caller's default notebook (FR-007, FR-020). When there is none, it does the following, then returns the notebook:

- creates "{alias}'s Notebook" with the caller as owner;
- seeds its catalog from the caller's catalog;
- links it to the caller's signup kitchen if they are still a member;
- sets it as the default.

The answer is the same whether or not the notebook was just created: always 200, no `created` flag.

**200** `NotebookResponse` with `access: "owner"`, `is_default: true`.

## GET /notebooks/{notebook_id}

BFF: `GET /api/notebooks/{notebookId}`. One notebook, for its owner, its members, and the members of any kitchen it is linked to (`access: "reader"`). For a kitchen notebook, the members of its kitchen get `access: "member"` (FR-012). Never creates anything.

**200** `NotebookResponse`

**404** `{ "detail": "Notebook not found.", "code": "notebook_not_found" }` when the notebook does not exist or the caller has no access. The body is the same in both cases (AC1a.2, SC-003).

## GET /notebooks/kitchens/{kitchen_id}

BFF: `GET /api/notebooks/kitchens/{kitchenId}`. For any member of the kitchen, including when it is archived or hidden: the notebooks linked to it, and its kitchen notebook when one exists (FR-013). Each notebook carries the caller's access. The capture screen (S-016) offers the items with `access` `"owner"` or `"member"` (and `kind: "personal"`) when there are several. Never creates anything; the list may be empty.

**200** `{ "notebooks": [ … ] }`

**404** `{ "detail": "<KitchenNotFoundError.MESSAGE>", "code": "kitchen_not_found" }` when the kitchen does not exist or the caller is not a member. The body is the same in both cases.

## Removed routes

`GET /notebooks/members/{user_id}` and `GET /notebooks/members/{user_id}/{notebook_id}` are removed, together with their BFF routes under `ui/app/api/notebooks/members/`. `GET /notebooks/kitchens/{kitchen_id}` changes from one kitchen notebook to a list. No ui page used any of them.

## In-process: the capture notebook step (no route, FR-021)

`ResolveCaptureNotebookService.execute(ResolveCaptureNotebookCommand(actor_user_id, kitchen_id, picked_notebook_id=None)) -> Notebook`

S-016's save calls it before saving the recipe. A notebook it creates is committed on its own and kept even if the recipe save then fails (2026-10-23). Research R6 has the full order of checks.

| Situation | Result |
|---|---|
| Kitchen missing, or caller not a member | `KitchenNotFoundError` |
| Kitchen archived (checked before the candidates) | `KitchenArchivedError`; nothing is created or used |
| One linked notebook the caller owns or is a member of, no pick | That notebook |
| `picked_notebook_id` is one of those notebooks | That notebook |
| `picked_notebook_id` is not one of them | `NotebookNotFoundError` |
| Several, no pick | `NotebookChoiceRequiredError(candidate_ids)` |
| None, signup kitchen, no default notebook yet | The default notebook, created and linked as in `GET /notebooks/default` |
| None, otherwise | New "{alias}'s Notebook ({kitchen name})": caller is owner, catalog seeded, linked by the caller |

Simultaneous first calls by one member in one kitchen create one notebook (SC-002). S-016 maps the errors to HTTP when its save route lands.

## In-process: catalog readers (no route, FR-014)

`IngredientCatalog.names_for_notebook(notebook_id) -> list[str]` and `IngredientCatalog.names_for_person(user_id) -> list[str]` return sorted, distinct names. S-016 uses `names_for_person` for a draft in a kitchen where the member has no capture notebook yet.
