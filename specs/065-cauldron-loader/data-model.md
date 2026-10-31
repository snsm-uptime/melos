# Data Model: Cauldron Loader

Nothing is stored: no table, migration or api change. The only data is one value resolved when the loader renders.

## Tilt angle

| Input | Result |
|---|---|
| Not given, general placement | 25 |
| Not given, button placement | 10 |
| 0 to 45 | That value |
| Negative | Its size, then the same rules |
| Above 45 | 45 |
| Not a number | The placement's default |

The two defaults live in one place, `ui/components/CauldronLoader/tilt.ts` (FR-005).

## States

The loader has no state of its own. It runs while mounted and is gone when removed. The screen that owns the wait decides when (FR-016: no delay, no minimum time). Reduced motion shows the resting drawing instead.
