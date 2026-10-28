# Implementation Plan: Match Captured Ingredient Names to the Notebook's Catalog

**Branch**: `018-ingredient-catalog-match` (spec folder `018-ingredient-catalog-match`, story S-018) | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-ingredient-catalog-match/spec.md`

## Summary

After a member captures a recipe from text, each ingredient line in the draft shows
either "matched: <catalog name>" or "new ingredient". A changed name ("onions" →
"onion") is listed for undo, and the member can change any line's match. The AI
model proposes a catalog match per line and the text's own name for it; a fixed,
pure domain rule confirms or rejects each proposal (spec clarification 2026-10-26,
FR-012). Matching reads the notebook catalog and writes nothing.

Technical approach: a pure `domain/ingredient_catalog.py` holds the normalization
(trim, case, spaces, English and Spanish singular rules, accent-insensitive
comparison) and the confirm-or-reject rule. The extraction schema and prompt gain
two per-line fields, `text_name` and `catalog_match`. `check_draft` runs the rule
after its existing checks and returns each line's match and the change list. The
ui shows the labels and the change list, and holds the member's undo and match
choices in the client-only capture store. No table, migration or new library.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: the S-015 `RecipeExtraction` use case, `GeminiRecipeExtractor` (`google-genai`, through the `adapters/llm/` port), `FakeRecipeExtractor`, `domain/recipe_draft.py`. ui: `captureStore`, `draftRules`, `IngredientLineRow`, `captureMessages`. **No new library.**

**Storage**: PostgreSQL 16, unchanged. The matcher only reads `ingredient` through the existing `IngredientCatalog` port (spec 056). No table, column or migration is added (spec FR-006).

**Testing**: pytest + ruff (api). Domain tests for the rule are pure, with no database (constitution §6). Application tests use the fake extractor. Integration runs in the Compose test overlay with real Postgres. vitest + eslint + typecheck (ui). The AI fixtures in `api/tests/fixtures/ai_eval/` give the manual SC-004 check.

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: Matching adds no visible wait to a draft: the rule runs in memory over the notebook's catalog (SC-003: up to 30 lines against up to 500 names).

**Constraints**:
- The rule is pure: no I/O, no SDK import in `domain/` (constitution §3).
- The model's output is data. Its proposals are checked by the rule and never trusted as matches (constitution §5: the model does not decide what is saved).
- Matching never writes the catalog (FR-006). The draft is still never saved in this feature (S-020).
- Labels and the change list are English only (spec Assumptions; spec 017 pattern).

**Scale/Scope**: One household. About 1 new domain module, edits to 4 api modules (extraction schema, prompt, fake extractor, draft check), 1 ui module plus edits to 3 ui files. Test files for each.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and reuse | No new service, no new library, reuses the S-015 use case and the S-056 catalog port. | Pass |
| 2. Tech stack stability | Gemini stays behind `adapters/llm/`; the model name still comes from settings. The schema and prompt change only. | Pass |
| 3. Hexagonal architecture | The rule and the normalization live in `domain/` with no I/O. The catalog is read in `application/` through the existing port. | Pass |
| 4. Security and privacy | The catalog names and the new fields reach the model inside the existing delimited blocks (prompt rule: text is data). No personal data added. | Pass |
| 5. No AI shortcuts | The model proposes; the rule confirms or rejects; the member sees and can undo every change before saving (no save here). | Pass |
| 6. Testing and quality | Pure domain tests for the rule (match, reject, singular, accents, duplicates, empty catalog). Application and integration tests with the fake extractor. Browser check for the labels and undo. | Pass |
| 7. Deployment | No deploy change. | Pass (n/a) |
| 8. Code review and git | One commit per logical change; no schema change, so no Alembic revision. | Pass |
| 9. Scope | S-018 is Must and "Capture" epic; it is in the ordered Must list. Copy (S-048) and join (S-057) reuse the rule later and are not built here. | Pass |

**Result**: No violations. Complexity Tracking not needed.

**Post-design re-check**: Pass. The design adds no table, service or library, and keeps the rule in `domain/`.

## Project Structure

### Documentation (this feature)

```text
specs/018-ingredient-catalog-match/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── matching.md      # Extraction fields, draft match response, ui behaviour
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── ingredient_catalog.py      # NEW: normalize_name, singular forms, match_line (pure)
│   └── recipe_draft.py            # EDIT: IngredientLine gains text_name, catalog_match;
│                                  #       _normalized_name replaced by the rule; check_draft
│                                  #       returns matches and changes
├── application/
│   └── recipe_extraction.py       # EDIT: passes the catalog to check_draft (no shape change)
├── adapters/llm/
│   ├── gemini_extractor.py        # EDIT: schema gains text_name, catalog_match; maps them
│   ├── prompt.py                  # EDIT: rule text for text_name and catalog_match
│   └── fake_extractor.py          # EDIT: canned results carry the new fields
├── api/routes/recipe_capture.py   # EDIT: draft response gains lines[].match and changes
└── tests/
    ├── test_ingredient_catalog_domain.py        # NEW: pure rule tests
    ├── test_recipe_draft_domain.py              # EDIT: check_draft with matches
    ├── test_recipe_extraction_application.py    # EDIT: matches reach the draft
    ├── test_recipe_capture_application.py       # EDIT: capture returns matches
    ├── test_recipe_capture_integration.py       # EDIT: real catalog in a capture
    ├── test_gemini_extractor_adapter.py         # EDIT: schema and mapping of new fields
    └── fixtures/ai_eval/                        # EDIT: plural/case/spacing fixtures (SC-004)

ui/
├── lib/capture/
│   ├── captureStore.ts            # EDIT: LineView gains match and undo state; choose/undo actions
│   ├── captureClient.ts           # EDIT: parses matches and changes from the response
│   ├── draftRules.ts              # unchanged
│   └── labels.ts                  # EDIT: matched / new ingredient / change list labels
├── lib/i18n/capture.ts            # EDIT: English strings for labels and change list
└── components/RecipeDraft/
    ├── IngredientLineRow.tsx      # EDIT: label line and "change match" control
    ├── RecipeDraftEditor.tsx      # EDIT: change list section above the ingredient table
    └── *.test.tsx                 # EDIT/NEW: vitest for labels, undo, choose match
```

**Structure Decision**: Extend the existing S-016 capture modules; no new package, service or
route. The rule is one domain module so S-048 and S-057 can import it later.

## Complexity Tracking

Not applicable: no constitution violations.
