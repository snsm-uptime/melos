# Implementation Plan: Cauldron Loader

**Branch**: `065-cauldron-loader` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/065-cauldron-loader/spec.md`, backlog S-065

## Summary

One shared `CauldronLoader` component in `ui/` replaces every loading state in the app: the pulsing placeholder, the text-only "Loading…" lines and all five spinners. It is an inline SVG animated with CSS only (transform and opacity), so it needs no library, no timer and no network. Bubbles rise in fixed positions while the cauldron group rocks around a pivot near its base. The tilt angle is a prop, with two defaults kept in one module (25 general, 10 in buttons), and an angle outside 0 to 45 is resolved by one pure function. Colors come from the existing theme tokens, so a theme change recolors it without restarting the animation. Loading buttons stop using the grey disabled look, which fails the 3:1 rule (research R6). No api change.

## Technical Context

**Language/Version**: TypeScript with Next.js 16 and React 19 (ui). No api change.

**Primary Dependencies**: Tailwind 4 and SCSS modules, both already in use. No new library.

**Storage**: N/A

**Testing**: vitest for the tilt rule, geometry bounds, colour contrast, markup, labels and the swapped call sites. Browser walk in [quickstart.md](quickstart.md). The i18n parity test covers the new text.

**Target Platform**: Phone and desktop browsers, light and dark theme, `prefers-reduced-motion`.

**Project Type**: Web application (`ui/` only)

**Performance Goals**: Only `transform` and `opacity` animate, so no layout or paint per frame (SC-004). No JavaScript runs while it loops.

**Constraints**: No network (FR-014). No element ids in the markup, so several loaders on one screen never clash. Text in English and Spanish. All motion stays inside the loader's own box.

**Scale/Scope**: One new component folder, one i18n file, 5 spinner call sites, 1 placeholder page and 10 text-only loading lines (in 9 files) swapped (full table in [contracts/cauldron-loader-ui.md](contracts/cauldron-loader-ui.md)). `SpinnerIcon` and the button spinner CSS are deleted.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| 1 Simplicity and Reuse | Pass | No service added. Reuses the theme tokens and the i18n pattern. |
| 2 Tech Stack | Pass | No library added. |
| 3 Hexagonal | N/A | `ui/` only. |
| 4 Security and Privacy | Pass | No data, no request, no user input beyond a tilt number that is clamped. |
| 5 No AI Shortcuts | N/A | No AI. |
| 6 Testing | Pass | vitest for the rules and call sites, plus the browser check the principle requires. |
| 7 Deployment | Pass | No infrastructure change. |
| 8 Git Discipline | Pass | Small commits, one per swapped group. |
| 9 Scope and Schedule | **Exception approved by the owner, 2026-10-31** | Backlog S-065 is priority "should", not a PRD Appendix C "Must". Must stories are still open before 02/11. The owner's approval is recorded under Complexity Tracking. Task T001 checks that record before work starts. |

Post-design re-check: same result. The design added no violation.

## Project Structure

### Documentation (this feature)

```text
specs/065-cauldron-loader/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cauldron-loader-ui.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
ui/
├── components/CauldronLoader/                  # new
│   ├── CauldronLoader.tsx, index.ts            # the component
│   ├── CauldronLoader.module.scss              # shapes, keyframes, colours, reduced motion
│   ├── tilt.ts                                 # the two defaults, the 45 limit, resolveTilt()
│   ├── geometry.ts                             # viewBox and pivot, bounds at a given angle
│   └── *.test.ts(x)                            # tilt, geometry, contrast, markup, labels
├── lib/i18n/loader.ts                          # new: "Loading" / "Cargando"
├── lib/i18n/parity.test.ts                     # add the new set
├── components/soft-ledger/BaseButton.tsx       # spinner -> CauldronLoader (button tone)
├── components/soft-ledger/BaseButton.module.scss  # loading keeps variant colours; spinner CSS removed
├── components/ItemChipSelector/ItemChipSelector.tsx
├── components/RecipeEdit/RecipeEditForm.tsx, RecipeEditScreen.tsx
├── components/RecipeDraft/RecipeDraftEditor.tsx
├── components/StackedListPanel/StackedListPanel.tsx
├── components/RecipeList/RecipeList.tsx, RecipeDetail/RecipeDetailScreen.tsx
├── components/ShoppingList/ShoppingListSection.tsx, ClosedLists.tsx
├── components/Cart/CartScreen.tsx
├── app/signup/SignupForm.tsx, app/invites/accept/AcceptInvitePanel.tsx
├── app/kitchens/[kitchenId]/loading.tsx        # pulse blocks -> one loader
├── app/icons/SpinnerIcon.tsx, index.ts, README.md   # removed
└── COMPONENT_PATTERNS.md                       # "Loading states" section points at the component
```

**Structure Decision**: Existing `ui/` layout. `ui/components/CauldronLoader/` follows the one-folder-per-component pattern already used there. The tilt rule and the geometry are plain modules beside it so they test without a DOM.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle 9: story outside Appendix C "Must", planned while Must stories are open | Direct owner request; the spec is already on `main` | Waiting for Must to finish is the alternative. It is the owner's call before `/speckit-implement`, not one this plan can make. |

**Approval record** (the constitution asks for it in writing, as in spec 064):

- Approved by: Sebastian Soto M (project owner), in the Claude Code session that produced this plan ("approved, record it in plan.md")
- Date: 2026-10-31
- Scope: build S-065 (all four stories) before the open Must stories are done
