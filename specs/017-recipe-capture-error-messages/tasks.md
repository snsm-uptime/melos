# Tasks: Clear Recipe Capture Error Messages

**Input**: Design documents from `specs/017-recipe-capture-error-messages/`
**Prerequisites**: plan.md (required), spec.md (required, user stories), research.md, data-model.md, contracts/capture-messages.md, quickstart.md

**Tests**: Included. Constitution §6 makes tests mandatory for domain (pure pytest), application (fake ports), integration (Compose) and UI (vitest). Write each story's tests first and confirm they fail before the implementation task that makes them pass.

**Organization**: Tasks are grouped by user story. Story labels follow spec.md: US1 (P1, missing parts and ingredient problems), US2 (P1, not a recipe and one recipe), US3 (P2, unreadable answer), US4 (P2, one message file).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on an incomplete task
- **[Story]**: US1 to US4; Setup, Foundational and Polish have no label

## Path Conventions

Repo root: `/Users/sebastiansotom/Documents/github/mstr/melos/`. Paths below are relative to it.

---

## Phase 1: Setup (Baseline)

**Purpose**: Confirm the current suites pass before any change, so a later failure is ours.

- [ ] T001 Run the api suite in Compose (`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`) and record the result; run `cd ui && npm test && npm run lint && npm run typecheck` and record the result

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Value types and the display-name rule that every story uses. No story starts until this phase is done.

**⚠️ CRITICAL**: Blocks all user stories.

- [X] T002 [P] Add `LineProblemKind` string enum (`quantity_missing`, `unit_missing`, `unit_not_recognized`), `LineProblem` dataclass (`name: str`, `kind: LineProblemKind`) and `DraftProblems` exception (`missing: tuple[str, ...]` with values `"title"`/`"steps"` in that order, `line_problems: tuple[LineProblem, ...]`) in `api/domain/recipe_draft.py`, next to `InvalidDraftError`
- [X] T003 [P] Add pure function `clean_display_name(raw: str | None) -> str | None` in `api/domain/recipe_draft.py`: trim, collapse runs of spaces to one, return `None` when empty or longer than 40 characters, return `None` when any character is not a letter (any language), space, hyphen (`-`) or apostrophe (`'`); otherwise return the cleaned string
- [X] T004 [P] Add string enum `NotRecipeReason` with `QUESTION_OR_REQUEST = "question_or_request"`, `NOT_FOOD = "not_food"`, `STORY_OR_ARTICLE = "story_or_article"`, `MULTIPLE_RECIPES = "multiple_recipes"` in `api/application/recipe_extraction.py`; change `NotARecipe` to `reason: NotRecipeReason` plus `ingredient: str | None = None`; add dataclass `DraftIncomplete(problems: DraftProblems)` and add it to the `ExtractionResult` union
- [X] T005 [P] Domain tests for `clean_display_name` in `api/tests/test_recipe_draft_domain.py`: "butter" → "butter"; "  crème fraîche " → "crème fraîche"; "2 x butter!" → None; "" and None → None; 41 letters → None; 40 letters → kept; "o'neil-style" → kept; double spaces collapsed

**Checkpoint**: Types exist and `clean_display_name` is tested. T005 must pass before any story task that depends on it.

---

## Phase 3: User Story 1 - Member learns which part of the recipe is missing (Priority: P1) 🎯 MVP

**Goal**: A text with no title, no steps, or an ingredient line with no quantity, no unit or an unknown unit gets a message that names the missing part or the ingredient, says what to add, and keeps the text in the box.

**Independent Test**: Paste a recipe with ingredients and steps but no title → "Add a title for the recipe." and the text is still in the box. Paste "1/4 butter" as an ingredient → "Add a unit to butter, such as grams, cups or units." (quickstart rows 1, 2, 4, 5).

### Tests for User Story 1 ⚠️ (write first; must fail before T012 to T015)

- [X] T006 [P] [US1] Domain tests in `api/tests/test_recipe_draft_domain.py`: `check_draft` raises `DraftProblems` with `missing == ("title",)` for an empty title; `("steps",)` for no non-blank step; `("title", "steps")` when both are missing (order kept); no `DraftProblems` when the ingredient list is empty (FR-003, spec Assumptions)
- [X] T007 [P] [US1] Domain tests in `api/tests/test_recipe_draft_domain.py`: per-line kinds — no quantity → `quantity_missing`; quantity 0 or negative → `quantity_missing`; no unit → `unit_missing`; unit "widgets" → `unit_not_recognized`; line with neither quantity nor unit → two entries with the same name (`quantity_missing` and `unit_missing`); "1/4 butter" with no unit → `LineProblem(name="butter", kind=unit_missing)`; vague line (`vague=True`, no amount) → no line problem
- [X] T008 [P] [US1] Domain tests in `api/tests/test_recipe_draft_domain.py`: a draft with a missing title and a bad line returns both in one `DraftProblems`; servings 0 with no named problem still raises the generic `InvalidDraftError`; servings 0 together with a named problem raises `DraftProblems` (named problems win)
- [X] T009 [P] [US1] Application test in `api/tests/test_recipe_extraction_application.py` with `FakeRecipeExtractor` scripted to a draft missing its title: `extract` returns `DraftIncomplete` whose `problems.missing == ("title",)`; a generic break still returns `InvalidOutput`; the log record names kinds only (no ingredient name, no title)

### Implementation for User Story 1

- [X] T010 [US1] Change `check_draft` in `api/domain/recipe_draft.py` to run the title, steps and every ingredient-line check in one pass, collect `missing` and `line_problems` (per T002 types), raise `DraftProblems` when either is non-empty; otherwise run the servings and name checks and raise the existing `InvalidDraftError` for them. Each `LineProblem.name` is the normalized ingredient name (`butter` for "1/4 butter"). Depends on T002, T006 to T008
- [X] T011 [US1] Update `RecipeExtraction._evaluate` in `api/application/recipe_extraction.py`: catch `DraftProblems` and return `DraftIncomplete(problems=exc.problems)`; log `missing=<comma list>` and `line_problems=<comma list of kinds>` only (constitution §4). Depends on T004, T009, T010
- [X] T012 [US1] Map `DraftIncomplete` in `api/api/routes/recipe_capture.py` (`_outcome_response`): when `missing` is non-empty return 422 `draft_incomplete` with body `{"detail": "", "code": "draft_incomplete", "missing": [...], "line_problems": [...]}`; when only line problems exist return 422 `ingredient_line_problem` with `line_problems`. Each `line_problems` entry is `{"name": clean_display_name(name), "kind": kind.value}`. Depends on T011
- [X] T013 [US1] Integration tests in `api/tests/test_recipe_capture_integration.py` (Compose, fake extractor injected): no title → 422 `draft_incomplete`, `missing == ["title"]`; no steps → `["steps"]`; "1/4 butter" line → 422 `ingredient_line_problem` with `{"name": "butter", "kind": "unit_missing"}`; an ingredient name with digits (for example "2 x butter!") → `name` is `null`; both missing and a bad line → `draft_incomplete` with both lists filled; the `code` and body contain no assistant text. Depends on T012
- [X] T014 [US1] Extend `CaptureMessage` in `ui/lib/capture/captureStore.ts` to `{ code: string; reason?: string; missing?: string[]; lineProblems?: { name: string | null; kind: string }[]; ingredient?: string | null }`; in `ui/lib/capture/captureClient.ts` (`submitCapture`) copy `missing` and `line_problems` (mapped to `lineProblems`) from the 422 body into the message. Depends on T013
- [X] T015 [US1] Change `messageForCode` in `ui/lib/i18n/capture.ts` to take the `CaptureMessage` and `max`, and return one string: the `missing` sentences first (title, then steps), then the line sentences in order (at most five, then "and more ingredients need a change."). Use the exact wording from contracts/capture-messages.md ("Add a title for the recipe.", "Add the steps of the recipe.", "Add a quantity to {name}.", "Add a unit to {name}, such as grams, cups or units.", "{name} uses a unit the app does not know. Use a common unit, such as grams, cups or spoons."); `{name}` is "this ingredient" when `name` is null. Update the caller in `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx` (line 111). Depends on T014
- [X] T016 [P] [US1] vitest in `ui/lib/capture/captureClient.test.ts`: a 422 `draft_incomplete` body maps to `missing` and no `reason`; an `ingredient_line_problem` body maps `line_problems` with `name` and `kind`; a `null` name is kept as `null`. Depends on T014
- [X] T017 [US1] vitest in `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx`: after a `draft_incomplete` (title) response the message reads "Add a title for the recipe.", and the textarea still holds the pasted text (SC-004); after "1/4 butter" the message reads "Add a unit to butter, such as grams, cups or units.". Depends on T015, T016

**Checkpoint**: US1 works alone: quickstart rows 1, 2, 4, 5 pass with the text kept in the box.

---

## Phase 4: User Story 2 - Member learns why the text is not a recipe (Priority: P1)

**Goal**: A text that is a question or request, not about food, or a story, gets the matching reason in fixed wording. A question about one ingredient names it. Two recipes get the "one by one" message. The model's free text is never shown.

**Independent Test**: "What's the weather tomorrow?" → "That doesn't look like a recipe. It reads as a question or request. Clarify the text: paste the full recipe, with its ingredients and steps." and the text stays. "What's the total grams of a bar of butter?" → the message names butter (quickstart rows 6, 7, 9).

### Tests for User Story 2 ⚠️ (write first; must fail before T023 to T027)

- [X] T018 [P] [US2] Adapter tests in `api/tests/test_gemini_extractor_adapter.py`: `reason` "question_or_request", "not_food", "story_or_article" map to the matching `NotRecipeReason`; `multiple_recipes` maps to `NotARecipe(reason=MULTIPLE_RECIPES)`; an unknown reason or a missing reason → `InvalidOutput`; `ingredient` "butter" → kept; `ingredient` "2 x butter!" → `None`; the old free-text reason (for example "The text is about the weather") is no longer used anywhere in the result
- [X] T019 [P] [US2] Application test in `api/tests/test_recipe_extraction_application.py`: `NotARecipe` from the port passes through unchanged with its enum reason and ingredient; no string field in the result holds raw text
- [X] T020 [P] [US2] Add AI evaluation cases under `api/tests/fixtures/ai_eval/` as `.txt` files, matching the existing files there: `butter_grams_question.txt` ("What's the total grams of a bar of butter?"), `holiday_story.txt` (a short story about a holiday), `shopping_links.txt` (a list of web links). Record the expected reason and ingredient for each in the eval notes for this fixture set (manual evaluation, constitution §6); check how the existing files in that folder are documented before adding the notes

### Implementation for User Story 2

- [X] T021 [US2] In `api/adapters/llm/gemini_extractor.py`: change `RESPONSE_SCHEMA` so `reason` is an enum of `question_or_request`, `not_food`, `story_or_article` and `ingredient` is an optional string; change `_ExtractionPayload` to match; map `reason` to `NotRecipeReason` (unknown or missing → `InvalidOutput`); map `multiple_recipes` to `NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES)`; clean `ingredient` with `clean_display_name`; delete `MAX_REASON_CHARS` and the `ONE_RECIPE_REASON` import. Depends on T004, T018
- [X] T022 [P] [US2] In `api/adapters/llm/prompt.py`: list the three reasons with one line each (question or request; not about food; a story, article or list of links); say to set `ingredient` only when the text is a question about one ingredient, and to leave it out otherwise
- [X] T023 [US2] In `api/application/recipe_extraction.py`: remove `ONE_RECIPE_REASON` and its string comparisons; `RecipeTextRefusedError` and the rest stay. Depends on T004, T019
- [X] T024 [US2] In `api/api/routes/recipe_capture.py` (`_outcome_response`): `NotARecipe` with `MULTIPLE_RECIPES` → 422 `one_recipe_at_a_time`, `detail` ""; any other reason → 422 `not_a_recipe` with `detail` = the enum value and `ingredient` = the cleaned name or `null`. Delete `MAX_REASON_CHARS` use here. Depends on T021, T023
- [X] T025 [US2] Integration tests in `api/tests/test_recipe_capture_integration.py`: weather text → 422 `not_a_recipe`, `detail == "question_or_request"`, `ingredient` null; butter question (scripted fake) → `ingredient == "butter"`; two recipes → `one_recipe_at_a_time`; no assistant sentence appears in any body. Depends on T024
- [X] T026 [US2] In `ui/lib/capture/captureClient.ts`: for `not_a_recipe`, copy `detail` into `reason` (an enum value) and `ingredient` into `ingredient`; remove the code that used `detail` as prose. Depends on T014
- [X] T027 [US2] In `ui/lib/i18n/capture.ts`: add the reason sentences from contracts/capture-messages.md (question or request with no ingredient, question with `{name}`, question with null ingredient → "this ingredient"; not about food; story or article); change `oneRecipe` to "Only one recipe can be added at a time. Paste them one by one."; drop the old append of the free-text reason in `messageForCode`. Depends on T015, T026
- [X] T028 [P] [US2] vitest in `ui/lib/capture/captureClient.test.ts`: `not_a_recipe` with `detail: "story_or_article"` gives that reason and no prose; `ingredient: "butter"` is kept. And in `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx`: the question-about-butter message names butter and the text stays in the box; `one_recipe_at_a_time` shows the new wording. Depends on T027

**Checkpoint**: US2 works alone: quickstart rows 6, 7, 9 pass.

---

## Phase 5: User Story 3 - Member knows what to do when the app cannot build a draft (Priority: P2)

**Goal**: An answer that cannot become a recipe gets "The app could not build a recipe from this text. Try again, or shorten the text to one recipe." with no technical detail.

**Independent Test**: Make the fake extractor return `InvalidOutput`; the sheet shows the new wording, the text stays, and the 422 body has an empty `detail`.

### Tests for User Story 3 ⚠️

- [X] T029 [P] [US3] Integration test in `api/tests/test_recipe_capture_integration.py`: `InvalidOutput` → 422 `ai_invalid_output` with `detail` "" (no fixed prose in the body)
- [X] T030 [P] [US3] vitest in `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx`: `ai_invalid_output` shows "The app could not build a recipe from this text. Try again, or shorten the text to one recipe." and the text is still in the box

### Implementation for User Story 3

- [X] T031 [US3] In `api/api/routes/recipe_capture.py`: for `InvalidOutput` return `detail` "" (was "The assistant's answer could not be read as a recipe.") ; code stays `ai_invalid_output`. Depends on T029
- [X] T032 [US3] In `ui/lib/i18n/capture.ts`: change `invalidOutput` to "The app could not build a recipe from this text. Try again, or shorten the text to one recipe." Depends on T030, T031

**Checkpoint**: US3 works alone: quickstart section 3 passes.

---

## Phase 6: User Story 4 - Messages are written in one language now and can be translated later (Priority: P2)

**Goal**: Every capture refusal message comes from one definition in `ui/lib/i18n/capture.ts`.

**Independent Test**: Search the capture UI and client for inline refusal strings; none are found outside the message file.

### Tests for User Story 4 ⚠️

- [X] T033 [P] [US4] Create `ui/lib/i18n/capture.test.ts`: for each code in contracts/capture-messages.md (`not_a_recipe` with each reason, `one_recipe_at_a_time`, `draft_incomplete`, `ingredient_line_problem`, `ai_invalid_output`, `text_too_long`, `ai_unavailable`, `ai_limit_reached`, `ai_misconfigured`, `kitchen_archived`, `notebook_not_found`), `messageForCode` returns a non-empty string that equals a value in `captureMessages`; no code returns the generic fallback

### Implementation for User Story 4

- [X] T034 [US4] Audit `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx` and `ui/lib/capture/captureClient.ts` for refusal strings written inline (the sheet's `too long` fallback at around line 113 is one); move each into `captureMessages` in `ui/lib/i18n/capture.ts` and import it from there. Depends on T032, T033
- [X] T035 [P] [US4] Confirm that `api/api/routes/recipe_capture.py` returns no user-facing English for the refusal cases other than the fixed `detail` tokens listed in contracts/capture-messages.md (`text_empty`, `text_too_long` keep their spec 016 detail). Change only what does not match. Depends on T031

**Checkpoint**: US4 done: one message file holds every capture refusal string.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Checks across all stories.

- [X] T036 Confirm `ui/app/api/notebooks/[notebookId]/captures/text/route.ts` passes `missing`, `line_problems`, `ingredient` and `detail` through unchanged (it forwards the body as is, so no edit is expected; record the result)
- [X] T037 Run `ruff check .` in `api/` and the api suite in Compose; fix any new failures introduced by this feature
- [X] T038 Run `cd ui && npm test && npm run lint && npm run typecheck`; fix failures introduced by this feature
- [ ] T039 Browser walkthrough per `specs/017-recipe-capture-error-messages/quickstart.md` sections 2 to 4, rows 1 to 11; record each result
- [ ] T040 [P] Check FR-007 in the browser: none of the refusal messages shows assistant prose, a code or a stack (quickstart row 10)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none; baseline first
- **Foundational (Phase 2)**: after Setup; blocks all stories
- **US1 (Phase 3)** and **US2 (Phase 4)**: both after Foundational. They share `messageForCode`, `captureClient.ts` and the route; run US1 before US2
- **US3 (Phase 5)**: after US2 (it shares `messageForCode` and the route)
- **US4 (Phase 6)**: after US1 to US3 (it moves strings they added)
- **Polish (Phase 7)**: after all stories

### Story-level notes

- US1 is the MVP: Phases 1 to 3 give the missing-part and ingredient messages.
- Within a story: tests first, then domain, then application, then route, then ui.

### Parallel Opportunities

- T002, T003, T004, T005 touch different parts of the same two files; run T002 and T003 in one author's pass, T004 and T005 in another (`recipe_draft.py` vs `recipe_extraction.py`)
- Test tasks marked [P] in each story can be written in parallel
- T022 (prompt) runs in parallel with T021 (adapter)
- T036 and T040 are read-only checks

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. T001 baseline
2. Phase 2 foundational (T002 to T005)
3. Phase 3 US1 (T006 to T017)
4. Stop: run quickstart rows 1, 2, 4, 5 with the text kept

### Incremental Delivery

1. MVP above
2. US2 (not a recipe, butter question, one recipe)
3. US3 (unreadable answer)
4. US4 (one message file) and Polish

---

## Notes

- [P] = different files, no dependency on an incomplete task
- Tests are required by constitution §6; they are not optional here
- Each task ID appears once; this file is the only task list for S-017
- Commit per phase (plan.md Phase breakdown), with the Co-Authored-By trailer
