# Contract: Frosted surfaces

Two consumers: sticky top bars (frosted only when scrolled) and menu panels (always frosted).
Both share the frost tokens in `:root` (see [data-model.md](../data-model.md#frost-settings)).

## 1. Scroll state: `ChromeScroll`

File: `ui/components/ChromeScroll.tsx` (beside `ChromeBack.tsx`).

```ts
/** Wraps the AppShell's main scroller; owns the scroll listener. */
export function ChromeScrollProvider(props: {
  scrollerRef: React.RefObject<HTMLElement | null>;
  children: React.ReactNode;
}): JSX.Element;

/** true once the main scroller has left its top (scrollTop > 0); false at the top,
 *  on pages that never scroll, and outside a provider. */
export function useChromeScrolled(): boolean;
```

Behaviour:

- One `scroll` listener, `{ passive: true }`, on `scrollerRef.current`.
- Reads `scrollTop > 0` and calls `setState` only when the value changes.
- Re-reads on route change (`pathname`), so a page opened scrolled-to-top starts transparent.
- Outside a provider (signed-out layout with no header) returns `false`.

## 2. Frosted top bar

Applied to: the AppShell `<header data-app-chrome="header">` (with the progress bar inside the same
sticky wrapper), and on phones the headers of `RecipeDetailView`, `RecipeEditForm`,
`RecipeDraftEditor`.

Markup contract:

```tsx
<header className="frost-bar sticky top-0 z-10 …" data-frosted={scrolled ? "true" : "false"}>
```

- The page headers keep `max-md:sticky max-md:top-0 max-md:z-10`, drop `bg-background`, and add
  the modifier `frost-bar-phone`: on `md` and up they are not sticky and render transparent
  regardless of `data-frosted` (FR-001).
- Position, height, padding and safe-area insets are unchanged (FR-005).

CSS contract (`ui/app/globals.css`, unlayered utility class `.frost-bar`):

| Selector | Effect |
|----------|--------|
| `.frost-bar` | `position` as given; `isolation: isolate` |
| `.frost-bar::before` | `content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;` background `transparent`, no blur, no shadow; `transition: background-color, box-shadow, backdrop-filter var(--frost-fade) ease` |
| `.frost-bar[data-frosted="true"]::before` | `background: color-mix(in srgb, var(--background) var(--frost-alpha), transparent)`; `backdrop-filter` and `-webkit-backdrop-filter: blur(var(--frost-blur))`; `box-shadow: var(--frost-shadow)` |
| `@supports not (backdrop-filter…)` | frosted background at 97% |
| `@media (prefers-reduced-transparency: reduce)` | frosted background solid `var(--background)`, no blur |
| `@media (prefers-reduced-motion: reduce)` | `transition: none` |
| `@media (width >= 48rem)` `.frost-bar-phone::before` | never frosted (those headers are not sticky there) |

The bar element itself never gets `backdrop-filter`, `filter` or `transform` (R3): menus inside it
must be able to blur the page.

## 3. Frosted menu panel

File: `ui/components/MenuSurface/MenuSurface.module.scss`, class `.panel`, used by
`IconButtonPopup`, `soft-ledger/Select`, `SearchableSelect` (and any future dropdown that uses
`menuSurface.panel`).

| Rule | Value |
|------|-------|
| `background` | `color-mix(in srgb, var(--surface) var(--frost-alpha), transparent)` |
| `backdrop-filter`, `-webkit-backdrop-filter` | `blur(var(--frost-blur))` |
| `border`, `border-radius`, `box-shadow` | unchanged |
| `@supports not (backdrop-filter…)` | surface at 97% |
| `@media (prefers-reduced-transparency: reduce)` | `background: var(--surface)`, no blur |

`.item` hover/selected backgrounds stay opaque tints (`--menu-item-hover`, `--menu-item-selected`),
so a marked row never shows content through it (FR-018).

## Test hooks

- `data-frosted` on every frosted bar (asserted in `AppShell.test.tsx` and the recipe view tests:
  `"false"` at mount, `"true"` after a `scroll` event with `scrollTop = 1`, `"false"` again at 0).
- `MenuSurface.test.ts` asserts `.panel` contains the `--frost-alpha` mix and both blur properties.
