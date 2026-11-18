# Implementation Plan: Shopping List Export (Markdown copy and PDF)

**Branch**: `024-shopping-list-export` (story S-024) | **Date**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/024-shopping-list-export/spec.md`

## Summary

Any shopping list of a kitchen (active or closed, spec 025) can be exported as Markdown text or as a PDF download. The export is one reusable component that takes a list ID. The API checks that the member can read the list's kitchen and answers "not found" otherwise (FR-013). The Markdown is built from the stored list, and the PDF is built by a small PDF writer that uses only the Python standard library, so no new library is added. The export reads stored lines only, never the cart draft, and changes nothing. Markdown is the fallback when PDF fails (AC5.5). No migration and no new table.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only: FastAPI, SQLAlchemy, `domain/cart.py` (`ShoppingList`, `MeasuredLine`, `YourCallEntry`, `build_shopping_list`). PDF: Python standard library (`zlib` for compression, base-14 Helvetica with WinAnsi encoding, which covers the Latin accents used in Spanish and English). No new package.

**Storage**: None new. Reads the stored `shopping_list` and `shopping_list_item` rows from spec 025 (see [data-model.md](./data-model.md)).

**Testing**: pytest + ruff (domain renderers as pure unit tests; application use case with fake ports; API route with the existing test client); vitest, eslint, typecheck (ui); browser walk per [quickstart.md](./quickstart.md).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser UI.

**Project Type**: Web application (hexagonal FastAPI `api` + Next.js BFF `ui`).

**Performance Goals**: A PDF of a 100-line list is produced in under 1 s on the server (the list is already stored, so no consolidation runs). The copy action returns the text with no server round trip beyond the one read.

**Constraints**: `domain/` has no I/O and no framework imports (the PDF writer builds bytes in memory and is pure). 404 for non-members (existing rule). Logs carry outcome and counts only, never list contents. All new UI text in Spanish and English. No change to auth.

**Scale/Scope**: One list per request. 1 read-only API route, 1 BFF route, 1 reusable UI component, 1 pure domain module, 1 application use case. No migration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| 1. Simplicity and reuse | No new service. Reuses the spec 025 list read, the kitchen access check and the existing component pattern. | Pass |
| 2. Tech stack stability | No new library. The PDF writer is standard library code, so no approval is needed. A third-party PDF library would need approval (see research R2). | Pass |
| 3. Hexagonal architecture | `domain/shopping_export.py` is pure. The use case lives in `application/shopping_export.py` and reads through existing ports. The API route and the BFF route are adapters. | Pass |
| 4. Every external call through a port | No external call. | Pass |
| 5. Privacy and data | Export is visible only to members of the list's kitchen (the same visibility as the list). Nothing is stored or sent elsewhere. | Pass |
| 6. Testing | Pure domain tests, use-case tests with fakes, route tests for 404 and format. | Pass |
| 7. Observability | Logs record the outcome and the line count only. | Pass |
| 9. Post-MVP scope by priority | S-024 is `must` in the backlog and is in scope. | Pass |

Re-check after Phase 1: no new library, no new table, no new port. The domain module takes a `ShoppingList` value and returns text or bytes. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/024-shopping-list-export/
├── plan.md              # This file
├── research.md          # Phase 0: PDF approach, format rules, access rule
├── data-model.md        # Phase 1: no new entities; the export view of a list
├── quickstart.md        # Phase 1: run and validate the export
├── contracts/
│   └── shopping-list-export-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── shopping_export.py          # NEW: render_markdown(list) and render_pdf(list) -> bytes (pure)
├── application/
│   └── shopping_export.py          # NEW: export_shopping_list(kitchen_id, list_id, format) use case
├── adapters/web/
│   └── (route module for shopping lists)  # EXTENDED: GET /kitchens/{id}/shopping-lists/{list_id}/export
└── tests/
    ├── domain/test_shopping_export.py        # NEW: Markdown and PDF rules, accents, paging, empty list
    ├── application/test_shopping_export.py   # NEW: access refused as not found, closed list exports
    └── api/test_shopping_list_export.py      # NEW: format, 404 for non-members, Content-Disposition

ui/
├── app/api/kitchens/[kitchenId]/shopping-lists/[listId]/export/route.ts  # NEW: BFF proxy, passes PDF bytes
├── components/ShoppingListExport/
│   ├── ShoppingListExport.tsx      # NEW: reusable; takes kitchenId and listId; copy box and PDF button
│   ├── ShoppingListExport.test.tsx # NEW
│   └── exportText.ts               # NEW: client-side wrapper for the Markdown fetch and error mapping
├── app/kitchens/[kitchenId]/shopping-lists/[listId]/page.tsx  # EXTENDED: mounts the component
└── lib/i18n/                       # EXTENDED: es and en strings for the export
```

**Structure Decision**: The export is a read-only feature on top of spec 025. Markdown and PDF are both rendered on the server from the same `ShoppingList` value, so the two formats cannot drift apart. The UI component is reusable: any page that has a kitchen ID and a list ID can mount it. The copy box shows the Markdown returned by the API, and the copy action uses the clipboard API.

## Complexity Tracking

No constitution violations. Nothing to justify.

Note: the PDF writer is about 150 lines of standard library code. The simpler alternative, a third-party PDF library, would add a dependency that the constitution requires the project lead to approve. It is recorded in research R2 as a decision for the owner to confirm, not as a violation.
