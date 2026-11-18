# Data Model: Shopping List Export

No new tables, columns or migrations. The export reads the stored records from spec 025 (`shopping_list`, `shopping_list_item`) and builds a view of them. Nothing is written.

## Read model: ShoppingList (existing, `domain/cart.py`)

The export consumes the list as the existing read path returns it.

| Field | Source | Used by export |
|-------|--------|----------------|
| `list_id` | `shopping_list.id` | Route and file name |
| `kitchen_id` | `shopping_list.kitchen_id` | Access check only |
| `closing_date` | `shopping_list.closing_date` | Shown in the heading; null for an active list |
| `measured_lines` | Stored lines with a quantity | Markdown and PDF body |
| `your_call` | Stored lines flagged vague | "Your call" section |
| `item.recipes` | Recipe titles per line | Parenthesized titles; none for a manual item |
| `item.is_manual` | `shopping_list_item.is_manual` | "(manual)" label |

## Export view (new, `domain/shopping_export.py`)

Pure value built from the read model above. Not persisted.

- **ExportLine**: `text` (quantity and ingredient name), `sources` (recipe titles, empty for manual items), `is_manual` (bool).
- **ExportDocument**: `title` (list date), `lines` (ExportLine, measured first), `your_call` (ExportLine, vague items), `locale` (`es` or `en`, for headings).

**Validation**: No new validation. Recipe titles and names are free text; the PDF writer maps characters outside WinAnsi to "?" (research R2). Empty `lines` and `your_call` are allowed.

**State transitions**: None. Export does not change the list.
