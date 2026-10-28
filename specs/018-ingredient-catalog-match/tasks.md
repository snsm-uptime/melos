# Tasks: Match Captured Ingredient Names to the Notebook's Catalog

**Input**: Design documents from `specs/018-ingredient-catalog-match/`

**Prerequisites**: plan.md (required), spec.md (required, user stories), research.md, data-model.md, contracts/matching.md, quickstart.md

**Organization**: Tasks are grouped by user story (spec.md: US1 P1 labels, US2 P1 change list and undo, US3 P2 change match). Phase 2 holds the blocking work every story needs, including the prompt centralization requested for this feature.

**Tests**: The spec does not request TDD, but constitution §6 requires pure pytest for domain rules and the plan lists the test files, so test tasks are included. Each test task is marked with the file it creates or edits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 (story phases only)
- Paths are repository-relative. The api code runs from `api/`, so `domain/…` in code means `api/domain/…` on disk.

## Path Conventions

- api: `api/domain/`, `api/application/`, `api/adapters/llm/`, `api/api/routes/`, `api/tests/`
- ui: `ui/lib/capture/`, `ui/lib/i18n/`, `ui/components/RecipeDraft/`

---

## Phase 1: Setup

- [X] T001 Record the baseline: run `cd api && uv run pytest -q && uv run ruff check .` and `cd ui && npm test && npm run lint && npm run typecheck`. Save the pass counts in `specs/018-ingredient-catalog-match/notes.md` (create it) under "Baseline".

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: The prompt centralization, the matching rule and the extraction fields. No user story can finish without these.

**⚠️ CRITICAL**: No story phase starts until this phase is complete.

### Prompt centralization (requested in the tasks context)

Goal: every system prompt and prompt template lives in one folder as single-purpose markdown files, filled by text replacement. Pasted text is data: values must never be expanded a second time.

- [X] T002 Write a characterization test in `api/tests/test_prompt_characterization.py` that renders `system_instruction(vocabulary)` and `build_contents(text, names)` with a fixed vocabulary, a fixed text and fixed catalog names, and compares them to golden files. First generate the golden files from the current code, before any edit: write the outputs to `api/tests/fixtures/prompts/recipe_extraction_system.golden.txt` and `api/tests/fixtures/prompts/recipe_extraction_user.golden.txt`. Run the test and confirm it passes on the unchanged code.
- [X] T003 [P] Create the folder `api/adapters/llm/prompts/` with two single-purpose templates, copied verbatim from `api/adapters/llm/prompt.py`:
  - `api/adapters/llm/prompts/recipe_extraction_system.md`: the body of `system_instruction`, with the placeholders `{{TEXT_OPEN}}`, `{{TEXT_CLOSE}}`, `{{NAMES_OPEN}}`, `{{NAMES_CLOSE}}`, `{{MAIN_KEYS}}`, `{{VAGUE_PHRASES}}` in place of the f-string fields.
  - `api/adapters/llm/prompts/recipe_extraction_user.md`: the user turn of `build_contents`, with `{{TEXT_OPEN}}`, `{{TEXT_CLOSE}}`, `{{TEXT}}`, `{{NAMES_OPEN}}`, `{{NAMES_CLOSE}}`, `{{NAMES_JSON}}`.
- [X] T004 [P] Write `api/adapters/llm/prompts/README.md`: one line per template (its purpose, the model call that uses it, its placeholders), the `{{name}}` syntax, and the rule that a template holds one purpose and no code.
- [X] T005 Create `api/adapters/llm/prompt_templates.py` with:
  - `load_template(name: str) -> str` reading `prompts/<name>.md` next to the module (`Path(__file__).parent / "prompts"`).
  - `render(name: str, **values: str) -> str` that replaces every `{{key}}` in one pass using `re.sub` with a callback, so a value that contains `{{…}}` is inserted as text and never expanded again.
  - Raise `PromptTemplateError` (a subclass of `ValueError`) when a placeholder in the template has no value, or a value is given for a placeholder that does not exist.
- [X] T006 [P] Write `api/tests/test_prompt_templates.py`: a missing value raises `PromptTemplateError`; an unknown key raises it; a value containing `{{TEXT_CLOSE}}` is inserted unchanged; a template file that does not exist raises `FileNotFoundError`.
- [X] T007 Rewrite `api/adapters/llm/prompt.py` so `system_instruction` and `build_contents` call `render("recipe_extraction_system", …)` and `render("recipe_extraction_user", …)`. Keep the constants `TEXT_OPEN`, `TEXT_CLOSE`, `NAMES_OPEN`, `NAMES_CLOSE` and `VAGUE_PHRASES` in the module. Run `test_prompt_characterization.py`: it must pass unchanged.
- [X] T008 Confirm the folder ships in the image: `api/Dockerfile` copies `adapters` whole, so no Dockerfile edit is expected. Run `docker compose -f docker-compose.yml -f docker-compose.test.yml build api`, then `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm api ls adapters/llm/prompts`. Expect the two `.md` templates and `README.md`. If not, add `COPY` lines to `api/Dockerfile`.

### Matching rule (domain, pure)

- [X] T009 [P] Create `api/domain/ingredient_catalog.py` with `normalize_name(text: str) -> str` (trim, NFKD with combining marks removed, casefold, runs of spaces collapsed), `singular_forms(normalized: str) -> frozenset[str]` (English rules: "-ies"→"-y", "-oes"→"-o", "-ves"→"-f" for a short fixed list, "-s" dropped unless it ends in "ss", "us" or "is"; Spanish rules: "-es" dropped after a consonant, "-s" dropped after a vowel), and `match_line(text_name: str | None, name: str, proposal: str | None, catalog: Sequence[str]) -> LineMatch | None` per `contracts/matching.md` §4. Standard library only.
- [X] T010 [P] Write `api/tests/test_ingredient_catalog_domain.py` (pure pytest, no database) covering: "onions" matches "onion"; "tomatoes" matches "tomato"; "berries" matches "berry"; "leaves" matches "leaf"; "cebollas" matches "cebolla"; "limones" matches "limón" (accent-insensitive); "Onion" equals "onion" (case); two spaces equal one; a proposal not in the catalog gives no match; no proposal gives no match; two catalog entries that normalize the same: the proposal wins if it is one of them, else no match; an empty catalog gives no match. Each case is a named test.
- [X] T011 Add `LineMatch` (fields `kind: Literal["matched", "new"]`, `entry: str | None`) and `NameChange` (fields `line: int`, `from_name: str`, `to: str`) to `api/domain/ingredient_catalog.py`, per `data-model.md`. Note: the field is `from_name` in Python because `from` is a keyword; the JSON key stays `from`.

### Extraction fields and draft check

- [X] T012 Extend `IngredientLine` in `api/domain/recipe_draft.py` (around line 115) with `text_name: str | None = None` and `catalog_match: str | None = None`. Add `matches: tuple[LineMatch, ...] = ()` and `changes: tuple[NameChange, ...] = ()` to `DraftRecipe` (around line 127). Defaults keep every existing caller working.
- [X] T013 Replace `_normalized_name` in `api/domain/recipe_draft.py` (around line 477) inside `check_draft` (around line 566): for each line call `match_line` from T009 with the line's `text_name`, `name`, `catalog_match` and the catalog. A matched line's displayed `name` becomes the catalog entry. Build `matches` (one per line, in order) and `changes` (one per matched line whose `from_name` and `to` differ after case folding and space collapsing). Keep the existing unit and line checks unchanged.
- [X] T014 Update `api/tests/test_recipe_draft_domain.py`: the existing cases still pass; add cases for a matched line, a new line, a change listed, and no change for a case-only difference.
- [X] T015 Extend the extraction schema in `api/adapters/llm/gemini_extractor.py`: in the response schema (around lines 59–68) add `text_name` and `catalog_match` as optional strings (not in `required`); in `_LinePayload` (around line 87) add the two fields; in the mapping (around lines 137–147) pass them into `IngredientLine`.
- [X] T016 Update the system prompt in `api/adapters/llm/prompts/recipe_extraction_system.md`: describe `text_name` (the name as written in the pasted text, in the text's language) and `catalog_match` (one entry of the catalog block, spelled exactly as in that block, or null), per `contracts/matching.md` §1. Then regenerate `api/tests/fixtures/prompts/recipe_extraction_system.golden.txt` in the same commit, because this is a deliberate prompt change.
- [X] T017 Update `api/tests/test_gemini_extractor_adapter.py`: the schema lists the two optional fields and does not require them; a payload with them maps into `IngredientLine`; an older payload without them still validates.
- [X] T018 [P] Update `api/adapters/llm/fake_extractor.py` so its canned recipes carry `text_name` and `catalog_match` on some lines.
- [X] T019 Update `api/tests/test_recipe_extraction_application.py`: with the fake extractor, a draft returns `matches` and `changes` as specified in `contracts/matching.md`.

**Checkpoint**: The rule, the prompt folder and the extraction fields are tested. The user stories can start.

---

## Phase 3: User Story 1 - See which ingredients match the catalog (Priority: P1) 🎯 MVP

**Goal**: Each ingredient line in the draft shows "matched: <entry>" or "new ingredient".

**Independent Test**: Capture "2 large onions" and "200 g flour" into a notebook whose catalog has "onion". The draft labels onions "matched: onion" and flour "new ingredient" (spec US1 scenarios 1, 2 and 4).

### Implementation for User Story 1

- [X] T020 [US1] Add `match` to each line in `_draft_body` in `api/api/routes/recipe_capture.py` (around line 91) per `contracts/matching.md` §2: `{"kind": "matched", "entry": …}` or `{"kind": "new", "entry": null}`. Add `text_name` to each line.
- [X] T021 [US1] Add `changes` to the response in `api/api/routes/recipe_capture.py` (top level of `draft`), from `DraftRecipe.changes`.
- [X] T022 [US1] Extend `api/tests/test_recipe_capture_integration.py`: with a real catalog containing "onion", a capture of "2 large onions" and "200 g flour" returns the expected `match` values and one change `onions → onion`.
- [X] T023 [US1] Parse `match`, `text_name` and `changes` in `ui/lib/capture/captureClient.ts`. Extend `ui/lib/capture/captureClient.test.ts`.
- [X] T024 [US1] Add `match` and `undone` to `LineView` in `ui/lib/capture/captureStore.ts` (around line 31) and set them in `showDraft` (around line 124). Extend `ui/lib/capture/captureStore.test.ts`.
- [X] T025 [US1] Add English labels to `ui/lib/i18n/capture.ts`: "matched: {entry}" (as a function taking the entry name) and "new ingredient".
- [X] T026 [US1] Show the label under the name in `ui/components/RecipeDraft/IngredientLineRow.tsx` (the row already receives `line`). Keep the existing layout and classes.
- [X] T027 [US1] Extend `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: each line shows exactly one of the two labels.

**Checkpoint**: US1 works on its own. Run quickstart §4 steps 1–3.

---

## Phase 4: User Story 2 - See and undo each name change (Priority: P1)

**Goal**: The draft lists each name change ("onions → onion") and the member can undo one at a time.

**Independent Test**: The change list shows "onions → onion". Undo it: the line reads "new ingredient" with "onions", the change disappears, and other lines are unchanged (spec US2 scenarios 1, 2 and 4).

### Implementation for User Story 2

- [X] T028 [US2] In `ui/lib/capture/captureStore.ts`, derive the change list from the lines: a change exists for each line whose `match.kind` is "matched", that is not `undone`, and whose text name (`text_name`, or `name` when absent) and entry differ after case folding and space collapsing. Export it as `nameChanges(lines)`. Add tests in `captureStore.test.ts`.
- [X] T029 [US2] Add the action `undoChange(index: number)` to `ui/lib/capture/captureStore.ts`: it sets `undone` on that line, sets its label to "new ingredient" and its displayed name back to the name it had before the match. It changes no other line. Add tests.
- [X] T030 [US2] Create `ui/components/RecipeDraft/NameChangeList.tsx`: a list of "<from> → <to>" items, each with an Undo button calling `undoChange`. Render nothing when the list is empty. Use the existing button and text styles.
- [X] T031 [US2] Render `NameChangeList` above the ingredient table in `ui/components/RecipeDraft/RecipeDraftEditor.tsx`.
- [X] T032 [US2] Add to `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: the list shows the change; Undo removes it and reverts only that line.

**Checkpoint**: US1 and US2 work. Run quickstart §4 steps 3–4.

---

## Phase 5: User Story 3 - Change a match (Priority: P2)

**Goal**: The member can choose another catalog entry for a line, or "new ingredient".

**Independent Test**: With catalog entries "onion" and "spring onion", capture "2 spring onions". The draft matches "onion". Choose "spring onion" and the label reads "matched: spring onion" (spec US3 scenario 1).

### Implementation for User Story 3

- [X] T033 [US3] Amend `specs/018-ingredient-catalog-match/contracts/matching.md` §2: add a top-level `catalog` array of the capture notebook's catalog names, sorted. Explain it is needed for the match control (FR-005) and is not a new read route.
- [X] T034 [US3] Add `catalog` to the draft response in `api/api/routes/recipe_capture.py`, from the names the capture already read (`names_for_notebook`). Extend `api/tests/test_recipe_capture_integration.py`.
- [X] T035 [US3] Store the catalog in `captureStore.ts` (`catalog` on the draft view) and add `chooseMatch(index: number, choice: string)` where `choice` is a catalog entry or "new". Choosing an entry sets the line to matched with that entry; "new" sets it to new with its name. Add tests.
- [X] T036 [US3] In `ui/components/RecipeDraft/IngredientLineRow.tsx`, add a match control: a native `<select>` styled like the other fields in the row, listing "new ingredient" and every catalog entry, with the current choice selected. It calls `chooseMatch`.
- [X] T037 [US3] Add to `RecipeDraftEditor.test.tsx`: choosing an entry updates the label and the change list at once.

**Checkpoint**: All three stories work. Run quickstart §4 steps 5–6.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T038 Run the full checks: `cd api && uv run pytest -q && uv run ruff check .` and `cd ui && npm test && npm run lint && npm run typecheck`. Then run the Compose test overlay from quickstart §2. Record the counts in `notes.md`.
- [ ] T039 Add the plural, letter-case and spacing fixtures to `api/tests/fixtures/ai_eval/` (one text file per case, with the expected catalog entry in a header line). Run the manual evaluation (quickstart §5) and record the share in `notes.md`. Target: at least 90% (SC-004).
- [ ] T040 Run the browser walkthrough: quickstart §4, steps 1 to 6. Record the result in `notes.md`.
- [X] T041 Add the prompts folder to the project structure in `AGENTS.md` (under `api/adapters/`): `prompts/` holds the single-purpose prompt templates, see `api/adapters/llm/prompts/README.md`.
- [ ] T042 Update S-018 in `dev/docs/backlog.yaml` to `status: done` only after T038 to T040 pass, and add the verification counts to its `verification` field.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
  - Prompt centralization: T002 → (T003, T004 [P]) → T005 → T006 [P] → T007 → T008. T016 depends on T007.
  - Matching rule: T009 [P] and T010 [P] → T011 → T012 → T013 → T014.
  - Extraction: T015 depends on T012. T017 depends on T015 and T016. T018 [P] depends on T012. T019 depends on T013 and T018.
- **User stories (Phase 3–5)**: Depend on Phase 2. US2 depends on US1's client data (T023, T024). US3 depends on US2's store (T028, T029).
- **Polish (Final)**: Depends on the stories it verifies.

### Parallel opportunities

- T003 and T004 touch different files.
- T006 runs alongside T005 once the module exists.
- T009 and T010 (domain rule and its tests) are independent of the prompt work.
- T018 runs alongside T015 and T016.
- Within US1, T023 (api client) and T025 (labels) touch different files.

### Parallel example: Phase 2 start

```text
Task: "T003 Create the folder api/adapters/llm/prompts/ with recipe_extraction_system.md and recipe_extraction_user.md"
Task: "T004 Write api/adapters/llm/prompts/README.md"
Task: "T009 Create api/domain/ingredient_catalog.py"
Task: "T010 Write api/tests/test_ingredient_catalog_domain.py"
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 and Phase 2 (T001–T019).
2. Phase 3 (T020–T027).
3. Stop and check quickstart §4, steps 1 to 3.

### Incremental delivery

1. MVP above.
2. Add US2 (T028–T032): change list and undo.
3. Add US3 (T033–T037): change match.
4. Polish (T038–T042).

### Notes

- The prompt centralization is a refactor requested for this feature. It is not in spec.md. Its characterization test (T002) makes sure the current prompt output is unchanged before the prompt changes in T016.
- T016 is the only deliberate prompt change; its golden file is updated in the same commit.
- Changing the draft response's shape is a contract change (T033 amends the contract first).
