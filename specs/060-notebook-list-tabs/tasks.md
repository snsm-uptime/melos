# Tasks: Notebook List and Tabs in the UI

**Input**: Design documents from `specs/060-notebook-list-tabs/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/notebook-screens.md, quickstart.md

**Tests**: Included. The constitution (§6) requires vitest component tests for UI, and plan.md's Testing section names them. Each test task is marked so it can be skipped if the team decides otherwise.

**Organization**: Tasks are grouped by user story so each story can be built and checked on its own. All changes are in `ui/`. No api, BFF route, table, migration or dependency changes (plan.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)
- Paths are relative to the repository root.

## Path Conventions

- Web application: `ui/` only (Next.js 16 App Router, React 19, Tailwind 4, vitest)
- BFF routes already exist from spec 056 and are not touched: `ui/app/api/notebooks/route.ts`, `ui/app/api/notebooks/default/route.ts`, `ui/app/api/notebooks/kitchens/[kitchenId]/route.ts`, `ui/app/api/notebooks/[notebookId]/route.ts`

---

## Phase 1: Setup (Baseline)

**Purpose**: Record the state of the ui before any change, so later failures are attributable.

- [X] T001 Run `cd ui && npm test && npm run lint && npm run typecheck` and record any failures that already exist before this feature's changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pieces used by both the Notebook tab (US1) and the kitchen notebooks section (US2). MUST complete before any user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Create the en/es dictionary in `ui/lib/i18n/notebooks.ts` following the shape of `kitchensMessages` in `ui/lib/i18n/kitchens.ts`. Keys: section title, tab title, owner label, owner "unknown", access "owner", access "member", default marker "Default", tab empty state, kitchen empty state, loading error with retry, and the kitchen not-found message (reuse the text of `detailNotFound` from `ui/lib/i18n/kitchens.ts`). Constraint (spec FR-011): "Notebook names MUST be shown as stored, without translation or change. Labels on these screens ... MUST be in English until the account language setting (Story 1.6) exists, and MUST then follow the person's chosen language." Every string has an `en` and an `es` entry; none is hard-coded in a component.
- [X] T003 [P] Create `ui/lib/notebooksClient.ts` with the `NotebookResponse` type and fetch helpers that call the same-origin BFF only: `fetchDefaultNotebook()` → `GET /api/notebooks/default`, `fetchPersonalNotebooks()` → `GET /api/notebooks`, `fetchKitchenNotebooks(kitchenId)` → `GET /api/notebooks/kitchens/{kitchenId}`. `NotebookResponse` fields, as spec 056 defines them: `id`, `name`, `kind`, `owner_alias`, `access`, `is_default`, `kitchen_id`, `kitchen_is_archived`. Each helper returns the parsed answer or a typed error that keeps the HTTP status and any `code` (needed for `alias_required` and `kitchen_not_found`). Follow the style of the existing `ui/app/kitchens/kitchensClient.ts`.
- [X] T004 [P] Create the shared inert card in `ui/components/NotebookCard/NotebookCard.tsx` with `NotebookCard.module.scss` next to it. Props: `name: string`, `ownerAlias: string | null`, `access?: "owner" | "member" | "kitchen_member"`, `isDefault?: boolean`, `locale: "en" | "es"`. Render a notebook-shaped element (cover or spine edge) as an `article` or `li`. It MUST NOT render a link or a button and MUST NOT have a click handler (FR-014, research R6). Show `access` only when it is passed (tab), and show the "Default" text marker only when `isDefault` is `true`. Constraint (data-model Validation): "A `null` owner alias is shown as "unknown"." Labels come from `ui/lib/i18n/notebooks.ts`.
- [X] T005 [P] Write `ui/components/NotebookCard/NotebookCard.test.tsx` (vitest, same style as `ui/components/AccountMenu.test.tsx`). Cases: renders no `a` and no `button`; shows "Default" only when `isDefault` is true; shows "unknown" when `ownerAlias` is null; shows access only when passed; labels switch with `locale`.
- [X] T006 [P] Write `ui/lib/notebooksClient.test.ts` (same style as `ui/app/kitchens/kitchensClient.test.ts`). Cases: each helper calls its BFF path; a 403 with `code: alias_required` is returned as such; a 404 with `kitchen_not_found` is returned as such; a network failure is returned as an error, not as an empty list.

**Checkpoint**: Shared dictionary, client and card exist and their tests pass. User story work can begin.

---

## Phase 3: User Story 1 - See my personal notebooks on the Notebook tab (Priority: P1) 🎯 MVP

**Goal**: A signed-in person with an alias opens the Notebook tab, the default notebook exists, and their personal notebooks are listed as cards with owner, access and the default marker (FR-001 to FR-003).

**Independent Test**: As a person with an alias and no notebooks, open the Notebook tab, then reopen it. Exactly one notebook appears both times, named "{alias}'s Notebook", marked Default, owner = the person, access "owner". No kitchen page lists it.

### Tests for User Story 1 (write before T011 if following TDD)

- [X] T007 [P] [US1] Update `ui/lib/appChrome.test.ts`: `/notebooks` and `/notebooks/...` keep the tab bar (`showsAppChrome`), and `tabKeyFromPath` returns `"notebook"` for them.
- [X] T008 [P] [US1] Write `ui/app/notebooks/NotebookTabScreen.test.tsx`. Cases: calls `GET /api/notebooks/default` before `GET /api/notebooks`; a default failure shows the loading error with retry and does not call the list; a `403 alias_required` redirects to the alias step; cards keep the order the answer gives (oldest first).

### Implementation for User Story 1

- [X] T009 [US1] Add `/notebooks` to `APP_CHROME_PREFIXES` in `ui/lib/appChrome.ts`, and return `"notebook"` from `tabKeyFromPath` for `/notebooks` and `/notebooks/...` paths (research R3).
- [X] T010 [US1] Add the Notebook tab item to the `tabs` array in `ui/components/AppShell.tsx` (key `notebook`, href `/notebooks`, an icon, and a label added to the dictionary AppShell already uses for `tabHome`, in en and es). Update `ui/components/AppShell.test.tsx` to expect the new tab.
- [X] T011 [P] [US1] Create `ui/app/notebooks/notebooks.module.scss` with the shared layout for the tab and the kitchen section (card grid, section spacing, state text). Keep it phone-width first, with no horizontal scroll (quickstart §7).
- [X] T012 [P] [US1] Create `ui/app/notebooks/page.tsx` as a server component. It runs `requireAlias("/notebooks")` first, resolves the locale from the `melos_lang_cache` cookie using the same rule as `resolvePageLocale` in `ui/app/kitchens/[kitchenId]/page.tsx` (`es` or `en`, else `en`), and renders `NotebookTabScreen` with that locale (FR-010, FR-011).
- [X] T013 [US1] Create `ui/app/notebooks/NotebookTabScreen.tsx` as a client component. On mount: call `fetchDefaultNotebook()`; only on success, call `fetchPersonalNotebooks()`. Render each notebook as a `NotebookCard` with `access` and `isDefault`, in the order the answer gives. Constraint (spec FR-012): "Lists MUST show cards in the order the answer gives them (oldest first), and MUST NOT hide, merge or de-duplicate cards." An empty list shows the tab empty state. A failure shows the loading error with a retry button and no list (FR-009). A `403 alias_required` redirects to the alias step. It has no create, rename, delete or copy control (FR-008). Depends on T002, T003, T004, T011.

**Checkpoint**: User Story 1 works alone: the tab appears, the default is created on first open, the list shows the personal notebooks only, and the tests from T007 and T008 pass.

---

## Phase 4: User Story 2 - See a kitchen's notebooks on its page (Priority: P1)

**Goal**: A member opens a kitchen page and sees a notebooks section that lists the kitchen's notebooks as cards. The first open creates the kitchen's first notebook through the list call (FR-004 to FR-007).

**Independent Test**: As Ana, create kitchen "Home" and open its page. Exactly one notebook "ana's (Home) Notebook" is listed, owned by Ana. Reload: the same notebook. Ben, a member, sees the same notebook. An archived kitchen lists its notebooks and shows no add-recipe action.

### Tests for User Story 2 (write before T014 if following TDD)

- [X] T014 [P] [US2] Write `ui/app/kitchens/KitchenNotebooksSection.test.tsx`. Cases: a `404 kitchen_not_found` shows the kitchen not-found message and no cards; an empty list shows the empty state; cards show name and owner only (no access, no default marker); no add-recipe action is rendered, active or archived; cards keep the order the answer gives.

### Implementation for User Story 2

- [X] T015 [US2] Create `ui/app/kitchens/KitchenNotebooksSection.tsx` as a client component. Props: `kitchenId: string`, `isArchived: boolean`, `locale: "en" | "es"`. On mount, call `fetchKitchenNotebooks(kitchenId)` and render a `NotebookCard` per notebook (name and `ownerAlias` only). A `404 kitchen_not_found` shows the kitchen not-found message. Any other failure shows the loading error with retry. Constraint (spec FR-006): "When a kitchen is archived, its notebooks section MUST still list its notebooks to members, and MUST NOT show any add-recipe action." `isArchived` is accepted for the future add-recipe action (S-016) but does not change the output in this feature. Depends on T002, T003, T004, T011.
- [X] T016 [US2] Render `KitchenNotebooksSection` in `ui/app/kitchens/[kitchenId]/page.tsx` in the `detailPrimary` column, under the members list, with a `SectionLabel` from `ui/components/soft-ledger/SectionLabel.tsx`. Pass `kitchenId`, the archive state from the kitchen detail the page already fetches, and the locale the page already resolves. Update any page-level test that asserts the primary column content.

**Checkpoint**: User Story 2 works alone: the section lists the kitchen's notebooks for members, shows the not-found message to non-members, has no add-recipe action, and the tests from T014 pass.

---

## Phase 5: User Story 3 - Lists stay accurate when access changes (Priority: P2)

**Goal**: A person who loses access stops seeing the notebook on the next load. Nothing stale stays on screen. A failed load shows a retry message, never a partial or empty list (FR-009, FR-010).

**Independent Test**: As Ben, a member of Home with its page open, end his membership and reload: the not-found message and no notebook. Stop the api and load the tab: the retry message, no list. Start the api and press retry: the default and the list appear.

### Tests for User Story 3

- [X] T017 [P] [US3] Add cases to `ui/app/notebooks/NotebookTabScreen.test.tsx`: a retry after a failure re-runs the default call and then the list; cards from an earlier load are gone when a new load fails.
- [X] T018 [P] [US3] Add cases to `ui/app/kitchens/KitchenNotebooksSection.test.tsx`: a `403 alias_required` redirects to the alias step and shows no cards; a retry after a failure re-runs the load; cards from an earlier load are gone when a new load fails or returns 404.

### Implementation for User Story 3

- [X] T019 [US3] In `ui/app/kitchens/KitchenNotebooksSection.tsx`, handle `403 alias_required` by redirecting to the alias step, with no cards and no notebook shown (FR-010), and clear the previous list when a load starts or fails (no stale cards).
- [X] T020 [US3] In `ui/app/notebooks/NotebookTabScreen.tsx`, clear the previous list when a load starts or fails, and make the retry button re-run the whole sequence (default, then list) (FR-009, research R8). Confirm that an error from step 1 never calls step 2.

**Checkpoint**: All three stories work independently. Failures show retry, access changes do not leave stale cards, and the tests from T017 and T018 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full checks and browser checks for the whole feature.

- [X] T021 Run `cd ui && npm test && npm run lint && npm run typecheck` and confirm all green (quickstart §1). Failures already present at T001 are reported as such, not fixed here.
- [X] T022 [P] Confirm no write control and no link exists on the two screens: grep `ui/app/notebooks/`, `ui/app/kitchens/KitchenNotebooksSection.tsx` and `ui/components/NotebookCard/` for `<a`, `<Link`, `<button`, `href`, `onClick`. The only button allowed is the retry button in the error state (FR-008, FR-014).
- [ ] T023 Browser check with the Compose stack per quickstart §2 to §5: Notebook tab first visit, reload, shared-family card, kitchen section for Ana and Ben, archived kitchen, non-member not-found, stopped api retry, alias gate. Phone width first (quickstart §7). Record results in the PR description.
- [ ] T024 [P] Browser check of language per quickstart §6: no cookie gives English; `melos_lang_cache=es` gives Spanish labels; notebook names unchanged.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. Start here.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational. Independent of US1 in code, but T016 is a change to the kitchen page, so it can merge at any time.
- **User Story 3 (Phase 5)**: Depends on US1 (T013) and US2 (T015), because it edits both components.
- **Polish (Phase 6)**: Depends on all user stories.

### User Story Dependencies

- **US1 (P1)**: After Foundational. No dependency on US2 or US3.
- **US2 (P1)**: After Foundational. No dependency on US1 or US3.
- **US3 (P2)**: After US1 and US2, because it extends both screens.

### Within Each User Story

- Tests before implementation when following TDD (tests are marked "write before").
- Shared pieces (dictionary, client, card) before screens.
- Styles and server page before the client screen that uses them.
- Story complete before moving to the next priority.

### Parallel Opportunities

- Foundational: T002, T003, T004, T005, T006 touch different files and can run in parallel.
- US1: T007, T008, T011, T012 can run in parallel. T009 and T010 touch different files and can also run in parallel.
- US2: T014 can run while T015 is written, if TDD is followed.
- US3: T017 and T018 touch different test files.
- Polish: T022 and T024 can run in parallel with each other.
- US1 and US2 can be built by different people after Foundational.

---

## Parallel Example: Foundational

```bash
# Launch together (different files, no dependencies):
Task: "T002 Create en/es dictionary in ui/lib/i18n/notebooks.ts"
Task: "T003 Create BFF client in ui/lib/notebooksClient.ts"
Task: "T004 Create inert NotebookCard in ui/components/NotebookCard/NotebookCard.tsx"
Task: "T006 Write ui/lib/notebooksClient.test.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002 to T006)
3. Complete Phase 3: User Story 1 (T007 to T013)
4. **STOP and VALIDATE**: Check the Notebook tab in the browser (quickstart §3)
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → shared pieces ready
2. Add US1 → test independently → MVP (Notebook tab)
3. Add US2 → test independently (kitchen section)
4. Add US3 → failure and access-change behavior
5. Polish → full checks and browser checks

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps each task to a user story for traceability
- Nothing is created, renamed, deleted, shared or copied in this feature. The only writes are the ones spec 056 already makes when the screens load (default notebook on the tab, first notebook on a kitchen page).
- No recipe content, add-recipe action, or tap action on cards (S-016, S-021). Cards stay inert.
- Commit only when asked (constitution §8).
