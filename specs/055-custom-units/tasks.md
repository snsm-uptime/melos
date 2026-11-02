# Tasks: Custom Units and Admin Dashboard

**Input**: Design documents from `specs/055-custom-units/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution principle 6 requires them, and quickstart.md lists the risks they must prove. Write each test task first and see it fail. Paths in `api/` run with `cd api && uv run pytest -q <file>`; integration tests run in the Compose test overlay; `ui/` runs with `cd ui && npm test`.

**Before starting**: Two owner approvals are open (plan.md, Complexity Tracking): principle 9 and the AGENTS.md change. T001 is the gate: no other task starts until both are written in plan.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story from spec.md

---

## Phase 1: Setup

- [X] T001 Gate: confirm `specs/055-custom-units/plan.md`, Complexity Tracking, records the owner's written approval, with who and when and a scope limit, of (a) the principle 9 exception for this `later` story and (b) the edits to `AGENTS.md` in T072. If either is missing, stop and ask; do not start T002
- [X] T002 Create branch `055-custom-units` in its own worktree with `./scripts/worktree/worktree-add.sh` and run the bootstrap it prints. Compose projects share the dev data directory, so never start a second project with the main `.env`
- [X] T003 [P] Add `ui/lib/i18n/customUnits.ts` exporting `customUnitMessages` with `en` and `es` text for the question ("Use \"{word}\" as a unit from now on?"), yes, no and "Other…", in the style of `ui/lib/i18n/sidePanel.ts`, and add it to the `SETS` map in `ui/lib/i18n/parity.test.ts` (FR-015)
- [X] T004 [P] Add `ui/lib/i18n/admin.ts` exporting `adminMessages` with `en` and `es` text for the entry, the four tabs and every column in `contracts/admin-api.md`, and add it to `SETS` in `ui/lib/i18n/parity.test.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The schema, the pure rules and the unit repository. No user story can start before this is done.

- [X] T005 Write `api/tests/test_custom_units_migration.py` in the style of `api/tests/test_shopping_lists_migration.py`. It proves: the ten rows are seeded as default with no references; `reference_count` follows `user_references` and refuses a direct write; a `unit` name that fails `name = lower(btrim(name))` or is outside 1 to 32 characters is refused; `lata` can be stored on a recipe line and a blank unit cannot; `custom` is accepted as a list item kind; `cart_activity.action` allows only `created`, `edited`, `closed`; deleting a user removes their `cart_activity` rows; `is_admin` defaults to false; downgrade refuses, with a clear message, while a recipe line or list item uses a custom unit (R19)
- [X] T006 Create `api/adapters/persistence/migrations/versions/0013_custom_units.py` after `0012_notebook_invite`, exactly as in `data-model.md`. Table `unit`: `name` text primary key with check `name = lower(btrim(name))` and 1 to 32 characters; `user_references uuid[]` not null default `{}`; `reference_count` integer `GENERATED ALWAYS AS (cardinality(user_references)) STORED`; `is_default` boolean not null default false; `created_at` timestamptz not null default now. Seed `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit` as default with no references. Table `cart_activity`: `id` uuid primary key `gen_random_uuid()`; `user_id` uuid not null, FK `users.id` `ON DELETE CASCADE`, indexed; `action` text not null with check `created`, `edited` or `closed`; `created_at` timestamptz not null default now. `users.is_admin boolean NOT NULL DEFAULT false`. On `recipe_ingredient`, drop `ck_recipe_ingredient_unit` and add `ck_recipe_ingredient_unit_not_blank`: `unit IS NULL OR btrim(unit) <> ''`. `ck_shopping_list_item_kind` allows `mass`, `volume`, `count`, `custom`. Downgrade refuses as in R19 (depends on T005)
- [X] T007 Update `api/adapters/persistence/models.py` to match T006: add `UnitModel` and `CartActivityModel`, add `is_admin` to `UserModel`, remove `UNITS_SQL`, and change the two checks (depends on T006)
- [X] T008 [P] Write tests in `api/tests/test_recipe_draft_domain.py` for `custom_unit_name` (R8): `latas`, `botes`, `paquetes`, `sobres`, `cans`, `jars`, `slices` and `bunches` become singular; `Latas ` and `lata` are equal; `None` for empty, over 32 characters, no letter, or anything but letters, digits, spaces, hyphens and apostrophes. Then for `lookup_unit(raw, extra=())` (R9): default spellings win, then an exact match in `extra` ignoring accents, then near-miss over both; `latta` maps to `lata`; a word near two units is invalid output; `tazas` stays `cup`
- [X] T009 Implement `custom_unit_name` and `lookup_unit(raw, extra=())` in `api/domain/recipe_draft.py`. Keep `ALLOWED_UNITS` as the base of the spelling table (depends on T008)
- [X] T010 Write tests in `api/tests/test_recipe_draft_domain.py`, then add to `api/domain/recipe_draft.py` the frozen value `UnknownUnit(word, lines)` and `DraftRecipe.unknown_units` (a tuple, empty in the raw value and after an edit check). `check_draft` gains `available_units`: a word that can be offered keeps its line, the line's `unit` becomes the normalized word, and it is reported once per word with all its line indexes, so "lata" on three lines and "latas" on another give one entry with four (US1 scenario 5). A word that can't be offered keeps today's refusal (R7). `check_edited_draft` gains `allowed_units`, and `_line_problems` and `_check_line` use `lookup_unit(line.unit, allowed)`, giving `unit_not_recognized` for anything outside it (FR-007). Size stays valid only on `unit`, so "una lata grande" records no size (depends on T009)
- [X] T011 Add `UnitRepository` to `api/application/ports.py`: `extras_for(user_id) -> list[str]` (`is_default OR referenced`, without the ten), and `add_user(names, user_id)`. T051 adds `remove_user(user_id)`
- [X] T012 Write `api/tests/test_units_integration.py`: two people keep one word and get one row with count 2; the same person twice counts once; concurrent saves of the same two words don't deadlock (R2); a person's extras show none of another account's units (SC-003)
- [X] T013 Create `api/adapters/persistence/units.py` implementing `UnitRepository`. `add_user` runs the single statement in R2, verbatim, with names in sorted order. This is the only code that adds to `user_references` (depends on T007, T011, T012)
- [X] T014 Create `api/application/units.py` with `available_units(extras)` (the ten in today's order, then the rest sorted, R20), and `kept_units_to_add(keep_units, saved_lines, available)` (only offerable words a saved line uses and nothing already covered, R10), with tests in `api/tests/test_units_application.py` against a fake `UnitRepository` (depends on T011)
- [X] T015 Wire `UnitRepository` into `api/api/deps.py` (depends on T013)

**Checkpoint**: The migration runs up and down, and the pure rules and repository tests pass. `cd api && uv run ruff check .` is clean.

---

## Phase 3: User Stories 1 and 2 - Keep a new unit, and know it from then on (Priority: P1) 🎯 MVP

**Goal**: An unknown word opens a draft with a question. A yes adds it at Save, and from then on capture, add and edit know it. The plan builds these two together because one has no value without the other. Tasks carry the label of the story they serve.

**Independent Test**: On a fresh account, capture a recipe with "una lata de frijoles", accept, save, then capture "2 latas de atún" and open a recipe for editing. The first line reads `1 lata frijoles`; the second capture asks nothing; "lata" can be picked. A second account's list is unchanged.

### Tests

- [X] T016 [P] [US1] Add to `api/tests/test_recipe_extraction_application.py`: two accounts paste the same text at once and each gets a draft judged by their own units (R5); `unknown_units` is returned for an unknown word
- [X] T017 [P] [US1] Add to `api/tests/test_prompt_templates.py` or `api/tests/test_prompt_characterization.py`: no stored unit appears in what is sent to the model (R4, FR-021)
- [X] T018 [P] [US1] Add to `api/tests/test_recipe_save_application.py`: a kept word used by a line joins the list; a kept word no line uses, or one already covered, is ignored; a refused save and a replayed save add nothing; an unknown word not in `keep_units` is `unit_not_recognized` and stores nothing (`contracts/units-api.md`)
- [X] T019 [P] [US2] Add to `api/tests/test_recipe_manage_application.py`: `keep_units` on update behaves as in T018
- [X] T020 [P] [US2] Create `api/tests/test_recipe_vocabulary_integration.py`: `GET /recipe-vocabulary` is per person, in R20 order; `POST /recipe-vocabulary/unit-check` answers `known`, `new` and `not_a_unit` as in the contract, stores nothing, and refuses a word over 200 characters
- [X] T021 [P] [US1] Add to `api/tests/test_recipe_capture_integration.py` and `api/tests/test_recipe_save_integration.py`: the full capture, accept and save route flow with a fake extractor, and account isolation (US2 scenario 4)
- [X] T022 [P] [US1] Add to `ui/lib/capture/draftRules.test.ts`: `checkDraft` takes the allowed units as an argument and flags a line outside them, and a word asked about is listed once
- [X] T023 [P] [US1] Add to `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx` and `ui/lib/capture/saveClient.test.ts`: the question shows once per word, accept clears the flag and sends `keep_units`, decline keeps the flag and blocks Save, discard sends nothing, and two words are answered apart (US1 scenarios 1 to 6)
- [X] T024 [P] [US2] Add to `ui/components/RecipeEdit/RecipeEditForm.test.tsx`: the picker shows the vocabulary, "Other…" swaps in a text field, leaving it calls `unit-check`, `new` asks, `known` writes the mapped unit, and `not_a_unit` stays flagged

### API

- [X] T025 [US1] Add one rule to `api/adapters/llm/prompts/recipe_extraction_system.md`: a container or measure word is reported as written and never folded into a plain count (FR-002). Update `api/tests/fixtures/prompts/recipe_extraction_system.golden.txt`, and add `api/tests/fixtures/ai_eval/canned_beans.txt` with invented text. The `RecipeExtractor` port does not change
- [X] T026 [US1] In `api/application/recipe_extraction.py`, hash the text, the catalog names and the available units together for the in-flight key, and pass the units to `check_draft` (R5)
- [X] T027 [US1] In `api/application/recipe_capture.py`, read the caller's units through `UnitRepository` and pass them to extraction, for pasted text and web pages (FR-009)
- [X] T028 [US1] Add `unknown_units` to the draft response in `api/api/schemas/recipes.py` and `api/api/routes/recipe_capture.py`, in the shape `{ "word": "lata", "lines": [0, 3] }`
- [X] T029 [US1] In `api/application/recipe_save.py`, take `keep_units`, allow `available ∪ kept` in `check_edited_draft`, and call `add_user` after the write in the same transaction, beside `add_names` (R10, FR-005)
- [X] T030 [US2] In `api/application/recipe_manage.py`, do the same for update, and also allow every unit on the stored recipe (R11)
- [X] T031 [US1] Add `keep_units: list[str]`, default `[]`, at most one entry per allowed line count, to both bodies in `api/api/schemas/recipes.py` and pass it through `api/api/routes/recipes.py`
- [X] T032 [US2] In `api/application/recipe_vocabulary.py`, return `available_units` for the caller, and add a pure unit check answering `known`, `new` or `not_a_unit`, using `lookup_unit` and `custom_unit_name` (R12)
- [X] T033 [US2] Add `POST /recipe-vocabulary/unit-check` to the vocabulary route in `api/api/routes/`, with a body of at most 200 characters

### UI

- [X] T034 [US1] In `ui/lib/capture/draftRules.ts`, make `checkDraft` take the allowed units as an argument, and add a pure `pendingUnitQuestions(lines, allowed, keptUnits, declinedUnits)`: a word is asked about while a line uses it and it's in none of the three lists (data-model.md). Remove `ALLOWED_UNITS` from the `RecipeEditForm` path, and update every `checkDraft` caller
- [X] T035 [US1] In `ui/lib/capture/captureStore.ts`, carry `keptUnits` and `declinedUnits` on the draft, seeded empty, cleared on discard, and never persisted as a refusal (FR-006). In `ui/lib/capture/captureClient.ts`, read `unknown_units`. In `ui/lib/capture/saveClient.ts`, send `keep_units` from `buildSaveBody`
- [X] T036 [US1] Create `ui/components/RecipeDraft/UnknownUnitQuestion.tsx` and export it from `ui/components/RecipeDraft/index.ts`: one question per word, using `customUnitMessages`, works at 360px, and shows the word as stored in both languages
- [X] T037 [US1] Show `UnknownUnitQuestion` above the lines in `ui/components/RecipeDraft/RecipeDraftEditor.tsx`
- [X] T038 [US2] In `ui/components/RecipeDraft/IngredientLineRow.tsx`, the `<select>` lists the available units, plus the line's current unit if missing, plus "Other…", which swaps in a text field. Leaving the field calls `unit-check` (R15)
- [X] T039 [US2] Add a `unit-check` handler in `ui/app/api/recipe-vocabulary/`, and a client for it in `ui/lib/recipesClient.ts`
- [X] T040 [US2] In `ui/components/RecipeEdit/RecipeEditForm.tsx` and `ui/lib/recipeEdit.ts`, load the vocabulary, carry `keptUnits` and `declinedUnits`, show `UnknownUnitQuestion`, and send `keep_units` on update

**Checkpoint**: The Independent Test passes. Stories 1 and 2 are complete, but do not release until Phase 4 is done: without it a saved `lata` drops off a shopping list and blocks other members' edits (plan.md, Build order).

---

## Phase 4: User Story 3 - Shared recipes keep working for everyone (Priority: P2)

**Goal**: Any stored unit works for every reader in reading, scaling, editing, snapshots, the cart and the shopping list. This ships in the same release as Phase 3.

**Independent Test**: With A's recipe using "lata" in a shared kitchen, B opens it, scales it, edits the title, saves and adds it to the cart. Nothing fails, and B's list does not change.

### Tests

- [X] T041 [P] [US3] Add to `api/tests/test_cart_domain.py`: `unit_kind` answers `custom` outside the ten; 1 + 2 lata is `3 lata`; 1.5 lata is `2 lata`; lata and g stay on separate lines with no conversion; two custom units of one ingredient share a line; `custom` sorts after `count`
- [X] T042 [P] [US3] Add to `api/tests/test_shopping_list_integration.py`: the shape in `contracts/units-api.md` with `"kind": "custom"`, saved and closed lists keep it, and a hand item with `lata` is still refused (FR-016). Confirm every existing shopping list test passes unchanged (SC-004)
- [X] T043 [P] [US3] Add to `api/tests/test_recipe_manage_integration.py`: B updates A's recipe, including reordering its lines, with no refusal and no change to B's list; a new unknown word from B is still refused without `keep_units`
- [X] T044 [P] [US3] Add to `api/tests/test_notebook_snapshots_integration.py`: a snapshot keeps `lata` and changes nobody's list
- [X] T045 [P] [US3] Add to `ui/lib/shoppingListClient.test.ts`, `ui/lib/recipeScale.test.ts` and `ui/components/RecipeEdit/RecipeEditForm.test.tsx`: a `custom` line prints `3 lata`; a custom unit scales; another member's picker shows their units plus the line's current one, and no question appears for an untouched line

### Implementation

- [X] T046 [US3] In `api/domain/cart.py`, add `custom` to `Kind` and rank it after `count` in `_KIND_RANK`, make `unit_kind` answer it, and in `_measured_lines` group a custom line by name, sum per unit, round each sum up, and sort its units by name (R13). Check `api/domain/shopping_list.py`: `hand_item` must still test `_UNITS` before calling `unit_kind` (R14)
- [X] T047 [US3] Add `custom` to the `kind` literal in `api/api/schemas/shopping_list.py`
- [X] T048 [US3] Add `custom` to `kind` in `ui/lib/shoppingListClient.ts`, and confirm `formatLine` in `ui/lib/shoppingListText.ts` prints the unit for it
- [X] T049 [US3] Verify the read, cart and scale paths don't depend on the fixed list: `api/application/carts.py`, `api/application/notebooks.py` (`AddNotebookSnapshotService`), `ui/lib/recipeScale.ts`, `ui/lib/recipeLines.ts`, `ui/components/RecipeDetail/`. Fix anything that assumes the ten. Reading a recipe must add no query for the person's list (FR-011)

**Checkpoint**: Stories 1, 2 and 3 pass. This is the first releasable point.

---

## Phase 5: Account removal rule (supports FR-020b)

**Purpose**: The rule that S-054 must call. It has no route and nothing a person sees until then.

- [X] T050 Add tests to `api/tests/test_units_application.py` and `api/tests/test_units_integration.py`: removal drops the count, removes the empty non-default row, keeps a default row, never touches a recipe line, does nothing on a second run, and never commits
- [X] T051 Add `RemoveUserFromUnitsCommand(user_id: UUID)` and `RemoveUserFromUnitsService(units: UnitRepository).execute(command) -> None` to `api/application/units.py`, `remove_user` to `UnitRepository` in `api/application/ports.py`, and its implementation to `api/adapters/persistence/units.py`, locking rows in name order (R3, `contracts/units-api.md`)
- [X] T052 Add the service name `RemoveUserFromUnitsService` to the S-054 note in `dev/docs/backlog.yaml`, which already requires the removal (spec 055 FR-020b) in the same transaction

---

## Phase 6: User Story 4 - See how the app is used (Priority: P3)

**Goal**: A read-only dashboard of units, ingredients, recipes and users for the admin only, and the cart activity behind it. This phase is the plan's cut-line: it can move to a later release with no effect on cooking flows.

**Independent Test**: With several accounts holding overlapping data, open `/admin` as the admin and as a normal account. The figures match the known data, and the normal account gets not-found with no entry in the side panel.

### Tests

- [ ] T053 [P] [US4] Add to `api/tests/test_cart_domain.py`: `cart_save_action(before, after)` gives `created` from empty to filled, `edited` for any other difference including emptying, and nothing for no difference (R18)
- [ ] T054 [P] [US4] Add to `api/tests/test_carts_application.py` and `api/tests/test_shopping_list_application.py`: Save records one action for the person; Close records one `closed` and no `edited`; other kitchen members get none; discarding a draft records nothing (US4 scenario 7)
- [ ] T055 [P] [US4] Add to `api/tests/test_side_panel_application.py` and `api/tests/test_side_panel_integration.py`: `is_admin` for the caller only, on GET and on `PUT /side-panel/default-kitchen`, and `/auth/me` does not gain it
- [ ] T056 [P] [US4] Create `api/tests/test_admin_application.py`: access is refused for a non-admin, with a fake `AdminReportRepository`
- [ ] T057 [P] [US4] Create `api/tests/test_admin_integration.py`: signed-out and non-admin answers equal an unknown path byte for byte; each section's figures match invented data for US4 scenarios 1, 2, 3 and 7; a catalog name no recipe uses shows 0; a deleted author doesn't count; response keys equal the lists in `contracts/admin-api.md` exactly (FR-019); no email, ingredient, step, conversation, password or token appears
- [ ] T058 [P] [US4] Create `ui/app/admin/AdminDashboard.test.tsx` and `ui/app/api/admin/admin.bff.test.ts`: a tab loads its section when opened, and the BFF passes the four sections and answers 404 to anything else. Add to `ui/components/SidePanel/SidePanel.test.tsx`: the entry shows only when `is_admin` is true

### Cart activity

- [ ] T059 [US4] Add `CartAction` (`created`, `edited`, `closed`) and pure `cart_save_action(before, after)` to `api/domain/cart.py`
- [ ] T060 [US4] Add `CartActivityLog` to `api/application/ports.py` and create `api/adapters/persistence/cart_activity.py`
- [ ] T061 [US4] In `api/application/carts.py`, `SaveCartService` records the action, using the items it read under the cart lock, in its transaction. In `api/application/shopping_list.py`, `CloseShoppingListService` records `closed`. Wire both in `api/api/deps.py`. No cart behaviour reads this table

### Admin API

- [ ] T062 [US4] Add `is_admin` to `SidePanelView` in `api/application/side_panel.py`, `api/adapters/persistence/side_panel.py` and `api/api/schemas/side_panel.py`. No route or body writes it (FR-017a, R16)
- [ ] T063 [US4] Add the admin not-found error to `api/domain/errors.py`, and `AdminReportRepository` to `api/application/ports.py`
- [ ] T064 [US4] Create `api/application/admin.py`: the access check and the four reads. Put the written exception to the "every recipe query" rule at the top of the file, scoped to the `/admin/recipes` route (plan.md, Complexity Tracking)
- [ ] T065 [US4] Create `api/adapters/persistence/admin.py` with plain SQL aggregates as in R17: ingredients from `recipe_ingredient` and `ingredient` with `COUNT(DISTINCT recipe_id)` and `COUNT(DISTINCT author_id)`; the people figure from notebook members or kitchen members by kind; open sessions are `expires_at > now()`; the sort orders in the contract
- [ ] T066 [US4] Create `api/api/schemas/admin.py` and `api/api/routes/admin.py` with the four GET routes, register the router, and answer the identical `404 {"detail":"Not Found"}` to signed-out and non-admin callers (depends on T064, T065)

### Admin UI

- [ ] T067 [US4] Create `ui/app/api/admin/[section]/route.ts`: pass `units`, `ingredients`, `recipes` and `users` through, and answer 404 to anything else
- [ ] T068 [US4] Add `is_admin` to `ui/lib/sidePanelClient.ts`, and the admin entry to `ui/components/SidePanel/SidePanel.tsx`, shown only when true
- [ ] T069 [US4] Create `ui/app/admin/page.tsx`, server-rendered, where a 404 from the api renders the app's not-found page, and `ui/app/admin/AdminDashboard.tsx` with four tabs that each load their section when opened, using `adminMessages`, working at 360px

**Checkpoint**: All four stories pass. Figures match the data (SC-006).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T070 [P] Update `dev/docs/prd.md`: §1.6, §2 J2 and Appendix B (the fixed list of ten units, and the rule that an unknown unit is invalid output), and §3 (no in-app admin, and the recipe title exception)
- [ ] T071 [P] Add to `README.md` the SQL line that sets the flag, from `contracts/admin-api.md`, as a step for the owner. Do not rewrite anything else in the README
- [ ] T072 Update `AGENTS.md` where it describes the fixed units and the "every recipe query" rule, only as approved in T001
- [ ] T073 [P] Set S-055 to its finished status in `dev/docs/backlog.yaml`
- [ ] T074 Run the automated checks in `quickstart.md`: the Compose test overlay, `cd api && uv run ruff check .`, and `cd ui && npm test && npm run lint && npm run typecheck`
- [ ] T075 Run `api/tests/fixtures/ai_eval/canned_beans.txt` by hand against the real model. Expected: unit "lata", name "frijoles"
- [ ] T076 Walk `quickstart.md` steps 1 to 10 in the browser at 360px and 1280px, in both languages, on the isolated stack
- [ ] T077 Record the finished change in `dev/memory/` with the procedure in `dev/skills/save_to_memory.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 blocks everything.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all stories.
- **US1 and US2 (Phase 3)**: Depend on Foundational, and are built together.
- **US3 (Phase 4)**: Depends on Foundational. It can run in parallel with Phase 3 except T045's picker test, which needs T038, but it must ship with it.
- **Account removal (Phase 5)**: Depends on Foundational only.
- **US4 (Phase 6)**: Depends on Foundational only. It needs T006 and T007, and nothing from Phases 3 to 5.
- **Polish (Phase 7)**: Depends on the phases included in the release.

### User Story Dependencies

- **US1**: After Foundational.
- **US2**: After Foundational. Shares the save path with US1 (T029, T030, T031).
- **US3**: After Foundational. Releases with US1.
- **US4**: After Foundational. The cut-line.

### Within Each Phase

- Tests are written first and must fail.
- Domain, then ports, then adapters, then application, then routes, then ui.
- These files are touched by more than one task, so those tasks run in order: `api/domain/recipe_draft.py`, `api/domain/cart.py`, `api/application/ports.py`, `api/application/units.py`, `api/api/schemas/recipes.py`, `api/api/deps.py`.

### Parallel Opportunities

- T003 and T004 in Setup.
- T016 to T024 in Phase 3, except that T018 and T019 need `keep_units` planned the same way.
- T041 to T045 in Phase 4.
- T053 to T058 in Phase 6.
- After Foundational, Phases 3 and 4, Phase 5 and Phase 6 can run side by side.

---

## Parallel Example: User Stories 1 and 2

```bash
# Tests first, each in its own file:
Task: "T016 in-flight key test in api/tests/test_recipe_extraction_application.py"
Task: "T017 no stored unit reaches the model, in api/tests/test_prompt_templates.py"
Task: "T018 keep_units on save in api/tests/test_recipe_save_application.py"
Task: "T022 allowed units in ui/lib/capture/draftRules.test.ts"
```

---

## Implementation Strategy

### MVP First

1. Complete Phases 1 and 2.
2. Complete Phase 3 and validate its Independent Test.
3. Complete Phase 4. Stop and validate. This is the smallest release that is safe for a shared kitchen, because Phase 3 alone is not (plan.md, Build order).

### Incremental Delivery

1. Setup + Foundational.
2. US1 + US2 + US3: first release.
3. Account removal rule: invisible until S-054.
4. US4: dashboard, or move it to a later release.

---

## Notes

- Commit after each task or logical group, with one change per commit.
- `git add` only your own files; other agents share the checkout.
- Do not push or deploy without the owner's review.
- Per-recipe "Copy to notebook" has no route today, so only the snapshot half of US3 scenario 7 can be tested. When that route is built, it must keep the unit as stored.
