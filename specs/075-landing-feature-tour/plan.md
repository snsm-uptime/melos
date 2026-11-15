# Implementation Plan: Landing page feature tour

**Branch**: `075-landing-feature-tour` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/075-landing-feature-tour/spec.md`

## Summary

Replace the signed-out landing page (`ui/app/page.tsx`: hero plus three static cards) with a
feature tour: a redesigned hero with an overview demo, an index of six feature groups, one section
per group with its feature list and an animated demo, a "Coming soon" strip of planned features,
and a closing call to action, in English and Spanish.

The feature inventory is one typed data file in the ui (`ui/lib/featureInventory.ts`): groups in a
fixed order, features with English and Spanish text, their stories and a status (`available` or
`planned`). The page reads it, so a feature added there appears with no page change. Demos are
server-rendered scenes built from the app's own tokens and chip/card classes, animated with CSS
keyframes only inside `@media (prefers-reduced-motion: no-preference)`; their resting style is the
final state. A small client wrapper pauses a demo out of view (IntersectionObserver) and gives the
pause/resume button. No api change, no new data, no new library.

## Technical Context

**Language/Version**: TypeScript 5, Next.js 16 App Router, React 19 (ui only)

**Primary Dependencies**: Tailwind 4 and the app's CSS tokens (`app/globals.css`), SCSS modules
(already used, e.g. `CauldronLoader.module.scss`). No new dependency.

**Storage**: N/A. The inventory is source code; nothing is stored.

**Testing**: vitest + jsdom (`renderToStaticMarkup` page tests as in `app/page.home.test.tsx`,
component tests with mocked IntersectionObserver), the i18n parity test, and a browser walk
(constitution 6).

**Target Platform**: Modern browsers, phone (320 px) to desktop, light and dark themes.

**Project Type**: Web application (Next.js BFF ui + FastAPI api); this story touches the ui only.

**Performance Goals**: Group demo loop under 15 s, overview under 20 s (SC-004). Animations use only
`transform` and `opacity` so they stay smooth on phones. No images or video: scenes are markup.

**Constraints**: No sideways scroll at 320 px (FR-015); reduced motion shows the still final state
(FR-008); every string in both languages (FR-013); no calls to capture, AI or save endpoints
(FR-010); invented data only (constitution 4).

**Scale/Scope**: 1 page, 7 demo scenes (overview + 6 groups), about 25 available and 5 planned
features.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and Reuse | No new service; auth layer untouched (redirect of signed-in visitors kept as is); reuses `PrimaryButton`, `GhostButton`, `CauldronMark`, chip and card classes. | Pass |
| 2. Tech Stack Stability | Next.js 16, React 19, Tailwind 4, SCSS modules, vitest. No new npm package (CSS keyframes and IntersectionObserver are built in). | Pass |
| 3. Hexagonal Architecture | No api, domain or adapter change. | Pass (N/A) |
| 4. Security and Privacy | Demo data is invented (example recipes, aliases "Ana" and "Leo" style placeholders); no real data; no network calls from demos. | Pass |
| 5. No AI Shortcuts | Demos show the draft-confirm flow as it is (review before save); nothing is generated. | Pass |
| 6. Testing and Quality | vitest for inventory rules, page structure, i18n parity and demo frame; browser walk in quickstart. | Pass |
| 7. Deployment | No compose or server change. | Pass (N/A) |
| 8. Git discipline | One story, small commits per user story; no migration. | Pass |
| 9. Product scope | S-075 in backlog (`in_design`, should) with a spec. Lifts no MVP rule. | Pass |

AGENTS.md "Do not add new folders without asking": the plan adds `ui/components/LandingTour/`.
Components get their own folder in this repo (`components/Cart`, `components/ShoppingList`, ...),
so this follows the existing structure rather than adding a new kind of folder. Flagged for the
owner's review; no new top-level folder.

**Post-design re-check**: unchanged, all pass. No Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/075-landing-feature-tour/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1: inventory shape and rules
├── quickstart.md        # Phase 1: validation walk
├── contracts/
│   ├── feature-inventory.md   # The inventory module's exported shape and invariants
│   └── landing-page.md        # Page structure, anchors, demo frame behaviour
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
ui/
├── app/
│   ├── page.tsx                      # Rewritten: hero, index, group sections, coming soon, closing CTA
│   ├── page.home.test.tsx            # Updated: structure, order, anchors, both languages, redirect kept
│   └── globals.css                   # scroll-margin for section anchors; smooth scroll under no-preference;
│                                     # .theme-dark-scope / .theme-light-scope share the theme token blocks
├── components/AppShell.tsx           # data-scroller="signed-out" on the signed-out scroller (no other change)
├── components/LandingTour/
│   ├── index.ts
│   ├── LandingHero.tsx               # Headline, intro, account buttons, overview demo
│   ├── TourIndex.tsx                 # Six anchor links
│   ├── GroupSection.tsx              # Title, lede, feature list, demo
│   ├── ComingSoon.tsx                # Planned features strip (hidden when none)
│   ├── ClosingCta.tsx
│   ├── SurfaceBand.tsx               # Surface band with curved top and bottom edges (FR-018)
│   ├── DemoFrame.tsx                 # "use client": in-view play/pause, pause button, sr description
│   ├── DemoFrame.module.scss         # play-state rules, reduced-motion guard
│   ├── DemoFrame.test.tsx
│   └── scenes/
│       ├── OverviewScene.tsx         # capture -> notebook -> cart -> shopping line
│       ├── CaptureScene.tsx
│       ├── NotebooksScene.tsx
│       ├── TogetherScene.tsx
│       ├── ShopScene.tsx
│       ├── IngredientsScene.tsx
│       ├── HomeScene.tsx
│       ├── scenes.module.scss        # keyframes, all inside prefers-reduced-motion: no-preference
│       └── scenes.test.tsx           # each scene renders its final-state text in en and es
└── lib/
    ├── featureInventory.ts           # Groups + features (single source, FR-001..FR-005)
    ├── featureInventory.test.ts      # Invariants: order, one group each, both languages, statuses
    └── i18n/
        ├── landing.ts                # Rewritten: hero, index, CTA, coming soon, demo copy and descriptions
        └── parity.test.ts            # Already covers landingMessages
```

Also, only with the owner's explicit approval (AGENTS.md, Amendments to Governance): `AGENTS.md`
(one line under "Backlog files": a done story that adds, removes or changes a user feature updates
`ui/lib/featureInventory.ts` and says so in its verification note, FR-017). Without approval the
rule lives only in the inventory's header comment.

**Structure Decision**: ui-only change inside the existing Next.js app. Page composition stays a
server component; only `DemoFrame` is a client component, so scenes render on the server and the
page works, with still demos, before any JavaScript runs.

## Complexity Tracking

No constitution violations to justify.
