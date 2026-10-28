# Contract: Servings control on the recipe detail (ui)

No api contract changes: `GET /recipes/{id}` already returns what is needed. Text lives in `lib/i18n/recipeDetail.ts` (EN and ES). No codes are shown.

## Placement

On the detail page's Ingredients heading row, in place of the plain "N servings" text. The Steps column gets a note when the servings differ from the saved ones.

## The control

```text
Ingredients                         Servings  [−] [ 6 ] [+]   Makes 4 (estimated)  [Reset]
```

| Part | Behavior |
|---|---|
| Label "Servings" | visible, tied to the number field |
| `−` / `+` | step the applied servings by 1; `−` is disabled at 1, `+` at 100; accessible names "Fewer servings" / "More servings" |
| Number field | text input, numeric keypad hint; a valid whole number 1 to 100 applies at once; an invalid or empty entry is not applied and shows the hint; Enter or leaving the field with an invalid entry restores the applied value |
| Hint | "Enter a whole number from 1 to 100." (`role="alert"`), shown only for an invalid entry |
| "Makes N" | shown only while applied ≠ saved; N is the saved servings; the "estimated" badge sits beside it when the saved servings were estimated |
| Reset | shown only while applied ≠ saved; sets applied back to saved |
| Live note | hidden, `aria-live="polite"`: "Amounts for N servings" after each applied change |

When applied = saved the heading row shows the control and, if estimated, the badge; no "Makes N", no Reset.

## What scales

| Line kind | Shown |
|---|---|
| Measured (`1 cup rice`) | quantity × factor, unit unchanged: `1.5 cup` |
| Counted (`2 large onion`) | quantity × factor, size unchanged: `3 large`; fractions shown (`2.5 large`) |
| Vague (`salt, to taste`) | unchanged (note as saved) |
| Preparation, name, order | unchanged |
| Steps | unchanged text; note above the steps while applied ≠ saved |

## Rules

- Computed from the saved quantity each time (4 → 6 → 4 returns to the saved amounts).
- The value is never put in the address, storage, a cookie, or any request. The Edit link and the edit page do not receive it.
- Available to every reader, including members who cannot edit.
