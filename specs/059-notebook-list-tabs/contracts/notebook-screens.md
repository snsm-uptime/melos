# Contract: Notebook screens (ui consumption)

**Feature**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **API contract**: [../../055-notebooks/contracts/notebooks-api.md](../../055-notebooks/contracts/notebooks-api.md)

This feature adds no route. It lists which existing same-origin BFF routes each screen calls, in what order, and what each answer leads to.

## Notebook tab (`/notebooks`)

| Step | Call | On 200 | On 403 `alias_required` | On 404 / 502 / other |
|---|---|---|---|---|
| 1 | `GET /api/notebooks/default` | Continue to step 2 | Redirect to the alias step (`requireAlias` on the server runs first, so this is the fallback) | Show `loadError` with retry; do not call step 2 |
| 2 | `GET /api/notebooks` | Show the cards, the default marked, oldest first | Redirect to the alias step | Show `loadError` with retry |

Rules:
- Step 2 runs only after step 1 succeeds (R7).
- An empty step-2 list is shown as an empty state. It can happen only when step 1 failed, which shows the error instead.
- Cards are inert (R6).

## Kitchen notebooks section (on `/kitchens/{kitchenId}`)

| Call | On 200 | On 404 `kitchen_not_found` | On 403 `alias_required` | On other failure |
|---|---|---|---|---|
| `GET /api/notebooks/kitchens/{kitchenId}` | Show the cards in order; an empty list shows the empty state | Show the kitchen page's not-found message in this section; no cards | Redirect to the alias step | Show `loadError` with retry |

Rules:
- The first call on a kitchen with no notebook creates it (spec 055 FR-008a). The section shows whatever the answer lists, so there is no separate "create" call.
- No add-recipe action is shown, in archived or active kitchens (FR-006 of this spec, R5).
- Archived kitchens still list their notebooks to members (spec 055 FR-016).

## Card contract (`NotebookCard`)

| Input | Type | Required | Shown as |
|---|---|---|---|
| `name` | string | yes | Card title |
| `ownerAlias` | string or null | yes | Owner line; `null` shows "unknown" |
| `access` | `"owner"` / `"member"` / `"kitchen_member"` | no | Access line, only on the tab |
| `isDefault` | boolean | no | "Default" text marker, only when `true` |
| `locale` | `"en"` / `"es"` | yes | Labels from `ui/lib/i18n/notebooks.ts` |

The card renders no link and no button (FR-014, R6).

## Error and state strings

Every visible string comes from `ui/lib/i18n/notebooks.ts`, with `en` and `es` entries. No string is hard-coded in a component.
