---

description: "Task list for 076 Keep Pasted Recipe Text and Offer Personal Notebooks"
---

# Tasks: Keep Pasted Recipe Text and Offer Personal Notebooks

**Input**: Design documents from `/specs/076-keep-pasted-recipe-text/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md

**Tests**: Included. Constitution principle 6 requires vitest for UI components, and plan.md lists the test files.

**Organization**: Tasks are grouped by user story so each story can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1, US2)
- All paths are relative to the repository root. Run UI commands from `ui/`.

---

## Phase 1: Setup

- [X] T001 Create and switch to the feature branch: `git checkout -b 076-keep-pasted-recipe-text` from `main` (work is currently on `main`; constitution 8). Keep the two unrelated uncommitted edits in `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx` and `ui/components/RecipeList/RecipeList.tsx` out of this feature's commits: ask the owner whether to commit them separately first.

---

## Phase 2: Foundational

None. The two stories touch separate code paths: US1 the capture store and sign-in/sign-out, US2 the picker and side panel.

---

## Phase 3: User Story 1 - Pasted text survives a misclick or leaving the app (Priority: P1) 🎯 MVP

**Goal**: The text sheet's text is kept for the browser tab's session. It survives closing the sheet, navigating, leaving the app and reloading. It is cleared on save, discard, a hand-written draft, sign-in and sign-out, and when the tab closes.

**Independent Test**: Paste text, close the sheet, reload, reopen Text: the same text shows. Close the tab and open a new one: the field is empty (quickstart.md "Pasted text").

### Tests for User Story 1

- [X] T002 [P] [US1] Add a `describe("kept text (spec 076)")` block in `ui/lib/capture/captureStore.test.ts`. Clear `window.sessionStorage` and reset the module (`vi.resetModules()` plus a dynamic import) before each test. Cover the lifecycle table in data-model.md:
  - `setText("abc")` writes `sessionStorage["melos.capture.text"] === "abc"`, and `setText("")` removes the key.
  - With the key preset before import, the first `getCaptureState().text` is the stored value.
  - `closeSheet()`, `backToSheet()`, `failSubmit({code:"x"})` and `showDraft(...)` leave the key unchanged.
  - `markSaved("/x")`, `discardDraft()` and `startManualDraft(notebook, "en")` remove it.
  - `clearKeptCaptureText()` removes the key and sets `text` to `""`.
  - A long text (over 5000 chars) is stored and restored in full, not cut.
  - When `sessionStorage.setItem` and `getItem` throw (`vi.spyOn(Storage.prototype, ...)`), `setText` still updates the in-memory `text` and nothing throws.
- [X] T003 [P] [US1] In `ui/lib/signOut.test.ts`, add a test: with the key `melos.capture.text` set and `setText("abc")` called, `signOut("/")` clears both the key and `getCaptureState().text`. Mock `fetch` and `window.location.assign` as the file's existing tests do.

### Implementation for User Story 1

- [X] T004 [US1] In `ui/lib/capture/captureStore.ts`:
  - Add `const KEPT_TEXT_KEY = "melos.capture.text"`, plus private `readKeptText(): string` and `writeKeptText(text: string): void`. Wrap both in `try/catch`, return `""` or do nothing on any error, and do nothing when `typeof window === "undefined"`. `writeKeptText("")` calls `removeItem`.
  - In `update()`, when `patch.text !== undefined && patch.text !== state.text`, call `writeKeptText(patch.text)` after the state assignment.
  - Add a module-level `let keptTextLoaded = false`. In `getCaptureState()`, on the first browser call, set `state = { ...state, text: readKeptText() }` without notifying listeners, then return `state`. The server snapshot stays `EMPTY` (research R2).
  - Export `clearKeptCaptureText(): void`, which calls `writeKeptText("")` and `update({ text: "" })`.
  - Update the file header comment: the text is now kept in the tab's session storage until saved, discarded, signed out or the tab closes (spec 076). Nothing is sent before submit.
- [X] T005 [US1] In `ui/lib/signOut.ts`, import `clearKeptCaptureText` from `@/lib/capture/captureStore`. Call it next to `clearPrefsCache()` at the start of `signOut()` and in the `finally` block.
- [X] T006 [US1] In `ui/app/sign-in/SignInForm.tsx`, call `clearKeptCaptureText()` right before `window.location.assign(result.returnTo)` (line ~59), after a successful sign-in (research R3).
- [X] T007 [US1] In `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx`, update the component doc comment ("The pasted text stays in the store…") to say it also survives a reload and leaving the app for the session (spec 076). No behaviour change is needed: the sheet already reads `capture.text`.
- [X] T008 [US1] Run `npm run test -- captureStore signOut TextCaptureSheet CaptureSpanish` in `ui/` and fix any failures. Existing tests may now see text leaking between tests through `sessionStorage`. Add `window.sessionStorage.clear()` to a global `beforeEach` in `ui/vitest.setup.ts`.

**Checkpoint**: User Story 1 works on its own. Check steps 1–9 of quickstart.md "Pasted text" in a browser.

---

## Phase 4: User Story 2 - The right notebooks are offered when adding a recipe (Priority: P2)

**Goal**: The side panel's Add recipe offers every notebook the member can add to: their personal notebooks, and the notebooks of every active kitchen they belong to. They are grouped and labelled, and the right default is preselected. The notebook page (no picker) and the kitchen page (that kitchen's notebooks) are unchanged.

**Independent Test**: As a member with two own personal notebooks, one shared personal notebook and a kitchen with two notebooks, the side panel lists all five, with the default personal notebook preselected (quickstart.md "Notebook choice").

### Tests for User Story 2

- [X] T009 [P] [US2] In `ui/components/NotebookPicker/` (new `NotebookPicker.test.tsx`, using `testHelpers.ts`), test:
  - An option `{ id, name: "Dinners", detail: "Casa" }` renders the label `"Dinners · Casa"`, and searching "Casa" finds it.
  - An option without `detail` renders `name` only.
  - `dividerBefore: true` reaches `SearchableSelect`, so a divider is drawn above the row.
- [X] T010 [P] [US2] In `ui/components/QuickAddRecipe/QuickAddRecipe.test.tsx`, add cases with `fetch` stubbed for `/api/notebooks` and the membership kitchens store seeded through `replaceMembershipKitchens`:
  - (a) Outside a kitchen, the candidates are the personal notebooks (owned and `access: "member"`) and the notebooks of active kitchens. The default is the `is_default` personal notebook.
  - (b) Notebooks with `kitchen_is_archived: true` are not offered.
  - (c) On `/kitchens/{id}` pages, that kitchen's group comes first. The default is its `is_own_capture_notebook` row, or `OWN_NEW_NOTEBOOK_ID` when it has none, and only that kitchen gets a "new" row.
  - (d) With only personal notebooks, no candidate has `detail` or `dividerBefore`.
  - (e) With no personal notebooks, `/api/notebooks/default` is fetched first, as today.
  - Replace or adjust existing tests that assert the old kitchen-only call to `/api/notebooks/kitchens/{id}`.
- [X] T011 [P] [US2] Add regression tests for FR-009 and FR-010 in `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.test.tsx`:
  - With a single candidate (the notebook-page case), opening Text shows no notebook picker, and the sheet title is that notebook's name.
  - With only one kitchen's notebooks as candidates (the kitchen-page case), the picker lists exactly those.

### Implementation for User Story 2

- [X] T012 [P] [US2] In `ui/components/NotebookPicker/NotebookPicker.tsx`, extend `NotebookPickerOption` to `{ id: string; name: string; detail?: string; dividerBefore?: boolean }`. Map each option to `{ value: id, label: detail ? \`${name} · ${detail}\` : name, dividerBefore }` for `SearchableSelect`.
- [X] T013 [P] [US2] In `ui/components/AddRecipeCallToAction/AddRecipeCallToAction.tsx`, add optional `detail?: string` ("Shown after the name in the picker: 'Personal' or the kitchen's name (spec 076).") and `dividerBefore?: boolean` to `CaptureCandidate`. Check that `startManualDraft`'s choice mapping (`({ id, kind, name, kitchenId })`) still drops them, and that `pickerOptions` in `ui/components/AddRecipeCallToAction/captureNotebook.ts` keeps them when it swaps the "new" row (`{ ...item, id, name }` already does). The text, link and picture sheets already pass candidates straight to `NotebookPicker`, so they need no change.
- [X] T014 [P] [US2] Add a `personalGroup` message to `ui/lib/i18n/notebooks.ts`: en "Personal", es "Personal". Add `kitchenFallback` too: en "Kitchen", es "Cocina", used when a kitchen's name isn't in the membership roster.
- [X] T015 [US2] Rewrite `load()` in `ui/components/QuickAddRecipe/QuickAddRecipe.tsx` (depends on T012–T014), following data-model.md "Side-panel notebook choice":
  - Call `fetchPersonalNotebooks()` once. If no row has `kind === "personal"`, call `fetchDefaultNotebook()` and add it, as today.
  - Personal rows come first, oldest first, as `kind: "personal"`, `kitchenId: null`.
  - Kitchen rows are those with `kind === "kitchen"` and `kitchen_is_archived !== true`. Group them by `kitchen_id`, ordered by the `useMembershipKitchens()` roster, with the current `kitchenId` group first when on a kitchen's pages. Each row is `kind: "kitchen"`, `kitchenId`.
  - Only for the current kitchen, and only when none of its rows has `is_own_capture_notebook`, put `{ id: OWN_NEW_NOTEBOOK_ID, name: notebooksMessages[locale].ownNotebookNew, kind: "kitchen", kitchenId }` first in its group.
  - Only when more than one group is offered: set `detail` to `personalGroup` for personal rows and to the kitchen's name (or `kitchenFallback`) for kitchen rows, and `dividerBefore: true` on the first row of every group after the first.
  - `defaultId`: on a kitchen's pages, its own capture notebook's id, or `OWN_NEW_NOTEBOOK_ID`. Otherwise the `is_default` personal notebook, then the first personal one, then the first row, else `null`.
  - Put the roster's kitchen ids and names in `targetKey` so labels refresh once the roster loads.
  - Remove the now-unused `fetchKitchenNotebooks` import. Update the component doc comment to describe the side panel offering all notebooks (spec 076 FR-008).
- [X] T016 [US2] Run `npm run test -- QuickAddRecipe NotebookPicker AddRecipeCallToAction TextCaptureSheet UrlCaptureSheet PictureCaptureSheet RecipeFromNotebookSheet` in `ui/` and fix any failures.

**Checkpoint**: User Story 2 works on its own. Check steps 1–6 of quickstart.md "Notebook choice" in a browser.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T017 [P] Run `npm run lint && npm run typecheck && npm run test` in `ui/`. Everything must pass.
- [ ] T018 Run the full manual check in `specs/076-keep-pasted-recipe-text/quickstart.md` against `./scripts/compose-up.sh` on desktop and on a phone-width viewport (constitution 6). Note the results in the PR.
- [X] T019 [P] Record the side-panel change in spec 016: add a note under FR-001a in `specs/016-capture-recipe-text/spec.md` saying the side panel offers personal and kitchen notebooks together, superseded by spec 076 FR-008.
- [X] T020 Commit per story (US1, US2, docs), with messages explaining what changed and why. Open a PR to `main` for review (constitution 8).

---

## Dependencies & Execution Order

- **Setup (T001)** comes before everything.
- **US1 (T002–T008)** and **US2 (T009–T016)** are independent and can be done in either order or in parallel.
- Within US1, T002 and T003 (tests) come first, then T004, then T005 and T006 (both need `clearKeptCaptureText`), then T007, then T008.
- Within US2, T009–T011 (tests) and T012–T014 can run in parallel. T015 depends on T012–T014, and T016 comes last.
- **Polish (T017–T020)** comes after both stories.

## Parallel Example

```text
# US1 tests together:
T002 ui/lib/capture/captureStore.test.ts
T003 ui/lib/signOut.test.ts

# US2 groundwork together:
T009 NotebookPicker.test.tsx   T010 QuickAddRecipe.test.tsx   T011 AddRecipeCallToAction.test.tsx
T012 NotebookPicker.tsx        T013 AddRecipeCallToAction.tsx T014 lib/i18n/notebooks.ts
```

## Implementation Strategy

- **MVP**: Phase 1 plus User Story 1 (T001–T008). It fixes the pain the owner named first, losing pasted text, and can ship alone.
- **Increment 2**: User Story 2 (T009–T016). The side-panel notebook choice.
- **Finish**: Polish (T017–T020) and the PR.
