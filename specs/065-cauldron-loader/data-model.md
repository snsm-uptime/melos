# Data Model: Cauldron Loader

No database, api or stored data changes. Everything below lives in `ui/`.

## Tilt angle

| Item | Value | Where |
|---|---|---|
| `CAULDRON_TILT_DEFAULT` | `25` degrees each way | `ui/components/CauldronLoader/tilt.ts` |
| `CAULDRON_TILT_IN_BUTTON` | `10` degrees each way | same file |
| `CAULDRON_TILT_MAX` | `45` degrees | same file |

Rule, `resolveTilt(value, fallback)`:

| Input | Result |
|---|---|
| Finite number from 0 to 45 | The number |
| Finite number above 45 | `45` |
| Negative finite number | Its size, then the 45 limit (`-10` gives `10`, `-90` gives `45`) |
| `0` | `0`: upright, bubbles keep rising |
| `NaN`, `±Infinity`, `undefined`, `null`, a string | `fallback` |

`fallback` is `CAULDRON_TILT_IN_BUTTON` for the button tone and `CAULDRON_TILT_DEFAULT` otherwise.

## Geometry (derived, not stored)

`geometry.ts` exports the `viewBox`, the pivot point (near the base of the feet), the cauldron's outline points and a `boundsAt(angle)` function. The `viewBox` is chosen so `boundsAt(CAULDRON_TILT_MAX)` is inside it. Exact numbers are set while drawing and checked by the bounds test.

## Colour tokens

| Token | Page tone | Button tone |
|---|---|---|
| Cauldron | `color-mix(in srgb, var(--background) 40%, var(--foreground))` | `var(--loader-ink)` |
| Bubbles and drip | `var(--accent)` | `color-mix(in srgb, var(--loader-ink) 80%, var(--loader-fill))` |

`--loader-ink` and `--loader-fill` come from the button, per variant:

| Variant | Ink | Fill |
|---|---|---|
| Primary | `var(--on-accent)` | `var(--accent)` |
| Accent | `var(--on-secondary)` | `var(--secondary)` |
| Ghost | `var(--accent)` | `color-mix(in srgb, var(--accent) 8%, var(--surface))` |
| Header icon button (no fill) | `currentColor` | `var(--background)` |

Every row must reach 3:1 in light and dark (SC-003). The contrast test reads the token values from `globals.css` so it stays in step with the theme.

## Timing (tuned by eye)

| Item | Value |
|---|---|
| Period of the rock and of each bubble | about 3.2 s, all equal |
| Rock easing | `ease-in-out` on each half |
| Bubble phases | Negative `animation-delay`, spread over the period |
| Bubble opacity | 0 at both ends of its keyframes |

## Labels

`ui/lib/i18n/loader.ts`: `loaderMessages = { en: { loading: "Loading" }, es: { loading: "Cargando" } }`. Added to the parity test.
