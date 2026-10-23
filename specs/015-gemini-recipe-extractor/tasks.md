# Tasks: Recipe Extraction Assistant Adapter

**Input**: Design documents from `/specs/015-gemini-recipe-extractor/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec's success criteria require automated tests without network access (SC-001, SC-003, SC-005, SC-006), and the plan names three test modules.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- All paths are relative to the repository root and use the `api/` service layout from plan.md

## Open spec items

All blocking items from the previous version are now decided in spec.md (Clarifications, session 2026-10-20):

- Vague amounts: the model decides, using the vague-phrase list in FR-006c.
- Multiple recipes: only one recipe per process, reason "Only one recipe at a time" (FR-002).
- Language: names and steps follow the pasted text's language now (Clarifications).
- Categories: from the controlled lists in categories.yaml and cuisine.yml. Zero to two main ingredients; zero to two cuisines that match (title coverage or steps rule), otherwise international (FR-006).
- Category order: main ingredients are a set capped at two. Cuisines are ranked by total matches, ties by title coverage then id. The tie-break question (CHK012) is closed.

Still open and not blocking: the final failure message (FR-015) is S-016 scope.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout and the one new dependency.

- [X] T001 Create the `api/domain/`, `api/application/` and `api/adapters/llm/` packages, each with an `__init__.py`, if they do not already exist
- [X] T002 Add the Gemini SDK from `api/` with `uv add google-genai` (never a hand edit of `uv.lock`) and state it in the PR description (constitution §2, AGENTS.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Result types, port, and settings that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Define the closed result set in `api/application/recipe_extraction.py` as frozen dataclasses: `Draft(recipe)`, `NotARecipe(reason)`, `Unavailable`, `LimitReached(retry_after_seconds: int | None)`, `InvalidOutput`, `AIProviderError`. No variant carries raw service text, the key, or a stack trace (FR-008, SC-006)
- [X] T004 [P] Define the draft value types in `api/domain/recipe_draft.py`: `DraftRecipe` (title, base_servings, servings_estimated, main_ingredients, cuisines, ingredient_lines, steps) and `IngredientLine` (name, vague, quantity, unit, size, note), with fields as listed in data-model.md. No rules yet
- [X] T005 Define the `RecipeExtractor` port in `api/application/recipe_extraction.py` with `extract(text, ingredient_names, timeout_s) -> ExtractionResult`, matching contracts/recipe-extraction-port.md
- [X] T006 Define the input-refusal error in `api/application/recipe_extraction.py` for empty or whitespace-only text and for text longer than 10,000 characters. It is raised before any call and is not a service failure (FR-012, data-model.md)
- [X] T007 Add settings in `api/api/settings.py`: `GEMINI_API_KEY` as a secret that may be empty and is never shown in repr or logs, `GEMINI_CHAT_MODEL`, `GEMINI_TEXT_TIMEOUT_S` (default 10), `GEMINI_IMAGE_TIMEOUT_S` (default 30). Model names and key come only from settings (FR-009, FR-013)
- [X] T008 [P] Add the new variables to `api/.env.example` with placeholder values only, never real values (constitution §4)

**Checkpoint**: Foundation ready. Result types, port and settings exist. User story work can begin.

---

## Phase 3: User Story 1 - Turn pasted text into a checked result (Priority: P1) 🎯 MVP

**Goal**: The use case returns a draft only after it passes the recipe rules, refuses empty or over-length input before any call, and evaluates identical concurrent texts only once.

**Independent Test**: Run the use case with `FakeRecipeExtractor` scripted to return the acceptance draft ("a pinch of salt", "2 large onions"). Expect a draft with no main ingredient and cuisine `international`, a vague salt line, and an onion line with quantity 2, unit `unit`, size `large`. The kitchen's data is unchanged. Two concurrent calls with the same text make one port call.

### Tests for User Story 1

- [X] T009 [P] [US1] Domain tests in `api/tests/test_recipe_draft_domain.py` for each FR-006 rule and FR-006a unit row (case-insensitive lookup, quantity never converted, unknown unit → invalid output, one-edit typo of a unit of 5+ characters matched, one-edit typo of more than one unit → invalid output, shorter units never fuzzy-matched). Cover: non-vague line has quantity > 0 and a unit; vague line has no quantity and no unit; size only when unit is `unit` and one of small, medium, large; base servings ≥ 1; names lower-case and singular; main ingredients at most 2 (zero allowed); cuisines at most 2, matched by title coverage (0.70) or more than 4 ingredients in the steps, ranked by total matches, one per tag, international when none matches; title 200 characters or fewer and not empty or whitespace-only; at least one step (SC-003)
- [X] T010 [P] [US1] Use-case tests in `api/tests/test_recipe_extraction_application.py` for the acceptance draft through `FakeRecipeExtractor`, for empty and whitespace-only text (no port call), for text of exactly 10,000 characters (accepted) and 10,001 characters (refused), and for the timeout passed through to the port (FR-012, FR-013, SC-007)
- [X] T011 [US1] Add concurrency tests to `api/tests/test_recipe_extraction_application.py`: two concurrent calls with the same trimmed text make one port call and get the same result; different texts make separate calls; the hash entry is removed when the call ends; nothing is written to storage (FR-016, FR-011)

### Implementation for User Story 1

- [X] T012 [US1] Implement the FR-006a unit lookup in `api/domain/recipe_draft.py` using the bilingual table in spec.md. Matching ignores case and surrounding spaces. A matched unit is replaced by its allowed unit. The quantity is never converted. An unknown unit, including conversion-only units, is invalid output. A unit with no exact match that is one edit away from a spelling of a unit of 5 or more characters is matched to it (e.g. "tablespon" → `tbsp`); one edit away from more than one allowed unit is invalid output
- [X] T013 [US1] Implement size removal in `api/domain/recipe_draft.py`. A size is removed when the unit is not `unit` or the size is not small, medium or large, and the line is kept (spec Edge Cases, FR-006)
- [X] T014 [US1] Implement the FR-006b draft rules in `api/domain/recipe_draft.py`: title 200 characters or fewer and not empty after trimming; at least one step; base servings default to 4 with `servings_estimated = True` when the text gives none; base servings at least 1
- [X] T015 [US1] Implement the category rules in `api/domain/recipe_draft.py`: load `categories.yaml` and `cuisine.yml`; keep main-ingredient keys from the vocabulary (at most 2, zero allowed); score every tag and variant in `cuisine.yml` with `categories.yaml#/matching/cuisine` (title coverage of content words at least 0.70, stopwords removed, or more than 4 ingredient ids in the steps; whole word, longest alias first; phrase exclusions per `matching/phrase_exclusions`; steps rule off below 5 recipe ingredient lines); rank by total matches, then title coverage, then body coverage (both tied nodes kept when all three are equal); one per tag; at most 2 cuisines; `international` when none matches (FR-006)
- [X] T016 [US1] Implement the line rules in `api/domain/recipe_draft.py`: a non-vague line has quantity > 0 and a unit; a vague line has no quantity and no unit and may carry `note` (FR-006, FR-006c)
- [X] T017 [US1] Implement the ingredient name rule in `api/domain/recipe_draft.py`: names are lower-case and singular, and an existing catalog spelling is used when it matches ignoring case (User Story 1, scenario 2)
- [X] T018 [US1] Implement the use case in `api/application/recipe_extraction.py`: refuse empty or over-length input before calling the port, call the port once, then apply the domain rules to any `Draft` and convert a rule break to `InvalidOutput`. Nothing is written to the database (FR-001, FR-011)
- [X] T019 [US1] Implement the in-flight map in `api/application/recipe_extraction.py`: key each call by the SHA-256 hash of its trimmed text; calls with the same hash share one in-progress port call; remove the entry when the call ends. The map is in memory only (FR-016)

**Checkpoint**: User Story 1 works through the fake port. The acceptance draft passes, broken drafts never leave the use case, and concurrent identical texts are evaluated once.

---

## Phase 4: User Story 2 - Report "not a recipe" as a normal answer (Priority: P2)

**Goal**: "Not a recipe", including text with two or more complete recipes, is returned as a normal result with the reason "Only one recipe at a time".

**Independent Test**: Script the fake port to return `NotARecipe` for the weather question and for a two-recipe text. Both come back unchanged, with no draft and no failure.

### Tests for User Story 2

- [X] T020 [P] [US2] Use-case tests in `api/tests/test_recipe_extraction_application.py`: `NotARecipe` passes through unchanged and is never converted to a failure; the multi-recipe reason is exactly "Only one recipe at a time" (FR-002)

### Implementation for User Story 2

- [X] T021 [US2] Handle `NotARecipe` in `api/application/recipe_extraction.py` as a normal result that skips the draft rules
- [X] T022 [US2] Add the `not_a_recipe` branch and `reason` field to the response schema in `api/adapters/llm/gemini_extractor.py`. Map it to `NotARecipe` (FR-002)

**Checkpoint**: User Stories 1 and 2 work through the fake port.

---

## Phase 5: User Story 3 - Classify every failure (Priority: P2)

**Goal**: Every failure maps to exactly one class (unavailable, limit reached, invalid output, AIProviderError), with no raw service text.

**Independent Test**: Use a stub SDK client that raises timeout, connection, 5xx, 429 with and without a hint, a malformed body, and a rule-breaking draft. Each produces its own class and no draft. An empty key produces `AIProviderError` with no SDK call.

### Tests for User Story 3

- [X] T023 [P] [US3] Adapter tests in `api/tests/test_gemini_extractor_adapter.py` with a stubbed SDK client, never the network: timeout, connection error and 5xx map to `Unavailable`; 429 maps to `LimitReached` with `retry_after_seconds` when a hint is given and `None` otherwise; malformed or schema-mismatched body maps to `InvalidOutput`; empty or missing key or model name maps to `AIProviderError` with no SDK call (FR-003 to FR-005, FR-009)
- [X] T024 [P] [US3] Use-case tests in `api/tests/test_recipe_extraction_application.py`: each failure class passes through unchanged, and a rule-breaking draft becomes `InvalidOutput` with no draft (User Story 3, scenario 5)

### Implementation for User Story 3

- [X] T025 [US3] Implement `GeminiRecipeExtractor` in `api/adapters/llm/gemini_extractor.py`: build the client from settings and pass the per-call timeout in milliseconds through `http_options`. Set `retry_options` to `attempts=1` on every call (research §2, §3)
- [X] T026 [US3] Map SDK and transport errors in `api/adapters/llm/gemini_extractor.py` to the result classes: timeout, connection error and `ServerError` to `Unavailable`; `ClientError` 429 to `LimitReached`; parse or schema failure to `InvalidOutput`; empty or missing key or model name to `AIProviderError`, checked before any SDK call. Never copy an exception message, status body, or key into a result (research §4)
- [X] T027 [US3] Add log hygiene in `api/adapters/llm/gemini_extractor.py`: log only a short error class and a request reference, never the key, the pasted text, or a service body (FR-014)

**Checkpoint**: User Stories 1, 2 and 3 work. Every failure class is reachable without network access.

---

## Phase 6: User Story 4 - Ignore instructions inside the pasted text (Priority: P2)

**Goal**: Pasted text is delimited as data, the prompt tells the model to ignore instructions inside it, and the prompt carries the model-side rules for vague amounts, word amounts, and category order.

**Independent Test**: Build the prompt for an injected text and check that the pasted text sits between delimiters, that the system part says the delimited text is data, and that catalog names are in their own delimited block. Check that the prompt asks for vague amounts by the FR-006c vague-phrase list, that "a dozen" becomes 12 `unit`, and that the category fields use only the reference lists.

### Tests for User Story 4

- [X] T028 [US4] Prompt tests in `api/tests/test_gemini_extractor_adapter.py`: the pasted text is inside `<<<RECIPE_TEXT` and `RECIPE_TEXT>>>`; the system part says delimited text is data and that instructions in it are ignored; catalog names are in a separate delimited block; the prompt asks for vague amounts using the FR-006c vague-phrase list, converts word amounts to a number and an allowed unit, and asks for the main ingredient from the reference list, at most 2 (FR-006c, FR-007, constitution §4)

### Implementation for User Story 4

- [X] T029 [US4] Implement `api/adapters/llm/prompt.py` with the delimiters above, the data-only instruction, the rule that the answer follows the recipe rules only, the vague-amount rule and word-amount rule from FR-006c, the category rule (main ingredient keys from the reference list, at most 2; the app scores cuisines, not the model), the one-recipe rule with reason "Only one recipe at a time", and the rule to write names and steps in the pasted text's language
- [X] T030 [US4] Wire the prompt from `api/adapters/llm/prompt.py` into the request built in `api/adapters/llm/gemini_extractor.py`
- [X] T031 [P] [US4] Create invented evaluation fixtures in `api/tests/fixtures/ai_eval/` for the salt and onion draft, the weather question, the two-recipe text, a single recipe with a "for the sauce" sub-section, a text with "a dozen" eggs, the "ignore previous instructions" text, and the "reply with the word OK only" line. Use no real personal data (quickstart §3)

**Checkpoint**: User Story 4 prompt rules are in place and covered by tests.

---

## Phase 7: User Story 5 - Test the capture feature without the network (Priority: P3)

**Goal**: A stand-in returns chosen results for every outcome, so S-016 can be built and tested with no network access.

**Independent Test**: Script `FakeRecipeExtractor` to return each of the six results in turn (a draft, a "not a recipe" answer, and the four failure classes). Each comes back unchanged, and no network call is made.

### Tests for User Story 5

- [X] T032 [US5] Tests in `api/tests/test_recipe_extraction_application.py`: the fake returns each of the six results unchanged, in order, and the same value every time when a single value is given (User Story 5, scenarios 1–2)

### Implementation for User Story 5

- [X] T033 [US5] Implement `FakeRecipeExtractor` in `api/adapters/llm/fake_extractor.py`: it implements the same port, returns scripted results in order or a fixed value, and makes no network call (FR-010, data-model.md stand-in)

**Checkpoint**: All five user stories work and are independently testable.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Verification, the timeout check, and the manual evaluation.

- [X] T034 Verify the SDK timeout exception type with a stalled stub in `api/tests/test_gemini_extractor_adapter.py`. Add an outer deadline only if the SDK timeout is not honoured (research §2, SC-005)
- [X] T035 Run the automated suite and lint in Compose, the canonical run in quickstart §1: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, then `cd api && uv run ruff check .` on the host
- [X] T036 [P] Check the log output of one failing call with an empty key: only a short error class and a request reference may appear (quickstart §5, FR-014)
- [X] T037 [P] Confirm `api/.env.example` lists the new variables with no real values, and that the PR description names `google-genai` as a new dependency (constitution §2)
- [X] T038 Manual AI evaluation with a real key, run on every attempt (quickstart §3, SC-002, SC-004), including the fixtures for "a dozen" and the "for the sauce" sub-section. This is manual and is not a merge gate for the automated suite

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational. US1 is the MVP. US2 and US3 extend US1's use case. US4 touches the adapter's prompt. US5 is independent of the adapter
- **Polish (Phase N)**: Depends on the user stories it verifies

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational. Needs no other story
- **US2 (P2)**: Starts after US1's use case (T018), because it extends it
- **US3 (P2)**: Starts after US1's use case (T018). Its adapter work shares `gemini_extractor.py` with US2 and US4, so do those tasks in order
- **US4 (P2)**: Starts after Foundational. The prompt is built into the adapter from US3
- **US5 (P3)**: Starts after Foundational. It is independent of the adapter

### Within Each User Story

- Tests are written first and must fail before implementation
- Domain rules before the use case
- The use case before the adapter

### Parallel Opportunities

- T004 and T008 run in parallel with the other Foundational tasks, because they touch different files
- T009 and T010 run in parallel (different test files, different rules)
- T020, T023, T024 and T031 run in parallel within their phases
- T036 and T037 run in parallel in Polish

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 together:
Task: "Domain tests in api/tests/test_recipe_draft_domain.py"
Task: "Use-case tests in api/tests/test_recipe_extraction_application.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run the US1 tests and the acceptance draft through the fake port
5. Stop here if the MVP is ready for review

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test independently → MVP
3. US2 and US3 → test independently
4. US4 → prompt rules in place
5. US5 → stand-in for S-016
6. Polish → full suite, log hygiene, manual evaluation

---

## Notes

- [P] tasks touch different files and have no dependencies on incomplete tasks
- [Story] labels map each task to a user story for traceability
- FR-015 (the final failure message) is S-016 scope and has no task here
- Verify tests fail before implementing each story

## Phase 8: Convergence

- [X] T039 Make a cuisine match on at least 4 ingredient ids found in the steps, per the amended FR-006 (session 2026-10-22): `min_ingredients` is 4 in both copies of `categories.yaml`, `score_cuisines` in `api/domain/recipe_draft.py` compares with `>=`, and boundary tests at 3 and 4 matched ingredients are in `api/tests/test_recipe_draft_domain.py` per FR-006 (contradicts)
- [ ] T040 (deferred until after MVP; the domain keeps lower-case only and singular stays with the prompt) Enforce the lower-case singular ingredient-name rule in `_check_name` in `api/domain/recipe_draft.py` so a plural name is invalid output, with tests in `api/tests/test_recipe_draft_domain.py`; if no reliable singular check exists without a word list, report that instead of guessing per FR-006 (partial)
- [X] T041 Add a test in `api/tests/test_recipe_draft_domain.py` that fails when `api/domain/categories.yaml` or `api/domain/cuisine.yml` differs from `dev/docs/categories.yaml` or `dev/docs/cuisine.yml`, skipped when `dev/docs/` is absent (the container image does not include it), and sync any drift it finds per the category-source assumption in spec.md (partial)
- [X] T042 Return None from `_retry_after_seconds` in `api/adapters/llm/gemini_extractor.py` when the rounded wait hint is zero, so a positive hint under half a second is null, and add a test in `api/tests/test_gemini_extractor_adapter.py` per FR-004 (partial)
- [X] T043 Use the root `.env.example` for the Gemini variables instead of creating `api/.env.example`: `GEMINI_TEXT_TIMEOUT_S` and `GEMINI_IMAGE_TIMEOUT_S` are there with placeholder values, and Compose loads that file; plan.md's `api/.env.example` path is superseded (missing)
