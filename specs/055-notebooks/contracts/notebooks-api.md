# Contract: Notebook routes and the capture notebook step

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md) | **Status**: designed 2026-10-23 for the snapshot model, updated 2026-10-24 (a kitchen notebook stores its owner; a kitchen's first notebook is created on its first open); replaces the 2026-10-22 routes `/notebooks/kitchens/{id}` (single kitchen notebook) and `/notebooks/members/{user_id}[/{notebook_id}]`, and the kitchen-link design of earlier on 2026-10-23

All routes are `GET`. They need a session cookie (`melos_session`) and a claimed alias (`require_user_alias`). The ui calls them through same-origin BFF routes on the same paths under `/api` (for example `/api/notebooks/default`). The BFF forwards the `cookie` header and returns the api's status and body unchanged, or 502 `{ "detail": "Upstream unavailable.", "code": "bad_gateway" }` when the api is unreachable (FR-021).

## The notebook object

Every answer uses this shape (`NotebookResponse`). A personal notebook:

```json
{
  "id": "9a41…",
  "name": "ana's Notebook",
  "kind": "personal",
  "access": "owner",
  "owner_alias": "ana",
  "kitchen_id": null,
  "kitchen_is_archived": null,
  "is_default": true
}
```

A kitchen notebook:

```json
{
  "id": "c3d0…",
  "name": "ana's (Home) Notebook",
  "kind": "kitchen",
  "access": "kitchen_member",
  "owner_alias": "ana",
  "kitchen_id": "5e7b…",
  "kitchen_is_archived": false,
  "is_default": false
}
```

| Field | Values |
|---|---|
| `name` | The stored name, fixed at creation. It does not follow alias or kitchen renames |
| `kind` | `"personal"` or `"kitchen"` |
| `access` | Personal: the caller's role, `"owner"` or `"member"`. Kitchen: always `"kitchen_member"` |
| `owner_alias` | Personal: the owner's alias, or `null` when no owner remains (the ui shows "unknown"). Kitchen: the alias of the notebook's stored owner, the member who created it; when none is stored, the kitchen owner's alias; `null` when neither exists (the ui shows "unknown") |
| `kitchen_id` | Kitchen: the kitchen it belongs to. Personal: `null` |
| `kitchen_is_archived` | Kitchen: whether its kitchen is archived, read at request time; the ui hides "add recipe" when `true` (spec 016 FR-033). Personal: `null` |
| `is_default` | `true` only on the caller's default notebook; always `false` for a kitchen notebook |

The origin label (`source_notebook_id`) is not in the answer; S-034 adds it as a new field (research R3).

Lists are `{ "notebooks": [NotebookResponse, …] }`, ordered by creation, oldest first (FR-019).

## Common errors

| Status | Body | When |
|---|---|---|
| 401 | existing unauthenticated body | No valid session |
| 403 | `{ "detail": "Choose an alias before using kitchens.", "code": "alias_required" }` | Signed in without an alias. No notebook is created (FR-020) |
| 422 | FastAPI validation body | A path id is not a UUID |

## GET /notebooks

The caller's personal notebooks: those they own or are a member of (FR-014). Never a kitchen notebook. Creates nothing, so a person who has never opened their Notebook tab gets an empty list.

- **200** `{ "notebooks": [...] }`, each with `kind: "personal"`.

## GET /notebooks/default

The caller's default personal notebook, created on the first call (FR-007). Declared before `/notebooks/{notebook_id}`.

- **200** `NotebookResponse` with `kind: "personal"`, `access: "owner"`, `is_default: true`. Same status and shape whether it was just created or not.
- Simultaneous first calls leave one notebook (SC-001). After the default is deleted, the next call creates a new one with a new `id` (SC-007).

## GET /notebooks/kitchens/{kitchen_id}

The kitchen's notebooks, for a member of the kitchen (FR-016). Declared before `/notebooks/{notebook_id}`.

- **200** `{ "notebooks": [...] }`, each with `kind: "kitchen"` and `access: "kitchen_member"`. When the kitchen has no notebook and is not archived, the first call creates its notebook for the caller, who becomes its owner (FR-008a), and lists it; later calls list the same notebook. In an archived kitchen with no notebook, the list is empty and nothing is created. Archived kitchens with notebooks are still listed for their members.
- The route can write, only for the first call on a kitchen with none. It is idempotent (research R14), and the owner does not treat that creation as a risk (2026-10-24).
- **404** `{ "detail": "Kitchen not found.", "code": "kitchen_not_found" }` for a missing kitchen and for a non-member, same body (SC-004).

## GET /notebooks/{notebook_id}

One notebook (FR-015).

- **200** `NotebookResponse` when it is a personal notebook the caller owns or is a member of, or a kitchen notebook of a kitchen the caller is a member of.
- **404** `{ "detail": "Notebook not found.", "code": "notebook_not_found" }` for a missing notebook, a personal notebook the caller does not belong to (even if they share a kitchen with its owner), and a kitchen notebook of a kitchen they do not belong to; same body (SC-004, AC1a.2).

## In-process: the capture notebook step (no route, FR-013)

Called by the recipe save (S-019) before it writes the recipe. Not reachable over HTTP in this feature.

```text
ResolveCaptureNotebookService.execute(
    ResolveCaptureNotebookCommand(actor_user_id, kitchen_id: UUID | None, picked_notebook_id: UUID | None)
) -> CaptureNotebook(notebook_id: UUID, created: bool)
```

| Case | Result |
|---|---|
| `kitchen_id` missing, or caller not a member | `KitchenNotFoundError` (S-019 maps it to the 404 `kitchen_not_found` body) |
| Kitchen archived | `KitchenArchivedError` (`kitchen_archived`, "This kitchen is archived, so recipes can't be added."), checked right after membership, before any notebook is read; nothing created |
| Several candidates, a pick that is not one of them | `NotebookNotFoundError`; nothing created |
| No pick, several candidates | `NotebookChoiceRequiredError(candidate_ids)`; nothing created |
| One candidate (any pick ignored) | that notebook, `created = false` |
| Several candidates, a valid pick | that notebook, `created = false` |
| Kitchen, no candidates | new kitchen notebook "{alias}'s ({kitchen name}) Notebook" owned by the caller, catalog seeded from the caller's personal catalog (R14), committed; `created = true` |
| Personal (`kitchen_id` null), no candidates | the caller's default notebook, created as in `GET /notebooks/default`, committed; `created = true` |

Candidates: in a kitchen, its notebooks; outside a kitchen, the personal notebooks the caller owns or is a member of. Oldest first. The first open of a kitchen's notebooks (`GET /notebooks/kitchens/{kitchen_id}`) creates the same notebook with the same lock and seed, and does not commit: the response commits it (research R14). A notebook the step creates is committed before it returns, so it stays if the save then fails (research R8).

## In-process: catalog readers (no route, FR-018)

```text
IngredientCatalog.names_for_notebook(notebook_id) -> list[str]   # one notebook's catalog, sorted
IngredientCatalog.names_for_person(user_id)       -> list[str]   # personal catalog: distinct names in the
                                                                  # personal notebooks the person belongs to
```

S-016 uses `names_for_notebook` for a draft whose notebook is known, and `names_for_person` for a draft in a kitchen with no notebook yet. The caller has already checked access to the notebook or kitchen.

## ui BFF routes

| ui path | api path | File |
|---|---|---|
| `GET /api/notebooks` | `GET /notebooks` | `ui/app/api/notebooks/route.ts` (new) |
| `GET /api/notebooks/default` | `GET /notebooks/default` | `ui/app/api/notebooks/default/route.ts` (new) |
| `GET /api/notebooks/{notebookId}` | `GET /notebooks/{notebook_id}` | `ui/app/api/notebooks/[notebookId]/route.ts` (new) |
| `GET /api/notebooks/kitchens/{kitchenId}` | `GET /notebooks/kitchens/{kitchen_id}` | `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts` (kept) |

`ui/app/api/notebooks/members/` is deleted with the api routes it forwarded to.
