# Contract: Snapshot routes

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

The routes need a session cookie. The ui calls them through BFF routes on the same paths under `/api`, which return the api's status and body, or 502 `bad_gateway` when the api can't be reached (spec 056).

## `POST /notebooks/kitchens/{kitchen_id}/snapshots`

```json
{
  "source_notebook_id": "9a41…",
  "snapshot_key": "2f6e…",
  "confirm_repeat": false
}
```

Checks run in this order, and a refusal stores nothing:

| # | Check | Answer |
|---|-------|--------|
| 1 | Caller belongs to the kitchen | 404 `kitchen_not_found` |
| 2 | Kitchen isn't archived | 403 `kitchen_archived` |
| 3 | Key already used in this kitchen | 200, the existing snapshot |
| 4 | Source exists, is personal, and the caller owns it | 404 `notebook_not_found` |
| 5 | No snapshot of it here, or `confirm_repeat` is true | 409 `snapshot_exists` |
| 6 | Made | 201, the new notebook |

The 200 and 201 bodies are the notebook object below. An invalid body is 422.

Check 3 looks only at the key, so the ui must not reuse a key for a different source notebook (research R3).

## `POST /notebooks/kitchens/{kitchen_id}/capture-notebook`

No body. Runs the capture step for the caller and returns their own kitchen notebook, creating it if needed: 200 with the notebook object, 404 `kitchen_not_found`, or 403 `kitchen_archived`.

## Notebook object

All notebook routes gain three fields:

```json
{
  "origin_notebook_name": "ana's Notebook",
  "is_snapshot": true,
  "is_own_capture_notebook": false
}
```

`origin_notebook_name` is null when the notebook isn't a snapshot or the original was deleted. Personal notebooks answer `false` for both booleans.
