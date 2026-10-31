# Tasks: Kitchen Side Panel

**Input**: Design documents from `specs/064-kitchen-side-panel/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution principle 6 requires them at each layer, and plan.md lists them.

**Before starting**: The owner signs off on principle 9 (plan.md, Complexity Tracking). Work on branch `064-kitchen-side-panel`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story from spec.md

---

## Phase 1: Setup

- [X] T001 Create branch `064-kitchen-side-panel` from `main`, carrying the uncommitted spec files and `dev/docs/backlog.yaml`
- [X] T002 [P] Add all panel text in English and Spanish, with the pluralized recipe count, in `ui/lib/i18n/sidePanel.ts` (FR-015; the parity test covers it)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Default kitchen data, the side-panel route and the panel frame. No user story can start before this is done.

- [X] T003 Add `default_kitchen_id` to `UserModel` in `api/adapters/persistence/models.py`: "UUID, nullable, FK `kitchens.id`, `ON DELETE SET NULL`"
- [X] T004 Create migration `api/adapters/persistence/migrations/versions/0009_default_kitchen.py` that adds the column and drops it on downgrade, with no backfill (after 0008_cart_servings)
- [X] T005 [P] Write domain tests for the four resolution steps in data-model.md in `api/tests/test_default_kitchen_domain.py`
- [X] T006 Implement the pure resolution rule in `api/domain/default_kitchen.py`: stored if a member and active, else earliest-created active owned, else earliest-joined active, else none
- [X] T007 Add the side-panel repository port and the `GetSidePanelService` and `SetDefaultKitchenService` use cases in `api/application/side_panel.py`, with the port in `api/application/ports.py`: store a resolved result that differs, clear on "none", raise not found for a non-member and a kitchen-archived error for an archived kitchen
- [X] T008 [P] Test both use cases against a fake repository in `api/tests/test_side_panel_application.py`, including that restoring an archived old default does not switch back (research R2)
- [X] T009 Implement `api/adapters/persistence/side_panel.py`: kitchens with role and dates, default read and write, and the recipe count from research R3 (archived kitchens included; personal notebooks through `notebook_membership`)
- [X] T010 Add schemas in `api/api/schemas/side_panel.py` and routes `GET /side-panel` and `PUT /side-panel/default-kitchen` in `api/api/routes/side_panel.py`, returning the statuses and codes in `contracts/side-panel-api.md`, and register the router where the other routers are registered
- [X] T011 Add HTTP tests with Postgres in `api/tests/test_side_panel_integration.py`: `401`, `404` for a non-member, `409 kitchen_archived`, sign-up kitchen for an invitee, count across kitchens and notebooks excludes unreachable and deleted recipes, at most 4 SQL statements for a read with no change
- [X] T012 [P] Add BFF routes `ui/app/api/side-panel/route.ts` and `ui/app/api/side-panel/default-kitchen/route.ts`, following `ui/app/api/kitchens/route.ts`
- [X] T013 [P] Add `fetchSidePanel` and `setDefaultKitchen` with tests in `ui/lib/sidePanelClient.ts` and `ui/lib/sidePanelClient.test.ts`
- [X] T014 Replace `tabKeyFromPath` with `panelEntryFromPath(pathname, defaultKitchenId)` per the table in `contracts/side-panel-ui.md`, with tests, in `ui/lib/appChrome.ts` and `ui/lib/appChrome.test.ts`

**Checkpoint**: The api answers `/side-panel` and the BFF forwards it.

---

## Phase 3: User Story 1 - Move around the app from one left panel (Priority: P1) 🎯 MVP

**Goal**: One left panel reaches the default kitchen, other kitchens and notebooks, in place of the tab bar.

**Independent Test**: With three kitchens, reach each kitchen and the notebooks from the panel, starting on a recipe page.

- [X] T015 [P] [US1] Write panel tests in `ui/components/SidePanel/SidePanel.test.tsx`: entry order, Home opens the default, A-to-Z other kitchens without the default, no group for a single kitchen, current entry marked, last opened recorded
- [X] T016 [US1] Build `ui/components/SidePanel/SidePanel.tsx` with the three regions in `contracts/side-panel-ui.md`, reading the membership store and calling `fetchKitchens` and `fetchSidePanel` on every path change (research R4)
- [X] T017 [US1] Choosing a kitchen or Home in `ui/components/SidePanel/SidePanel.tsx` calls `setLastOpenedKitchen`, then navigates (FR-008)
- [X] T018 [US1] Mount the panel in `ui/components/AppShell.tsx` in place of `TabBar`, with content in a flex row beside it, and give toasts the safe-area padding (research R12); update `ui/components/AppShell.test.tsx`
- [X] T019 [US1] Change `ui/app/home/page.tsx` to redirect to the default kitchen, or show the create prompt when there are none; keep the `/kitchens` redirect in `ui/app/kitchens/page.tsx` (research R7)
- [X] T020 [US1] Remove Back to `/home` from `ui/app/kitchens/[kitchenId]/layout.tsx` and `ui/app/kitchens/KitchenDetailChrome.tsx`, and update `ui/app/kitchens/KitchenDetailChrome.test.tsx`

**Checkpoint**: The panel navigates on desktop. It is still open only (US2) and `/home` management is not yet replaced (US5).

---

## Phase 4: User Story 2 - Open and close the panel (Priority: P1)

**Goal**: Icons only when closed, labels when open, a remembered state, and a phone drawer.

**Independent Test**: Toggle by mouse, touch and keyboard, and compare both states.

- [X] T021 [P] [US2] Add `useSidePanelState` with tests in `ui/components/SidePanel/useSidePanelState.ts` and `ui/components/SidePanel/useSidePanelState.test.ts`: `localStorage["melos_side_panel_open"]`, `"true"` or `"false"`, absent means closed, closed as the server value (research R5)
- [X] T022 [US2] Add closed and open layouts to `ui/components/SidePanel/SidePanel.tsx`: tooltips and accessible names when closed, `size-11` targets, long names cut off with the full name kept for assistive technology and as a tooltip
- [X] T023 [P] [US2] Add `ui/components/SidePanel/KitchenIcon.tsx`: first letter on a rounded square coloured by `ui/lib/avatarColor.ts` from the kitchen id (research R10)
- [X] T024 [US2] Add the phone drawer below `md` in `ui/components/SidePanel/SidePanel.tsx`: backdrop, closes on Escape, backdrop tap and choosing an entry, not persisted (research R6)
- [X] T025 [US2] In `ui/components/AppShell.tsx`, always show the header on app pages below `md`, with the menu button first, beside Back on nested pages
- [X] T026 [P] [US2] Add state, keyboard and drawer tests to `ui/components/SidePanel/SidePanel.test.tsx`

**Checkpoint**: The navigation part of the feature works at phone and desktop width.

---

## Phase 5: User Story 3 - See who I am and what I have added (Priority: P2)

**Goal**: Avatar, alias and recipe count at the top of the panel.

**Independent Test**: With five recipes, check avatar, alias and count; add one and check again.

- [X] T027 [US3] Add the avatar block to `ui/components/SidePanel/SidePanel.tsx`: existing `Avatar` linking to `/account`, alias and pluralized count shown only when open, zero shown rather than hidden
- [X] T028 [US3] Remove `leading` avatars and delete `ui/components/ChromeAvatarLink.tsx`, updating `ui/app/notebooks/NotebookTabScreen.tsx` and any `/account` link it provided
- [X] T029 [P] [US3] Add avatar, zero count and count-refresh tests to `ui/components/SidePanel/SidePanel.test.tsx`

---

## Phase 6: User Story 4 - Log out from the panel (Priority: P2)

**Goal**: Log out exists only as the panel's last entry, and behaves as today.

**Independent Test**: Log out, confirm a protected page needs sign-in, and confirm settings has no log out.

- [X] T030 [US4] Move the sign-out steps to `ui/lib/signOut.ts` unchanged, taking the target page, with a test in `ui/lib/signOut.test.ts`: clear the prefs cache and membership store before and after `POST /api/auth/sign-out`, then `window.location.assign` (research R11)
- [X] T031 [US4] Remove the sign-out control from `ui/components/AccountMenu.tsx`, keep password reset through `ui/lib/signOut.ts`, and update `ui/components/AccountMenu.test.tsx` and the comment in `ui/app/account/page.tsx`
- [X] T032 [US4] Add log out as the last entry, after a divider, in `ui/components/SidePanel/SidePanel.tsx`, with a disabled state while it runs and a test in `ui/components/SidePanel/SidePanel.test.tsx`

---

## Phase 7: User Story 5 - Keep managing kitchens (Priority: P2)

**Goal**: Every kitchen action survives the removal of the list. Depends on US1.

**Independent Test**: Do each action once, starting from the panel, then repeat as a non-owner.

- [X] T033 [US5] Make `unarchiveKitchen` update the membership store, with a test, in `ui/app/kitchens/kitchensClient.ts` (FR-017)
- [X] T034 [P] [US5] Add `ui/components/SidePanel/CreateKitchenDialog.tsx` on `ActionDialog`, with name validation and errors moved from `KitchensPanel`, and a test
- [X] T035 [US5] Add the "Kitchens" row to `ui/components/SidePanel/SidePanel.tsx`: "+" in both states; subtitle and archive toggle open only; the toggle swaps the kitchen entries for archived ones through `fetchKitchens({ archived: true })`
- [X] T036 [US5] Add rename, archive or restore, delete with its confirmation, and set default to `ui/app/kitchens/KitchenDetailChrome.tsx` with the who-and-when rules in `contracts/side-panel-ui.md`; after archive or delete go to `/home`, and after any action refresh the side-panel data
- [X] T037 [US5] Below `md`, put set default, rename, archive or restore and delete in the dots menu in `ui/app/kitchens/KitchenDetailChrome.tsx` (research R8)
- [X] T038 [US5] Pass role, archive state and default state from `ui/app/kitchens/[kitchenId]/page.tsx` to the chrome
- [X] T039 [P] [US5] Add owner, non-owner, archived and already-default tests to `ui/app/kitchens/KitchenDetailChrome.test.tsx`
- [X] T040 [US5] Delete `ui/app/kitchens/KitchensPanel.tsx`, `ui/app/home/HomeKitchensSection.tsx`, `ui/app/home/HomeChrome.tsx`, `ui/components/soft-ledger/TabBar.tsx`, their tests, and unused messages in `ui/lib/i18n/kitchens.ts`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T041 Run `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, `uv run ruff check .` in `api/`, and `npm test && npm run lint && npm run typecheck` in `ui/`; compare with the S-023 baseline
- [X] T042 Run migration 0009 down to 0008 and up again on a scratch database
- [ ] T043 Walk `specs/064-kitchen-side-panel/quickstart.md` in the browser at 1280px and 360px, in English and Spanish
- [X] T044 Record the results and set the S-064 status and verification in `dev/docs/backlog.yaml`
- [X] T045 Last, once all tasks above are done: update `dev/docs/prd.md` to match what was built: the bottom bar in 1.10 and J2, the kitchen switcher in J1, `users.default_kitchen_id` in 1.6, `side-panel` routes in 1.4, the toast position in J4, and a decided item in Appendix D.

---

## Dependencies & Execution Order

- **Setup, then Foundational**: Phase 2 blocks every story.
- **US1** comes first. **US2, US3, US4** depend on US1's panel and can follow in any order.
- **US5** depends on US1. T040 removes the old list last, after every action has its new home.
- **Between T019 and T040** the app has no kitchen list page, so ship the phases together, not one by one.
- **Polish** follows all stories. T045 is the final task.

## Parallel Example

```text
Phase 2: T005, T008, T012, T013
US2:     T021, T023, T026
US5:     T034, T039
```

Tasks in `SidePanel.tsx` touch one file, so run those in order.

## Implementation Strategy

1. Phases 1 and 2, then US1 and US2 give the MVP: navigation in both states.
2. Add US3 and US4, which are small and independent.
3. Add US5 before release, since the feature must not lose any kitchen action.
4. Polish, then update the PRD.
