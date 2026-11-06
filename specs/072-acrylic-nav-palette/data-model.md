# Data Model: Acrylic App Chrome and the Portfolio Palette

No database, api or stored data changes. The "entities" are UI state and design tokens.

## Theme palette

A set of colour roles, each a CSS custom property with one light value (`:root`) and one dark value
(`html.dark`, mirrored in the `prefers-color-scheme: dark` block). Exposed to Tailwind through
`@theme` as `--color-<role>` (so `bg-surface`, `text-accent`, …).

| Role (property) | Meaning | New? |
|-----------------|---------|------|
| `--background` | Page background | |
| `--surface` | Cards, panels, menus, dialogs, sheets, side panel | |
| `--foreground` | Text | |
| `--muted` | Quiet text, secondary icons | |
| `--border` | Dividers, card and panel outlines (decorative) | |
| `--field-border` | Outlines of inputs, selects, textareas, checkboxes (≥3:1) | yes |
| `--accent` | Main colour **ink**: links, coloured icons, selected tab, "in cart", focus rings, radio/checkbox marks | |
| `--accent-fill` | Main colour **area**: badges, selected pills and days | yes |
| `--on-accent` | Text on `--accent-fill` | |
| `--primary` | Brand and filled-button violet | yes |
| `--on-primary` | Text on `--primary` | yes |
| `--secondary` | Second brand (magenta): `AccentButton`, loader ink | |
| `--on-secondary` | Text on `--secondary` | |
| `--error` | Error text and outlines | |
| `--danger` | Destructive action text/icons | |
| `--danger-strong` | Destructive fill with white text (`kitchens.module.scss .primaryDanger`) | |
| `--warn` | Warning text | |
| `--owed` | Success text | |
| `--menu-item-hover` | `color-mix(--accent-fill 10%, --surface)` | formula changes |
| `--menu-item-selected` | `color-mix(--accent-fill 22%, --surface)` | formula changes |
| `--card-selected` | `color-mix(--accent-fill 12%, --surface)` | formula changes |

Removed: the `--wb-*` aliases (Warm Balance).

Values and the checked contrast of every pair: [contracts/theme-tokens.md](contracts/theme-tokens.md).

**Validation rules** (enforced by `ui/app/palette.test.ts`):

- Each pair in the contract table meets its minimum (4.5:1 text, 3:1 icons, input borders, focus).
- The `html.dark` block and the `prefers-color-scheme: dark` block declare the same values.
- No declaration in `globals.css` uses a value from the old palette (list of old hexes).

## Frost settings

Theme-independent tokens in `:root`:

| Property | Value | Source |
|----------|-------|--------|
| `--frost-alpha` | `86%` | R4 (80% fails quiet text; 86% fails quiet menu text over white at 4.22:1) |
| `--frost-blur` | `8px` | portfolio `backdrop-blur` |
| `--frost-shadow` | `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` | portfolio `shadow-sm` |
| `--frost-fade` | `300ms` | portfolio `duration-300` |

## Top bar state

Per page, derived, never stored.

| State | When | Bar look |
|-------|------|----------|
| `transparent` | Main scroller at `scrollTop === 0`, or the page does not scroll, or the bar is not sticky (wide-screen recipe header) | no background, no blur, no shadow |
| `frosted` | Main scroller `scrollTop > 0` and the bar is sticky | `--background` at `--frost-alpha`, blur, shadow |

Transitions: `transparent ⇄ frosted` on every flip of `scrollTop > 0`, fading over `--frost-fade`
(none with reduced motion). Exposed as `data-frosted="true|false"` on the bar.

## Menu surface state

Always `frosted` while open: `--surface` at `--frost-alpha`, blur, existing border and
shadow. No transparent state. Solid under reduced transparency; 97% where blur is unsupported.
