# Research: Landing page feature tour

No `NEEDS CLARIFICATION` remained in the Technical Context. These are the design decisions behind
the plan.

## R1. Where the feature inventory lives

- **Decision**: One typed TypeScript module, `ui/lib/featureInventory.ts`, holding groups and
  features with their English and Spanish text inline.
- **Rationale**: The page is its only runtime reader, and keeping the text next to the entry makes
  "add a feature in both languages" one edit. TypeScript makes a missing field a compile error; a
  vitest file checks the rules a type cannot (unique ids, non-empty text, group order).
- **Alternatives considered**: A Markdown file in `dev/docs/` (readable, but the page would need a
  build-time parser and two sources drift); a YAML file (same parser cost, and `yaml` is not a ui
  dependency); feature text in `lib/i18n/landing.ts` keyed by id (splits one feature across two
  files, so a feature can be added without its text).

## R2. How demos animate

- **Decision**: Scenes are plain server-rendered markup; each animated element has a CSS keyframe
  animation declared only inside `@media (prefers-reduced-motion: no-preference)`. The element's
  resting style is the scene's final state. All steps of a scene share one loop duration and use
  keyframe percentages for timing, so the scene loops with `animation-iteration-count: infinite`.
- **Rationale**: Same pattern as `CauldronLoader.module.scss`. Reduced motion, no JavaScript, a
  failed hydration or a thumbnail all show the final state for free (FR-008, edge case "demo fails
  to load"). Only `transform` and `opacity` animate, so phones stay smooth.
- **Alternatives considered**: A JavaScript step timer with React state (more code, re-renders,
  harder to keep the reduced-motion path still); an animation library such as Framer Motion (new
  dependency, constitution 2); recorded video or GIF (rejected in clarification Q1).

## R3. Playing only in view, and pausing

- **Decision**: `DemoFrame` (client) wraps each scene. It sets `data-playing="true|false"` on its
  root; the SCSS rule `[data-playing="false"] *` sets `animation-play-state: paused`. Playing is
  `inView && !userPaused`. `inView` comes from one IntersectionObserver per frame (threshold 0.35).
  The pause button is a real `<button>` with `aria-pressed`, labelled in the page language, and is
  not rendered when the visitor prefers reduced motion (nothing moves to pause).
- **Rationale**: Meets FR-007 and WCAG 2.2.2 (auto-moving content over 5 s can be paused). Pausing
  through `animation-play-state` keeps the scene's place instead of restarting it.
- **Alternatives considered**: One page-level observer (fewer observers but couples sections);
  restarting on resume (jumpy).
- **Overview demo**: in the hero, so in view on load; same frame, so FR-002a needs no special case.

## R4. Screen reader text

- **Decision**: The scene markup is `aria-hidden="true"`; `DemoFrame` renders a visually hidden
  paragraph with the scene's description (from `lib/i18n/landing.ts`) and labels the region with
  `role="group"` and `aria-label` set to the demo title.
- **Rationale**: Animated fragments read out of order are noise; one sentence says what the demo
  shows (FR-009).

## R5. Reusing app components inside scenes

- **Decision (revised 2026-11-10, owner request)**: Scenes mount the app's real components with
  invented data in the app's own types (`scenes/data.ts`): `RecipeCard`, `NotebookCard`,
  `CartEntryRow`, `ShoppingLineRow`, `TabList`/`TabButton`, `ServingsControl`, `IngredientLineRow`
  (editable and read only), `AddRecipeOptionsDialog`, `ActionDialog`, `SearchableSelect`,
  `DataTable` with the catalog's `catalogTable` schema, and `Avatar`. Labels come from the app's
  messages. Components that read the api on mount (`ShareRecipeDialog`, `MergeDialog`, the text
  capture sheet, whole screens) are not mounted; their dialog is drawn with `ActionDialog` and the
  same fields.
- **Safety**: the scene wrapper is `inert` and `aria-hidden`, so no control can be focused or
  pressed. Small additive props keep the components from touching the page: `InlineDialogs`
  (ActionDialog drawn in place: no scrim, focus trap, scroll lock or key handling), an optional
  `kitchenId` on `RecipeChips`/`ShoppingRow` and `from` on `CartEntryRow` (no link, so no route
  prefetch), and `locale` on `AddRecipeOptionsDialog`. `PlaceTabs` is not used: its scroll into view
  would move the landing page. Tests check that no scene links anywhere or calls `fetch`.
- **Other-theme card (home demo)**: dark tokens are defined only on `html.dark`, so a single dark
  card on a light page cannot get them. The theme token selectors gain a scope class
  (`html.dark, .theme-dark-scope`; same for light), so the card reads the same values with no copy.
- **Earlier decision, replaced**: scenes drawn with the app's tokens and small look-alike parts,
  keeping data-bound components out. The owner found the demos did not show the real screens.
- **Cost accepted**: a change to one of these components changes the landing demo with it, which is
  the point; scene tests catch a change that breaks it.

## R6. Index and section addresses

- **Decision**: Each group has a stable slug id (`capture`, `notebooks`, `together`, `shop`,
  `ingredients`, `home`), used as the section's `id` and the index link's `#hash`. Sections get
  `scroll-margin-top` so the floating language switch never covers a title. Smooth scrolling is
  set on the signed-out scroller only under `prefers-reduced-motion: no-preference`. That scroller
  is a plain div in `ui/components/AppShell.tsx`, so it gets a `data-scroller="signed-out"`
  attribute for the stylesheet to target.
- **Rationale**: Plain fragment links work without JavaScript and are shareable (US3). Slugs stay
  in English in both languages, so a shared link works for everyone.

## R7. Language

- **Decision**: The page keeps `getServerLocale()` (spec 063). Feature text comes from the
  inventory's `en`/`es` fields; all other text from `landingMessages`. The existing parity test
  covers `landingMessages`; `featureInventory.test.ts` checks every feature and group has non-empty
  text in both languages (FR-013, SC-005). Scene text (recipe names, amounts) also comes from
  `landingMessages` so the Spanish scene shows "una pizca de sal", "2 cebollas grandes".

## R8. Feature list for the first release

- **Decision**: The spec's Context tables are the first inventory, checked against the running app
  in the quickstart walk. Admin-only features are left out. The quick add entry belongs to group 1.
  Note: the backlog lists S-069 twice (refused sites and quick add); the inventory stores story ids
  as strings with a short label, so both can be named without guessing a new number.
