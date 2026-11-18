# Contract: Shopping List Export API

Read-only. Builds on the spec 025 shopping list routes (`GET /kitchens/{id}/shopping-lists/{list_id}`).

## GET /kitchens/{kitchen_id}/shopping-lists/{list_id}/export

**Auth**: Session required (existing rule). The caller must be a member of the list's kitchen.

**Query**:

| Name | Required | Values |
|------|----------|--------|
| `format` | yes | `markdown` or `pdf` |

**Responses**:

| Status | When | Body |
|--------|------|------|
| 200 (markdown) | Member can read the list | `text/markdown; charset=utf-8`, the text from research R3 |
| 200 (pdf) | Member can read the list and PDF generation succeeds | `application/pdf`, `Content-Disposition: attachment; filename="shopping-list-YYYY-MM-DD.pdf"` (date = list closing date, or today for an active list) |
| 400 | `format` missing or not one of the two values | `{"detail": "format must be markdown or pdf"}` |
| 404 | List ID unknown, or caller is not a member of the list's kitchen | `{"detail": "Not found"}` (same body for both cases, FR-013) |
| 500 | PDF generation raised an error | `{"detail": "PDF could not be created"}`; the UI keeps the Markdown copy working (AC5.5) |

**Side effects**: None. No write, no audit row, no email.

**Logging**: `outcome`, `format`, `line_count`. No line text.

## BFF: GET /api/kitchens/{kitchenId}/shopping-lists/{listId}/export?format=

Proxies the API response unchanged, including status and headers. The browser never sees the API's internal error text.

## UI component: ShoppingListExport

Props: `kitchenId: string`, `listId: string`. Reusable on any page that has both IDs.

Behaviour:
- Copy box: loads the Markdown on mount; "Copy" writes it to the clipboard and shows a confirmation.
- "Download PDF": requests the PDF; on error shows the message and keeps the copy box.
- Both actions are disabled when the list has no lines; the hint text explains why.
