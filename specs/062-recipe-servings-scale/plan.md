# Implementation Plan: Scale a Recipe's Servings on the Detail Page

**Branch**: `062-recipe-servings-scale` (spec folder `062-recipe-servings-scale`, story S-062) | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/062-recipe-servings-scale/spec.md`

## Summary

On the recipe detail page (spec 027) a member sets a number of servings and every measured or counted ingredient quantity shows multiplied by chosen ÷ saved servings. The number is only a view: it lives in the page's own state, is never sent to the api, and a reload, a new visit, another member, the edit form, lists and exports all keep the saved servings.

Technical approach: **ui only. No api change, no route, no table, no migration, no library.** One pure module (`ui/lib/recipeScale.ts`) parses the typed servings and scales a line; the existing quantity formatter gains the "never show a nonzero amount as 0" rule; a small `ServingsControl` component holds the stepper, the typed text, the hint and the reset; `RecipeDetailView` keeps the chosen servings in local state and passes scaled lines to the existing read-only ingredient cards. The step text and vague notes are passed through untouched.

## Technical Context

**Language/Version**: TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`). No Python change.

**Primary Dependencies**: Existing only: `IngredientLineRow` (read-only mode), `StepCard`, `Chip`, `lib/recipeLines.formatQuantity`, `lib/i18n/recipeDetail`. **No new library.**

**Storage**: None. The chosen servings are React state in the detail view; nothing is written to the api, the browser storage or the address.

**Testing**: vitest + eslint + typecheck. Pure tests for parsing, scaling and formatting; component tests for the control and the view (scales, hint, reset, steps note, stored values untouched, keyboard). A browser check of the page at phone and desktop width (constitution §6).

**Target Platform**: Mobile-first browser ui under Docker Compose.

**Project Type**: Web application; this change is in `ui/` only.

**Performance Goals**: Amounts update within 0.1 s of a change for a recipe of up to 100 lines (SC-001). The work is one multiplication per line in the same render, so no debounce or request is needed.

**Constraints**:
- No unit conversion and no merging of lines (PRD §4, constitution §5): only the quantity of a line is derived.
- Servings are whole numbers 1 to 100; anything else is not applied (FR-005).
- Stored data, the api and the edit form never see the chosen servings (FR-006 to FR-008).
- English and Spanish text, with no codes (FR-013).

**Scale/Scope**: One new component, one new pure module, one changed formatter, one changed view, about 10 new strings per locale.

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. No new service, folder at the top level, route or library. Reuses the read-only cards of spec 027. |
| 2. Tech stack | Pass. No dependency added. |
| 3. Hexagonal | Pass. Nothing in `api/` changes; the scaling rule is a pure ui function. |
| 4. Security and privacy | Pass. Nothing is stored or sent, so there is nothing to leak. |
| 5. No AI shortcuts | Pass. No model involved; "no unit conversion" is kept. |
| 6. Testing | Pass. Pure and component tests, plus a browser walk. |
| 7. Deployment | Pass. No compose or server change. |
| 8. Git discipline | Pass. No schema change; small commits. |
| 9. Scope | Pass for a *Should* item added by the owner on 2026-10-28; it does not displace a Must (S-027 is done). |

Post-design re-check: unchanged. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/062-recipe-servings-scale/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ui-servings.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
ui/
├── lib/
│   ├── recipeScale.ts            # NEW: parseServings, scaleLine, scaleFactor
│   ├── recipeScale.test.ts
│   ├── recipeLines.ts            # formatQuantity: a nonzero amount never shows as 0
│   ├── recipeLines.test.ts
│   └── i18n/recipeDetail.ts      # + servings control, hint, reset, "Makes N", steps note
└── components/RecipeDetail/
    ├── ServingsControl.tsx       # NEW: stepper, typed text, hint, reset, live announcement
    ├── ServingsControl.test.tsx
    ├── RecipeDetailView.tsx      # keeps the chosen servings; scales lines; steps note
    └── RecipeDetailView.test.tsx
```

**Structure Decision**: ui only, beside the spec 027 detail components. The state is local to `RecipeDetailView` (it becomes a client component) so that leaving or reloading the page drops it by construction; nothing lifts it into the screen, the router or storage.

## Complexity Tracking

No violations to justify.
