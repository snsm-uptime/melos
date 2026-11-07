---
description: "Task list for S-072: acrylic app chrome and the portfolio palette"
---

# Tasks: Acrylic App Chrome and the Portfolio Palette

**Input**: Design documents from `specs/072-acrylic-nav-palette/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/theme-tokens.md](contracts/theme-tokens.md), [contracts/frost-surface.md](contracts/frost-surface.md), [quickstart.md](quickstart.md)

**Tests**: Included. SC-003 requires a contrast check of every pair, constitution principle 6 requires vitest for components and a browser check before done.

**Scope**: `ui/` only. No api, mcp, migration or dependency change. All paths below are relative to the repo root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 = acrylic bar and menus (P1), US2 = dark palette (P2), US3 = light palette (P3)

---

## Phase 1: Setup

**Purpose**: Know the starting point, so regressions are told apart from failures that were already there.

- [X] T001 Run `cd ui && npm test && npm run lint && npm run typecheck` on the current `main` and write the list of tests that already fail (today's memory notes 2 known failures in `ClosedLists.test.tsx`) at the top of the "Notes" section at the end of `specs/072-acrylic-nav-palette/tasks.md`
- [ ] T002 [P] On the current `main` at 390×844 and 1440×900, record the app top bar's height and its top offset on a notebook page and a recipe page (devtools, element `header[data-app-chrome="header"]` and the recipe page `<header>`), and write them in the "Notes" section of `specs/072-acrylic-nav-palette/tasks.md`; they are the FR-005 reference

---

## Phase 2: Foundational (blocks every story)

**Purpose**: The frost tokens shared by bars (US1) and menus (US1), and read by the contrast test (US2, US3).

- [X] T003 In `ui/app/globals.css`, inside the first `:root` block (theme-independent, next to `--lift-key`), add with a comment citing spec 072 R4: `--frost-alpha: 88%;` `--frost-blur: 8px;` `--frost-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);` `--frost-fade: 300ms;`. The comment says 88% (not the portfolio's 80%) is the lowest opacity at which quiet text passes 4.5:1 over pure black and pure white in both themes

**Checkpoint**: Tokens exist; stories can start.

---

## Phase 3: User Story 1 - The top bar turns to frosted glass as the page scrolls (Priority: P1) 🎯 MVP

**Goal**: Sticky top bars are transparent at the top and frosted once content scrolls under them; dots menus and dropdowns are always frosted. Works on the current (warm) colours.

**Independent Test**: On the current colours, open a long notebook, scroll down and back up; the bar goes transparent → frosted → transparent, content visibly blurred under it; open a dots menu over a recipe photo and see it blurred. Quickstart §2 and §3.

### Tests for User Story 1 (write first, see them fail)

- [X] T004 [P] [US1] Create `ui/components/ChromeScroll.test.tsx`: render `ChromeScrollProvider` with a scroller div and a consumer printing `useChromeScrolled()`; assert `false` at mount, `true` after setting `scrollTop = 1` and dispatching `scroll`, `false` after `scrollTop = 0` + `scroll`; assert the consumer re-renders only on a flip (count renders across two scroll events with `scrollTop` 5 then 10); assert `useChromeScrolled()` returns `false` outside a provider
- [X] T005 [P] [US1] Extend `ui/components/AppShell.test.tsx`: the `header[data-app-chrome="header"]` is a descendant of the element with class `overflow-y-auto` (the main scroller), has classes `frost-bar`, `sticky`, `top-0`, and `data-frosted="false"`; after `scrollTop = 1` + `scroll` on the scroller it is `data-frosted="true"`; when a `progressBar` is set it sits inside the same sticky wrapper as the header
- [X] T006 [P] [US1] Extend `ui/components/RecipeDetail/RecipeDetailView.test.tsx`, `ui/components/RecipeEdit/RecipeEditForm.test.tsx` and `ui/components/RecipeDraft/RecipeDraftEditor.test.tsx`: the page `<header>` has classes `frost-bar` and `frost-bar-phone`, no `bg-background`, and `data-frosted` follows `useChromeScrolled()` (render inside a `ChromeScrollProvider` with a scroller and scroll it)
- [X] T007 [P] [US1] Update `ui/components/MenuSurface/MenuSurface.test.ts`: assert `MenuSurface.module.scss` `.panel` contains `color-mix(in srgb, var(--surface) var(--frost-alpha), transparent)`, `backdrop-filter: blur(var(--frost-blur))`, `-webkit-backdrop-filter: blur(var(--frost-blur))`, a `prefers-reduced-transparency: reduce` rule with `background: var(--surface)`, and an `@supports not` fallback; keep the existing hover/selected assertions

### Implementation for User Story 1

- [X] T008 [US1] Create `ui/components/ChromeScroll.tsx` (beside `ChromeBack.tsx`, `"use client"`) per `contracts/frost-surface.md` §1: `ChromeScrollProvider({ scrollerRef, children })` attaches one `scroll` listener `{ passive: true }` to `scrollerRef.current`, computes `scrollTop > 0`, calls `setState` only when the value changes, re-reads the value when `usePathname()` changes, and removes the listener on unmount; `useChromeScrolled()` returns the context value, `false` without a provider. Makes T004 pass
- [X] T009 [US1] In `ui/app/globals.css`, add the unlayered `.frost-bar` rules from `contracts/frost-surface.md` §2: `.frost-bar { isolation: isolate; }`; `.frost-bar::before { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; background: transparent; box-shadow: none; transition: background-color var(--frost-fade) ease, box-shadow var(--frost-fade) ease, backdrop-filter var(--frost-fade) ease, -webkit-backdrop-filter var(--frost-fade) ease; }`; `.frost-bar[data-frosted="true"]::before { background: color-mix(in srgb, var(--background) var(--frost-alpha), transparent); -webkit-backdrop-filter: blur(var(--frost-blur)); backdrop-filter: blur(var(--frost-blur)); box-shadow: var(--frost-shadow); }`; `@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))` → frosted background at `97%`; `@media (prefers-reduced-transparency: reduce)` → frosted background `var(--background)`, `backdrop-filter: none`; `@media (prefers-reduced-motion: reduce)` → `.frost-bar::before { transition: none; }`; `@media (width >= 48rem)` → `.frost-bar-phone::before { background: transparent; backdrop-filter: none; -webkit-backdrop-filter: none; box-shadow: none; }`. Never put `backdrop-filter`, `filter` or `transform` on `.frost-bar` itself (research R3). Note: the sticky bars are already `position: sticky`, which is a containing block for the absolute `::before`
- [X] T010 [US1] Restructure `ui/components/AppShell.tsx` (`AppShellFrame`, the layout with header or panel): create a `scrollerRef` on the main scroller `div.flex.min-h-0.flex-1.flex-col.overflow-x-hidden.overflow-y-auto`; move the progress bar and the `<header>` inside that scroller as its first child, wrapped in one `div` with `className="frost-bar sticky top-0 z-10 shrink-0"` and `data-frosted` from `useChromeScrolled()` (consumed in a small child component rendered under the provider); wrap the scroller's content in `ChromeScrollProvider scrollerRef={scrollerRef}`, placed so the recipe headers (children) can read it. Keep every header class, padding, safe-area inset and the `md:hidden` logic unchanged (FR-005); keep `ToastViewport` and `languageSwitch` outside the scroller. The no-header layout (`!showHeader && !showPanel`) is unchanged. Makes T005 pass
- [X] T011 [P] [US1] In `ui/components/RecipeDetail/RecipeDetailView.tsx:102`, on the `<header>`: remove `bg-background`, add `frost-bar frost-bar-phone`, add `data-frosted={scrolled ? "true" : "false"}` with `const scrolled = useChromeScrolled();`; keep `max-md:sticky max-md:top-0 max-md:z-10` and all padding classes
- [X] T012 [P] [US1] Same change as T011 in `ui/components/RecipeEdit/RecipeEditForm.tsx:243`
- [X] T013 [P] [US1] Same change as T011 in `ui/components/RecipeDraft/RecipeDraftEditor.tsx:213`. If this page shows a capture progress bar above its own header, put it inside the same frosted header so it stays at the very top (spec edge case "Bars with a progress bar")
- [X] T014 [P] [US1] In `ui/components/MenuSurface/MenuSurface.module.scss` `.panel`: replace `background: var(--surface);` with `background: color-mix(in srgb, var(--surface) var(--frost-alpha), transparent); -webkit-backdrop-filter: blur(var(--frost-blur)); backdrop-filter: blur(var(--frost-blur));`; add `@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) { .panel { background: color-mix(in srgb, var(--surface) 97%, transparent); } }` and `@media (prefers-reduced-transparency: reduce) { .panel { background: var(--surface); backdrop-filter: none; -webkit-backdrop-filter: none; } }`; leave border, radius, shadow and `.item*` rules unchanged (row tints stay opaque, FR-018). Update the file's top comment. Makes T007 pass
- [X] T015 [US1] Check that no consumer overrides the frosted panel background: `ui/components/IconButtonPopup/IconButtonPopup.module.scss` (`.panel` at lines 12 and 34), `ui/components/SearchableSelect/SearchableSelect.tsx:253`, `ui/components/soft-ledger/Select.tsx:217-218`, `ui/components/ChipPicker/ChipOptionsPanel.tsx`; remove any `background`/`bg-*` set on top of `menuSurface.panel`. If `ChipOptionsPanel` is a dropdown list that does not use `menuSurface.panel`, give it `menuSurface.panel` (FR-017 covers "the searchable pickers")
- [X] T016 [US1] Run `cd ui && npm test && npm run lint && npm run typecheck`; fix anything T008–T015 broke (pages whose layout relied on the header being outside the scroller, e.g. `h-full` children; switch them to `flex-1 min-h-0`)
- [ ] T017 [US1] Browser walk quickstart §2 (steps 1–8) and §3 in the current colours, both themes, 390×844 and 1440×900; compare bar height and offset with T002 (FR-005); write the result in the "Notes" section of this file

**Checkpoint**: US1 complete and shippable alone on the warm palette.

---

## Phase 4: User Story 2 - Melos wears the portfolio's colours in the dark theme (Priority: P2)

**Goal**: The dark theme uses the portfolio palette; filled buttons violet, main colour orange, magenta second brand; inputs have 3:1 borders. Light keeps its current look until US3, through interim mappings.

**Independent Test**: Switch to dark and walk the screens of quickstart §4; only new colours, every text passes. `ui/app/palette.test.ts` green for dark.

### Tests for User Story 2

- [X] T018 [P] [US2] Create `ui/app/palette.test.ts`, reusing the parsing approach of `ui/components/CauldronLoader/contrast.test.ts` (read `ui/app/globals.css`, extract the `html.dark { … }` block and the `html:not(.light):not(.dark) { … }` block inside `@media (prefers-color-scheme: dark)`, resolve `var()` and `color-mix(in srgb, A P%, B)` to hex, WCAG luminance). Assert: (a) every **dark** pair of the table in `specs/072-acrylic-nav-palette/contracts/theme-tokens.md` meets its minimum (4.5 for text, 3 for focus ring, icons and `--field-border`), including the frosted rows, computed as `--background` (bar) or `--surface` (menu) mixed with `#000000` and with `#ffffff` at `--frost-alpha`; (b) the two dark blocks declare identical custom properties and values; (c) neither dark block contains any of `#17140f #221e17 #f0e9dc #a89b88 #3a342a #8fbb8e #d48b78 #7ec794 #d9b866 #adbdff`. Encode the pairs as a data table in the test so a reader can match it to the contract

### Implementation for User Story 2

- [X] T019 [US2] In `ui/app/globals.css` `@theme`, add `--color-primary: var(--primary); --color-on-primary: var(--on-primary); --color-accent-fill: var(--accent-fill); --color-field-border: var(--field-border);`
- [X] T020 [US2] In `ui/app/globals.css`, replace the declarations of **both** dark blocks (`html.dark` and `html:not(.light):not(.dark)` under `prefers-color-scheme: dark`, identical) with the dark values from `contracts/theme-tokens.md`: `--background: #141218; --surface: #201d27; --foreground: #e5e7eb; --muted: #9ca3af; --border: #36313f; --field-border: #756e82; --accent: #fd9c21; --accent-fill: #fd9c21; --on-accent: #141218; --primary: #6d1aad; --on-primary: #ffffff; --secondary: #d82591; --on-secondary: #ffffff; --error: #f87171; --danger: #f26363; --danger-strong: #d32f2f; --warn: #facc15; --owed: #4ade80;` and keep `color-scheme: dark`. Drop the `--wb-*` declarations from the dark blocks (set the role properties directly)
- [X] T021 [US2] In `ui/app/globals.css` `:root` (light), add interim values so light looks exactly as today until US3: `--primary: var(--wb-accent); --on-primary: var(--wb-on-accent); --accent-fill: var(--wb-accent); --field-border: var(--wb-border);` with a comment `/* interim until US3 of spec 072 */`. Change the three row tints in `:root` to mix `--accent-fill` instead of `--accent`: `--menu-item-hover: color-mix(in srgb, var(--accent-fill) 10%, var(--surface));` `--menu-item-selected: color-mix(in srgb, var(--accent-fill) 22%, var(--surface));` `--card-selected: color-mix(in srgb, var(--accent-fill) 12%, var(--surface));`, and update the matching strings in `ui/components/MenuSurface/MenuSurface.test.ts`
- [X] T022 [US2] In `ui/components/soft-ledger/BaseButton.module.scss`, `.primary` and its hover/active rules: replace `var(--accent)` with `var(--primary)` and `var(--on-accent)` with `var(--on-primary)` (fill, text, `--loader-ink`, `--loader-fill`, the 78% white/black mixes). Update the doc comments in `ui/components/soft-ledger/PrimaryButton.tsx` ("Moss accent CTA" → violet filled CTA) and `AccentButton.tsx` ("Blue accent" → magenta)
- [X] T023 [P] [US2] Filled primary actions built by hand → `bg-primary text-on-primary` (replacing `bg-accent` and `text-background`): `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx:186`, `ui/components/AddRecipeCallToAction/UrlCaptureSheet.tsx:134`, `ui/components/AddRecipeCallToAction/RecipeFromNotebookSheet.tsx:75` (`primaryClassName`), `ui/components/ShoppingList/DoneButton.tsx:45` (keep its `focus-visible:outline-accent`)
- [X] T024 [P] [US2] Orange areas that carry text → `bg-accent-fill` (text stays `text-on-accent`): `ui/components/Badge/Badge.tsx:23`, `ui/components/LanguageChoice.tsx:63`, `ui/components/SignedOutLanguageSwitch.tsx:48`, `ui/components/DateRangeField/DateRangeField.tsx:293`; and the in-range tint `bg-accent/15` at `DateRangeField.tsx:292` → `bg-accent-fill/15`; `hover:bg-accent/10` in `ui/components/ItemChipSelector/ItemChipSelector.tsx:129` → `hover:bg-accent-fill/10`. Leave `Radio.tsx` and `BoughtToggle.tsx` checked marks on `accent` (research R7)
- [X] T025 [P] [US2] SCSS modules using `--accent`/`--on-accent`/`--secondary`: `ui/app/signup/signup.module.scss`, `ui/app/kitchens/kitchens.module.scss`, `ui/app/notebooks/notebooks.module.scss`, `ui/components/Tabs/Tabs.module.scss`, `ui/components/NotebookCard/NotebookCard.module.scss`, `ui/components/soft-ledger/GhostTextField.module.scss`, `ui/components/FormIconSubmit/FormIconSubmit.module.scss`, `ui/components/ButtonGroup/ButtonGroup.module.scss`, `ui/components/TriSwitch/TriSwitch.module.scss`. Rule per declaration: `background` that is a filled primary action → `var(--primary)` with `color: var(--on-primary)`; any other orange `background` or `color-mix` tint used as a background → `var(--accent-fill)` (text on a solid fill `var(--on-accent)`); `color`, `border-color`, `outline`, `fill`/`stroke` of icons → keep `var(--accent)`. Leave `kitchens.module.scss` `.primaryDanger` as is: its white text on `--danger-strong` is checked in the contract (4.98:1)
- [X] T026 [P] [US2] Remove warm hard-coded fallbacks in `ui/components/IconButton/IconButton.module.scss` (lines 6, 17, 30, 41, 94, 107, 115): delete each `rgba(226, 216, 200, …)` / `rgba(63, 107, 69, …)` declaration that precedes a token-based one; where there is no token-based twin, write it as `color-mix(in srgb, var(--border) 30%, transparent)`, `color-mix(in srgb, var(--accent) 55%, transparent)` or `color-mix(in srgb, var(--accent-fill) 12%, transparent)` matching the comment
- [X] T027 [P] [US2] In `ui/components/soft-ledger/Select.tsx:177`, replace `aria-invalid:border-[#b33]` with `aria-invalid:border-error`, and at lines 204–205 replace the broken `rgba(var(--foreground), 0.55)` with `color-mix(in srgb, var(--foreground) 55%, transparent)`
- [X] T028 [US2] Input outlines → `border-field-border` (FR-013 ≥3:1): in each file below, change `border-border` (or `border-b-…border-border`) **only on `<input>`, `<textarea>`, `<select>`, the `soft-ledger/Select` trigger and checkbox-like `appearance-none` inputs**, never on cards, rows or dividers: `ui/components/MinimalInput/MinimalInput.tsx`, `ui/components/soft-ledger/GhostInput.tsx`, `ui/components/soft-ledger/GhostTextField.module.scss` (its border declaration), `ui/components/soft-ledger/Select.tsx`, `ui/components/SearchableSelect/SearchableSelect.tsx:272`, `ui/components/ShoppingList/BoughtToggle.tsx`, `ui/components/ShoppingList/HandItems.tsx`, `ui/components/Cart/CountField.tsx`, `ui/components/RecipeDetail/ServingsControl.tsx`, `ui/components/RecipeDraft/RecipeDraftEditor.tsx`, `ui/components/RecipeDraft/StepCard.tsx`, `ui/components/RecipeDraft/CategoryChips.tsx`, `ui/components/RecipeEdit/RecipeEditForm.tsx`, `ui/components/AddRecipeCallToAction/TextCaptureSheet.tsx`, `ui/components/AddRecipeCallToAction/UrlCaptureSheet.tsx`, `ui/components/SidePanel/NewKitchenRow.tsx`, `ui/components/DateRangeField/DateRangeField.tsx`, `ui/components/Ingredients/IngredientsScreen.tsx`, `ui/components/RecipeList/RecipeList.tsx`, `ui/components/FormIconSubmit/FormIconSubmit.tsx`, `ui/components/DataTable/DataTable.tsx`, `ui/components/RecipeImagePicker/RecipeImagePicker.tsx`. The global `:focus` rule in `globals.css` keeps `border-color: var(--accent)`
- [X] T029 [US2] Run `cd ui && npm test`; update tests that pin old class names or colours changed by T019–T028 (search the failures for `bg-accent`, `text-background`, `border-border`, `--accent)`), and make `ui/components/CauldronLoader/contrast.test.ts` pass on the new dark values (adjust only its expectations, not its 3:1 rule; if the loader fails 3:1 in dark, change the loader colour, not the rule). T018 must pass
- [ ] T030 [US2] Browser walk quickstart §4 in **dark** only: every listed screen, filled buttons violet/white, links, selected cards, "in cart", selected tab and focus rings orange, `AccentButton` and loader magenta, error red, success green; no warm colour; write the result in "Notes"

**Checkpoint**: Dark theme on the portfolio palette; light unchanged.

---

## Phase 5: User Story 3 - A light theme in the same family (Priority: P3)

**Goal**: Light theme derived from the portfolio palette; no warm colour or `--wb-*` left; theme switching and first paint unchanged.

**Independent Test**: Switch to light and walk the screens of quickstart §4; switch light/dark/system back and forth and hard-reload in each; `palette.test.ts` green for both themes.

### Tests for User Story 3

- [X] T031 [US3] Extend `ui/app/palette.test.ts`: (a) every **light** pair of `contracts/theme-tokens.md` (from the `:root` block) meets its minimum, frosted rows included; (b) `globals.css` contains no `--wb-` and none of the old light hexes `#f7f3ec #fffcf7 #2a241c #6e6456 #e2d8c8 #3f6b45 #a04936 #2f6e48 #a6791f #8b3a2a #4356a3`; (c) `:root` declares every role listed in `specs/072-acrylic-nav-palette/data-model.md` "Theme palette" table, and so does `html.dark`

### Implementation for User Story 3

- [X] T032 [US3] In `ui/app/globals.css` `:root`, delete every `--wb-*` declaration, the interim mappings of T021 and the old `--secondary: #4356a3` comment block, and set the light values from `contracts/theme-tokens.md`: `--background: #f7f5fa; --surface: #ffffff; --foreground: #1d1a24; --muted: #5f596b; --border: #e4e0ea; --field-border: #8b8497; --accent: #a65400; --accent-fill: #fd9c21; --on-accent: #141218; --primary: #6d1aad; --on-primary: #ffffff; --secondary: #d82591; --on-secondary: #ffffff; --error: #c42727; --danger: #b91c1c; --danger-strong: #d32f2f; --warn: #8a6a00; --owed: #15803d;`. Replace the "Warm Balance light (UX-DR1)" comment with one citing spec 072 and the portfolio (`snsm-uptime/portfolio`, `src/app/globals.css`). Keep `html.light { color-scheme: light; }`
- [X] T033 [P] [US3] Check `themeBootScript` (imported in `ui/app/layout.tsx`, defined beside `ui/components/PreferencesProvider.tsx`) still only toggles `html.light`/`html.dark` and needs no change; if it sets any inline colour (e.g. a background to avoid flash), replace it with `#f7f5fa` (light) / `#141218` (dark). Also replace any `themeColor`/`theme-color` metadata value that uses an old colour
- [X] T034 [US3] Run `cd ui && npm test && npm run lint && npm run typecheck`; T031 and `CauldronLoader/contrast.test.ts` must pass for light; fix remaining pinned colours in tests
- [ ] T035 [US3] Browser walk quickstart §4 in **light**, then the theme switching and hard-reload checks (light, dark, system with the OS in each, SC-005), and quickstart §2 step 9 side by side with the portfolio nav in dark (SC-002, the owner judges); write the results in "Notes"

**Checkpoint**: All three stories done.

---

## Phase 6: Polish & Cross-Cutting

- [X] T036 [P] Run the leftover grep from quickstart §1 (`grep -rnE "wb-|#3f6b45|#f7f3ec|#17140f|rgba\(63, 107, 69|rgba\(226, 216, 200" ui/app ui/components`) and fix any hit (SC-004)
- [ ] T037 [P] Performance check quickstart §5 (SC-006): 100-recipe notebook, CPU 4× slowdown, frosted bar; no new long frames compared with `main`; React profiler shows `AppShell` re-rendering only on the at-top flip
- [X] T038 Full check: `cd ui && npm test && npm run lint && npm run typecheck`; only the failures recorded in T001 may remain
- [X] T039 [P] Update the design references that name the old palette: `ui/app/icons/README.md` only if it names colours; the comments in `ui/app/globals.css` that cite "Warm Balance", "moss" or the finance-dashboard button DESIGN.md for colours (point them at spec 072)
- [ ] T040 Set S-072 to `status: verification` in `dev/docs/backlog.yaml` with a `verification` note listing tests run, the browser walk results from "Notes", and any check still open; append one line to `dev/memory/$(date +%d%m%y).md` with the command in `dev/skills/save_to_memory.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001–T002)**: none
- **Foundational (T003)**: after Setup; blocks US1 (frost CSS) and US2/US3 (frosted contrast rows)
- **US1 (T004–T017)**: after T003. Independent of US2/US3
- **US2 (T018–T030)**: after T003. Independent of US1 in code, except both touch `ui/app/globals.css` (T009 vs T019–T021) and `MenuSurface.test.ts` (T007 vs T021): do those edits one after the other, not at once
- **US3 (T031–T035)**: after US2 (T032 removes the interim mappings T021 adds; T031 extends T018's file)
- **Polish (T036–T040)**: after the stories you ship

### Within each story

- Tests first (T004–T007, T018, T031) and see them fail
- US1: T008 → T010 (AppShell needs the provider) → T011–T013 (headers need the hook); T009 and T014 any time after T003
- US2: T019 → T020 → T021 → T022; T023–T028 after T019 (utilities must exist); T029 after all; T030 last
- US3: T031 → T032 → T033/T034 → T035

### Parallel opportunities

- T001 ∥ T002
- US1: T004 ∥ T005 ∥ T006 ∥ T007; then T011 ∥ T012 ∥ T013 ∥ T014 (after T008/T009)
- US2: T023 ∥ T024 ∥ T025 ∥ T026 ∥ T027 (different files, after T019); T028 touches files T023 also edits (`TextCaptureSheet`, `UrlCaptureSheet`) and T024 (`DateRangeField`): run it after them
- Polish: T036 ∥ T037 ∥ T039

## Parallel Example: User Story 1

```text
T004 ChromeScroll.test.tsx      T005 AppShell.test.tsx
T006 recipe header tests        T007 MenuSurface.test.ts
-- then --
T008 ChromeScroll.tsx  →  T010 AppShell.tsx
T009 .frost-bar CSS    ∥  T014 MenuSurface.module.scss
-- then --
T011 RecipeDetailView  ∥  T012 RecipeEditForm  ∥  T013 RecipeDraftEditor
```

## Parallel Example: User Story 2

```text
T018 palette.test.ts (dark)
T019 → T020 → T021 → T022 (globals.css, BaseButton)
-- then --
T023 filled buttons ∥ T024 orange fills ∥ T025 SCSS modules ∥ T026 IconButton ∥ T027 Select
-- then --
T028 input borders → T029 tests → T030 dark walk
```

## Implementation Strategy

### MVP first (US1 only)

1. T001–T003
2. T004–T017: the acrylic bar and menus on the current colours
3. Stop, show the owner the effect (it is what was asked first), commit

### Incremental delivery

1. US1 → commit (the effect)
2. US2 → commit (dark on the portfolio palette; light unchanged thanks to T021)
3. US3 → commit (light derived; warm palette gone)
4. Polish → backlog to verification

One commit per story keeps each change small (constitution 8). Commit on `main` only when asked, staging only this story's files (other agents share the checkout).

## Notes

- Pre-existing failures (T001): on `main` before the change, 17 tests in 5 files fail (none from this feature): `AddRecipeCallToAction.test.tsx` (1), `AddRecipeOptionsDialog.test.tsx` (1), `RecipeFromNotebookSheet.test.tsx` (10), `QuickAddRecipe.test.tsx` (3), `ShoppingList/ClosedLists.test.tsx` (2). They sit in the uncommitted notebook/quick-add work of the checkout. After the change: the same 17, no new failures; `npm run lint` and `npm run typecheck` pass.
- Bar reference measurements (T002): NOT DONE. Needs a browser; WSL has none (see memory "Browser walk on WSL").
- US1 walk (T017): NOT DONE (browser). Unit tests cover the frost state (`AppShell.test.tsx`, recipe view tests, `ChromeScroll.test.tsx`, `MenuSurface.test.ts`).
- Dark walk (T030): NOT DONE (browser).
- Light walk, switching, reload, side by side (T035): NOT DONE (browser).
- Perf check (T037): NOT DONE (browser).
- Decisions taken while implementing:
  - T021 was skipped as an interim step: the final light values (T032) went in with the dark ones in one edit, so light never had an interim state.
  - T018/T031 `palette.test.ts` was written after the CSS change, so it was not seen failing first.
  - `ui/app/icon.test.ts` read the old `--wb-*` tokens. Spec FR-016 keeps the logo unchanged, so the test now pins the logo's Warm Balance colours as constants instead of reading the theme.
  - `ui/components/CauldronLoader/contrast.test.ts`: the primary variant now uses `--primary`/`--on-primary`. The R6 expected values were re-measured on the new palette (cauldron on background 4.39 light / 5.98 dark; bubble on a primary button 6.08 in both).
  - `ChipOptionsPanel` is an inline chip list, not a floating menu, so it was not given `menuSurface.panel`.
  - `GhostTextField.module.scss` has no `--border` declaration (`border: none`), so nothing changed there.
  - T040 (backlog to `verification`, memory line) not done: it depends on the browser walks.
