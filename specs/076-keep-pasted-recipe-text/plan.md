# Implementation Plan: Keep Pasted Recipe Text and Offer Personal Notebooks

**Branch**: `076-keep-pasted-recipe-text` (spec directory; work is currently on `main`) | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/076-keep-pasted-recipe-text/spec.md`

## Summary

Two UI-only changes to adding a recipe:

1. **Keep the pasted text for the session.** The capture store's `text` is mirrored to the browser's per-tab session storage. It survives closing the sheet, navigating, leaving the app and reloading. It is cleared on save, discard, a hand-written draft, sign-in and sign-out, and when the tab closes. Back from the draft still shows it (spec 016 FR-031).
2. **The side panel offers every notebook the member can add to.** `QuickAddRecipe` builds its choice from the existing `GET /api/notebooks`, which already returns personal and kitchen notebooks. It drops archived kitchens and groups personal notebooks and each kitchen's notebooks, with dividers and a "Personal" or kitchen-name label. The notebook page (one notebook, no picker) and the kitchen page (that kitchen's notebooks) are unchanged and get regression tests.

No API, database or dependency changes.

## Technical Context

**Language/Version**: TypeScript (Next.js 16, React 19)

**Primary Dependencies**: Existing only: Next.js, React, Tailwind 4, vitest

**Storage**: Browser `sessionStorage` (one key, client only). No database change.

**Testing**: vitest (store lifecycle, `QuickAddRecipe` candidates, `NotebookPicker` labels, sign-out), then a manual browser check (constitution 6)

**Target Platform**: Web app (desktop and mobile browsers)

**Project Type**: Web application (`ui/` frontend; `api/` untouched)

**Performance Goals**: The side panel makes one notebook request, as today. Reading the text from storage is synchronous and instant.

**Constraints**: No hydration mismatch. Storage failures fall back to in-memory behaviour. The text never leaves the device before submit.

**Scale/Scope**: About 6 UI files changed plus tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| 1. Simplicity and Reuse | No new service; reuses the capture store, `/api/notebooks` and `SearchableSelect`'s existing `dividerBefore`. Auth layer untouched (sign-in and sign-out only gain a client cache clear, like the existing prefs and kitchens clears). | ✅ |
| 2. Tech Stack Stability | No new libraries. | ✅ |
| 3. Hexagonal Architecture | No api changes. | ✅ |
| 4. Security and Privacy | Text stays on the device in tab-scoped storage. It is cleared on sign-in and sign-out so another member never sees it. Nothing is sent before submit. | ✅ |
| 5. No AI Shortcuts | The draft still needs confirmation; nothing is saved automatically. | ✅ |
| 6. Testing and Quality | vitest for store, picker and side panel; manual browser check in [quickstart.md](./quickstart.md). | ✅ |
| 7. Deployment | No change. | ✅ |
| 8. Git Discipline | Small commits per story; PR for review. A feature branch must be created before implementing (currently on `main`). | ✅ (action noted) |
| 9. Product Scope | Spec exists. It changes spec 016 FR-001a for the side panel, as recorded in the spec. Add a backlog entry if the owner wants one tracked. | ✅ |

**Post-design re-check**: No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/076-keep-pasted-recipe-text/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── ui-contract.md   # Phase 1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
ui/
├── lib/
│   ├── capture/
│   │   ├── captureStore.ts            # mirror `text` to sessionStorage; clearKeptCaptureText()
│   │   └── captureStore.test.ts       # lifecycle tests (+ storage blocked)
│   ├── signOut.ts                     # call clearKeptCaptureText()
│   ├── signOut.test.ts
│   └── i18n/                          # "Personal" label (en, es) for the picker detail
├── app/
│   └── sign-in/SignInForm.tsx         # call clearKeptCaptureText() on success
└── components/
    ├── NotebookPicker/NotebookPicker.tsx          # optional detail + dividerBefore
    ├── AddRecipeCallToAction/
    │   ├── AddRecipeCallToAction.tsx              # CaptureCandidate gains detail?, dividerBefore?
    │   ├── TextCaptureSheet.tsx / UrlCaptureSheet.tsx / PictureCaptureSheet.tsx
    │   │                                          # pass detail/dividerBefore to the picker
    │   └── AddRecipeCallToAction.test.tsx         # regression: notebook page → no picker
    ├── QuickAddRecipe/
    │   ├── QuickAddRecipe.tsx                     # all notebooks, grouped, archived kitchens dropped
    │   └── QuickAddRecipe.test.tsx
    └── RecipeList / app/kitchens/KitchenNotebooksSection.tsx   # unchanged (regression only)
```

**Structure Decision**: Existing `ui/` web frontend only. `api/` is not touched because `GET /api/notebooks` already returns every notebook the member can see ([research R4](./research.md)).

## Implementation Notes

- **Store** ([research R1–R2](./research.md)): add `KEPT_TEXT_KEY = "melos.capture.text"`, plus `readKeptText()` and `writeKeptText(text)` helpers wrapped in try/catch. In `update()`, when `patch.text !== undefined && patch.text !== state.text`, write the new text, or remove the key for `""`. Start `state` from `EMPTY` and set `text` from storage on the first client `getCaptureState()` call (a guarded one-time init). Update the module comment, which today says "a reload clears it".
- **Sign-in and sign-out** ([R3](./research.md)): `clearKeptCaptureText()` removes the key and calls `update({ text: "" })`.
- **Side panel** ([R4, R5, R7](./research.md)): replace the two branches in `QuickAddRecipe.load()` with one call to `fetchPersonalNotebooks()`, keeping the `fetchDefaultNotebook()` fallback when there are no personal notebooks. Group the rows by kitchen using `useMembershipKitchens()` for names and order. If a kitchen is missing from the roster, label it with a generic "Kitchen". Add `kitchens` to the effect's dependency key so the labels refresh once the roster loads.
- **Picker labels**: set `detail` and `dividerBefore` only when more than one group is offered, so personal-only members see no change.

## Complexity Tracking

None.
