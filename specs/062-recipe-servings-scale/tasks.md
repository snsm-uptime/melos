# Tasks: Scale a Recipe's Servings on the Detail Page

**Input**: Design documents from `specs/062-recipe-servings-scale/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-servings.md, quickstart.md

**Organization**: Grouped by user story (spec.md: US1 P1 see the amounts for other servings, US2 P1 the change is only a view, US3 P2 reset and the saved servings). Phase 2 holds the pure scaling module, the number formatting and the text every story needs. **This feature is ui only: no api change, no migration, no new library** (plan). US2 is mostly guaranteed by design (the number lives in component state); its tasks prove it with tests so a later change cannot break it.

**Tests**: The spec does not request TDD, but constitution §6 requires tests, so test tasks are included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 (story phases only)
- Paths are repository-relative. ui code runs from `ui/`.

## Path Conventions

- ui: `ui/lib/`, `ui/lib/i18n/`, `ui/components/RecipeDetail/`

---

## Phase 1: Setup

- [X] T001 Record the baseline: run `cd ui && npm test && npm run lint && npm run typecheck` and write the pass counts under "Baseline" in `specs/062-recipe-servings-scale/notes.md` (create it). Known at planning time: 88 files, 526 tests, lint and typecheck clean. Also run `git diff --stat api/` and write "api: untouched" so the end can be compared.

---

## Phase 2: Foundational (blocking prerequisites)

- [X] T002 [P] Create `ui/lib/recipeScale.ts` (pure, no React): constants `MIN_SERVINGS = 1` and `MAX_SERVINGS = 100`; `parseServings(text: string): number | null` that trims the text and returns the number only for digits-only text that is a whole number with `1 ≤ n ≤ 100`, else `null` (so "", "abc", "0", "101", "2.5", "-3", "1e2" and "٣" all give `null`); `scaleFactor(chosen: number, saved: number): number` returning `chosen / saved`; and `scaleLine<T extends { quantity: number | null }>(line: T, chosen: number, saved: number): T` returning a copy with `quantity = line.quantity * chosen / saved` when the quantity is not null, and the same object unchanged when it is null (a vague line). The quantity is always computed from the *saved* quantity passed in, never from an earlier scaled value (research R2). `stepServings(current: number, direction: -1 | 1): number` returning `current ± 1` clamped to 1..100 (from above 100, `−` goes to 100).
- [X] T003 [P] Create `ui/lib/recipeScale.test.ts`: `parseServings` accepts "6", " 6 ", "1", "100" and rejects the cases listed in T002; `scaleLine` gives 1 cup → 1.5 for 4→6, 0.5 for 4→2, 2 large → 3 for 4→6 and 2.5 for 4→5, leaves a line with `quantity: null` as the same object, copies unit, size, name, preparation and note unchanged, does not mutate its input (use `Object.freeze`), and returns to the exact saved amounts for 4→6→4 (computed from the saved line each time); `stepServings` clamps at 1 and 100 and steps 120 down to 100.
- [X] T004 [P] Edit `ui/lib/recipeLines.ts` `formatQuantity`: keep "at most 2 decimals, no trailing zero" (0.5 → "0.5", 1.25 → "1.25", 2 → "2"); add an epsilon before rounding so 1.005 shows "1.01"; and when the rounded value is 0 but the quantity is above 0 return `"<0.01"` (research R3: a nonzero result is never shown as 0). Update the file's comment. Extend `ui/lib/recipeLines.test.ts`: 0.004 → "<0.01", 0.005 → "0.01", 0.1 × 1/100 → "<0.01", 1.005 → "1.01", 0.3333 → "0.33", 2 → "2".
- [X] T005 [P] Edit `ui/lib/i18n/recipeDetail.ts`: add to the `en` block and the `es` block (the type `Messages = typeof en` forces both): `servingsControlLabel` ("Servings" / "Porciones"), `fewerServings` ("Fewer servings" / "Menos porciones"), `moreServings` ("More servings" / "Más porciones"), `servingsHint` ("Enter a whole number from 1 to 100." / "Escribe un número entero del 1 al 100."), `makes: (count: number) => string` ("Makes 4" / "Rinde 4"), `resetServings` ("Reset" / "Restablecer"), `scaledAnnouncement: (count: number) => string` ("Amounts for 6 servings" / "Cantidades para 6 porciones"), `stepsAsSaved` ("Steps show the recipe as saved." / "Los pasos muestran la receta como se guardó."). Plain words only, no codes (FR-013).
- [X] T006 Run `cd ui && npm run typecheck && npx vitest run lib/recipeScale lib/recipeLines` and fix failures before Phase 3.

**Checkpoint**: parsing, scaling, formatting and text exist; no screen uses them yet.

---

## Phase 3: User Story 1 - See the amounts for a different number of servings (Priority: P1)

**Goal**: A member sets the servings on the detail page and every measured and counted quantity shows in proportion, at once (spec FR-001 to FR-005, FR-010 to FR-012).

**Independent Test**: Open a 4-serving recipe with "1 cup rice" and "2 large onion"; set 6; rice reads "1.5 cup", onion reads "3 large", salt's note is unchanged; the saved recipe still says 4. (quickstart §2 steps 1 to 3)

- [X] T007 [US1] Create `ui/components/RecipeDetail/ServingsControl.tsx` (client component) with props `{ value: number; onChange: (servings: number) => void; locale: Locale }`: a visible label (`servingsControlLabel`) tied to a text input with `inputMode="numeric"`; a `−` button (`aria-label` `fewerServings`, disabled when `value` is 1) and a `+` button (`moreServings`, disabled when `value` is 100) that call `onChange(stepServings(value, ∓1))`. The input keeps its own *typed text* (starts as `String(value)`, follows `value` when it changes from outside): on each change, if `parseServings(text)` is a number different from `value` call `onChange` with it; if it is `null` (including an empty field) show the hint (`servingsHint`, `role="alert"`) and do not call `onChange`. A valid prefix such as "1" on the way to "12" is valid, so it never shows the hint. On blur, or on Enter, restore the text to `String(value)` and hide the hint. A visually hidden `aria-live="polite"` element says `scaledAnnouncement(value)` after each applied change (not on first render). Use the draft page's field classes (`rounded-[0.75rem] border border-border bg-background px-3 py-1 text-[1rem] text-foreground`, width `w-20`) and the `−`/`+` look of the other icon-sized buttons.
- [X] T008 [P] [US1] Create `ui/components/RecipeDetail/ServingsControl.test.tsx` (jsdom, helper `setValue` as in `components/RecipeEdit/RecipeEditForm.test.tsx`): typing "6" calls `onChange(6)`; typing "1" on the way to "12" calls `onChange(1)` then `onChange(12)` and never shows the hint; "abc", "0", "101", "2.5" and "" call nothing and show the hint; blur restores the applied value and hides the hint; Enter restores too; `+` and `−` call `onChange` with value ± 1; `−` is disabled at 1 and `+` at 100; a `value` of 120 steps down to 100; the live region reads "Amounts for 6 servings" after a change and is empty on first render; the field has an accessible label.
- [X] T009 [US1] Edit `ui/components/RecipeDetail/RecipeDetailView.tsx`: add `"use client"`; keep `const [servings, setServings] = useState(recipe.base_servings)`; compute `lines = useMemo(() => recipe.ingredient_lines.map((l) => scaleLine(l, servings, recipe.base_servings)), [...])` and pass those lines to `IngredientLineRow ... readOnly`; replace the plain `t.servings(...)` text on the Ingredients heading row with `<ServingsControl value={servings} onChange={setServings} locale={locale} />`, keeping the "estimated" `Chip` beside it when `recipe.servings_estimated`; above the steps list show a `<p>` with `t.stepsAsSaved` only while `servings !== recipe.base_servings`. The `steps` array, `recipe`, the Edit link and the Delete handler are not touched. Nothing is written to storage, the address or the router.
- [X] T010 [US1] Extend `ui/components/RecipeDetail/RecipeDetailView.test.tsx` (fixture `recipeFixture` in `ui/components/RecipeDetail/fixtures.ts`: rice 1 cup, onion 2 unit large chopped, salt vague "to taste"; servings 4): setting 8 shows rice "2 cup" and onion "4 large"; setting 2 shows "0.5 cup"; setting 6 shows "1.5 cup" and "3 large"; setting 5 shows "2.5 large"; the salt note, the preparation "chopped", the unit names and the order of the lines are unchanged; an estimated recipe scales from the same saved number and still shows the "estimated" badge; the step texts are identical and the note "Steps show the recipe as saved." appears only while the servings differ; a fixture with 100 lines updates every amount after one change (check the first and the last); a line with quantity 0.01 on a recipe saved for 4, shown at 1 serving (0.0025), reads "<0.01"; Spanish (`locale="es"`) shows "Porciones" and "Los pasos muestran la receta como se guardó.".

**Checkpoint**: quickstart §2 steps 1 to 3 pass; US1 works with no reset and no "Makes".

---

## Phase 4: User Story 2 - The change is only a view and never persists (Priority: P1)

**Goal**: The chosen number is never stored, sent, remembered or shared, and the saved recipe, the edit form and every other view keep the saved servings (spec FR-006 to FR-008, FR-011).

**Independent Test**: Set 6, reload: 4 and the saved amounts; open as another member: 4; open Edit: 4 and saved amounts. (quickstart §2 steps 5 to 7)

- [X] T011 [US2] Extend `ui/components/RecipeDetail/RecipeDetailView.test.tsx` with persistence checks: with a spy on `fetch` and on `Storage.prototype.setItem`, a spy on `document.cookie` setter, and a mocked `next/navigation` router, changing the servings (typing, `+`, `−`) makes no `fetch` call, writes no `localStorage`/`sessionStorage` item, sets no cookie and calls no router method; the `recipe` object passed in is deep-frozen and is not mutated (no exception, `base_servings`, every `quantity` and every step unchanged afterwards); unmounting and rendering the view again shows `recipe.base_servings` and the saved amounts (a reload); the Edit link's `href` is identical before and after a servings change and contains no `servings` text; a recipe with `can_write: false` can still change the servings and shows no Edit or Delete (FR-011).
- [X] T012 [P] [US2] Extend `ui/components/RecipeDetail/RecipeDetailScreen.test.tsx`: after the detail loads and the servings are changed to 6, the Edit link `href` equals what it was at load, and after the member confirms a delete the router call is the same list path as before (the servings never enter the address).
- [X] T013 [P] [US2] Extend `ui/components/RecipeEdit/RecipeEditScreen.test.tsx` (or add a short case in `RecipeEditForm.test.tsx`): the edit form built from a fixture with `base_servings: 4` shows 4 in the servings field and the saved quantities, and its save body (`toUpdateBody`) carries `base_servings: 4`; nothing in `RecipeEditForm.tsx` or `ui/lib/recipeEdit.ts` imports `recipeScale` (assert with a `grep` in the task's check step, see T018).

**Checkpoint**: quickstart §2 steps 5 to 7 pass; the persistence tests would fail if anyone stored the value.

---

## Phase 5: User Story 3 - Go back to the recipe's own servings (Priority: P2)

**Goal**: One action returns to the saved servings, and the page always states what the recipe was written for (spec FR-009).

**Independent Test**: Scale to 7, press Reset: the servings and every amount are the saved ones, and "Makes" and Reset are gone. (quickstart §2 steps 2 and 4)

- [X] T014 [US3] Edit `ui/components/RecipeDetail/RecipeDetailView.tsx`: while `servings !== recipe.base_servings` show beside the control the text `t.makes(recipe.base_servings)` (with the "estimated" `Chip` next to it when the saved servings were estimated) and a **Reset** button (`t.resetServings`) that calls `setServings(recipe.base_servings)`; when they are equal show neither (spec: no reset action is offered when equal). When equal and the recipe is estimated, keep the badge next to the control as in T009.
- [X] T015 [US3] Extend `ui/components/RecipeDetail/RecipeDetailView.test.tsx`: no "Makes" text and no Reset at the saved servings; after changing to 6 the text "Makes 4" and a Reset button appear; Reset returns the control to 4 and every amount to the saved one and removes "Makes", Reset and the steps note; "Makes 4" carries the "estimated" badge for an estimated recipe; going from the saved number to another and back to the saved one takes at most 2 actions (SC-005: one change and one Reset, or one change back); typing the saved number by hand also hides Reset.

**Checkpoint**: quickstart §2 steps 2 and 4 pass; all three stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T016 [P] Run the full checks: `cd ui && npm test && npm run lint && npm run typecheck` and compare with the baseline in `specs/062-recipe-servings-scale/notes.md`. Then `grep -rn "recipeScale" ui/components/RecipeEdit ui/lib/recipeEdit.ts ui/app` must print nothing outside `ui/components/RecipeDetail` and `ui/lib` (the edit form and routes never use the scale), and `git diff --stat api/` must still print nothing.
- [ ] T017 Walk `specs/062-recipe-servings-scale/quickstart.md` §2 and §3 in a browser at phone width and desktop width (constitution §6): the control layout on the Ingredients heading row, wrapping on a narrow screen, the hint, keyboard-only use, and the network log showing no request when the servings change. Record what was checked, and anything not done, in `specs/062-recipe-servings-scale/notes.md`.
- [X] T018 Update `dev/docs/backlog.yaml` S-062 to `status: done` with a `verification` note (counts from T016, what T017 covered, ui only, no migration). Do this only after T016 and T017 pass; if T017 cannot be done, say so in the note as S-027's note does.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. Phase 2 blocks every story.
- **US1 (Phase 3)** needs Phase 2. Within it: T007 → T009; T008 can run with T007; T010 needs T009.
- **US2 (Phase 4)** needs US1's T009 (it tests the view); T011, T012 and T013 touch different files after that.
- **US3 (Phase 5)** needs T009 and edits the same view file, so T014 follows T009 and T015 follows T010 and T011 (same test file; run in order).
- Polish after all stories.

## Parallel Opportunities

- Phase 2: T002, T003, T004 and T005 touch different files and can all run together (T003 needs T002's names to compile; write them together).
- US1: T007 and T008 together; T010 after T009.
- US2: T012 and T013 in parallel with each other once T009 exists.
- Polish: T016 while preparing T017.

## Implementation Strategy

1. **MVP (US1)**: Phases 1 to 3. A member can change the servings and see proportional amounts. Demoable alone, and already view-only because the state is local.
2. **Add US2** (tests that lock the "never persists" behavior), then **US3** (Reset and "Makes N").
3. Check after each phase: `npm run typecheck`, `npm run lint`, the phase's tests. Commit per layer (lib, component, tests, docs); do not push without review (constitution §8). Work on its own branch `062-recipe-servings-scale`, created from the current branch since the detail page it changes is not on `main` yet.
