# Research: Scale a Recipe's Servings on the Detail Page (S-062)

No `NEEDS CLARIFICATION` remained. These are the design decisions the plan rests on.

## R1. Where the chosen servings live

- **Decision**: React state inside `RecipeDetailView`, initialised from `recipe.base_servings`. Nothing in the address, `localStorage`, `sessionStorage`, a cookie or the api.
- **Rationale**: FR-006 and FR-007 say the number is never remembered, so the simplest design that cannot violate them is state that dies with the page. A reload remounts the component and starts from the saved servings. The edit page is a different route and never receives the value.
- **Alternatives**: `?servings=` in the address (would survive a reload and be shareable, both rejected by the request); `sessionStorage` (survives a reload in the tab); lifting the state into `RecipeDetailScreen` (no gain, and a risk of passing it to the edit link).

## R2. The scaling rule

- **Decision**: `scaled = quantity × chosen ÷ saved`, computed from the *saved* quantity each time, never from the previously scaled value, so going 4 → 6 → 4 returns exactly to the saved amounts. Only lines with a non-null quantity are scaled; a vague line (no quantity) passes through with its note. Unit, size, name and preparation are copied unchanged.
- **Rationale**: Matches the PRD's factor form (`people × meals / base_servings`) used by the cart, and avoids drift from repeated rounding.
- **Alternatives**: scaling the previous displayed value (accumulates rounding error); rounding counted items up as the shopping list does (the spec says counted items show exactly, "2.5 large onion").

## R3. Display of amounts

- **Decision**: Keep `formatQuantity` (two decimals, no trailing zero) and add one rule: if the rounded value is 0 but the quantity is above 0, show `<0.01`. Rounding adds a tiny epsilon first so 1.005 does not round down by floating-point error.
- **Rationale**: FR-004 says a nonzero result is never shown as 0. `<0.01` is honest about the size and keeps the two-decimal limit. It only arises at extreme ratios (for example 0.1 tsp at 1 of 100 servings).
- **Alternatives**: always show `0.01` (wrong value); show more decimals (breaks the two-decimal rule); hide the line (loses an ingredient).

## R4. Input handling (FR-005)

- **Decision**: The control keeps two things: the *typed text* (whatever the member typed) and the *applied servings* (a number). `parseServings(text)` returns a whole number from 1 to 100 or `null`. On a valid entry the applied value changes; on an invalid entry the applied value is kept and a hint says "Enter a whole number from 1 to 100." The minus and plus buttons step the applied value and stop at 1 and 100 (disabled at the ends). Blur with an invalid entry restores the text to the applied value.
- **Rationale**: Typing "1" on the way to "12" must not flash an error or reset; separating typed text from applied value avoids that, and the amounts never change on an invalid entry.
- **Alternatives**: a `<select>` of 1 to 100 (long, and the earlier request wanted no dropdowns on this page); a native `type=number` with clamping (clamps silently, so "250" would apply as 100 without telling the member).

## R5. The steps note (FR-010)

- **Decision**: When applied ≠ saved, a one-line note sits above the steps: "Steps show the recipe as saved." (EN) / "Los pasos muestran la receta como se guardó." (ES). The step text is passed through untouched.
- **Rationale**: Steps may say "add 2 cups of water"; reading numbers out of free text is not something the app does. The member is told once so they do not trust a step number.
- **Alternatives**: try to rewrite numbers in steps (unreliable, rejected in the spec's assumptions).

## R6. Saved servings and the badge (FR-009, US3)

- **Decision**: The heading row shows the control. While applied ≠ saved it also shows "Makes N" (N = saved) and a **Reset** button; both disappear when equal. The "estimated" badge stays next to "Makes N" / the saved number, because it describes the saved servings.
- **Rationale**: Gives the member the base the amounts were written for and a one-action way back, without a permanent extra row.

## R7. Accessibility (FR-012)

- **Decision**: The number field has a visible label and `inputMode="numeric"`; the buttons are real buttons with labels ("Fewer servings", "More servings"); Enter in the field applies like a blur. A visually hidden `aria-live="polite"` region says "Amounts for N servings" after each applied change; the hint uses `role="alert"`.
- **Rationale**: Keyboard use needs no mouse, and screen readers learn that amounts changed without the ingredient list being re-read.

## R8. Read-only members (FR-011)

- **Decision**: The control does not depend on `can_write`. It is shown to every reader.
- **Rationale**: It changes nothing stored, so write access is irrelevant.

## R9. No api and no migration

- **Decision**: No change in `api/`. The detail response already carries `base_servings`, `servings_estimated` and the quantities.
- **Rationale**: The feature is a pure view of data the page already has.
