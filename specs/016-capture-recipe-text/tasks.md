# Tasks: Capture a Recipe from Pasted Text

**Input**: Design documents from `/specs/016-capture-recipe-text/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/capture-api.md, contracts/capture-ui.md, quickstart.md. Spec 056-notebooks must be merged first (T001).

**Tests**: Included. The constitution (§6) requires domain tests, use-case tests against fake ports, Compose integration tests and vitest for components. SC-005 and SC-008 are checked by automated tests. No test needs the network: the Compose overlay replaces the extractor with `FakeRecipeExtractor`.

**Organization**: Tasks are grouped by user story (US1 to US4 from spec.md). Phase 2 holds what every story needs: the S-015 touch-ups, the capture use case, the route, the BFF proxy, the store and the shared component changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4, from spec.md
- All paths are relative to the repository root.

## Notes that apply to every task

- No new library in `api/` or `ui/`. Do not edit `uv.lock` or `package-lock.json` by hand.
- Add libraries only with `uv add` or `npm install` (none planned).
- English for code, comments and UI text (AGENTS.md). Internationalization is a later story after MVP (FR-034); keep every message in `ui/lib/i18n/capture.ts` so that story can add Spanish.
- Use `uv run` for every Python command and `npm` for every Node command.
- The draft is never saved (FR-019). No task in this feature writes a recipe, ingredient, category, source, step or cart row.
- Messages to members never contain raw service text, keys or traces (FR-029).

---

## Phase 1: Setup (shared checks and configuration)

- [X] T001 Confirm spec 056 is in place: `api/domain/errors.py` defines `NotebookNotFoundError`, `KitchenArchivedError` and `NotebookChoiceRequiredError`; `api/api/routes/notebooks.py` serves `GET /notebooks`, `GET /notebooks/default`, `GET /notebooks/kitchens/{kitchen_id}` and `GET /notebooks/{notebook_id}`; `cd api && uv run alembic heads` shows `0003_notebooks_ingredients`. Stop and report if any is missing.
- [X] T002 [P] Add `RECIPE_TEXT_MAX_CHARS` (integer, default `5000`, applied after trimming) to the settings class in `api/api/settings.py`, and to `.env.example` with a comment and no real value.

---

## Phase 2: Foundational (blocking prerequisites for every story)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### S-015 touch-ups (domain, adapter, prompt)

- [X] T003 [P] Add `preparation: str | None` to `IngredientLine` in `api/domain/recipe_draft.py`. Trimmed; a blank value becomes `None`. It is never part of `name` (data-model: `IngredientLine`; FR-010).
- [X] T004 [P] Add domain tests in `api/tests/test_recipe_draft_domain.py`: `preparation` is kept, trimmed, and a blank string becomes `None`.
- [X] T005 Map the new field in `api/adapters/llm/gemini_extractor.py`: `_LinePayload.preparation` → `IngredientLine.preparation`.
- [X] T006 Add the preparation rule to the ingredient fields in `api/adapters/llm/prompt.py`: how the ingredient is cut or prepared goes in `preparation` ("chopped") and never in `name` (FR-010). Quote the pasted text inside the existing delimiters (constitution §4).
- [X] T007 [P] Add an adapter test in `api/tests/test_gemini_extractor_adapter.py`: a line with a preparation maps to `IngredientLine.preparation`.
- [X] T008 Make the too-long refusal in `api/application/recipe_extraction.py` use the configured limit: "That text is too long. Paste up to {limit} characters." The limit comes from `RECIPE_TEXT_MAX_CHARS` (FR-002). The spec 015 10,000-character refusal stays as the upper bound.

### Domain rules for this feature

- [X] T009 [P] Add the `capture_recipe` action to `api/domain/kitchen_access.py`: allowed for any member (owner or member role). A non-member is denied as `NotebookNotFoundError` at the route, so the kitchen's existence is not revealed (FR-022, FR-030).
- [X] T010 [P] Create `api/domain/labels.py` with `pick_label(labels: dict[str, str], language: str) -> str`: the label in `language`, otherwise the other language. No text detection (research R4). Add `api/tests/test_labels_domain.py`: the member's language wins, and a missing label falls back to the other language.

### Application: the capture use case and the vocabulary

- [X] T011 Create `api/application/recipe_capture.py` with `CaptureRecipeText.execute(actor_user_id, notebook_id, text, language)`. Order: (1) text is empty or longer than `RECIPE_TEXT_MAX_CHARS` after trimming → refuse, with no read and no extractor call; (2) load the notebook through the spec 056 `NotebookRepository.get`; (3) personal notebook: the caller must hold a `notebook_membership` row, otherwise `NotebookNotFoundError`; kitchen notebook: the caller must be a kitchen member, otherwise `NotebookNotFoundError`; (4) kitchen notebook of an archived kitchen → `KitchenArchivedError` (after membership); (5) read the catalog with `IngredientCatalog.names_for_notebook`; (6) call the S-015 `RecipeExtraction` use case with the text and the catalog; (7) return the S-015 result unchanged, wrapped as `CapturedDraft` (with `notebook`, `language`) on success.
- [X] T012 [P] Create `api/tests/test_recipe_capture_application.py` with fake ports (fake notebook repository, fake catalog, `FakeRecipeExtractor`). Prove: a capture sends only its notebook's catalog; a missing notebook, another member's personal notebook, and a kitchen notebook of a non-member each raise `NotebookNotFoundError` before any catalog read or extractor call; an archived kitchen raises `KitchenArchivedError` with zero extractor calls; a too-long text is refused with zero extractor calls; each S-015 result passes through unchanged.
- [X] T013 [P] Create `api/application/recipe_vocabulary.py`: the vocabulary answer (units, sizes, the two limits, the main ingredient and cuisine lists with `{en, es}` labels and tags, the paste limit) built from the spec 015 controlled lists `api/domain/categories.yaml` and `api/domain/cuisine.yml`. Include every cuisine variant and tag that `score_cuisines` (`api/domain/recipe_draft.py`) can assign, plus `international`.

### API: schemas, route, dependencies

- [X] T014 Create `api/api/schemas/recipe_capture.py` with the request model (`text: str`) and the response models for the 200 draft answer and the vocabulary answer, matching `contracts/capture-api.md`.
- [X] T015 Create `api/api/routes/recipe_capture.py` with `POST /notebooks/{notebook_id}/captures/text` and `GET /recipe-vocabulary`. Map results exactly as the contract's error table: `NotebookNotFoundError` → 404 `notebook_not_found`; `KitchenArchivedError` → 409 `kitchen_archived`; `RecipeTextRefusedError` → 422 `text_empty` / `text_too_long`; `NotARecipe` → 422 `not_a_recipe` (reason at most 120 characters) or `one_recipe_at_a_time`; `InvalidOutput` → 422 `ai_invalid_output`; `LimitReached` → 429 `ai_limit_reached` with `Retry-After` when hinted; `Unavailable` → 503 `ai_unavailable`; `AIProviderError` → 503 `ai_misconfigured`. Every body is `{ "detail": "<plain sentence>", "code": "<code>" }` and never carries service text (FR-029). Read the member's language from `users.language` through `effective_language`.
- [X] T016 Register the router in `api/api/app.py` with `dependencies=[Depends(require_user_alias)]`, next to the notebooks router.
- [X] T017 Add dependencies in `api/api/deps.py`: `get_recipe_extraction`, a singleton on `app.state` (like `get_rate_limiter`), and `get_vocabulary`. Tests replace the extractor with `app.dependency_overrides[get_recipe_extraction]`.

### UI: shared component changes, store, client, BFF

- [X] T018 [P] Make `confirmLabel`, `cancelLabel` and `onConfirm` optional in `ui/components/ActionDialog/ActionDialog.tsx`. When both labels are absent, do not render the footer and move focus to the first focusable child. Existing callers pass all three and render as before. Update `ui/components/ActionDialog/` tests.
- [X] T019 [P] Create `ui/lib/i18n/capture.ts` with every English message and label from `contracts/capture-api.md` ("ui message per code") and `contracts/capture-ui.md`, quoted exactly. Strings are English for now (FR-034).
- [X] T020 Create `ui/lib/capture/captureStore.ts`, a module store read with `useSyncExternalStore` (same pattern as `membershipKitchensStore.ts`). Fields as in data-model "Client-only state": `notebook`, `text`, `sheetOpen`, `phase`, `message`, `draft`, `originalHash`, `language`. `edited` is derived. Reload clears the store.
- [X] T021 [P] Create `ui/lib/capture/draftRules.ts` with the FR-013 checks: a measured line has `quantity > 0` and a unit from `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`; a vague line has no quantity and no unit; `size` only when `unit === "unit"`, one of small, medium, large; base servings an integer of at least 1; title 1–200 characters after trimming; at least one non-empty step; at most 2 main ingredients and 2 cuisines. Add `ui/lib/capture/draftRules.test.ts`.
- [X] T022 [P] Create `ui/lib/capture/draftHash.ts`: a content hash of the title, servings, categories, ingredient lines and steps, in order, that decides `edited` (FR-032: changing a value and changing it back is not an edit). Add `ui/lib/capture/draftHash.test.ts`.
- [X] T023 Create `ui/lib/capture/captureClient.ts`: POST `/api/notebooks/{notebookId}/captures/text` and GET `/api/recipe-vocabulary`; map each response `code` to a key in `ui/lib/i18n/capture.ts`; treat 502 like `ai_unavailable`; any unknown code shows the `ai_unavailable` message. Add `ui/lib/capture/captureClient.test.ts`.
- [X] T024 Create the BFF route `ui/app/api/notebooks/[notebookId]/captures/text/route.ts` (POST): forward the `cookie` header and `Content-Type`; return status, body and `Retry-After` as received; abort after `(GEMINI_TEXT_TIMEOUT_S || 10) + 2` seconds and answer 503 `{ "code": "ai_unavailable" }`; other upstream failures answer 502 `bad_gateway`; invalid JSON answers 400 `invalid_body` without calling the api.
- [X] T025 Create the BFF route `ui/app/api/recipe-vocabulary/route.ts` (GET), forwarding to `/recipe-vocabulary` with the same status handling.
- [X] T026 [P] Add BFF tests for both routes to `ui/app/api/notebooks.bff.test.ts`: abort after the deadline → 503 `ai_unavailable`; invalid JSON → 400 `invalid_body`; upstream failure → 502 `bad_gateway`; status and `Retry-After` pass through unchanged.

### API integration foundation

- [X] T027 Create `api/tests/test_recipe_capture_integration.py` (Compose, real Postgres, `FakeRecipeExtractor` through the dependency override). Start with the access and row-count checks: a non-member and a missing notebook get the same 404 body; `ingredient` row count is unchanged after every capture (SC-005, SC-008).

**Checkpoint**: Foundation ready. The use case, route, BFF, store and shared dialog exist, so the user stories can start.

---

## Phase 3: User Story 1 - Turn pasted recipe text into a reviewable draft (Priority: P1) 🎯 MVP

**Goal**: A member opens their Notebook page or a kitchen's Notebook tab, taps the plus, pastes a recipe, submits, and gets a draft review page where they can edit and go back. Nothing is saved.

**Independent Test**: Sign in, open the Notebook tab, paste "a pinch of salt" and "2 large onions", submit, and check the draft (quickstart section 3, steps 1–7). Nothing in the notebook changes.

### Tests for User Story 1

- [X] T028 [P] [US1] Add integration tests to `api/tests/test_recipe_capture_integration.py`: a personal notebook and a kitchen notebook each give a 200 draft with `notebook.kind` `"personal"` or `"kitchen"` and the fake extractor's draft; the response contains a `language` field from the member's account setting.
- [X] T029 [P] [US1] Add a component test `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.test.tsx`: the placeholder is a button named "Add a recipe" with a centred plus icon; activating it opens the options dialog.
- [X] T030 [P] [US1] Add a component test `ui/components/AddRecipeCallToAction/AddRecipeOptionsDialog.test.tsx`: no confirm or cancel buttons; order URL (aria-disabled, "Not available yet"), Picture (aria-disabled, "Coming soon"), Text; Escape and a backdrop click close it and change nothing.
- [X] T031 [P] [US1] Add a component test `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: title, servings with the "estimated" badge, chips in the account language, the ingredient rows, steps, the "For: <notebook name>" line, Back, and no Save control.

### Implementation for User Story 1

- [ ] T032 [P] [US1] Create the icon `ui/app/icons/BookIcon.tsx` following `ui/app/icons/README.md`, and export it from the icon index.
- [ ] T033 [US1] Add the Notebook tab to `ui/components/AppShell.tsx` after Home, with `{ key: "notebook", href: "/notebook", Icon: BookIcon }` and label "Notebook". In `ui/lib/appChrome.ts`, add `/notebook` to `APP_CHROME_PREFIXES` and map `/notebook` and `/notebook/*` to `"notebook"` in `tabKeyFromPath`. The kitchen's Notebook route stays under `"home"`. Update `ui/lib/appChrome.test.ts` and `ui/components/AppShell.test.tsx`.
- [X] T034 [P] [US1] Create `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx` (rounded placeholder rectangle, centred `PlusIcon`, accessible name "Add a recipe"; opens the options dialog; reopens the sheet from the store when `sheetOpen` is set for the same notebook) and `ui/components/AddRecipeCallToAction/index.ts`.
- [X] T035 [P] [US1] Create `ui/components/AddRecipeCallToAction/AddRecipeOptionsDialog.tsx`: `ActionDialog` without footer buttons, with the three options in order and dividers between them. URL and Picture are `aria-disabled`; Text opens the text sheet.
- [X] T036 [US1] Create `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx` on the existing `ui/app/kitchens/Sheet.tsx`: a notebook picker (outside a kitchen, the personal notebooks from `GET /api/notebooks` with the default preselected, hidden when there is one; inside a kitchen, the kitchen's notebooks from `GET /api/notebooks/kitchens/{id}`), the title is the chosen notebook's name, a "Recipe text" paste input, a live counter once the text passes 90% of the limit, submit disabled per FR-002, a progress state "Reading your recipe…" with the input read-only during submit (FR-004), and a second submit blocked while one is running. On 200, store the draft and navigate to the notebook's draft route.
- [X] T037 [US1] Create `ui/app/notebook/page.tsx` (server component): sign-in and alias checks as in `ui/app/kitchens/[kitchenId]/page.tsx`; read the default notebook through `GET /api/notebooks/default` (spec 056) with `ui/lib/notebooksClient.ts`; header "Notebook"; render `AddRecipeCallToAction`; no recipe list (S-021).
- [X] T038 [US1] Create `ui/app/notebook/draft/page.tsx`: when the store has no draft, redirect to `/notebook`; otherwise render `RecipeDraftEditor` as a full-screen page with the chrome header "Review recipe" and a Back control.
- [ ] T039 [P] [US1] Create the kitchen tabs `ui/app/kitchens/KitchenSectionTabs.tsx` (Members | Notebook links). Members is the default, so existing links keep working.
- [ ] T040 [US1] Edit `ui/app/kitchens/[kitchenId]/page.tsx` to render `KitchenSectionTabs` under the header, with Members active. Existing Members content is unchanged.
- [X] T041 [US1] Create `ui/app/kitchens/[kitchenId]/notebook/page.tsx`: header is the kitchen name; read the kitchen's notebooks from `GET /api/notebooks/kitchens/[kitchenId]` (the first open creates the notebook, spec 056 FR-008a) and use the first one; `KitchenSectionTabs` with Notebook active; `AddRecipeCallToAction` for that notebook. A non-member sees the existing not-found view. No recipe list (S-047).
- [X] T042 [US1] Create `ui/app/kitchens/[kitchenId]/notebook/draft/page.tsx`: as T038, redirecting to `/kitchens/[kitchenId]/notebook` when there is no draft or when the stored notebook id is not that kitchen's notebook.
- [X] T043 [P] [US1] Create `ui/components/RecipeDraft/RecipeDraftEditor.tsx` (the draft page body): notebook line "For: <name>" (FR-001a); title (error "Add a title." / "Keep the title under 200 characters."); servings with the "estimated" badge (error "Servings must be a whole number of at least 1."); categories from `CategoryChips`; the ingredient table; the steps list; Back returns to the Notebook page with the sheet open and the text unchanged (FR-031). No Save control (S-020).
- [X] T044 [P] [US1] Create `ui/components/RecipeDraft/CategoryChips.tsx`: two groups (main ingredients, cuisines) with labels from `pick_label` in the account language; a variant chip reads "Variant · Tag"; add pickers (`ui/components/ChipPicker`) fed by `GET /api/recipe-vocabulary`, hidden at two; a remove control on each chip.
- [X] T045 [P] [US1] Create `ui/components/RecipeDraft/IngredientLineRow.tsx`: name, quantity, unit select (allowed set only), size select (only when unit is `unit`), preparation, note, and a "vague amount" toggle that clears quantity and unit. Rows can be added, removed, moved up and moved down (FR-012). Line errors appear under the row: "Add an amount and a unit, or mark it as vague." / "A vague amount has no number or unit." / "Size is only for counted items."
- [X] T046 [US1] Create `ui/components/RecipeDraft/index.ts` and wire the steps list (ordered, add, remove, move up and down; error "Add at least one step.") inside `RecipeDraftEditor.tsx`.
- [X] T047 [US1] Create `ui/components/RecipeDraft/LeaveDraftGuard.tsx`: while `edited`, listen for clicks on same-origin `<a>` elements in the capture phase and show an `ActionDialog` titled "Leave without saving?" with the body "Your changes to this draft will be lost.", buttons "Stay" (keeps the draft) and "Leave" (clears the store and follows the link). Register `beforeunload` while edited (FR-032). Back and Discard bypass it.
- [X] T048 [US1] Mount `LeaveDraftGuard` in `ui/app/notebook/draft/page.tsx` and `ui/app/kitchens/[kitchenId]/notebook/draft/page.tsx`.

**Checkpoint**: US1 works end to end on both Notebook pages: capture, draft, edit, Back, leave guard. Run quickstart section 3, steps 1–9 and 11.

---

## Phase 4: User Story 2 - Reject input that is not a recipe (Priority: P2)

**Goal**: Text that is not a recipe, or that holds two recipes, shows a clear message, keeps the text, and creates nothing.

**Independent Test**: Paste "What's the weather tomorrow?" and submit: "That doesn't look like a recipe." appears with a reason and the text stays. Paste two recipes: "Upload only one recipe at a time" appears.

### Tests for User Story 2

- [X] T049 [P] [US2] Add integration tests to `api/tests/test_recipe_capture_integration.py`: `NotARecipe` gives 422 `not_a_recipe` with `reason` at most 120 characters; the one-recipe reason gives 422 `one_recipe_at_a_time`; no row is created in any table (SC-003, SC-005).
- [X] T050 [P] [US2] Add a component test `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx` (new file, used by US2–US4): "That doesn't look like a recipe." followed by the reason is shown; "Upload only one recipe at a time" is shown; the text stays in the input and can be edited and submitted again.

### Implementation for User Story 2

- [X] T051 [US2] Confirm the mapping in `ui/lib/capture/captureClient.ts` (T023) returns `not_a_recipe` with its `reason` and `one_recipe_at_a_time` as separate keys; the sheet shows the reason in role `alert`.

**Checkpoint**: US2 works on its own with the fake extractor scripted to return `NotARecipe`.

---

## Phase 5: User Story 3 - Keep the pasted text when the assistant fails (Priority: P2)

**Goal**: Timeouts, usage limits, unreadable results and a missing setup show the matching message, keep the text, and let the member retry.

**Independent Test**: Make the assistant fail in each way (quickstart "Failure messages"). Each case shows its message and the text stays in the box.

### Tests for User Story 3

- [X] T052 [P] [US3] Add integration tests to `api/tests/test_recipe_capture_integration.py`: `Unavailable` → 503 `ai_unavailable`; `LimitReached` → 429 `ai_limit_reached` with `Retry-After` when a hint is set; `InvalidOutput` → 422 `ai_invalid_output`; `AIProviderError` → 503 `ai_misconfigured`. No `detail` contains service text, a key or a trace (FR-029).
- [X] T053 [P] [US3] Add a unit test `ui/lib/capture/captureClient.test.ts` (extend T023): each code maps to its message key; 502 maps like `ai_unavailable`; an unknown code shows the `ai_unavailable` message.
- [X] T054 [P] [US3] Add component tests to `ui/components/AddRecipeCallToAction/TextCaptureSheet.test.tsx`: each failure message appears in role `alert`; the text is unchanged; submitting again sends a new request (one attempt per submission, FR-025).

### Implementation for User Story 3

- [X] T055 [US3] Wire the failure messages in `TextCaptureSheet.tsx`: on any non-200, show the message for its `code` and leave the text editable (FR-016, FR-017, FR-018, FR-028).

**Checkpoint**: US3 works on its own with the fake extractor set to fail in each way.

---

## Phase 6: User Story 4 - Discard a draft (Priority: P3)

**Goal**: The member discards a draft. The draft is gone, the sheet returns empty, and nothing is saved.

**Independent Test**: Create a draft, choose Discard, and check that the notebook is unchanged and the text sheet is empty.

### Tests for User Story 4

- [X] T056 [P] [US4] Add a store test `ui/lib/capture/captureStore.test.ts`: Discard clears the draft and the text; Back keeps the text and drops the draft; reload empties the store.
- [X] T057 [P] [US4] Add to `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: Discard is enabled even when the draft has validation errors, and returns to the Notebook page with the sheet open and empty.

### Implementation for User Story 4

- [X] T058 [US4] Add the Discard control to `ui/components/RecipeDraft/RecipeDraftEditor.tsx`: always enabled (FR-020); clears the draft and the text in the store, then navigates to the Notebook page with the sheet open and empty (no leave prompt).

**Checkpoint**: US4 works on its own: create a draft, Discard, notebook unchanged.

---

## Final Phase: Polish & cross-cutting concerns

- [X] T059 Hide the add-recipe call to action on an archived kitchen's Notebook tab in `ui/app/kitchens/[kitchenId]/notebook/page.tsx` (FR-033): the page reads `kitchen_is_archived` from the notebook answer and renders no `AddRecipeCallToAction`. Add a vitest case in `ui/app/kitchens/` tests.
- [X] T060 Add a logging test in `api/tests/test_recipe_capture_application.py` (`caplog`): a capture logs the text length and the outcome, and never the pasted text (constitution §4).
- [X] T061 [P] Run the automated checks: `cd api && uv run ruff check .`, `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, `cd ui && npm test && npm run lint && npm run typecheck`.
- [ ] T062 Run the browser walkthrough in quickstart.md section 3 (steps 1–15), including the Spanish-account check for chip labels.
- [ ] T063 Run the data-unchanged check in quickstart.md section 5: `ingredient` and `notebook` row counts are unchanged by captures, edits and discards (SC-005).
- [ ] T064 Manual AI evaluation (not CI, constitution §6) with a real key: each file in `api/tests/fixtures/ai_eval/` through the ui 10 times, compare with the expected draft (SC-002, SC-006: at least 90% correct title, servings and lines). Check `injected_instruction.txt` does not change the draft (FR-021). Record results in `dev/memory/` per AGENTS.md.
- [ ] T065 Note for later: internationalization (Spanish for every message, chosen by `users.language`) is a story after MVP, not in this feature. Add it to `dev/docs/backlog.yaml` when MVP is done.

---

## Dependencies & execution order

- **Phase 1 (T001–T002)** → **Phase 2 (T003–T027)** → user stories.
- **Phase 2 blocks every story.** Within it, the S-015 touch-ups (T003–T008), the domain rules (T009–T010), the use case (T011–T013), the API (T014–T017), and the UI foundation (T018–T026) can run in parallel where marked [P].
- **US1 (P1)** is the MVP. US2 and US3 only add tests and messages on top of US1's sheet; they can follow US1 in any order. US4 depends on US1's draft page.
- **Polish** waits for every story.

### Within User Story 1

- Tests (T028–T031) are written first and fail until the components exist.
- T032 and T034–T035 are independent; T036 needs T034 and the store (T020); T037–T042 need the components; T043–T045 are the draft page body; T047 comes after T043.

## Parallel execution examples

**Phase 2, S-015 and domain**:
```text
T003 (IngredientLine.preparation)  |  T009 (capture_recipe action)  |  T010 (pick_label)
T004 (domain test)                 |  T012 (application test)       |  T013 (vocabulary)
```

**Phase 2, UI foundation**:
```text
T018 (ActionDialog optional)  |  T019 (i18n strings)  |  T021 (draftRules)  |  T022 (draftHash)
```

**User Story 1, components**:
```text
T032 (BookIcon)  |  T034 (CTA)  |  T035 (options dialog)  |  T044 (CategoryChips)  |  T045 (IngredientLineRow)
```

## Implementation strategy

1. **MVP first**: Phase 1, Phase 2, Phase 3 (US1). Stop there and check quickstart sections 1–3 with the fake extractor.
2. **Incremental**: add US2 (not-a-recipe), then US3 (failure messages), then US4 (discard). Each story is checked on its own.
3. **Then polish**: archived-kitchen rule, logging, automated checks, walkthrough, data-unchanged check, manual AI evaluation.

## Open items for review (not tasks)

- **AGENTS.md "English for the UI"** matches the MVP decision (FR-034). Internationalization is T065.
- **`ui/lib/capture/`** is a new folder under `ui/lib/`, flagged in plan.md for review (AGENTS.md: do not add folders without asking).
- **Spec 056 status**: the backlog marks S-056 `in_progress`. T001 must pass before any task here.


---

## Implementation notes (2026-10-25)

Marked `[X]`: the work is in the tree and checked by the automated suites (API in Compose, UI in vitest, lint and type check). Left open, with the reason:

- **T032, T033, T039, T040 (not needed).** The Notebook tab already exists from spec 060 at `/notebooks`, with its icon, and the kitchen's notebooks are a section (`KitchenNotebooksSection`), not a tab. The capture reuses both. The tab and kitchen section changes are in `ui/app/notebooks/NotebookTabScreen.tsx` and `ui/app/kitchens/KitchenNotebooksSection.tsx`.
- **T037, T041, T038/T042 (routes changed).** The member's capture button is on `/notebooks`. The kitchen's is in the notebooks section. One draft route, `/notebooks/draft`, serves both, and Back and Discard return to the page that opened the capture.
- **T008, T009 (no change needed).** The capture use case enforces the configured limit (`RECIPE_TEXT_MAX_CHARS`) before the S-015 use case runs; the S-015 10,000-character bound stays. Access uses spec 056's `notebook_view`, so no separate `capture_recipe` action was added.
- **T044 (native select).** The category editor adds values with a native select instead of `ChipPicker`. It is simpler and gives the same choices.
- **T001 (migration head).** Spec 056's head is `0004_drop_kitchen_hide`, not `0003`. T001 checked it.
- **T062 (browser walkthrough) and T064 (manual AI evaluation).** Not run here. The walkthrough needs a browser and two signed-in accounts, and the AI evaluation needs a real Gemini key.
- **T063 (data-unchanged check).** The integration tests check the `ingredient` and `notebook` row counts after each capture. The manual `psql` check was not run.
- **T065.** The i18n story is for after MVP. Add it to `dev/docs/backlog.yaml` when MVP is done.

Changes to other specs (done in this feature's work, for review):
- **Spec 056 route guard** (`api/tests/test_notebook_integration.py`): the GET-only check now excludes the capture route, which is the one POST under `/notebooks`, and asserts it separately.
- **`ui/lib/capture/`** is a new folder under `ui/lib/`, as flagged in plan.md. AGENTS.md asks for approval before new folders.
