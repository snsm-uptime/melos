# Tasks: Cauldron Loader

**Input**: Design documents from `specs/065-cauldron-loader/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution principle 6 requires vitest for components, and plan.md lists them. All work is in `ui/`; run `cd ui && npm test` after each phase.

**Before starting**: The owner signs off on principle 9 (plan.md, Complexity Tracking). T001 is the gate: no other task starts until the approval is written in plan.md. Work on branch `065-cauldron-loader`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story from spec.md

---

## Phase 1: Setup

- [X] T001 Gate: confirm the owner's written approval of the principle 9 exception is recorded in `specs/065-cauldron-loader/plan.md` under Complexity Tracking (with who and when). If it is not there, stop and ask; do not start T002. Then create branch `065-cauldron-loader` from `main`, carrying the uncommitted files in `specs/065-cauldron-loader/` and the S-065 entry in `dev/docs/backlog.yaml`
- [X] T002 [P] Add `ui/lib/i18n/loader.ts` exporting `loaderMessages = { en: { loading: "Loading" }, es: { loading: "Cargando" } }` in the style of `ui/lib/i18n/sidePanel.ts`, and add it to the `SETS` map in `ui/lib/i18n/parity.test.ts` (FR-011)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The tilt rule, the geometry and an empty-but-valid component shell. No user story can start before this is done.

- [X] T003 [P] Write tests first in `ui/components/CauldronLoader/tilt.test.ts`, then implement `ui/components/CauldronLoader/tilt.ts` exporting `CAULDRON_TILT_DEFAULT = 25`, `CAULDRON_TILT_IN_BUTTON = 10`, `CAULDRON_TILT_MAX = 45` and `resolveTilt(value: unknown, fallback: number): number`. Rule, verbatim from data-model.md: "Finite number from 0 to 45 → the number; finite number above 45 → `45`; negative finite number → its size, then the 45 limit (`-10` gives `10`, `-90` gives `45`); `0` → `0`; `NaN`, `±Infinity`, `undefined`, `null`, a string → `fallback`". Cover every row
- [X] T004 [P] Write tests first in `ui/components/CauldronLoader/geometry.test.ts`, then implement `ui/components/CauldronLoader/geometry.ts` exporting the `viewBox`, the pivot point near the base of the feet, the cauldron outline points (body, rim, two handles, two feet, drip) and `boundsAt(angleDeg)`. The test rotates every outline point by `CAULDRON_TILT_MAX` degrees in both directions about the pivot and asserts all stay inside the `viewBox` (edge case "small spaces", FR-013). Redraw the shapes by eye from the drawing in spec.md: dark pot with rim, two side handles, two feet, a drip running down from the rim
- [X] T005 Create `ui/components/CauldronLoader/CauldronLoader.tsx` and `ui/components/CauldronLoader/index.ts`: a `"use client"` component with props `tone` (`"page" | "button"`, default `"page"`), `tilt`, `size` (CSS length; page tone: the width, default `3rem`; button tone: the **height**, default `1.2em`, with the width following the drawing's ratio, so a button never grows when it loads), `label`, `className`, as in `contracts/cauldron-loader-ui.md`. Render the markup in that contract: a root `<span>` with inline `--cauldron-tilt` (`${resolveTilt(tilt, tone === "button" ? CAULDRON_TILT_IN_BUTTON : CAULDRON_TILT_DEFAULT)}deg`) and the size (`width` in page tone, `height` in button tone). In page tone the root has `role="status"` and `aria-live="polite"`. In button tone the root has **no** `role` or `aria-live`, because the children of a `<button>` are presentational and a nested status is not announced; the hidden text then becomes part of the button's name and the button's own `aria-busy` is the signal (research R9). Inside, an `aria-hidden` `focusable="false"` svg with a bubbles group (two circles of different radii) and a cauldron group (body, rim, two handles, two feet, drip) built from `geometry.ts`, and a `sr-only` span holding `label ?? loaderMessages[useLocale()].loading`. Use no `id`, `clipPath`, `mask` or gradient (depends on T002, T003, T004)
- [X] T006 Create `ui/components/CauldronLoader/CauldronLoader.module.scss` with the layout only: root `display: inline-block`, svg `display: block; width: 100%; height: auto`, the pivot (`transform-box: view-box; transform-origin` from the pivot in `geometry.ts`) on the cauldron group, and every shape filled with `currentColor` for now (colours come in US3). Import it in `CauldronLoader.tsx` (depends on T005)

**Checkpoint**: `<CauldronLoader />` renders a still, one-colour cauldron. Tilt and geometry tests pass.

---

## Phase 3: User Story 1 - See that the app is working (Priority: P1) 🎯 MVP

**Goal**: Bubbles rise out of the cauldron in a seamless loop, and every page-level wait shows the loader.

**Independent Test**: Open a slow page (network throttled) and watch the loader for 30 seconds. Bubbles keep leaving the mouth, fade out above it, and no jump or restart can be seen.

- [X] T007 [US1] Write markup tests in `ui/components/CauldronLoader/CauldronLoader.test.tsx`: page-tone root has `role="status"` and `aria-live="polite"`; button-tone root has neither and still contains the hidden label text; page tone sets `width` and button tone sets `height` on the root, never both; the svg has `aria-hidden="true"`; the cauldron group holds a body, a rim, two handles, two feet and a drip; the bubble group holds at least two circles with different radii (FR-001, FR-002); the rendered HTML has no `id` attribute; two loaders on one screen render with independent root nodes (depends on T005)
- [X] T008 [US1] In `ui/components/CauldronLoader/CauldronLoader.module.scss`, add the bubble animation. Base style is the still pose: bubbles at fixed visible positions above the mouth, full opacity. Inside `@media (prefers-reduced-motion: no-preference)` add `@keyframes` that move each bubble straight up from the mouth with `opacity` 0 at 0% and 100% (FR-003), the same period of 3.2s for every bubble, `animation-iteration-count: infinite`, `animation-timing-function: ease-in-out`, and a different **negative** `animation-delay` per bubble so bubbles are mid-rise when the loader mounts (FR-016, research R4). Animate only `transform` and `opacity`. The bubble group stays outside the rotating cauldron group so bubbles rise straight up (depends on T006)
- [X] T009 [P] [US1] Replace the pulse blocks in `ui/app/kitchens/[kitchenId]/loading.tsx` with one `<CauldronLoader label={t.loadingKitchen} />` inside the existing `<main role="status" …>` wrapper's place (drop the nested duplicate `role="status"`); remove the `Pulse` helper (FR-015)
- [X] T010 [P] [US1] In `ui/components/ItemChipSelector/ItemChipSelector.tsx`, replace the `SpinnerIcon` in the busy dialog body with `<CauldronLoader />` and drop the `SpinnerIcon` import
- [X] T011 [P] [US1] In `ui/components/StackedListPanel/StackedListPanel.tsx`, replace the `SpinnerIcon` inside the `role="status"` box with `<CauldronLoader label={loadingLabel} />` and drop the duplicate role/label on the box; drop the `SpinnerIcon` import
- [X] T012 [P] [US1] In `ui/app/signup/SignupForm.tsx`, replace the `inviteLoading` text paragraph with `<CauldronLoader label={t.loadingInvite} />`
- [X] T013 [P] [US1] In `ui/components/RecipeList/RecipeList.tsx`, replace the `state.status === "loading"` paragraph with `<CauldronLoader label={t.loading} />`; keep `ui/components/RecipeList/RecipeList.test.tsx` passing (its "Loading recipes" check reads the screen-reader text, so it should hold; adjust the assertion to the `role="status"` element if it does not)
- [X] T014 [P] [US1] In `ui/components/RecipeEdit/RecipeEditScreen.tsx`, replace the loading paragraph inside `<main>` with `<CauldronLoader label={t.loading} />`
- [X] T015 [P] [US1] In `ui/components/RecipeDetail/RecipeDetailScreen.tsx`, replace the loading paragraph with `<CauldronLoader label={t.loading} />`
- [X] T016 [P] [US1] In `ui/components/Cart/CartScreen.tsx`, replace the loading paragraph with `<CauldronLoader label={t.loading} />`
- [X] T017 [P] [US1] In `ui/components/ShoppingList/ShoppingListSection.tsx`, replace the loading paragraph with `<CauldronLoader label={t.loading} />`
- [X] T018 [P] [US1] In `ui/components/ShoppingList/ClosedLists.tsx`, replace both loading paragraphs (two places) with `<CauldronLoader label={t.loading} />`
- [X] T019 [P] [US1] In `ui/app/invites/accept/AcceptInvitePanel.tsx`, while `pending` is true render `<CauldronLoader label={t.accepting} />` instead of the `t.accepting` text; when not pending keep the `t.acceptSuccess` paragraph with `role="status"` (FR-015, analysis G1)
- [X] T020 [US1] In `ui/components/RecipeEdit/RecipeEditForm.tsx`, replace the `checking` paragraph (`t.checkingNames`, `role="status"`) with `<CauldronLoader label={t.checkingNames} size="1.25rem" />` in a left-aligned `px-4` row (FR-015, analysis G1). The same file is edited in T029, so do not run them together
- [X] T021 [US1] Run `cd ui && npm test && npm run lint && npm run typecheck`. Fix any test that asserted the old loading markup (paragraph text, `animate-pulse`, `animate-spin`) in the files touched by T009 to T020 (depends on T008 to T020)

**Checkpoint**: Every page-level wait shows rising bubbles. Buttons and header save actions still use the old spinner (US3).

---

## Phase 4: User Story 2 - Cauldron tilts side to side (Priority: P2)

**Goal**: The cauldron rocks to the configured angle, 25 degrees by default and 10 in a button.

**Independent Test**: Show the loader with no setting and check it rocks to 25 degrees each side. Set another angle and check it rocks to that one.

- [X] T022 [US2] Add tilt tests to `ui/components/CauldronLoader/CauldronLoader.test.tsx`, asserting the root's `--cauldron-tilt` style value: no `tilt` → `25deg`; `tone="button"` → `10deg`; `tilt={10}` → `10deg`; `tilt={0}` → `0deg`; `tilt={-10}` → `10deg`; `tilt={90}` → `45deg`; `tilt={NaN}` and `tilt={"x" as unknown as number}` → the tone default (US2 scenarios 1, 2, 4, 5; FR-005, FR-006)
- [X] T023 [US2] In `ui/components/CauldronLoader/CauldronLoader.module.scss`, inside the same `prefers-reduced-motion: no-preference` block, add the rock `@keyframes`: 0% `rotate(calc(var(--cauldron-tilt) * -1))`, 50% `rotate(var(--cauldron-tilt))`, 100% `rotate(calc(var(--cauldron-tilt) * -1))`, with `ease-in-out` on each half so speed is zero at both ends (FR-007), `infinite`, a period of 3.2s equal to the bubbles' (FR-008, research R4). Apply to the cauldron group, which already has the pivot from T006. Animate only `transform`. With a tilt of `0deg` the rocking has no effect and the bubbles keep rising (depends on T008)

**Checkpoint**: The cauldron rocks while bubbles rise straight up. Tilt resolves per the table in data-model.md.

---

## Phase 5: User Story 3 - Loader fits the light and dark themes (Priority: P2)

**Goal**: Accent bubbles on a theme-shaded cauldron on pages, and a two-tone loader inside buttons that stays readable on every button fill.

**Independent Test**: Show the loader in both themes and in a loading Primary, Accent and Ghost button, then switch theme while it runs. Contrast is at least 3:1 everywhere and the animation does not restart.

- [X] T024 [US3] Write `ui/components/CauldronLoader/contrast.test.ts`. Read the colour tokens for light (`:root`) and dark (`html.dark`) from `ui/app/globals.css`, resolve `color-mix(in srgb, A p%, B)` with a small sRGB mixer in the test, and assert WCAG contrast of at least 3 for: accent on background and on surface; the page-tone cauldron `color-mix(in srgb, var(--background) 40%, var(--foreground))` on background and on surface; and, for each button variant in data-model.md (Primary `--on-accent` on `--accent`, Accent `--on-secondary` on `--secondary`, Ghost `--accent` on `color-mix(in srgb, var(--accent) 8%, var(--surface))`, header icon button `--accent` on `--background`), the ink as cauldron and `color-mix(in srgb, ink 80%, fill)` as bubbles and drip against the fill, in both themes (SC-003). Expected values from research R6: cauldron 4.03 and 6.08 on background, Primary bubble 4.54 and 5.79
- [X] T025 [US3] In `ui/components/CauldronLoader/CauldronLoader.module.scss`, replace the `currentColor` fills with the colour tokens: page tone bubbles and drip `var(--accent)`, cauldron `color-mix(in srgb, var(--background) 40%, var(--foreground))`; button tone cauldron `var(--loader-ink, currentColor)`, bubbles and drip `color-mix(in srgb, var(--loader-ink, currentColor) 80%, var(--loader-fill, var(--background)))`. Select the tone with a class set in `CauldronLoader.tsx` from the `tone` prop (depends on T024 passing)
- [X] T026 [US3] In `ui/components/soft-ledger/BaseButton.module.scss`, set `--loader-ink` and `--loader-fill` on `.primary` (`var(--on-accent)`, `var(--accent)`), `.accent` (`var(--on-secondary)`, `var(--secondary)`) and `.ghost` (`var(--accent)`, `color-mix(in srgb, var(--accent) 8%, var(--surface))`). Then restore the variant's normal fill, text and border while loading, with selectors strong enough to beat the disabled rules: `.primary[aria-busy="true"]:disabled`, `.accent[aria-busy="true"]:disabled`, `.ghost[aria-busy="true"]:disabled` (background, color and, for ghost, border-color as in the idle rule), plus `.base[aria-busy="true"] { cursor: progress; }`. Disabled buttons that are not loading keep the grey look (research R6)
- [X] T027 [US3] In `ui/components/soft-ledger/BaseButton.tsx`, replace the private `Spinner` function with `<CauldronLoader tone="button" />`, and delete the `.spinner` rule and `@keyframes base-button-spin` from `BaseButton.module.scss`. The loader's `1.2em` **height** (button tone, T005) matches the button's `line-height: 1.2`, so the button must not grow when loading. Measure the button's height idle and loading in the browser for `sm`, `md` and `lg` and expect the same number (depends on T026)
- [X] T028 [P] [US3] Add loading-button tests to `ui/components/soft-ledger/soft-ledger.test.tsx`: a `loading` Primary, Accent and Ghost button renders the loader with its hidden label text inside the button's name and no nested `role="status"`, stays `disabled`, keeps `aria-busy="true"`, and no longer renders the old spinner svg
- [X] T029 [P] [US3] In `ui/components/RecipeEdit/RecipeEditForm.tsx`, replace the `SpinnerIcon` in the save `HeaderAction` icon with `<CauldronLoader tone="button" size="1.25rem" />` (button tone, so `1.25rem` is the height and matches the `size-5` icon; the `HeaderAction` already carries `label={t.saving}`, so pass `label={t.saving}` to avoid a second hidden "Loading" in its name) and drop the `SpinnerIcon` import
- [X] T030 [P] [US3] In `ui/components/RecipeDraft/RecipeDraftEditor.tsx`, make the same replacement in the save `HeaderAction`
- [ ] T031 [US3] Run `cd ui && npm test && npm run lint && npm run typecheck`, then in a browser trigger loading on sign in, sign up, verify and forgot-password buttons in light and dark and switch theme while one runs: colours change and the animation keeps going (US3 scenario 3) (depends on T024 to T030)
  - _Status 2026-10-31: tests, lint and typecheck pass. The in-app browser part is not done: no stack was running. In headless Chrome on a static copy of the compiled CSS: all three variants and the header icon render in both themes, and idle and loading buttons have the same height at sm, md and lg._

**Checkpoint**: Every loader is themed. Loading buttons show their normal colours and the old spinner is gone from buttons.

---

## Phase 6: User Story 4 - Loader works for people who cannot see or do not want motion (Priority: P3)

**Goal**: A screen reader hears a loading message in the person's language, and reduced motion shows a still cauldron.

**Independent Test**: With a screen reader, hear "Loading" in English and "Cargando" in Spanish. With the OS set to reduce motion, nothing moves over 30 seconds.

- [X] T032 [US4] Add label tests to `ui/components/CauldronLoader/CauldronLoader.test.tsx`: with no provider the text is "Loading"; wrapped in `PreferencesProvider` with locale `es` it is "Cargando"; a `label` prop replaces it; the same holds in button tone, where the text sits in the button's accessible name (`getByRole("button", { name: /Loading/ })` finds a loading Primary button); the svg is `aria-hidden` and carries no `<title>`, so the drawing is not described (FR-011, SC-005). Follow how `ui/components/LanguageChoice.test.tsx` sets the locale
- [X] T033 [US4] Add a reduced-motion guard test in `ui/components/CauldronLoader/CauldronLoader.test.tsx` that reads `CauldronLoader.module.scss` as text and asserts every `animation` declaration and every `@keyframes` sits inside a `@media (prefers-reduced-motion: no-preference)` block, and that the base rules for the bubbles set a visible opacity (FR-012, SC-006, research R5)
- [X] T034 [US4] Check the still pose by eye in a browser with "Reduce motion" on: cauldron upright, bubbles visible at full opacity, nothing moving. If a bubble is invisible, fix its base style in `CauldronLoader.module.scss` (depends on T033)
- [ ] T035 [US4] Announcement check (SC-005, research R9 and analysis A1, A2): with VoiceOver in Safari, open a page that loads slowly (network throttled) in English and in Spanish and note whether the page-level loader is announced ("Loading" / "Cargando", or its specific message). Then focus a loading Primary button and note what is read (expect its label plus the hidden text, and "busy"). If the page-level loader is **not** announced, apply the fallback in research R9: in page tone, mount the `role="status"` root empty and set the hidden text in a `useEffect` right after mount, keep the markup otherwise unchanged, and update the label tests in T032 to wait for the text. Record the result in the T040 notes (depends on T032)
  - _Status 2026-10-31: not done. Needs VoiceOver on a real device. If the page-level loader is not announced, apply the R9 fallback._

**Checkpoint**: All four stories work. Labels read in both languages and reduced motion is still.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T036 Delete `ui/app/icons/SpinnerIcon.tsx`, its export in `ui/app/icons/index.ts` and its `### SpinnerIcon` section in `ui/app/icons/README.md` (research R11). Do this only when no import of `SpinnerIcon` remains (depends on T010, T011, T029, T030)
- [X] T037 [P] Update `ui/COMPONENT_PATTERNS.md`: add a "Loading states" section that points to `ui/components/CauldronLoader/` as the only loading indicator and says to pass `label` for a specific message and `tone="button"` inside buttons. Do not edit `AGENTS.md`; it needs explicit approval
- [X] T038 Sweep (SC-007): run `cd ui && grep -rnE "animate-spin|animate-pulse|SpinnerIcon|base-button-spin" app components` and expect no match. Then run `cd ui && grep -rn 'role="status"' app components --include='*.tsx' | grep -v '\.test\.'` and read each hit: a line that shows a wait (not a result such as a saved, sent or dropped notice) must be the loader. Known results to leave alone: `InviteForm` "invite sent", `CopyButton`, `Toast`, `SavedNotice`, `NameChangeNotice`, `Cart/EditorNotice`, `CartEditingBar`, `CartView` dropped notice, and the confirmation lines in the verify, forgot-password and reset-password forms. Then open `ui/app/notebooks/NotebookTabScreen.tsx`, `ui/app/notebooks/[notebookId]/NotebookRecipesScreen.tsx` and `ui/app/kitchens/KitchenNotebooksSection.tsx` and confirm their `"loading"` state renders no loading element of its own; if one does, replace it as in T013
- [X] T039 Run `cd ui && npm test && npm run lint && npm run typecheck` and record the result against the S-023 baseline
- [ ] T040 Run the browser walk in `quickstart.md` (items 1 to 11) in light and dark, English and Spanish, at 1280px and 360px, and note anything not verified
- [X] T041 Update the S-065 entry in `dev/docs/backlog.yaml`: set `status` to the real state and add a one-line note of what was verified and what was not

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Needs T002 for T005. Blocks every story.
- **US1 (Phase 3)**: Needs Phase 2.
- **US2 (Phase 4)**: Needs T008 (same stylesheet and block). Independent of the call-site swaps in US1.
- **US3 (Phase 5)**: Needs Phase 2. T025 edits the same stylesheet as T008 and T023, so do it after them.
- **US4 (Phase 6)**: Needs T008 and T023 to exist for the guard test.
- **Polish (Phase 7)**: T036 needs the spinner call sites from US1 and US3 done. T040 needs all stories.

### Story Order

- US1 (P1) first: the loader exists and every page wait uses it.
- US2 and US3 (both P2) can follow in either order. US3 touches buttons and header actions; US2 touches only the loader stylesheet.
- US4 (P3) last: it verifies and guards what the earlier stories built.

### Within Each Story

- Tests before the code they cover (T003, T004, T024).
- `CauldronLoader.module.scss` is edited in T006, T008, T023, T025 and T034 in that order. Do not run these in parallel.

### Parallel Opportunities

- Phase 2: T003 and T004 together.
- US1: T009 to T019 touch different files and run together once T005 exists. T020 follows them, and it must finish before T029 because both edit `RecipeEditForm.tsx`.
- US3: T028, T029 and T030 run together after T027.

---

## Parallel Example: User Story 1

```bash
# After T005 and T008, swap the call sites together:
Task: "Replace pulse blocks in ui/app/kitchens/[kitchenId]/loading.tsx"
Task: "Replace SpinnerIcon in ui/components/ItemChipSelector/ItemChipSelector.tsx"
Task: "Replace loading paragraph in ui/components/RecipeList/RecipeList.tsx"
Task: "Replace loading paragraph in ui/components/Cart/CartScreen.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2.
2. Phase 3: bubbles rise and every page wait shows the loader.
3. **Stop and check**: watch it on a throttled page for 30 seconds.

The MVP is one-colour and does not rock. Ship US2 and US3 together before release, because the colours and the loading button fix are what make it presentable and meet SC-003.

### Incremental Delivery

1. Setup + Foundational → shell ready.
2. US1 → bubbles on every page wait.
3. US2 → rocking.
4. US3 → theme colours and button loaders; old spinner gone from buttons.
5. US4 → labels and reduced motion verified.
6. Polish → delete the old icon, sweep, browser walk.

---

## Notes

- The supplied cauldron drawing is not in the repo. Redraw it by eye in `geometry.ts`; the bounds test only checks that it fits.
- Timing (3.2s) is tuned by eye against FR-007 and FR-008. Change it in one place in the stylesheet.
- A loading button changes from grey to its normal colours. This is intended (research R6); flag it in the review.
- Commit per group: foundation, US1 call sites, rocking, colours and buttons, tests for US4, cleanup.
