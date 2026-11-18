# Research: Shopping List Export

Date: 2026-11-17. Inputs: [spec.md](./spec.md) (clarified 2026-11-17), constitution 3.0.0, `api/pyproject.toml`, spec 025 contracts.

## R1. Which list is exported and who may read it

**Decision**: Any shopping list ID of a kitchen (active or closed). The use case checks the member's read access to the list's kitchen through the existing `KitchenAccessAuthorizer` port. A member without access gets the same "not found" response as for an unknown ID.

**Rationale**: Clarified 2026-11-17 (spec Clarifications). The rule matches the rest of the API, where non-members get 404 (plan constraints, spec 025 contract).

**Alternatives considered**: Exporting only the active list (rejected by the owner). A separate "export" permission (rejected: read access is enough, nothing is changed).

## R2. How the PDF is produced without a new library

**Decision**: A pure writer in `domain/shopping_export.py` that emits a PDF 1.4 file with one text stream per page, two base-14 fonts (Helvetica and Helvetica-Bold, WinAnsiEncoding), page breaks by line count, and `zlib` for stream compression. No image, no embedded font.

**Rationale**: WinAnsiEncoding covers the Latin-1 accents used in Spanish and English (á é í ó ú ü ñ ¿ ¡). The base-14 fonts need no font file. The list is plain text with a few section headings, so a full PDF library is more than the feature needs. Standard library code keeps the stack unchanged (constitution principle 2).

**Risks**: Characters outside WinAnsi (for example a name with Greek or CJK letters) would show as "?". Ingredient and recipe names are free text, so the writer replaces any character outside WinAnsi with "?" and the tests assert it. This is a known limit; a Unicode font would need an approved library or an embedded TTF.

**Alternatives considered**:
- `fpdf2` or `reportlab`: full Unicode and layout, but a new dependency that needs the project lead's approval (constitution principle 2). **Owner decision needed only if the WinAnsi limit is not acceptable.**
- Browser print to PDF on the client: no server code, but the output depends on the browser and cannot be tested reliably; rejected.

## R3. Markdown format

**Decision**: Plain Markdown built on the server from the same `ShoppingList` value:

```text
## Shopping list (<list title or date>)

- flour — 1 cup + 3 tbsp (Recipe A, Recipe B)
- eggs — 2
- lemon (manual)

## Your call

- salt — to taste (Recipe C)
```

Manual items show "(manual)" in place of recipe titles (spec FR-004 and clarification: manual items have no recipe). Headings come from the UI locale (FR-010). Numbers use the same formatting as the cart (at most two decimals, trailing zeros removed).

**Rationale**: One renderer for the copy box and the PDF text keeps both formats identical (SC-002).

## R4. Where the export text is built and how it is delivered

**Decision**:
- The API returns `GET /kitchens/{kitchen_id}/shopping-lists/{list_id}/export?format=markdown|pdf` (see [contracts](./contracts/shopping-list-export-api.md)). Markdown returns `text/markdown; charset=utf-8`. PDF returns `application/pdf` with `Content-Disposition: attachment; filename="shopping-list-YYYY-MM-DD.pdf"`.
- The UI's BFF route proxies both to the browser without transforming the bytes.
- The component fetches the Markdown when it opens and shows it in a copy box. The copy action writes it to the clipboard and shows a confirmation.
- If the PDF request fails, the component shows an error message and leaves the copy box working (AC5.5).

**Rationale**: The server has the authoritative list and the same renderer for both formats. The copy box needs no second round trip after the first fetch.

## R5. Empty list and empty cart

**Decision**: A list with no lines still exports (title and the headings only, with the line "No items"). The empty-cart rule from the spec applies to the cart page, not to this export. The component disables both actions when the list has no lines and shows the hint "Add recipes or items to the list first."

**Rationale**: Clarified spec edge case; keeps the export honest about what the list holds.

## R6. Closed lists

**Decision**: A closed list exports exactly like an active one. The use case never writes, so the closing date and the read-only state are unchanged (FR-012).

## R7. Logging

**Decision**: The route logs the outcome, the format and the number of lines. It never logs line text or recipe titles.

**Rationale**: Constitution principle 7; the lines hold household data.

## Open items

- Owner: confirm R2 (standard library PDF writer, WinAnsi limit) or approve a PDF library. The plan proceeds with R2 unless told otherwise.
