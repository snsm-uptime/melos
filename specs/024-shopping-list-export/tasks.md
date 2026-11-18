# Tasks: Shopping List Export (Markdown copy and PDF)

**Input**: Design documents from `specs/024-shopping-list-export/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The plan's testing section and constitution principle 6 require domain, application and route tests for this feature.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)
- File paths are exact. API routes live in `api/api/routes/`; the spec 025 list route is `api/api/routes/shopping_list.py`.

## Phase 1: Setup

**Purpose**: Confirm the starting point. No new dependencies (research R2).

- [X] T001 Confirm the spec 025 list read path and its test fixtures by reading `api/application/shopping_list.py` and `api/tests/test_shopping_list_saved_integration.py`, and note the fixture helpers to reuse in `specs/024-shopping-list-export/notes.md`
- [X] T002 [P] Confirm the baseline is green: run `cd api && uv run pytest tests/test_shopping_list_saved_application.py tests/test_shopping_list_saved_integration.py` and `cd ui && npm run test -- ShoppingList`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The read model, the access rule and the route skeleton that both formats need. No format is implemented here.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create the pure export view types `ExportLine`, `ExportDocument` and the `build_export_document(shopping_list, locale)` function in `api/domain/shopping_export.py`. Lines are ordered measured first, then "Your call"; manual items have no recipe titles (data-model.md)
- [X] T004 [P] Write domain tests for `build_export_document` in `api/tests/test_shopping_export_domain.py`: order of measured lines, "Your call" section, manual item has no sources, empty list gives empty lists
- [X] T005 Create the use case `export_shopping_list(kitchen_id, list_id, format, actor)` in `api/application/shopping_export.py`. It reads the list through the existing spec 025 repository port, checks read access through `KitchenAccessAuthorizer` and raises the same not-found error as an unknown ID (FR-013). It never writes (FR-009, FR-012)
- [X] T006 [P] Write application tests in `api/tests/test_shopping_export_application.py` with the existing fake ports: member gets the document, non-member gets not-found, unknown ID gets not-found with the same error, closed list is allowed, no write call is made
- [X] T007 Add the route `GET /kitchens/{kitchen_id}/shopping-lists/{list_id}/export` with a `format` query parameter (`markdown` or `pdf`) in `api/api/routes/shopping_list.py`. For now it returns 400 for a bad format and calls the use case; format rendering is added in later phases
- [X] T008 Write route tests for the 400 on a bad format and the 404 for a non-member and an unknown ID, which must have the same body (`{"detail": "Not found"}`), in `api/tests/test_shopping_list_export_api.py`
- [X] T009 Add the BFF proxy `ui/app/api/kitchens/[kitchenId]/shopping-lists/[listId]/export/route.ts` that forwards the query string, status and headers without changing the body. Follow the pattern of `ui/app/api/kitchens/[kitchenId]/shopping-lists/[listId]/route.ts`
- [X] T010 [P] Add the export strings (headings, "Copy", "Download PDF", "No items", "Add recipes or items to the list first.", "(manual)", error texts) in English and Spanish in `ui/lib/i18n/shoppingExport.ts`, following `ui/lib/i18n/cart.ts`

**Checkpoint**: The use case, route and proxy exist and the access rule is tested. Formats are still missing.

---

## Phase 3: User Story 1 - Copy the shopping list as Markdown (Priority: P1) 🎯 MVP

**Goal**: A member opens any shopping list of their kitchen, sees the Markdown in a copy box and copies it in one action.

**Independent Test**: With a list of two recipe lines and one manual item, open the list page, press Copy, paste into a plain text field and check that every line, its quantity, its recipe titles, "(manual)" and the "Your call" section are present (quickstart section 3).

### Tests for User Story 1

- [X] T011 [P] [US1] Write domain tests for `render_markdown(document)` in `api/tests/test_shopping_export_markdown.py`: headings, recipe titles in parentheses, "(manual)" for manual items, "Your call" section after measured lines, number formatting with at most two decimals and trailing zeros removed, empty list text ("No items")
- [X] T012 [P] [US1] Write route tests for `format=markdown` in `api/tests/test_shopping_list_export_api.py`: 200, `Content-Type: text/markdown; charset=utf-8`, body equals the domain renderer output for a seeded list

### Implementation for User Story 1

- [X] T013 [US1] Implement `render_markdown(document)` in `api/domain/shopping_export.py` following the format in research R3. It is pure and returns `str`
- [X] T014 [US1] Wire `format=markdown` in `api/api/routes/shopping_list.py`: call the use case, render with `render_markdown` and return the text with the Markdown content type
- [X] T015 [US1] Add a log line for the markdown export in `api/api/routes/shopping_list.py` with `outcome`, `format` and `line_count` only, never line text (research R7)
- [X] T016 [P] [US1] Add the client wrapper `ui/components/ShoppingListExport/exportText.ts` that fetches `/api/kitchens/{kitchenId}/shopping-lists/{listId}/export?format=markdown` and returns the text or a typed error
- [X] T017 [US1] Create the reusable component `ui/components/ShoppingListExport/ShoppingListExport.tsx` with props `kitchenId` and `listId`. It loads the Markdown on mount, shows it in a read-only text box, and its Copy action writes it to the clipboard and shows a confirmation. It disables actions and shows the hint when the list has no lines (research R5)
- [X] T018 [US1] Add `ui/components/ShoppingListExport/index.ts` that exports `ShoppingListExport`
- [X] T019 [US1] Mount `ShoppingListExport` on the list page in `ui/app/kitchens/[kitchenId]/shopping-lists/[listId]/page.tsx`, so both active and closed lists show it
- [X] T020 [P] [US1] Write component tests in `ui/components/ShoppingListExport/ShoppingListExport.test.tsx`: text loads into the box, Copy writes the exact text and shows confirmation, empty list disables Copy and shows the hint
- [X] T021 [P] [US1] Write a test for `exportText.ts` in `ui/components/ShoppingListExport/exportText.test.ts`: success returns text, a 404 returns the not-found error

**Checkpoint**: User Story 1 works on its own: any list of the kitchen can be copied as Markdown, and the Markdown matches the API.

---

## Phase 4: User Story 2 - Download the shopping list as PDF (Priority: P2)

**Goal**: A member downloads the same list as a PDF with recipe titles after each line in parentheses, and the "Your call" section.

**Independent Test**: With a list of three recipes including a vague line and a scaled line, download the PDF and compare every line with the copy box (quickstart section 4).

### Tests for User Story 2

- [X] T022 [P] [US2] Write domain tests for the PDF writer in `api/tests/test_shopping_export_pdf.py`: output starts with `%PDF-1.4` and ends with `%%EOF`, a list of 100 lines spans more than one page, accented text (á é í ó ú ü ñ ¿ ¡) is encoded in WinAnsi, a character outside WinAnsi becomes "?" (research R2), recipe titles appear in parentheses
- [X] T023 [P] [US2] Write route tests for `format=pdf` in `api/tests/test_shopping_list_export_api.py`: 200, `Content-Type: application/pdf`, `Content-Disposition` is `attachment; filename="shopping-list-YYYY-MM-DD.pdf"` with the closing date or today for an active list
- [X] T024 [P] [US2] Write a test in `ui/components/ShoppingListExport/exportText.test.ts` that the PDF request returns a Blob and the file name from `Content-Disposition`

### Implementation for User Story 2

- [X] T025 [US2] Implement the PDF writer `render_pdf(document) -> bytes` in `api/domain/shopping_export.py` using only the standard library: PDF 1.4 objects, Helvetica and Helvetica-Bold with WinAnsiEncoding, page breaks by line count, `zlib` stream compression, correct xref offsets, `%%EOF`
- [X] T026 [US2] Wire `format=pdf` in `api/api/routes/shopping_list.py`: render with `render_pdf` and return `application/pdf` with the `Content-Disposition` from the contract
- [X] T027 [US2] Extend the log line in `api/api/routes/shopping_list.py` so it records `format=pdf` and `line_count` only
- [X] T028 [US2] Add the PDF request to `ui/components/ShoppingListExport/exportText.ts`: returns a Blob and the file name from `Content-Disposition`
- [X] T029 [US2] Add the "Download PDF" button to `ui/components/ShoppingListExport/ShoppingListExport.tsx` that saves the Blob using a temporary object URL, and is disabled when the list has no lines

**Checkpoint**: User Stories 1 and 2 both work: copy and download produce the same lines.

---

## Phase 5: User Story 3 - Recover when PDF fails (Priority: P3)

**Goal**: When PDF generation fails the member sees a clear error, no partial file downloads, and the Markdown copy still works (AC5.5).

**Independent Test**: Make the PDF step fail on purpose; check that the error is shown, no file downloads, and Copy still works (quickstart section 5).

### Tests for User Story 3

- [X] T030 [P] [US3] Write a route test in `api/tests/test_shopping_list_export_api.py` that a PDF render error returns 500 with `{"detail": "PDF could not be created"}` and that the Markdown route still returns 200 for the same list
- [X] T031 [P] [US3] Write a component test in `ui/components/ShoppingListExport/ShoppingListExport.test.tsx` that a failed PDF request shows the error text, creates no object URL and leaves the copy box and Copy usable

### Implementation for User Story 3

- [X] T032 [US3] In `api/api/routes/shopping_list.py`, catch a PDF render error, log `outcome=pdf_failed` with `line_count` only, and return the 500 body from the contract
- [X] T033 [US3] In `ui/components/ShoppingListExport/ShoppingListExport.tsx`, show the PDF error message from `ui/lib/i18n/shoppingExport.ts` on failure, and keep the copy box and Copy untouched (AC5.5)

**Checkpoint**: All three stories work independently.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Checks that span the stories.

- [ ] T034 [P] Add the export entry to the feature inventory in `ui/lib/featureInventory.ts` only if the owner confirms the feature is ready for the landing page (AGENTS.md "Backlog files" inventory rule)
- [X] T035 [P] Verify the Spanish strings in `ui/lib/i18n/shoppingExport.ts` match the English keys one to one (existing parity test pattern, `ui/lib/i18n/*.test.ts`)
- [X] T036 Run `cd api && uv run ruff check . && uv run ruff format --check .` and fix findings in the files this feature touched
- [X] T037 Run `cd ui && npm run lint && npm run typecheck` and fix findings in the files this feature touched
- [ ] T038 Run the full quickstart validation in `specs/024-shopping-list-export/quickstart.md` in the browser at 360 px and 1280 px, in English and Spanish, and record the outcome in `specs/024-shopping-list-export/notes.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational. It reuses the component from US1 (T017, T029 extends it), so start it after T017 is merged.
- **User Story 3 (Phase 5)**: Depends on US1 and US2 because it changes the component and the route both formats use.
- **Polish (Phase N)**: After the stories you ship.

### Within Each User Story

- Tests are written first and fail before implementation.
- Domain renderer before route wiring.
- Route before the UI that calls it.

### Parallel Opportunities

- T002 with T001.
- T004 and T006 with T003 and T005 (different files).
- T010 with the domain and application work.
- Within US1: T011, T012, T016, T020, T021 in parallel.
- Within US2: T022, T023, T024 in parallel.
- T030 and T031 in parallel (API and UI files).
- T034 and T035 in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first, in parallel:
Task: "Domain tests for render_markdown in api/tests/test_shopping_export_markdown.py"
Task: "Route tests for format=markdown in api/tests/test_shopping_list_export_api.py"
Task: "Component tests in ui/components/ShoppingListExport/ShoppingListExport.test.tsx"

# Then the client wrapper while the API renderer is written:
Task: "Client wrapper ui/components/ShoppingListExport/exportText.ts"
Task: "render_markdown in api/domain/shopping_export.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2 (read model, access rule, route, proxy, strings).
2. Phase 3 (Markdown copy).
3. **Stop and validate** with quickstart sections 3 and 6. This is the first shippable increment: it covers the copy path and the access rule.

### Incremental Delivery

1. Foundation → access rule and route tested.
2. US1 → Markdown copy works for any list (MVP).
3. US2 → PDF download.
4. US3 → failure path (AC5.5).
5. Polish → checks, quickstart in the browser.

---

## Notes

- Route module is `api/api/routes/shopping_list.py` (corrected from the plan, which named `adapters/web`).
- The PDF writer is pure standard library code. A third-party PDF library would need the project lead's approval (research R2); the tasks do not add one.
- Every new text string is in both `es` and `en`.
- Commit after each task or logical group.
