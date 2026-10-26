# Implementation Plan: Clear Recipe Capture Error Messages

**Branch**: `S-017` (spec folder `017-recipe-capture-error-messages`) | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-recipe-capture-error-messages/spec.md`

**Related**: Changes the refusal and failure messages of spec 016 (`specs/016-capture-recipe-text/`) for the not-a-recipe, one-recipe, unreadable-answer and missing-part cases. Spec 016's other messages are unchanged (FR-011).

## Summary

When a member's pasted text is refused, the capture sheet shows a message. Today that message is often generic: a missing title or steps, a bad ingredient line, and an unreadable assistant answer all show the same or near-same text, and the not-a-recipe reason is free text from the model. This feature makes each refusal say what is wrong in plain English and give one next step, and keeps the pasted text in the box.

Technical approach: the domain rule check stops at the first failure today and the use case folds every draft failure into one `InvalidOutput` result. Instead, the domain collects every missing part (title, steps) and every ingredient-line problem (quantity missing, unit missing, unit not recognized) into a structured result. The use case passes that result through, the route maps it to two new 422 codes, and the ui maps each code to a fixed English message in the one message file. The model's free-text `reason` is replaced by a closed set of reasons the app words itself (FR-007). No table, no new library, no new service.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: the S-015 `RecipeExtraction` use case and `check_draft` in `domain/recipe_draft.py`, `GeminiRecipeExtractor` (`adapters/llm/`), FastAPI route `api/routes/recipe_capture.py`. ui: `lib/capture/captureClient.ts`, `lib/i18n/capture.ts`, `components/AddRecipeCallToAction/TextCaptureSheet.tsx`. **No new library.**

**Storage**: None. This feature stores nothing (spec: Key Entities N/A, FR-019 from spec 016 still holds).

**Testing**: pytest + ruff (api). Domain tests pure (`api/tests/`, domain rule cases). Use-case tests use `FakeRecipeExtractor`. Integration tests in the Compose test overlay for the routes. vitest + eslint + typecheck (ui). Browser walkthrough per `quickstart.md`. Manual AI evaluation for the not-a-recipe reason set uses `api/tests/fixtures/ai_eval/`.

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: No change. The message is shown within the spec 016 deadline (`GEMINI_TEXT_TIMEOUT_S` + 2 s). No extra assistant call and no extra database read.

**Constraints**:
- Every refusal message names the reason and, where the member can act, one next step (SC-001).
- No raw assistant text, service error, key or trace reaches a message (FR-007, SC-003). Reasons come from fixed wording in the app.
- The pasted text stays in the box (FR-008, SC-004). The ui already keeps it on every failure; this feature must not clear it.
- Messages are English and defined once, in `ui/lib/i18n/capture.ts` (FR-009, FR-010).
- The model keeps one extraction call per submission (spec 016 FR-025).

**Scale/Scope**: About 3 api modules edited, 2 api test modules edited and 1 new, 1 ui message file and 2 ui components/clients edited, 1 ui test file edited. No migration, no route added.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| §1 Simplicity and Reuse | No new service, route or library. Existing 422 response shape (`detail`, `code`) is reused with two new codes. | PASS |
| §2 Tech stack | No dependency change. The reason set is a schema enum in the existing Gemini `response_schema`. | PASS |
| §3 Hexagonal | Domain (`check_draft`) stays pure: it returns problems, it does not format text. The fixed English sentences live in the ui message file, and the api only sends codes and fixed field names. The `RecipeExtractor` port keeps its shape; only the `NotARecipe` payload changes from free text to a closed reason. | PASS |
| §4 Security and Privacy | The api never sends the assistant's reason text. The only assistant-derived value in a message is an ingredient name, cleaned and length-capped before use (Design Decision 5; FR-007). Logs keep the rule name and outcome, never values (already the S-015 behaviour). | PASS |
| §5 No AI Shortcuts | Draft is still never saved. No automatic retry or edit of the text (spec Out of Scope). | PASS |
| §6 Testing | Domain pure tests cover each problem kind and the multi-part case. Use-case tests cover pass-through. Integration tests check each code. vitest checks each code maps to one fixed message. | PASS |
| §7 Deployment | No compose, env or proxy change. | PASS |
| §8 Git discipline | One commit per phase (see Phase breakdown). Prompt change and schema change go in one commit with their tests. | PASS |
| §9 Scope | Must-have for the S-017 story. Translation and retry are out of scope. | PASS |
| AGENTS.md: "The user's input is never lost on error" | Each refusal keeps the text in the box (FR-008). | PASS |
| AGENTS.md: "Do not add new folders without asking" | No new folder. | PASS |
| AGENTS.md: "If the spec and this file disagree, ask" | Not applicable. | PASS |

**Open points that need a decision before tasks (not gate failures)**: see the Design Decisions section, items 4 and 5.

**Result**: No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/017-recipe-capture-error-messages/
├── spec.md                       # Feature spec (input)
├── plan.md                       # This file
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output (value types only; nothing stored)
├── quickstart.md                 # Phase 1 output (validation guide)
├── contracts/
│   └── capture-messages.md       # Phase 1 output: codes, reasons, fixed wording, HTTP delta
├── checklists/requirements.md
└── tasks.md                      # Created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── recipe_draft.py                   # EDIT: check_draft collects DraftProblems
│                                         #       (missing parts, line problems); generic
│                                         #       InvalidDraftError kept for other breaks
├── application/
│   └── recipe_extraction.py              # EDIT: NotARecipe.reason becomes NotRecipeReason
│                                         #       (closed enum); new DraftIncomplete outcome
│                                         #       carrying the DraftProblems; InvalidOutput
│                                         #       for other breaks unchanged
├── adapters/llm/
│   ├── gemini_extractor.py               # EDIT: outcome "not_a_recipe" takes reason from an
│   │                                     #       enum in RESPONSE_SCHEMA; free text dropped
│   └── prompt.py                         # EDIT: list the allowed reasons and what each means
├── api/routes/recipe_capture.py          # EDIT: map new outcomes to 422 codes; no free text
│                                         #       in detail for not_a_recipe
└── tests/
    ├── test_recipe_draft_domain.py       # EDIT: missing-part and line-problem cases, multi-part
    ├── test_recipe_extraction_application.py  # EDIT: outcomes pass through; logs keep names only
    ├── test_gemini_extractor_adapter.py  # EDIT: reason enum maps to NotRecipeReason
    └── test_recipe_capture_integration.py  # EDIT: each new code and its 422 status, text kept

ui/
├── lib/
│   ├── i18n/capture.ts                   # EDIT: new fixed English messages, one per reason
│   │                                     #       and code; "oneRecipe" and "notARecipe" reworded
│   └── capture/captureClient.ts          # EDIT: read the new fields (missing parts, line
│                                         #       problems); drop the free-text reason
└── components/AddRecipeCallToAction/
    ├── TextCaptureSheet.tsx              # EDIT: show the messages from messageForCode
    └── TextCaptureSheet.test.tsx         # EDIT: each code shows its fixed message; text kept
```

**Structure Decision**: Extend the existing S-015 and S-016 modules. The message text stays in `ui/lib/i18n/capture.ts`, so the api never needs to know wording (FR-010). No new folder.

## Design Decisions (summary; detail in research.md)

1. **Every missing part is named, not only the first.** `check_draft` today raises on the first broken rule. It becomes a pass that checks the title, the steps and every ingredient line, and collects the failures (research R1). Refusal order does not change: text checks (empty, too long) still run before any extraction call.

2. **Missing parts are the title and the steps only.** The ingredient list is not required (clarified in spec 017, matching `check_draft` today).

3. **Ingredient line problems are three kinds, each with its ingredient.** `quantity_missing` (no quantity, or a quantity that is not a positive number), `unit_missing` (no unit), `unit_not_recognized` (a unit the app does not know). Each problem carries the ingredient name, so "1/4 butter" with no unit gives "Add a unit to butter." A line with neither quantity nor unit reports both kinds for that name (FR-012). A vague line (`vague: true`) is valid and never reports these kinds. Other rule breaks (name empty, servings below 1, vague line with an amount) keep the generic message (clarification Q2).

4. **The not-a-recipe reason is a closed set the app words itself (FR-004, FR-007).** The model's free-text `reason` is no longer shown. The model picks one value from a fixed enum (research R2): `question_or_request` (the text asks something, or is a request, instead of giving a recipe; confirmed 2026-10-25, the message asks the member to clarify the text by pasting the full recipe), `not_food`, and `story_or_article`. The model also returns an optional `ingredient` when the question is about one ingredient (FR-013), for example "what's the total grams of a bar of butter?" gives `butter`. The app maps the value to one fixed sentence and adds the ingredient name when present.

5. **Ingredient names are shown, cleaned first (FR-007, FR-012, FR-013).** The name is the only assistant-derived value a message may show. Before it reaches the api response it is cleaned: trimmed, collapsed spaces, at most 40 characters, letters plus spaces, hyphens and apostrophes only (any other character drops the name). A name that fails the check is sent as `null`, and the ui then uses the generic phrase "this ingredient" in the sentence, so no unchecked text reaches the member. The cleaning runs in the domain (a pure function), and tests cover accents, digits, long names and empty names. Accents are allowed (letters in any language), so "crème fraîche" passes. Each line problem lists its own sentence; at most five sentences are shown, then "and more ingredients need a change."

6. **Two new 422 codes; no raw detail.** `draft_incomplete` (body `missing` list of `title`/`steps`, and `line_problems` list of `{name, kind}`) and `ingredient_line_problem` use the existing `{detail, code}` shape. `detail` holds only fixed English (or is empty); the ui reads `code` and the lists, and maps them to messages (contracts/capture-messages.md). `not_a_recipe` carries the reason value and, when present, the cleaned `ingredient` name. `one_recipe_at_a_time` keeps its code and gets new wording.

7. **Generic fallback for other breaks.** The unreadable-answer message is reworded to the spec's wording ("could not build a recipe from this text ... try again or shorten the text to one recipe") and keeps code `ai_invalid_output`. Service and availability messages stay (FR-011).

8. **Messages in one place.** Every new string goes in `ui/lib/i18n/capture.ts` next to the existing ones. Components only call `messageForCode` (FR-010). The api holds no user-facing English for these cases beyond fixed `detail` strings for logs and tests.

## Phase breakdown (for tasks.md, one commit each)

1. **Domain**: `DraftProblems` and line-problem kinds in `recipe_draft.py`; domain tests (research R1).
2. **Application**: new outcomes and reason enum in `recipe_extraction.py`; pass-through in `recipe_capture.py`; application tests (research R3).
3. **Adapter**: reason enum in `RESPONSE_SCHEMA` and `prompt.py`; adapter tests; AI evaluation fixtures for the three reasons (research R2).
4. **API route**: map outcomes to codes; integration tests (research R3, contracts).
5. **UI**: message file, client mapping, sheet, vitest; browser walkthrough (quickstart).

## Complexity Tracking

> Not applicable: no constitution violations.
