# Tasks: Share a recipe with a person from the recipe page

**Input**: Design documents from `specs/071-share-recipe-to-user/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/share-api.md, quickstart.md

**Tests**: Included. The constitution (principle 6) requires pytest for domain and application logic, integration tests on Postgres for routes and membership, and vitest for components. The spec does not ask for TDD, so tests are written alongside each task rather than strictly before it.

**Organization**: Grouped by user story so each can be built and tested alone.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 or US2, from spec.md
- Paths are relative to the repo root

## Path Conventions

- api: `api/domain`, `api/application`, `api/adapters/persistence`, `api/api/routes`, `api/api/schemas`, `api/tests`
- ui: `ui/components`, `ui/app`, `ui/lib`

---

## Phase 1: Setup

**Purpose**: Confirm the facts the plan left open, before any code depends on them.

- [X] T001 Read `api/adapters/persistence/migrations/versions/` and the `kitchen_memberships` and `notebook_members` models in `api/adapters/persistence/`; record whether each has a join timestamp, and note the result in `specs/071-share-recipe-to-user/research.md` under R-1
- [X] T002 Confirm `users.default_notebook_id` exists and find the helper that creates a default notebook on first use (`api/application/notebooks.py`); note its name in `specs/071-share-recipe-to-user/research.md` under R-5
- [X] T003 Read the S-018 ingredient-name matcher and record its callable interface and location in `specs/071-share-recipe-to-user/research.md` under R-3
- [X] T004 Ask the owner whether members of archived kitchens count as co-members (plan R-2); record the answer in `specs/071-share-recipe-to-user/research.md`. Default if no answer: include them

**Checkpoint**: research.md has no open items. If T001 finds no join timestamp, the ordering in T010 is alphabetical only and the story notes say so.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pieces that both stories need. No user story work starts until this phase is done.

- [X] T005 [P] Add `ShareRecipientNotFoundError`, `ShareSelfError`, and `ShareRecipientNoDefaultNotebookError` to `api/domain/errors.py`, each mapped to the codes in `contracts/share-api.md`
- [X] T006 [P] Add a `CoMemberDirectory` protocol with `list_co_members(user_id) -> list[CoMemberRecord]` and `is_co_member(user_id, other_id) -> bool` to `api/application/ports.py`
- [X] T007 Implement the `CoMemberDirectory` adapter in `api/adapters/persistence/co_members.py`: one SQL query over kitchen and notebook memberships, distinct by user, excluding the caller, returning `shared_at` as the max join time (or null) per research R-1, ordered by `shared_at` desc then alias case-insensitive (depends on T006)
- [X] T008 [P] Add the `CoMemberRecord` dataclass (`user_id`, `alias`, `shared_at`) to `api/application/recipe_share.py`
- [X] T009 Wire the adapter into the app's dependency container (where `SqlAlchemyRecipeRepository` is wired) in `api/api/deps.py` or the existing wiring module (depends on T007)
- [ ] T010 Write pytest unit tests for the co-member ordering rule against fake ports in `api/tests/application/test_recipe_share.py`: shared-kitchen and shared-notebook peers both appear, caller excluded, duplicates collapsed, `shared_at` desc then alias (depends on T008)
- [X] T011 Write integration tests for the co-member SQL in `api/tests/integration/test_co_members.py` against Postgres: a peer in a shared kitchen only, a peer in a shared notebook only, a peer in both (appears once), a stranger (absent), an archived-kitchen peer per T004 (depends on T007)

**Checkpoint**: Co-member listing works against Postgres and the domain errors exist.

---

## Phase 3: User Story 1 - Share a recipe with a cooking partner (Priority: P1) 🎯 MVP

**Goal**: From a recipe page, the user opens the share popup, picks a co-member, presses send, and the recipe is copied into that person's default notebook. The popup then shows a success message.

**Independent Test**: With two accounts sharing a kitchen, open a recipe as the first, share it to the second through the popup, and confirm the second account's default notebook holds a copy. Spec acceptance scenarios US1 1 to 6.

### Tests for User Story 1

- [ ] T012 [P] [US1] Write application tests for `ShareRecipeService` against fakes in `api/tests/application/test_recipe_share.py`: copy lands in the recipient's default notebook with the recipient as author; source unchanged; recipient not a co-member raises not-found; self-share raises; no default notebook raises and copies nothing (FR-008, FR-011, edge cases)
- [X] T013 [P] [US1] Write integration tests for both routes in `api/tests/integration/test_recipe_share_routes.py`: GET candidates ordering and empty list; POST 201 body shape; 404 for unreadable recipe and for non-co-member recipient with identical bodies; 409 `share_self`; 422 `recipient_no_default_notebook` with no row created; 401 unauthenticated (contracts/share-api.md)
- [X] T014 [P] [US1] Write vitest tests for the popup in `ui/components/ShareRecipeDialog/ShareRecipeDialog.test.tsx`: send disabled with nothing chosen (FR-007); search narrows list and keeps order (FR-005); success replaces list with a message naming the person (FR-009); error keeps selection and shows message (FR-010); double press sends once (R-4)

### Implementation for User Story 1

- [X] T015 [US1] Implement `ListShareCandidatesService` in `api/application/recipe_share.py` that calls `CoMemberDirectory.list_co_members` for the caller (depends on T007, T008)
- [X] T016 [US1] Implement `ShareRecipeService` in `api/application/recipe_share.py`: check the caller can read the source recipe (404 otherwise); check `is_co_member` for the recipient (404 with the same error as an unreadable recipe, no alias leak); refuse self-share; resolve the recipient's default notebook (refuse if unresolvable); call `recipes.copy_one(source, target_notebook, recipient_id)`; run name normalization with the S-018 matcher against the target catalog, target names winning (R-3); add names to the catalog. One transaction, no commit inside the service (depends on T005, T006, T015)
- [X] T017 [US1] Add request and response schemas `ShareCandidate`, `ShareCandidatesResponse`, `ShareRequest`, `ShareResponse` in `api/api/schemas/recipes.py` matching `contracts/share-api.md` (depends on T015)
- [X] T018 [US1] Add `GET /api/recipes/share-candidates` to `api/api/routes/recipes.py` (declare it before `/recipes/{recipe_id}` so it is not captured by the path parameter) and `POST /api/recipes/{recipe_id}/share` in the same file, mapping domain errors to the codes and statuses in the contract (depends on T016, T017)
- [X] T019 [US1] Add a proxy pass-through for the two new routes in the ui BFF, following the existing `/api/*` proxy in `ui/app` (no per-route code if the proxy is generic; verify and note in the PR)
- [X] T020 [P] [US1] Add EN and ES message strings for the popup title, search label, placeholder, empty result, send label, success message naming the person, and each error code in the existing i18n messages under `ui/lib/` (FR-012)
- [X] T021 [US1] Build `ShareRecipeDialog` in `ui/components/ShareRecipeDialog/ShareRecipeDialog.tsx` on `SearchableSelect` with its `action` prop set to the send icon from the invite-by-email form (import from `ui/app/icons/`, do not redraw); disabled until a person is chosen; single-flight send; success and error states per the spec state machine (depends on T018, T020)
- [X] T022 [P] [US1] Add `ui/components/ShareRecipeDialog/index.ts` exporting the component
- [X] T023 [US1] Add the share IconButton (aria-label from i18n) to the recipe page header component (find the current header in `ui/app/` recipe route or `ui/components/RecipeDetail*`), shown for any recipe the user can read, opening `ShareRecipeDialog` (FR-001; depends on T021, T022)

**Checkpoint**: US1 works end to end on the dev stack. Run quickstart steps 1 to 6 and the edge checks for no co-members and send failure.

---

## Phase 4: User Story 2 - Recipient sees a usable copy (Priority: P2)

**Goal**: The copy sits in the recipient's default notebook as their own recipe. They can edit or delete it without affecting the original.

**Independent Test**: Share a recipe, edit the copy as the recipient, confirm the original is unchanged. Spec acceptance scenarios US2 1 and 2.

### Tests for User Story 2

- [X] T024 [P] [US2] Integration test in `api/tests/integration/test_recipe_share_routes.py`: after a share, the recipient's `GET /api/notebooks/{default}/recipes` lists the copy with the recipient's alias as author (US2 scenario 1)
- [X] T025 [P] [US2] Integration test in `api/tests/integration/test_recipe_share_routes.py`: the recipient edits the copy via `PUT /api/recipes/{copy_id}`; the source recipe is unchanged, including its ingredient lines and author (US2 scenario 2, SC-003)
- [X] T026 [P] [US2] Integration test in `api/tests/integration/test_recipe_share_routes.py`: the recipient deletes the copy; the source still exists and is unchanged

### Implementation for User Story 2

- [X] T027 [US2] Confirm in code that the copy has no source link: `copy_one` must not write any column that references the source recipe; if one exists, clear it in `api/adapters/persistence/recipes.py` (FR-011, data-model)
- [X] T028 [US2] Confirm the copy is enqueued for embedding (research note on S-019) by calling the existing `EmbeddingJobs` path in `ShareRecipeService`, so search finds it; add to `api/application/recipe_share.py` (depends on T016)
- [X] T029 [US2] Show the author alias on the copy in the recipient's notebook list if the list does not already show it; verify in `ui/components/` recipe card, change only if needed (US2 scenario 1)

**Checkpoint**: US2 passes its integration tests and the recipient can work with the copy alone.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T030 [P] Run `uv run ruff check` and `uv run pytest` in `api/`; fix any failures in files this feature touched
- [X] T031 [P] Run `npx eslint components/ShareRecipeDialog` and `npx vitest run` in `ui/`; fix failures in files this feature touched
- [X] T032 Check that no real personal data or real aliases appear in tests or fixtures in the new files (constitution principle 4)
- [X] T033 Confirm no secrets, no hard-coded model names, and no new dependencies were added (`git diff -- '*.toml' '*.json' '*.lock'` shows only intended changes)
- [ ] T034 Walk quickstart.md steps 1 to 8 and the edge checks on the isolated stack; record outcomes in `specs/071-share-recipe-to-user/quickstart.md`
- [X] T035 Update `dev/docs/backlog.yaml` S-071 to `in_progress` with notes on the R-1 ordering result and the R-4 gap; move to `backlog-done.yaml` only after T034 passes
- [X] T036 Note in the S-048 entry of `dev/docs/backlog.yaml` that the single-recipe copy step is built under S-071, so S-048 needs only its confirmation step

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies; T001 to T003 can run in parallel, T004 waits on the owner.
- **Foundational (Phase 2)**: depends on Setup. Blocks both stories.
- **US1 (Phase 3)**: depends on Foundational. This is the MVP.
- **US2 (Phase 4)**: depends on US1's copy service (T016). Its tests can be written in parallel with US1 tests, but they run after T016.
- **Polish (Phase 5)**: after the stories it covers.

### Story dependencies

- **US1**: independent once Foundational is done.
- **US2**: builds on the copy from US1 (T016); it adds no new screens.

### Within each story

- Tests written first (T012 to T014), then services (T015, T016), schemas, routes, then UI.
- Routes before the UI that calls them.

### Parallel opportunities

- Phase 1: T001, T002, T003 in parallel.
- Phase 2: T005, T006, T008 in parallel; T007 after T006; T010, T011 after their dependencies.
- US1 tests T012, T013, T014 in parallel; T020 and T022 in parallel with backend work.
- US2 tests T024, T025, T026 in parallel.
- Polish T030 and T031 in parallel.

---

## Parallel Example: User Story 1

```text
# Tests together:
T012 application tests, api/tests/application/test_recipe_share.py
T013 route tests, api/tests/integration/test_recipe_share_routes.py
T014 popup tests, ui/components/ShareRecipeDialog/ShareRecipeDialog.test.tsx

# UI strings alongside backend:
T020 EN/ES messages under ui/lib/
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Complete Phase 1 (answer T004 or take the default).
2. Complete Phase 2.
3. Complete Phase 3 (US1).
4. Stop and validate with quickstart steps 1 to 6.

### Incremental delivery

1. MVP (US1) as above.
2. Add US2 to confirm the copy is independent and searchable.
3. Polish and backlog updates.

---

## Notes

- Commit only when asked. Stage only this feature's files: other agents may share the checkout.
- Tests named above are the ones quickstart.md relies on.

---

## Summary

- **Total tasks**: 36
- **Setup**: 4 (T001 to T004)
- **Foundational**: 7 (T005 to T011)
- **User Story 1 (P1, MVP)**: 12 (T012 to T023)
- **User Story 2 (P2)**: 6 (T024 to T029)
- **Polish**: 7 (T030 to T036)
- **Parallel opportunities**: marked `[P]` in each phase
- **Independent test per story**: in each story's header
- **MVP scope**: User Story 1 (Phases 1 to 3)
