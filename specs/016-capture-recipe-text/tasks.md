# Tasks: Capture a Recipe from Pasted Text

**Input**: Design documents from `/specs/016-capture-recipe-text/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/capture-api.md, contracts/capture-ui.md, quickstart.md

**Tests**: Included. The constitution (§6) requires domain tests, use-case tests against fake ports, Compose integration tests and vitest for components, and SC-005 and SC-008 are measured by automated tests. No test needs the network: the Compose overlay replaces the extractor with `FakeRecipeExtractor`.

**Organization**: Tasks are grouped by user story. Phase 2 holds what every story needs: the S-015 touch-ups, capture errors, access rules, and the ui basics (the notebook entity and its migration are in spec 055-notebooks).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4, from spec.md
- All paths are relative to the repository root. api paths use the `api/` layout and ui paths use `ui/`, as in plan.md.

## Notes that apply to every task

- No new library in `api/` or `ui/` (plan Technical Context). Do not edit `uv.lock` or `package-lock.json`.
- English for code, comments and UI text; Spanish equivalents go in the same i18n file (AGENTS.md).
- Invented data only in tests (constitution §4). Never read or print `.env`.
- Authentication and signup code is not changed (AGENTS.md). Notebook creation and the notebook read routes are in spec 055-notebooks (research R13).
- The draft is never saved: no task writes a recipe, ingredient, category, source or step row (FR-019). This feature creates no rows.
- Commit one task or one small group at a time. Do not push (AGENTS.md).
- No task in this feature changes an existing constructor.

---

## Phase 1: Setup

**Purpose**: Know the baseline and give the new code a home.

- [ ] T001 Run the baseline checks and note the result: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, then `cd ui && npm test && npm run lint && npm run typecheck`. Everything must be green before any change, so later failures are ours
- [ ] T002 [P] Create the empty folders with an `index.ts` barrel each: `ui/lib/capture/`, `ui/components/AddRecipeCallToAction/`, `ui/components/RecipeDraft/` (plan Source Code; `ui/lib/capture/` is flagged for review in plan.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: S-015 touch-ups, capture errors, access rules, and the ui basics that every story uses. Spec 055-notebooks must be merged first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### S-015 touch-ups (research R2, R6)

- [ ] T003 [P] Add `preparation: str | None = None` to `IngredientLine` in `api/domain/recipe_draft.py`. `check_draft` trims it and turns a blank value into `None`. "How the ingredient is cut or prepared ("chopped"). Trimmed; blank becomes None. Never part of `name`. No other rule." Add cases to `api/tests/test_recipe_draft_domain.py`: kept, trimmed, blank becomes `None`, a name never contains it
- [ ] T004 [P] Add `preparation: str | None = None` to `_LinePayload` in `api/adapters/llm/gemini_extractor.py` and map it into `IngredientLine`. Add the rule to the ingredient fields in `api/adapters/llm/prompt.py`: preparation is how the ingredient is cut or prepared, for example "chopped", and never goes in the name. Extend `api/tests/test_gemini_extractor_adapter.py` so a stubbed reply with a preparation reaches the draft
- [ ] T005 [P] Add `RECIPE_TEXT_MAX_CHARS` (default 5000) to the settings object next to `GEMINI_TEXT_TIMEOUT_S`, and document it in the env example and the README env table (constitution §4). Test the default and an override in the settings tests. The use case in T024 enforces it, so spec 015's own 10,000-character refusal stays unchanged (FR-002, research R6)

### Capture errors and access

- [ ] T007 [P] Add `KitchenArchivedError` (409 `kitchen_archived`, message "This kitchen is archived, so recipes can't be added.") to `api/domain/errors.py`, following the `MESSAGE` and `CODE` style of the existing errors. `NotebookNotFoundError` (404 `notebook_not_found`) comes from spec 055, which needs it for its own read routes; the capture use case reuses it for a missing notebook, another member's notebook and a kitchen notebook of a non-member
- [ ] T008 [P] Add the `capture_recipe` action to `KitchenAccessAction` and to `_MEMBER_READ_ACTIONS` in `api/domain/kitchen_access.py` (member, denied as 404), with a comment that capture writes nothing and S-019's save needs its own action (research R3). Extend `api/tests/test_kitchen_access_domain.py`: an owner and a member are granted; a non-member and a missing kitchen are denied as not found

### Moved to spec 055-notebooks (merged before this feature starts)

- T006 (notebook entity), T009 (ports), T010 (models), T011 (migration and backfill), T012 (notebook repository), T013 (ingredient catalog reader), T014 (integration test), T015 (member notebook on first use, replacing the alias-claim hook), and T016 (kitchen notebook with the kitchen) are delivered there.
- The read routes formerly T028 and T029 are delivered there too.
- `pick_label` (chip label fallback, research R4) stays in this feature, in `api/domain/labels.py`, because the capture route needs it (T027).

### UI basics

- [ ] T017 [P] Make `confirmLabel`, `cancelLabel` and `onConfirm` optional in `ui/components/ActionDialog/ActionDialog.tsx`. When both labels are absent the footer is not rendered and focus goes to the first focusable child; existing callers render exactly as before (contracts/capture-ui.md). Add `ui/components/ActionDialog/ActionDialog.test.tsx`: renders without buttons, Escape and backdrop close, a call with all three props is unchanged
- [ ] T018 [P] Add `ui/app/icons/BookIcon.tsx` (24×24 stroke icon following `ui/app/icons/stroke.ts`), export it from `ui/app/icons/index.ts`, and add it to the catalog in `ui/app/icons/README.md`
- [ ] T019 Add the Notebook tab: in `ui/lib/appChrome.ts` add `/notebook` to `APP_CHROME_PREFIXES` and map `/notebook` and `/notebook/*` to `"notebook"` in `tabKeyFromPath` (kitchen routes, including `/kitchens/[id]/notebook`, stay on `"home"`); add `tabNotebook` ("Notebook" / "Cuaderno") to `ui/lib/i18n/kitchens.ts`; add `{ key: "notebook", href: "/notebook", label: t.tabNotebook, Icon: BookIcon }` after Home in `ui/components/AppShell.tsx`. Extend `ui/components/AppShell.test.tsx` and add a `tabKeyFromPath` test
- [ ] T020 [P] Create `ui/lib/i18n/capture.ts` with English and Spanish strings for everything in contracts/capture-ui.md and the message table in contracts/capture-api.md, using the exact English wording from spec.md (FR-002, FR-014 to FR-018, FR-028, FR-032, FR-033, "Add a recipe", "Not available yet", "Coming soon", "My notebook", draft field errors). Follow the shape of `ui/lib/i18n/kitchens.ts`

**Checkpoint**: Foundation ready. Spec 055-notebooks is merged, and capture errors, access rules and ui basics are in place. User story work can begin.

---

## Phase 3: User Story 1 - Turn pasted recipe text into a reviewable draft (Priority: P1) 🎯 MVP

**Goal**: From either Notebook page, a member pastes text, submits, and sees an editable draft page. Back returns to the text with the text kept. Nothing is saved.

**Independent Test**: Quickstart section 3, steps 1 to 9 and 13. With the fake extractor scripted with a draft, the draft page shows each part of the draft and `ingredient` and `notebook` row counts are unchanged afterwards.

### Tests for User Story 1

- [ ] T021 [P] [US1] Write `api/tests/test_recipe_capture_application.py` against `FakeRecipeExtractor` and fake ports: a draft result becomes a `CapturedDraft` with the notebook and the chip language; the extractor receives only the names of the given notebook (spec FR-003, FR-022); another member's notebook, a missing notebook and a kitchen notebook of a non-member all raise `NotebookNotFoundError` before any catalog read or extractor call; check order from research R3
- [ ] T022 [P] [US1] Write `ui/lib/capture/draftRules.test.ts` for the FR-013 rules: a measured line has `quantity > 0` and a unit; a vague line has neither; size only with unit "unit" and one of small, medium or large; servings a whole number of at least 1; title not empty and 200 characters or fewer; at least one step; at most two main ingredients and two cuisines. Include a test that the unit list equals the `units` field of the vocabulary fixture (research R8)
- [ ] T023 [P] [US1] Write `ui/lib/capture/captureStore.test.ts`: state transitions from data-model.md (submit, draft, Back keeps the text, leave clears, `edited` is true only while the content hash differs from `originalHash` (a change reverted by hand is not an edit), a second submit is blocked while `phase` is `submitting`)

### Implementation for User Story 1: api

- [ ] T024 [US1] Create `api/application/recipe_capture.py` with `CaptureRecipeText.execute(actor_user_id, owner, text, language) -> CaptureOutcome`, where `owner` is the kitchen id, or the user id and notebook id, from the route, resolved to a notebook through the spec 055 repository and `CapturedDraft(recipe, language, notebook, kitchen_name)`. Order (research R3): trim and check the length against `RECIPE_TEXT_MAX_CHARS` (refuse with `text_too_long` and the configured limit in the message), load the notebook, a member-owned notebook must belong to the caller, a kitchen-owned notebook goes through `capture_recipe` authorization and then the archive check (`KitchenArchivedError`), read the catalog, call `RecipeExtraction.extract(text, names, timeout_s)` with the text timeout from settings, pass every non-draft S-015 result through unchanged. It stores nothing
- [ ] T025 [US1] Add the capture dependencies to `api/api/deps.py`: `get_recipe_extraction(request)` builds one `RecipeExtraction(GeminiRecipeExtractor(...), load_vocabulary())` per app and caches it on `app.state` like `get_rate_limiter` (research R11), `get_vocabulary`, `get_notebook_repository` and `get_ingredient_catalog_reader` (both from spec 055), and `get_member_language` (reads `users.language` through the preferences repository with `effective_language` as fallback)
- [ ] T026 [US1] Create `api/api/schemas/recipe_capture.py`: the request body `{ "text": str }` with a `max_length` of twice `RECIPE_TEXT_MAX_CHARS` (a size guard; the limit itself is checked in the use case, with the same `text_too_long` code); the draft response exactly as in contracts/capture-api.md (`outcome`, `notebook`, `language`, `draft` with chips as `{id, label}` and a cuisine `tag`, ingredient lines including `preparation`); the error body `{ "detail", "code" }`
- [ ] T027 [US1] Create `api/api/routes/recipe_capture.py` with `POST /notebooks/kitchens/{kitchen_id}/captures/text` and `POST /notebooks/members/{user_id}/{notebook_id}/captures/text` returning 200 for a draft and 404 `notebook_not_found` through the domain error. Chip labels come from `pick_label` with the member's language (research R4). Other outcomes are mapped in US2 and US3
- T028 — moved to spec 055-notebooks (member notebook read routes: the default notebook, and by notebook id).
- T029 — moved to spec 055-notebooks (kitchen notebook read route, `GET /notebooks/kitchens/{kitchen_id}`).
- [ ] T030 [US1] Add `GET /recipe-vocabulary` to `api/api/routes/recipe_capture.py`: `units`, `sizes`, `max_main_ingredients`, `max_cuisines`, `max_text_chars` (from `RECIPE_TEXT_MAX_CHARS`), every main ingredient with both labels, every assignable cuisine (tags and variants, with the variant's tag) plus the `international` fallback, as in contracts/capture-api.md. Read from the `Vocabulary` built by `load_vocabulary()`
- [ ] T031 [US1] Include the new router in `api/api/app.py` with `dependencies=[Depends(require_user_alias)]`, as the kitchens router does
- [ ] T032 [US1] Write `api/tests/test_recipe_capture_integration.py` (Compose, `app.dependency_overrides[get_recipe_extraction]` with a `FakeRecipeExtractor` that returns a draft): 200 body for a member notebook and a kitchen notebook; chips in `es` when the member's language is `es` and in `en` otherwise; 404 `notebook_not_found` is the same body for a missing notebook, another member's notebook and a kitchen the caller is not in; `GET /notebooks/{user_id}` for self, for someone else and for a member with no notebook; `GET /kitchens/{id}/notebook` for a member and a non-member; `GET /recipe-vocabulary` contents. After every call, the `ingredient` and `notebook` row counts are unchanged (SC-005)

### Implementation for User Story 1: ui

- [ ] T033 [P] [US1] Create the same-origin BFF routes, forwarding the `cookie` header and returning status and body as received (pattern of `ui/app/api/kitchens/[kitchenId]/route.ts`): `ui/app/api/notebooks/kitchens/[kitchenId]/captures/text/route.ts` (POST), `ui/app/api/notebooks/members/[userId]/[notebookId]/captures/text/route.ts` (POST; the read BFF routes are in spec 055; an invalid JSON body answers 400 `invalid_body` without calling the api), `ui/app/api/recipe-vocabulary/route.ts` (GET). Add a route test for each in the style of `ui/app/api/kitchens-invites.bff.test.ts`
- [ ] T034 [P] [US1] Create `ui/lib/capture/captureStore.ts`: a module store with `useSyncExternalStore`, the same pattern as `ui/app/kitchens/membershipKitchensStore.ts`, holding the fields in data-model.md "Client-only state" (`notebook {id, kind, label}`, `text`, `sheetOpen`, `phase`, `message`, `draft`, `edited`, `language`) and the transitions listed there. Add `ui/lib/capture/draftHash.ts` with a synchronous hash (for example cyrb53, because the `beforeunload` handler cannot await `crypto.subtle`) over a canonical serialization of the title, servings, categories, ingredient lines and steps, and a test: the same content gives the same hash, any edit changes it, and reverting an edit restores it
- [ ] T035 [P] [US1] Create `ui/lib/capture/draftRules.ts` implementing the rules tested in T022 and returning a map from field path to message key. It also holds the units and size constants
- [ ] T036 [US1] Create `ui/lib/capture/captureClient.ts`: `submitCapture(owner, text)` posting to the kitchen or member capture route, `fetchMemberNotebook(userId)`, `fetchKitchenNotebook(kitchenId)`, `fetchVocabulary()`, and a mapper from the draft response to `DraftView`. Non-200 handling is added in US2 and US3. Add `ui/lib/capture/captureClient.test.ts`
- [ ] T037 [P] [US1] Create `ui/components/AddRecipeCallToAction/AddRecipeOptionsDialog.tsx` on `ActionDialog` without confirm and cancel labels: a vertical list with dividers in this order: URL (`aria-disabled`, "Not available yet"), Picture (`aria-disabled`, "Coming soon"), Text (enabled). Escape or a backdrop click closes it without change (FR-023). Add `AddRecipeOptionsDialog.test.tsx`
- [ ] T038 [P] [US1] Create `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx` on `Sheet`, titled with `notebook.label`: a multi-line "Recipe text" input; submit disabled when the text is empty, whitespace-only, over `max_text_chars` (from the vocabulary route) after trimming (with "That text is too long. Paste up to {max_text_chars} characters."), or while submitting; a counter once the text is over 90% of `max_text_chars`; a progress state ("Reading your recipe…") with a read-only input while submitting (FR-002, FR-004). On a 200 it moves the store to `draft` and navigates to the notebook's draft route. Add `TextCaptureSheet.test.tsx`
- [ ] T039 [US1] Create `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx` and its `index.ts`: the rounded placeholder with a centred `PlusIcon`, a `<button>` named "Add a recipe", opening the options dialog and then the text sheet. On mount, when the store has `sheetOpen` for the same notebook id, it reopens the sheet with the stored text. Props as in contracts/capture-ui.md. Add `AddRecipeCallToAction.test.tsx` (shared component; do not rebuild it on a page, AGENTS.md)
- [ ] T040 [US1] Create `ui/app/notebook/page.tsx` (server component): sign-in and alias checks as in `ui/app/kitchens/[kitchenId]/page.tsx`, header "Notebook", the member's default notebook from `/api/notebooks/members/{user_id}` (spec 055), with the user id from `fetchSession()`, then `AddRecipeCallToAction` with `{ id, kind: "member", label: "My notebook" }`. No recipe list (S-020). Show a plain error line when the notebook cannot be loaded
- [ ] T041 [P] [US1] Create `ui/app/kitchens/KitchenSectionTabs.tsx` (Members | Notebook links, active state, styled like `ButtonGroup`) and render it in `ui/app/kitchens/[kitchenId]/page.tsx` with Members active. Existing content, links and tests stay as they are (research R10, FR-001b). Add a component test
- [ ] T042 [US1] Create `ui/app/kitchens/[kitchenId]/notebook/page.tsx`: header is the kitchen name, `KitchenSectionTabs` with Notebook active, the notebook from `/api/notebooks/kitchens/{id}` (spec 055), `AddRecipeCallToAction` with `{ id, kind: "kitchen", label: kitchen name }`. A non-member sees the existing not-found view (FR-022). No recipe list (S-046)
- [ ] T043 [P] [US1] Create the draft editor in `ui/components/RecipeDraft/`: `RecipeDraftEditor.tsx` (notebook line "For: " + `notebook.label`, title, servings with the "estimated" badge while `servingsEstimated` is true, steps list, Back control, no Save), `IngredientLineRow.tsx` (name, quantity, unit select from the allowed set, size select shown only when unit is `unit`, preparation, note, "vague amount" toggle that clears quantity and unit), `CategoryChips.tsx` (chips in the member's `language`, variant chips read "Variant · Tag", `ChipPicker` fed by `/api/recipe-vocabulary`, picker hidden at two). Ingredient lines and steps can be added, removed, moved up and moved down (FR-012). Field errors from `draftRules.ts` appear next to the field or line (FR-013). Any change sets `edited`. Add component tests for each file
- [ ] T044 [US1] Create the draft pages `ui/app/notebook/draft/page.tsx` and `ui/app/kitchens/[kitchenId]/notebook/draft/page.tsx` (client pages with chrome header "Review recipe"). With no draft in the store, or a stored notebook id that is not this page's notebook, `router.replace` to the notebook's Notebook page (research R5). Back clears the draft, sets `sheetOpen` with the text kept, and returns to the Notebook page with no prompt (FR-031)
- [ ] T045 [US1] Create `ui/components/RecipeDraft/LeaveDraftGuard.tsx`, mounted by the editor while `edited` is true: a capture-phase `click` listener for same-origin `<a href>` that leave the draft route opens an `ActionDialog` "Leave without saving?" / "Your changes to this draft will be lost." with Stay (cancel) and Leave (confirm: clear the store, follow the link); `beforeunload` while edited. Back and Discard are not intercepted; an unedited draft leaves without a prompt (FR-032, research R7). Add `LeaveDraftGuard.test.tsx`
- [ ] T046 [US1] Walk quickstart section 3, steps 1 to 9 and 13, with the fake extractor and then with a real key if available; fix what differs from spec scenarios 1 to 12 of User Story 1. Record the result in `dev/memory/`

**Checkpoint**: User Story 1 works on its own. A member can capture, review, edit and go back, and nothing is saved. This is the MVP.

---

## Phase 4: User Story 2 - Reject input that is not a recipe (Priority: P2)

**Goal**: Text that is not a recipe, or has two recipes, shows its message, creates no draft and no data, and the text stays in the box.

**Independent Test**: Quickstart steps 10 and 11. "What's the weather tomorrow?" shows "That doesn't look like a recipe." with a reason; `two_recipes.txt` shows "Upload only one recipe at a time"; `sauce_subsection.txt` gives one draft.

- [ ] T047 [US2] Map `NotARecipe` in `api/api/routes/recipe_capture.py`: reason "Only one recipe at a time" (`ONE_RECIPE_REASON`) → 422 `one_recipe_at_a_time`; any other reason → 422 `not_a_recipe` with `reason` (at most 120 characters). Extend `api/tests/test_recipe_capture_integration.py` with both cases and row counts unchanged (FR-014, FR-015, SC-003)
- [ ] T048 [US2] In `ui/lib/capture/captureClient.ts` map the codes `not_a_recipe` and `one_recipe_at_a_time` to message keys, carrying `reason` for the first. `TextCaptureSheet.tsx` shows the message in an `alert` region ("That doesn't look like a recipe." followed by the reason, or "Upload only one recipe at a time"), keeps the text unchanged and editable, and shows no draft. Extend `captureClient.test.ts` and `TextCaptureSheet.test.tsx`
- [ ] T049 [US2] Walk quickstart steps 10 and 11 and fix any difference from User Story 2 scenarios 1 to 4. Record the result in `dev/memory/`

**Checkpoint**: User Stories 1 and 2 both work.

---

## Phase 5: User Story 3 - Keep the pasted text when the assistant fails (Priority: P2)

**Goal**: Every failure shows its own plain message within the time limit, never raw service text, and the text stays in the box. Archived kitchens refuse capture before any assistant call.

**Independent Test**: Quickstart "Failure messages" table and steps 12 and 14, plus the integration tests below.

- [ ] T050 [US3] Map the remaining results in `api/api/routes/recipe_capture.py` as in contracts/capture-api.md: `InvalidOutput` → 422 `ai_invalid_output`; `Unavailable` → 503 `ai_unavailable`; `LimitReached` → 429 `ai_limit_reached` with a `Retry-After` header only when `retry_after_seconds` is set; `AIProviderError` → 503 `ai_misconfigured`; `RecipeTextRefusedError` → 422 `text_empty` or `text_too_long`; `KitchenArchivedError` → 409 `kitchen_archived`. Every `detail` is a plain sentence with no service text, key or trace (FR-029)
- [ ] T051 [US3] Extend `api/tests/test_recipe_capture_integration.py` and `api/tests/test_recipe_capture_application.py`: one case per code above; over-length and empty text and an archived kitchen leave the `FakeRecipeExtractor` with zero calls (FR-033, SC-008); an archived kitchen answers 409 only after membership passes (a non-member of an archived kitchen gets 404); a member's own notebook is never affected by a kitchen's archive state; a failure body never contains the key or any raw text
- [ ] T052 [US3] Add the safety deadline to the two capture BFF routes (kitchen and member): `AbortSignal.timeout(((Number(process.env.GEMINI_TEXT_TIMEOUT_S) || 10) + 2) * 1000)` on the upstream call; on abort or network failure answer 503 `{ "code": "ai_unavailable" }`; other upstream failures answer 502 `bad_gateway` as the existing routes do (research R9, FR-026). Add a route test with a stalled upstream
- [ ] T053 [US3] In `ui/lib/capture/captureClient.ts` map `ai_unavailable` and `bad_gateway` ("The assistant isn't responding. Your text is kept — try again."), `ai_limit_reached` ("We've hit the assistant's limit. Try again in a minute."), `ai_invalid_output` ("We couldn't read that recipe. Try rephrasing or adding detail."), `ai_misconfigured` ("Assistant misconfigured. Your text is kept"), `text_too_long`, `kitchen_archived` ("This kitchen is archived, so recipes can't be added."), `notebook_not_found` and `kitchen_not_found` (the kitchen not-found text), and any other code to the `ai_unavailable` message. The text is kept in every case and a second submission works (FR-016 to FR-018, FR-028). Extend `captureClient.test.ts` and `TextCaptureSheet.test.tsx`
- [ ] T054 [US3] Hide the add-recipe call to action on an archived kitchen's Notebook page in `ui/app/kitchens/[kitchenId]/notebook/page.tsx`, using `is_archived` from the notebook response (FR-033). Add a page test
- [ ] T055 [US3] Walk quickstart "Failure messages", step 12 and step 14, and fix any difference from User Story 3 scenarios 1 to 5. Record the result in `dev/memory/`

**Checkpoint**: User Stories 1 to 3 work. Every failure keeps the text.

---

## Phase 6: User Story 4 - Discard a draft (Priority: P3)

**Goal**: Discard is always available on the draft; it removes the draft and returns to an empty text sheet, and nothing is saved.

**Independent Test**: Quickstart step 8. After Discard the sheet is open and empty, and the notebook and ingredient counts are unchanged.

- [ ] T056 [US4] Add a Discard control to `ui/components/RecipeDraft/RecipeDraftEditor.tsx`, always enabled even when a field has an error (FR-020). It clears the draft and the text, sets `sheetOpen`, and returns to the notebook's Notebook page. It is not intercepted by `LeaveDraftGuard`. Add a store action `discard()` in `ui/lib/capture/captureStore.ts`. Extend `captureStore.test.ts` and `RecipeDraftEditor.test.tsx`: Discard works with a broken line, leaves an empty text, and Back (T044) still keeps the text
- [ ] T057 [US4] Walk quickstart step 8 and run the quickstart "Data unchanged" count after it; fix any difference from User Story 4 scenarios 1 and 2. Record the result in `dev/memory/`

**Checkpoint**: All four user stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T058 [P] Run `cd api && uv run ruff check .` and fix every finding in the files this feature touched
- [ ] T059 [P] Run `cd ui && npm test && npm run lint && npm run typecheck`; there must be no deprecation warning (AGENTS.md "Node")
- [ ] T060 Run the canonical api suite in Compose: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, and check that `alembic current` reports `0003_notebooks_ingredients` (migration from spec 055) (quickstart sections 1 and 2)
- [ ] T061 Walk all of quickstart section 3 once more in a browser, including the language check (Ana's language set to Spanish gives Spanish chips), and the "Data unchanged" counts (SC-005)
- [ ] T062 Run the manual AI evaluation with a real key (quickstart section 4): each file in `api/tests/fixtures/ai_eval/` ten times for SC-002, and the 90% check for SC-006, including `injected_instruction.txt` (FR-021). Record the results in `dev/memory/`
- [ ] T063 Update `dev/docs/backlog.yaml` (S-016 status once verified) and `specs/016-capture-recipe-text/checklists/requirements.md`; append the finished change to `dev/memory/` with the command in `dev/skills/save_to_memory.md`. Do not push or deploy without review (AGENTS.md)
- [ ] T064 Usability check (SC-007): each of the two household members completes one capture and one discard on the staging build, without help. Record the observations in `dev/memory/`. Needs both members' time before release.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: none.
- **Phase 2 (Foundational)**: after Phase 1. Blocks every story.
- **Phase 3 to 6 (User Stories)**: after Phase 2. US2, US3 and US4 build on the route, client and sheet created in US1, so US1 comes first; after US1 they are independent of one another.
- **Phase 7 (Polish)**: after the stories you want to ship.

### Inside Phase 2

- T003, T004, T005, T007, T008 can run together.
- Notebook tasks are in spec 055-notebooks, which this phase needs merged.
- T017, T018, T020 can run together; T019 needs T018.

### Inside User Story 1

- Tests T021 to T023 can be written first and run together.
- api: T024 → T025 → T026 → T027, then T030 (vocabulary route), then T031 and T032. T028 and T029 are in spec 055.
- ui: T033, T034, T035 can run together. T036 needs T034. T037 and T038 can run together; T039 needs both. T040, T042 need T039 and T036. T041 can run any time. T043 needs T034 and T035. T044 needs T043. T045 needs T043.
- The api group and the ui group can run in parallel; T046 needs both.

### Story dependencies

- **US1**: after Phase 2. No dependency on other stories.
- **US2**: after US1 (route and sheet).
- **US3**: after US1 (route and sheet). Independent of US2.
- **US4**: after US1 (editor and store). Independent of US2 and US3.

### Parallel example: Foundational

```text
T003  api/domain/recipe_draft.py (preparation)
T004  api/adapters/llm/gemini_extractor.py + prompt.py
T005  api/settings (RECIPE_TEXT_MAX_CHARS)
T007  api/domain/errors.py
T008  api/domain/kitchen_access.py
T017  ui/components/ActionDialog/ActionDialog.tsx
T018  ui/app/icons/BookIcon.tsx
T020  ui/lib/i18n/capture.ts
```

### Parallel example: User Story 1

```text
T033  ui BFF routes            T034  captureStore.ts        T035  draftRules.ts
T037  AddRecipeOptionsDialog   T038  TextCaptureSheet       T043  RecipeDraft components
T024..T032  api use case, deps, schemas and routes (one developer, in order)
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Spec 055-notebooks merged. Then Phase 1 and Phase 2: S-015 touch-ups, capture errors, access, ui basics.
2. Phase 3: capture, review, edit, Back. Nothing is saved.
3. **Stop and check**: walk quickstart steps 1 to 9 and 13. This is the smallest slice that gives a usable draft.

### Incremental delivery

1. US2 adds the not-a-recipe messages (small, mostly mapping).
2. US3 adds failure messages, the archive refusal and the time limit.
3. US4 adds Discard.
4. Polish: lint, full suites, the browser walkthrough and the manual AI evaluation.

### Cut lines

- The counter at 90% of the limit (T038) is optional; the limit itself is not.
- The manual AI evaluation (T062) needs a real key and is not part of CI.

---

## Notes

- Each task names the files it touches. Tasks that share a file (`recipe_capture.py` routes, `captureClient.ts`, `TextCaptureSheet.tsx`, `test_recipe_capture_integration.py`) are never marked [P] against each other.
- This feature saves nothing: Save, the name-change list and "matched" / "new ingredient" labels, copying between notebooks and the recipe lists are S-019, S-017, S-034 and S-020 / S-046.
- Cross-spec changes in this plan are already written into the PRD, AGENTS.md and specs 016 and 015 (notebook entity, preparation, member language, categories as ids).
