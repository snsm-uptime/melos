---

description: "Task list for the landing page feature tour (S-075)"
---

# Tasks: Landing page feature tour

**Input**: Design documents from `specs/075-landing-feature-tour/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec requires failing tests for one-language text (FR-013, SC-005) and
countable inventory rules (SC-001); the plan names the vitest files.

**Organization**: Tasks are grouped by user story. All paths are relative to the repo root; the
change is ui-only (`ui/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 to US5 from spec.md

---

## Phase 1: Setup

**Purpose**: Folder and exports the stories build on. No new dependency (plan, constitution 2).

- [X] T001 Create `ui/components/LandingTour/` with `index.ts` (empty barrel for now) and `ui/components/LandingTour/scenes/`; confirm with the owner that the new component folder is fine (plan, Constitution Check note on AGENTS.md "new folders")
- [X] T002 [P] Read `ui/components/CauldronLoader/CauldronLoader.module.scss` and `ui/components/Chip/Chip.tsx`, `ui/components/Card/` to note the reduced-motion pattern and the chip/card class exports the scenes will reuse (research R2, R5); record the exact export names as a comment at the top of `ui/components/LandingTour/index.ts`

---

## Phase 2: Foundational (blocking)

**Purpose**: The inventory and the landing copy module every story reads.

- [X] T003 Write `ui/lib/featureInventory.ts` per `contracts/feature-inventory.md`: types `Localized`, `GroupId` (`"capture" | "notebooks" | "together" | "shop" | "ingredients" | "home"`), `FeatureStatus` (`"available" | "planned"`), `FeatureGroup` (`id`, `order` 1..6, `title`, `lede`), `Feature` (`id` kebab-case unique, `group`, `name`, `summary`, `stories` with at least one `S-NNN`, `status`); exports `featureGroups`, `features`, `groupsInOrder()`, `availableFeatures(group)`, `plannedFeatures()`. Pure module: no React, Next.js or client imports
- [X] T004 Fill `featureGroups` in `ui/lib/featureInventory.ts` with the six groups in order capture 1, notebooks 2, together 3, shop 4, ingredients 5, home 6, titles "Capture any recipe", "Your recipe notebooks", "Cook together", "Plan the week and shop", "Ingredients that stay tidy", "Made for your home" and their Spanish titles, each with a one- or two-sentence lede in both languages (spec FR-002, clarification Q3)
- [X] T005 Fill `features` in `ui/lib/featureInventory.ts` from the spec's Context tables: the 25 available features with their stories (S-069 entries labelled by what they are, research R8) and the 5 planned ones (S-029/S-030 assistant, S-044, S-028, S-024, S-068), each with a short name and one plain sentence in English and Spanish; leave out admin-only features; English shopping text says "shopping list" (FR-016)
- [X] T006 [P] Write `ui/lib/featureInventory.test.ts` covering the six invariants in `contracts/feature-inventory.md`: six groups in the given order; unique feature ids; every `Localized` has non-empty trimmed `en` and `es`; every feature has a story matching `/^S-\d{3}$/`; every group has at least one available feature; each feature is in exactly one of its group's available list or the planned list
- [X] T007 Rewrite `ui/lib/i18n/landing.ts` as the landing copy (en and es, same keys): hero `headline`, `intro`, `createAccount`, `signIn`; `indexLabel`; `featuresHeading` (for the list); `comingSoonTitle`, `comingSoonLede`; `closingTitle`, `closingBody`; `demo.pause`, `demo.play`; and per demo id (`overview`, `capture`, `notebooks`, `together`, `shop`, `ingredients`, `home`) a `title`, a screen-reader `description` and the scene strings (invented recipe names, amounts such as "a pinch of salt", "2 large onions", "flour — 1 cup + 3 tbsp" and their Spanish forms, invented member aliases). Remove the old card keys, including "Shopping kitchen" and its Spanish twin "Cocina de compras"; the shopping text says "shopping list" / "lista de compras" (FR-016). Keep the `landingMessages` export name so `ui/lib/i18n/parity.test.ts` still checks it

**Checkpoint**: `cd ui && npm test -- featureInventory parity` passes.

---

## Phase 3: User Story 1 - Walk through what the app does (P1) 🎯 MVP

**Goal**: The signed-out page shows the redesigned hero, six group sections with their feature
lists in order, the "Coming soon" strip and the closing call to action.

**Independent Test**: Signed out, scroll `/` top to bottom: every available feature appears once in
its group, in order; planned ones only in the strip; account buttons at top and end.

### Tests for User Story 1

- [X] T008 [US1] Update `ui/app/page.home.test.tsx`: keep the cauldron-before-name and signed-in redirect tests; add tests that, signed out in `en`, the markup has one `<h1>`, the six section `id`s (`capture`, `notebooks`, `together`, `shop`, `ingredients`, `home`) in that order, then `coming-soon`, then a closing call to action with links to `/signup` and `/sign-in`; that every `availableFeatures(group)` name appears inside its own section and no planned feature name appears in a group section; that the `en` markup contains "shopping list" and not "Shopping kitchen", and the `es` markup contains "lista de compras" and not "Cocina de compras" (FR-016). No `DemoFrame` mock here: US1 renders empty demo slots, and `DemoFrame` does not exist until T018

### Implementation for User Story 1

- [X] T009 [P] [US1] Create `ui/components/LandingTour/LandingHero.tsx`: `h1` with `CauldronMark` (decorative, before the name) and the new headline, the intro, `PrimaryButton` to `/signup` and `GhostButton` to `/sign-in`, and a `demo` slot (ReactNode) for the overview demo added in US2; keep the existing wave background from `ui/app/page.tsx`
- [X] T010 [P] [US1] Create `ui/components/LandingTour/GroupSection.tsx`: `section` with `id={group.id}`, `h2` title, lede, `ul` of the group's available features (name in bold, summary as muted text), and a `demo` slot; one column on phones, text and demo side by side from `md`, alternating sides by group order; no fixed widths so 320 px has no sideways scroll (FR-015)
- [X] T011 [P] [US1] Create `ui/components/LandingTour/ComingSoon.tsx`: `section id="coming-soon"` with `h2` and a `ul` of `plannedFeatures()` (name + summary, no demo, no dates); returns `null` when the list is empty (FR-004)
- [X] T012 [P] [US1] Create `ui/components/LandingTour/ClosingCta.tsx`: short title and line from `landingMessages`, `PrimaryButton` to `/signup`, `GhostButton` to `/sign-in` (FR-012)
- [X] T013 [US1] Export T009 to T012 from `ui/components/LandingTour/index.ts`
- [X] T014 [US1] Rewrite the signed-out branch of `ui/app/page.tsx`: keep `dynamic`, the session redirect, `requireAlias` and `RedirectIfAuthenticated` unchanged (FR-014); render `LandingHero`, then one `GroupSection` per `groupsInOrder()` with `availableFeatures(group.id)` and the locale's text, then `ComingSoon`, then `ClosingCta`; delete the old `FeatureCard`
- [X] T015 [US1] Run `cd ui && npm test -- page.home featureInventory parity && npm run lint && npm run typecheck`; fix failures

**Checkpoint**: The tour reads end to end with empty demo slots.

---

## Phase 4: User Story 2 - See each feature group at work in a demo (P1)

**Goal**: An overview demo in the hero and one animated demo per section, in view only, pausable,
still under reduced motion, with a screen-reader description and no network calls.

**Independent Test**: Each demo plays its scene and loops (group under 15 s, overview under 20 s),
pauses in place, is still under reduced motion, reads its description to a screen reader.

### Tests for User Story 2

- [X] T016 [P] [US2] Write `ui/components/LandingTour/DemoFrame.test.tsx` with a mocked `IntersectionObserver` and `matchMedia`: before intersecting, root has `data-playing="false"`; at ratio ≥ 0.35 it becomes `"true"`; leaving view sets `"false"`; the pause button toggles `aria-pressed` and its label between `demo.pause` and `demo.play` and sets `"false"` while in view; with `prefers-reduced-motion: reduce` no button renders; root has `role="group"` and `aria-label` = title; the scene wrapper is `aria-hidden="true"`; the description is in the markup
- [X] T017 [P] [US2] Write `ui/components/LandingTour/scenes/scenes.test.tsx`: each of the seven scenes rendered with `renderToStaticMarkup` in `en` and `es` contains its final-state strings from `contracts/landing-page.md` (e.g. overview and shop contain "flour — 1 cup + 3 tbsp" in en and its Spanish string in es); no scene markup contains `href=` or `/api/` (FR-010)

### Implementation for User Story 2

- [X] T018 [US2] Create `ui/components/LandingTour/DemoFrame.tsx` (`"use client"`) per `contracts/landing-page.md`: props `id`, `title`, `description`, `pauseLabel`, `playLabel`, `children`; one `IntersectionObserver` (threshold 0.35) sets `inView`; `playing = inView && !userPaused`; root `role="group"`, `aria-label={title}`, `data-playing`; children wrapped in `aria-hidden="true"`; visually hidden `<p>` with the description; pause `<button aria-pressed>` rendered only when `matchMedia("(prefers-reduced-motion: reduce)")` does not match; disconnect the observer on unmount
- [X] T019 [US2] Create `ui/components/LandingTour/DemoFrame.module.scss`: frame surface (border, radius, `bg-surface`-equivalent token, fixed aspect so scenes do not shift layout), pause button placement, and `[data-playing="false"] *` → `animation-play-state: paused` (research R3)
- [X] T020 [US2] Create `ui/components/LandingTour/scenes/scenes.module.scss`: shared keyframes (fade/slide in, highlight, strike-through for bought, number swap) using only `transform` and `opacity`, all declared inside `@media (prefers-reduced-motion: no-preference)`; each element's resting style is the final state (research R2)
- [X] T021 [P] [US2] Create `ui/components/LandingTour/scenes/CaptureScene.tsx`: text, link and photo inputs shown as three small source tiles; pasted text with "a pinch of salt" and "2 large onions" turns into draft lines where salt has a vague note and onion reads "2 unit large"; a "Review" step before save; loop ≤ 15 s; strings from `landingMessages[locale].demo.capture` (FR-006.1)
- [X] T022 [P] [US2] Create `ui/components/LandingTour/scenes/NotebooksScene.tsx`: a notebook of invented recipe cards (chip/card classes from T002), one opened, servings switch from 4 to 2 and amounts halve; loop ≤ 15 s (FR-006.2)
- [X] T023 [P] [US2] Create `ui/components/LandingTour/scenes/TogetherScene.tsx`: a kitchen with two invented members (avatar initials, no photos) and their notebooks, then a recipe sent to one of them with a confirmation line; loop ≤ 15 s (FR-006.3)
- [X] T024 [P] [US2] Create `ui/components/LandingTour/scenes/ShopScene.tsx`: recipes A (3 tbsp flour) and B (1 cup flour) added to the cart, the list line "flour — 1 cup + 3 tbsp" with chips A and B (reuse `Chip`), then a store tab chosen and two lines marked bought; loop ≤ 15 s (FR-006.4)
- [X] T025 [P] [US2] Create `ui/components/LandingTour/scenes/IngredientsScene.tsx`: "onions" and "onion" merged into one name, then shown as "cebolla" under a Spanish label; loop ≤ 15 s (FR-006.5)
- [X] T026 [US2] In `ui/app/globals.css`, make the dark token block also apply to a scoped element: change the `html.dark { ... }` selector to `html.dark, .theme-dark-scope { ... }` (same values, one source), and the light block `:root { ... }` (the one starting with `--background:`) to `:root, .theme-light-scope { ... }`, so one card can show the other theme without copying colour values (a variable declared on the element itself wins over the one inherited from `html`). Leave the `@media (prefers-color-scheme: dark)` block's selector as is. `ui/app/palette.test.ts` finds the blocks by selector text (`blockBody(":root", "--background:")`, `blockBody("html.dark")`) and checks the two dark blocks are identical: update those lookups to the new selectors and keep every existing assertion. Then create `ui/components/LandingTour/scenes/HomeScene.tsx`: the same small card shown in Spanish inside `.theme-light-scope` and English inside `.theme-dark-scope` side by side, crossfading; loop ≤ 15 s (FR-006.6). Run `npm test -- palette` and check the page in both app themes
- [X] T027 [P] [US2] Create `ui/components/LandingTour/scenes/OverviewScene.tsx`: one flow — a recipe captured, saved to a notebook, added to the cart, shown as the line "flour — 1 cup + 3 tbsp" on the shopping list; loop ≤ 20 s (FR-002a)
- [X] T028 [US2] Export `DemoFrame` and the seven scenes from `ui/components/LandingTour/index.ts`; add a `demoFor(id)` map in the same folder that returns the scene for a `DemoId`
- [X] T029 [US2] Wire demos into `ui/app/page.tsx`: the overview `DemoFrame` in `LandingHero`'s demo slot, and each `GroupSection`'s demo slot with its group's `DemoFrame` + scene, titles and descriptions from `landingMessages[locale].demo`. In the same change, add to `ui/app/page.home.test.tsx` a `vi.mock` of `@/components/LandingTour/DemoFrame` that renders its title, description and children, so the page test stays server-only, and assert the seven demo titles appear in order (overview first)
- [X] T030 [US2] Run `cd ui && npm test -- LandingTour page.home && npm run lint && npm run typecheck`; fix failures

**Checkpoint**: US1 + US2 together are the full clarified release (MVP).

---

## Phase 5: User Story 3 - Jump to the feature group I care about (P2)

**Goal**: A short index near the top moves to each section; each section has a shareable address.

**Independent Test**: Each index link moves to its section with the title visible; `/#shop` opens at
Plan the week and shop.

- [X] T031 [P] [US3] Add to `ui/app/page.home.test.tsx`: a `nav` with `aria-label` = `indexLabel` holds six links whose `href`s are `#capture`, `#notebooks`, `#together`, `#shop`, `#ingredients`, `#home` in order, with the group titles as text
- [X] T032 [P] [US3] Create `ui/components/LandingTour/TourIndex.tsx`: `nav` with `aria-label`, a wrapping row of six anchor links (chip-like pills) from `groupsInOrder()`; wraps at 320 px without sideways scroll; export from `index.ts`
- [X] T033 [US3] Render `TourIndex` between `LandingHero` and the first `GroupSection` in `ui/app/page.tsx`
- [X] T034 [US3] In `ui/components/AppShell.tsx`, add `data-scroller="signed-out"` to the signed-out scroll container (the `fixed inset-0 overflow-y-auto` div in the `!showHeader && !showPanel` branch); change nothing else there. In `ui/app/globals.css`, give landing sections (`[data-landing-section]`) a `scroll-margin-top` that clears the floating language switch, and set `scroll-behavior: smooth` on `[data-scroller="signed-out"]` only inside `@media (prefers-reduced-motion: no-preference)` (research R6). Add the `data-landing-section` attribute in `ui/components/LandingTour/GroupSection.tsx` and `ComingSoon.tsx`. Keep the existing `ui/components/AppShell.test.tsx` passing

**Checkpoint**: Index works with and without JavaScript.

---

## Phase 6: User Story 4 - Read the tour in my language (P2)

**Goal**: Every text, list and demo is in the visitor's language (Spanish by default).

**Independent Test**: With `es` and `en`, no text from the other language appears anywhere,
including demos and screen-reader descriptions.

- [X] T035 [US4] Add to `ui/app/page.home.test.tsx`: render with `serverLocale` = `"es"` and `"en"`; for each, every group title, every available feature name, the demo titles and descriptions of that locale appear, and none of the other locale's group titles or demo descriptions do
- [X] T036 [P] [US4] Add to `ui/components/LandingTour/scenes/scenes.test.tsx`: for each scene, the `es` render contains none of the `en` scene strings that differ between languages, and the reverse
- [X] T037 [US4] Read every Spanish string in `ui/lib/featureInventory.ts` and `ui/lib/i18n/landing.ts` against the app's existing Spanish terms (`ui/lib/i18n/*.ts`: "cuaderno", "cocina", "lista de compras", "cdas", "taza") and align wording so the tour uses the same words as the app

**Checkpoint**: `npm test -- page.home scenes parity featureInventory` passes in both languages.

---

## Phase 7: User Story 5 - Keep the inventory and the page in step (P3)

**Goal**: Adding a feature to the inventory shows it on the page; finished stories update the
inventory.

**Independent Test**: An invented available feature added in a test shows in its section in both
languages; a planned one shows only in the strip.

- [X] T038 [US5] Add to `ui/app/page.home.test.tsx`: mock `@/lib/featureInventory` to add one invented available feature to `shop` and one invented planned feature; assert the first appears inside `#shop` in `en` and `es`, the second only inside `#coming-soon`; with no planned features, `#coming-soon` is absent
- [X] T039 [P] [US5] **Owner approval required first** (AGENTS.md "Amendments to Governance": changes to AGENTS.md need explicit approval). Ask the owner; only once approved, in `AGENTS.md` "Backlog files", add one line: when a done story adds, removes or changes a feature a person can use, it updates `ui/lib/featureInventory.ts` in the same change (planned → available when it ships) and its verification note says so (FR-017). If the owner declines, skip this task: T040 alone carries the rule
- [X] T040 [P] [US5] Add a header comment to `ui/lib/featureInventory.ts` stating the same rule and pointing to `specs/075-landing-feature-tour/contracts/feature-inventory.md`

---

## Phase 8: Polish & Cross-Cutting

- [ ] T041 Walk `specs/075-landing-feature-tour/quickstart.md` steps 1 to 12 in the browser (stack up with `./scripts/compose-up.sh -d`); check every listed feature against the running app and fix the inventory for any that does not work today (SC-001, SC-002)
- [ ] T042 [P] Time each demo loop in the browser: group demos under 15 s, overview under 20 s (SC-004); adjust durations in `ui/components/LandingTour/scenes/scenes.module.scss`
- [X] T043 [P] Check contrast of scene text and chips in light and dark against `ui/app/palette.test.ts` tokens; scenes use only existing tokens, with no hard-coded colours anywhere (the `HomeScene.tsx` cards get theirs from `.theme-light-scope` / `.theme-dark-scope`, T026)
- [X] T044 Run the full ui checks: `cd ui && npm test && npm run lint && npm run typecheck`; record any failure that already exists on `main` instead of hiding it
- [X] T045 Update `dev/docs/backlog.yaml` S-075 to `status: verification` with what was tested, and add the PRD note that the Visitor landing page is now the feature tour (`dev/docs/prd.md`, Visitor row and any landing description), per constitution 9

## Phase 9: Background depth (FR-018, SC-007; clarified 2026-11-11)

> **Replaced the same day (owner, 2026-11-11)**: the glows were built (T046–T055, commit 58741e9)
> and then removed at the owner's request; Phase 10 gives the surface band curved edges instead.
> `Glows.tsx`, `glowContrast.test.ts` and the `--glow-*-strength` tokens no longer exist, and SC-007
> was dropped from the spec.

**Goal**: Still, soft orange and purple glows behind the surface band ("Cook together" and "Plan the
week and shop") and behind the closing call to action; the hero keeps its waves and no other
section gets decoration.

**Independent test**: The page test finds the glows in exactly the band and the closing call to
action, hidden from screen readers, with no animation; a contrast test proves foreground and muted
text keep 4.5:1 over the strongest point of each glow in light and dark; screenshots at 1280, 500
and 320 px show the glows with no sideways scrolling.

**Design (fixed here so the tasks need no further choice)**: the glows are vectors, like the hero's
waves: one inline `<svg>` per place, each glow an `<ellipse>` filled with a `<radialGradient>` whose
centre stop is the colour at full strength and whose edge stop is fully transparent. No CSS
`filter: blur()` (a radial gradient gives the same soft edge with a known peak, which the contrast
test can compute). Colours come only from tokens: orange `var(--accent-fill)`, purple
`var(--primary)`. Peak strength per theme comes from two new tokens, `--glow-accent-strength` and
`--glow-primary-strength`, in both theme blocks of `ui/app/globals.css`. Nothing animates.

### Tests for background depth

- [X] T046 [P] Write `ui/components/LandingTour/glowContrast.test.ts` (node env), reading `ui/app/globals.css` with the same `blockBody` / `declarations` helpers as `ui/app/palette.test.ts` (copy them, or move both copies into a shared helper beside palette.test.ts and import it from both). For each theme block (`:root, .theme-light-scope` and `html.dark, .theme-dark-scope`) and each place (band over `--surface`, closing over `--background`): mix each glow colour (`--accent-fill` at `--glow-accent-strength`, `--primary` at `--glow-primary-strength`) over the place's background with plain alpha compositing, then assert the WCAG contrast of `--foreground` and of `--muted` against the result is at least 4.5 (SC-007). Also assert each strength parses as a number between 0.05 and 0.5, so a glow is visible and cannot be a solid wash. It must fail until T048 adds the tokens
- [X] T047 [P] Add to `ui/app/page.home.test.tsx`: the markup has exactly two `data-landing-glows` elements, one inside the `data-landing-band` element and one inside the closing call to action (after `<section id="coming-soon"`); each is an `<svg` with `aria-hidden="true"` and a `pointer-events-none` class; none is inside the hero `<section` or any `<section id="…">` outside the band; and the glows markup contains no `animate` element and no `animation` / `animate-` class (FR-018). It must fail until T050 and T051

### Implementation for background depth

- [X] T048 Add `--glow-accent-strength` and `--glow-primary-strength` to both theme blocks of `ui/app/globals.css` (`:root, .theme-light-scope` and `html.dark, .theme-dark-scope`), with a one-line comment that they are the glows' peak opacity, kept low enough for SC-007. Start from light 0.14 / 0.10 and dark 0.22 / 0.18, then lower any value T046 rejects; record the final values in the comment. Run T046 until it passes
- [X] T049 [P] Create `ui/components/LandingTour/Glows.tsx`, a server component `Glows({ place }: { place: "band" | "closing" })` that renders one `<svg data-landing-glows aria-hidden="true" focusable="false" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 -z-10 h-full w-full">` with a `viewBox` of `0 0 1440 800`, two `<radialGradient>` defs (ids made unique per place, e.g. `glow-band-accent`, so two instances on one page never share an id) whose stops use `style={{ stopColor: "var(--accent-fill)", stopOpacity: "var(--glow-accent-strength)" }}` at offset 0 and `stopOpacity: 0` at offset 1 (same for primary), and two or three large ellipses: for `band`, orange to the upper left and purple to the lower right; for `closing`, one orange and one purple meeting behind the centred text. Export it from `ui/components/LandingTour/index.ts`. Add a JSDoc line naming FR-018 and saying the glows are still on purpose
- [X] T050 In `ui/app/page.tsx`, make the band wrapper `relative isolate overflow-hidden border-y border-border bg-surface` (isolate keeps the `-z-10` glows above the band's own background; overflow-hidden keeps them from causing sideways scrolling, FR-015) and render `<Glows place="band" />` as its first child
- [X] T051 In `ui/components/LandingTour/ClosingCta.tsx`, wrap the existing content in a full-width `<div className="relative isolate overflow-hidden">` with `<Glows place="closing" />` as its first child; keep the inner `mx-auto max-w-2xl …` block and its classes unchanged

### Documentation for background depth

- [X] T052 [P] In `specs/075-landing-feature-tour/contracts/landing-page.md`, add a "Background glows" section: where they are (band and closing only; hero keeps its waves), `data-landing-glows`, `aria-hidden`, no pointer events, still, tokens used, and the SC-007 test. In `specs/075-landing-feature-tour/research.md`, add "R9. Background glows": SVG radial gradients over CSS blur (known peak for the contrast test, same vector approach as the hero), alternatives considered (CSS `filter: blur`, background images)
- [X] T053 [P] In `specs/075-landing-feature-tour/plan.md` "Source Code", add `Glows.tsx` under `components/LandingTour/` and `glowContrast.test.ts`; in `specs/075-landing-feature-tour/quickstart.md`, add a step: in light and dark, the band and the closing call to action show soft orange and purple glows that do not move, the hero still shows its waves, and no other section has decoration. In `specs/075-landing-feature-tour/spec.md` Assumptions, reword "The demos are built from the app's own look with invented data" to say they are the app's own components with invented data (research R5, revised 2026-11-10)

### Verification for background depth

- [X] T054 Build and screenshot with headless Chrome (`cd ui && npx next build && npx next start -p 3123`, then Chrome `--headless=new --force-prefers-reduced-motion` with `--force-dark-mode` and with `--blink-settings=preferredColorScheme=1`) at 1280 and 500 px wide, at `#together` and at the end of the page; confirm the glows show in both themes and nothing scrolls sideways. 320 px is checked in the browser walk (T041), since headless Chrome cannot render narrower than about 500 px
- [X] T055 Run `cd ui && npx vitest run app/page.home.test.tsx components/LandingTour app/palette.test.ts && npx eslint app components/LandingTour && npx tsc --noEmit -p .`; record any failure that already exists on `main`. Add a line to the S-075 note in `dev/docs/backlog.yaml` that FR-018 / SC-007 (background glows) are built and tested. Commit the phase (constitution 8), no push

## Phase 10: Curved surface band edges (FR-018, revised 2026-11-11)

**Goal**: The surface band behind "Cook together" and "Plan the week and shop" has gently curved
top and bottom edges instead of straight borders; no glows anywhere.

**Independent test**: The page test finds two still, hidden curve edges around the band's
sections, filled with `--surface`, and no `border-y` or glow; screenshots show the curves in light
and dark at 1280 and 500 px with no sideways scrolling.

- [X] T056 Remove the glows: delete `ui/components/LandingTour/Glows.tsx` and `ui/components/LandingTour/glowContrast.test.ts`, drop the `--glow-accent-strength` / `--glow-primary-strength` tokens from the three theme blocks of `ui/app/globals.css`, restore `ui/components/LandingTour/ClosingCta.tsx` to its pre-glow markup, and remove the export from `ui/components/LandingTour/index.ts`
- [X] T057 Create `ui/components/LandingTour/SurfaceBand.tsx`: a `relative bg-surface` wrapper with `data-landing-band` and two `Edge` SVGs (`data-landing-band-edge="top|bottom"`, `aria-hidden`, `focusable="false"`, `pointer-events-none`, `preserveAspectRatio="none"`, 32 px tall, 48 px from md) placed just outside the band with 1 px overlap; each fills the band side of a cubic curve with `fill-surface` and strokes the curve with `stroke-border` (non-scaling 1 px). Export it from `ui/components/LandingTour/index.ts` and use it for the banded run in `ui/app/page.tsx` in place of the `border-y` div
- [X] T058 In `ui/app/page.home.test.tsx`, replace the glow test with one for the curved edges (order around the band's sections, hidden, still, `fill-surface`, a `C` curve, no `border-y`, no glows), and narrow the band count to `/data-landing-band(?!-)/g`
- [X] T059 Update FR-018 in `specs/075-landing-feature-tour/spec.md` (and drop SC-007), the contract's "Surface band edges" section, research R9, the plan tree, quickstart step 13 and the S-075 backlog note; build and screenshot light and dark at 1280 and 500 px; run the page, landing and palette tests, lint and types

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T007)** → user stories.
- **US1 (T008–T015)** needs Foundational. It gives the page structure the other stories fill.
- **US2 (T016–T030)** needs US1's demo slots (T009, T010, T014). Scenes T021–T027 are independent of each other.
- **US3 (T031–T034)** needs US1 (T014); independent of US2.
- **US4 (T035–T037)** needs US1; T036 needs US2's scenes.
- **US5 (T038–T040)** needs US1 (ComingSoon, sections); T039 and T040 can start any time after T003.
- **Polish (T041–T045)** after the stories in scope are done.
- **Curved band edges (T056–T059)** replace Phase 9; T041 (browser walk) should run after them.
- **Background depth (T046–T055, replaced)** needed the surface band in `ui/app/page.tsx` and `ClosingCta.tsx` (both exist). Tests T046, T047 first; T048 makes T046 pass; T049 before T050 and T051; T050 and T051 make T047 pass; docs T052, T053 any time; T054, T055 last. T041 (browser walk) should run after this phase so it covers the glows too.

```text
T001 → T003 → T004,T005 → T006 ┐
       T007 ────────────────── ┴→ US1 → US2 ─┐
                                    ├→ US3   ├→ Polish
                                    ├→ US4 ──┤
                                    └→ US5 ──┘
```

## Parallel Examples

- **Foundational**: T006 (inventory tests) alongside T007 (landing copy) once T003 exists.
- **US1**: T009, T010, T011, T012 together (four new files), then T013 and T014.
- **US2**: T016 and T017 (tests) together; then T021–T025 and T027 (six scene files) together after T020. T026 is not [P]: it edits `ui/app/globals.css` and `ui/app/palette.test.ts`, which T034 (US3) also edits, so do not run T026 and T034 at the same time.
- **US3/US4/US5**: T032, T036, T039, T040 touch different files and can run alongside each other.
- **Background depth**: T046 and T047 together (different test files); T049 alongside T048 (new file vs `globals.css`); T052 and T053 alongside any of them. T050 and T051 touch different files but both need T049.

## Implementation Strategy

1. **MVP = US1 + US2** (both P1): the redesigned page with the full walkthrough and its demos.
   US1 alone is shippable if demos slip (empty slots render nothing; sections still list features).
2. Add **US3** (index) and **US4** (language checks); both are small.
3. Add **US5** (process line and dynamic test) last.
4. Add **background depth** (Phase 9, FR-018 / SC-007) after the owner's layout changes; it is
   small and shippable on its own.
5. Commit per phase (constitution 8); do not push before the owner's review.
