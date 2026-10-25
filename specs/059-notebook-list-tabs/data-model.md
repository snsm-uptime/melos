# Data Model: Notebook List and Tabs in the UI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

This feature adds no entities, tables, columns or migrations. It shows the notebook answers that spec 055 defines.

The source of truth is [../055-notebooks/data-model.md](../055-notebooks/data-model.md) and [../055-notebooks/contracts/notebooks-api.md](../055-notebooks/contracts/notebooks-api.md).

## The notebook as the ui reads it

The ui reads `NotebookResponse` as defined in spec 055 and shows these fields:

| Field | Shown on the Notebook tab | Shown in the kitchen section | Notes |
|---|---|---|---|
| `name` | yes | yes | Shown as stored (FR-011 of this spec) |
| `owner_alias` | yes (or "unknown" when null) | yes (or "unknown" when null) | |
| `access` | yes (`owner` or `member`) | no | Kitchen answers always say `kitchen_member`, so they are not shown |
| `is_default` | yes (default marker) | no | Always `false` for kitchen notebooks |
| `kind` | not shown | not shown | Used only to know which list a row came from; the screens do not show it |
| `kitchen_id` | no | no | The section already knows the kitchen |
| `kitchen_is_archived` | no | yes, indirectly | The section reads archive state from the kitchen detail the page already has, not from this field |
| `id` | no (kept as the React key) | no (kept as the React key) | |

## Client-side view state

| State | Where | Lifetime |
|---|---|---|
| Notebook list (tab) | component state, fetched on mount | Until the screen unmounts |
| Notebook list (section) | component state, fetched on mount | Until the screen unmounts |
| Locale | server prop from `melos_lang_cache` | Per request |

No browser storage. Nothing is written by this feature.

## Validation

The api enforces every rule. The ui does not re-check them. It only shows the answer.

- A `null` owner alias is shown as "unknown".
- A list is shown in the order the answer gives it (FR-012 of this spec).
