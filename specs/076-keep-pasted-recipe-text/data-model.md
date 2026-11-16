# Data Model: Keep Pasted Recipe Text and Offer Personal Notebooks

No database, API or migration changes. Everything here is client-side.

## Kept capture text (browser session storage)

| Field | Value |
|-------|-------|
| Key | `melos.capture.text` |
| Value | The text sheet's text, as typed (not trimmed) |
| Scope | One browser tab, which is the current session. Gone when the tab or window closes. |

**Lifecycle** (mirrors `CaptureState.text` in `ui/lib/capture/captureStore.ts`):

| Event | Store `text` | Stored key |
|-------|--------------|------------|
| First client read of the store | from the key, or `""` | read |
| `setText(t)`, `t !== ""` | `t` | written |
| `setText("")` (member cleared the field) | `""` | removed |
| `closeSheet()`, `backToSheet()`, `failSubmit()`, `showDraft()` | unchanged | unchanged |
| `markSaved()`, `discardDraft()`, `startManualDraft()` | `""` | removed |
| `clearKeptCaptureText()` (sign-in, sign-out) | `""` | removed |
| `clearCapture()` (member confirmed leaving an edited draft) | `""` | removed |

**Rules**
- Read and write errors (storage blocked, quota) are swallowed. The store keeps working in memory only.
- Nothing is sent to the API until the member submits (spec FR-005, unchanged submit path).
- A kept text longer than the paste limit is shown in full, with the usual too-long message.

## CaptureCandidate (extended)

`ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx`

| Field | Type | New | Notes |
|-------|------|-----|-------|
| `id` | string | | Notebook id, or `OWN_NEW_NOTEBOOK_ID` |
| `name` | string | | Plain notebook name, used for the sheet title and the draft |
| `kind` | `"personal" \| "kitchen"` | | |
| `kitchenId` | string \| null | | |
| `detail` | string? | yes | Shown in the picker after the name: "Personal" or the kitchen's name |
| `dividerBefore` | boolean? | yes | Starts a group in the picker |

## Side-panel notebook choice (built by `QuickAddRecipe`)

Built from `GET /api/notebooks` (`NotebookResponse[]`) and the membership kitchens (for kitchen names).

- **Order**: personal notebooks (oldest first), then kitchen notebooks grouped by kitchen, in the membership roster's order. On a kitchen's pages, that kitchen's group comes first, then the personal notebooks, then the other kitchens.
- **Filter**: drop kitchen notebooks whose `kitchen_is_archived` is true.
- **"New notebook" row**: only for the kitchen whose pages are open, and only when none of its notebooks has `is_own_capture_notebook`.
- **Default**: on a kitchen's pages, the own capture notebook there, or the "new" row. Elsewhere, `is_default` personal, then first personal, then first row.
- **Detail labels**: shown only when the choice mixes more than one group. A member with only personal notebooks sees the picker exactly as today.
