# Implementation Plan: Cauldron Loader

**Branch**: `065-cauldron-loader` (not created yet; work is on `main`) | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/065-cauldron-loader/spec.md`

## Summary

One shared `CauldronLoader` component, drawn as a single inline SVG and animated with CSS only, so it needs no client boundary and works in server `loading.tsx` files. It runs one 2.4 second loop: the cauldron rocks and two bubbles rise on the same period, so the whole picture repeats exactly. It then replaces every loading state in the ui: spinners, the pulsing placeholder, "Loading…" text, and the three screens that show nothing while loading.

Two existing problems have to be fixed for the spec to hold, both found while measuring contrast: a loading button is also a disabled button and its colors reach only about 2:1, and the accent drip barely separates from a cauldron in any shade of the background. See research R3 and R4.

## Technical Context

**Language/Version**: TypeScript, React 19, Next.js 16 App Router

**Primary Dependencies**: Existing only: Tailwind 4 and SCSS modules. No new library.

**Storage**: N/A

**Testing**: vitest for the component, tilt rules and each replaced site; browser walk for motion and reduced motion (constitution 6)

**Target Platform**: Current phone and desktop browsers

**Project Type**: Web application, ui only. No api, mcp or migration change.

**Performance Goals**: No visible stutter over 30 seconds on a typical phone (SC-004). Only `transform` and `opacity` are animated.

**Constraints**: Server-renderable; no network requests (FR-014); motion stays in the loader's own box (FR-013); 3:1 contrast (SC-003)

**Scale/Scope**: 1 new component; about 20 files changed (research R6)

## Constitution Check

*Re-checked after Phase 1: same result.*

| Principle | Result |
|---|---|
| 1. Simplicity and Reuse | Pass. One component, no service or auth change. |
| 2. Tech Stack Stability | Pass. No new library. |
| 3. Hexagonal Architecture | N/A, ui only. |
| 4. Security and Privacy | Pass. No data handled. |
| 5. No AI Shortcuts | N/A. |
| 6. Testing and Quality | Pass, provided the browser walk in quickstart.md is done. Motion cannot be proved in vitest. |
| 7. Deployment and Operations | N/A. |
| 8. Code Review and Git Discipline | Pass, provided the work moves to a branch first. |
| 9. Product Scope and Schedule | **Open.** S-065 is a Should, and the principle puts Should items after the Must work. Planning is fine, but building before the Must stories needs the owner's written approval, as S-064 had. |

## Project Structure

### Documentation (this feature)

```text
specs/065-cauldron-loader/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cauldron-loader.md
└── tasks.md             # /speckit-tasks
```

### Source Code

```text
ui/
├── app/
│   ├── globals.css                       # --cauldron-body per theme
│   └── icons/                            # SpinnerIcon removed; README updated
├── components/
│   ├── CauldronLoader/                   # new
│   │   ├── CauldronLoader.tsx
│   │   ├── CauldronLoader.module.scss
│   │   ├── CauldronLoader.test.tsx
│   │   ├── tilt.ts                       # the two defaults, angle rules, drawing box
│   │   ├── tilt.test.ts
│   │   └── index.ts
│   └── soft-ledger/BaseButton.*          # loader in; busy colors
└── (the sites listed in research R6)
```

**Structure Decision**: Follows the existing one-folder-per-component pattern under `ui/components/`.

## Complexity Tracking

No constitution violation is being justified here. Principle 9 stays open until the owner decides.
