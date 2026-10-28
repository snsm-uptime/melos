# Data Model: Scale a Recipe's Servings (S-062)

**No stored data, no schema change and no migration.** Everything below exists only in the browser while the detail page is open.

## Existing data read (unchanged)

| Field | Where | Use |
|---|---|---|
| `base_servings` (integer ≥ 1) | recipe detail response | the *saved servings*; the divisor of the scale factor |
| `servings_estimated` | recipe detail response | keeps the "estimated" badge on the saved servings |
| `ingredient_lines[]`: `quantity` (number or null), `unit`, `size`, `name`, `preparation`, `vague`, `note` | recipe detail response | the quantity is the only field that is derived |
| `steps[]` | recipe detail response | shown as saved |

## View state (not stored)

| Name | Type | Rule |
|---|---|---|
| `typed` | text | whatever the member typed in the servings field |
| `applied` | whole number 1 to 100 | starts at `base_servings`; changes only on a valid entry or a step button; **never sent anywhere** |
| `factor` | number | `applied ÷ base_servings` |

Validation of an entry (`parseServings`): trim; digits only; integer; `1 ≤ n ≤ 100`; otherwise `null` (not applied). `base_servings` itself is not limited to 100 by this feature: a recipe saved for 120 servings opens at 120, and the control then accepts only 1 to 100 when changed.

## Derived values

- **Scaled line**: a copy of the line with `quantity = saved quantity × factor` when the quantity is not null; every other field is copied. A vague line has no quantity and is copied whole.
- **Shown amount**: `formatQuantity(scaled quantity)`: at most 2 decimals, no trailing zero, `<0.01` when it would round to 0.

## State transitions

```text
open page            → applied = base_servings, typed = base_servings
valid entry / ± step → applied = n (typed follows)
invalid entry        → applied kept; hint shown; amounts unchanged
Reset                → applied = base_servings
reload / leave       → state is gone; next visit starts at base_servings
```

## What never changes

The recipe row, its lines, steps and times; the catalog; the edit form's contents; lists, cards, the cart and exports. The scaled lines are never passed to `PUT /recipes/{id}`.
