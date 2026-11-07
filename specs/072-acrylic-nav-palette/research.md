# Research: Acrylic App Chrome and the Portfolio Palette

All decisions below are grounded in the current code (`ui/app/globals.css`, `ui/components/AppShell.tsx`,
`ui/components/MenuSurface/`) and the portfolio's source
(`/home/snsm/source/personal/portfolio/src/components/navbar.tsx:110-114`, `src/app/globals.css`).
Contrast ratios were computed with the WCAG 2.x relative-luminance formula.

## R1. How content gets under the bar (FR-004)

- **Decision**: Move the app's `<header>` (and the progress bar above it) inside the main scroll
  container, as its first child, with `position: sticky; top: 0; z-index: 10`.
- **Rationale**: Today the header is a flex sibling of the scroller
  (`AppShell.tsx`, `div.overflow-y-auto`), so nothing ever passes beneath it. As a sticky first
  child of the same flex column, the content still starts below the bar at the top, scrolls under
  it, and pages that fill the rest of the height with `flex-1 min-h-0` (the wide recipe layout)
  keep working, because the header stays `shrink-0` in the column. No height measuring.
- **Alternatives considered**: Absolute header over the scroller with `padding-top` set from a
  `ResizeObserver` (extra JS, a frame of wrong padding on first paint, breaks when the title wraps);
  keeping the header outside and faking the effect (nothing to blur, fails FR-004).
- **Side effect**: the scrollbar now runs the full height, beside the bar. Accepted; it is what the
  portfolio does.

## R2. Detecting "content has scrolled under the bar" (FR-002, FR-003)

- **Decision**: A `ChromeScrollProvider` in `AppShell` owns a ref to the scroller and a passive
  `scroll` listener that sets `scrolled = scrollTop > 0`, calling `setState` only when the flag
  flips. `useChromeScrolled()` reads it. Bars set `data-frosted="true|false"`.
- **Rationale**: The recipe, recipe edit and draft review headers live inside the same scroller
  (they are `max-md:sticky top-0` children of the page), so one source of truth serves every bar.
  A boolean that changes twice per scroll gesture costs nothing (SC-006). Short pages never fire
  scroll events, so they stay transparent (edge case).
- **Alternatives considered**: `IntersectionObserver` on a sentinel (same result, more DOM and a
  zero-height sentinel quirk); a listener per header (duplicated logic); `scroll-timeline` CSS
  (not in Firefox or Safari stable).

## R3. Where the blur is painted

- **Decision**: The frost (background, `backdrop-filter`, shadow) lives on a `::before`
  pseudo-element (`position: absolute; inset: 0; z-index: -1`) of the bar, inside a bar that has
  `isolation: isolate`. The bar itself has no `backdrop-filter`.
- **Rationale**: An element with `backdrop-filter` becomes a *backdrop root* and a containing block
  for fixed descendants. The dots menu in the bar's `trailing` slot would then blur only the bar,
  not the page, and a fixed-position child would be placed against the bar. A pseudo-element
  avoids both and still fills the safe-area padding (story 1, scenario 6) because it covers the
  bar's padding box.
- **Alternatives considered**: `backdrop-filter` on the bar (breaks nested menus as above); a
  separate sibling div (extra markup in three page headers).

## R4. Frost values (FR-003, FR-006, FR-017, FR-019)

- **Decision**: Copy the portfolio's recipe with one change. Blur `8px` (Tailwind's bare
  `backdrop-blur`, which the portfolio uses), shadow equal to Tailwind 4 `shadow-sm`
  (`0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)`), `transition` on
  `background-color, box-shadow, backdrop-filter` over `300ms`. **Opacity 88%, not 80%**, for
  bars and menus in both themes, held in one token `--frost-alpha`.
- **Rationale**: Checked against the worst case the spec names (pure black and pure white beneath):
  at 80%, quiet text (`--muted`) fails in both themes (dark bar over white 3.97:1, light bar over
  black 3.88:1, dark menu over white 3.42:1). The lowest opacity at which every bar and menu pair
  passes is 88% (dark menu); the bar alone would need 86%. One value keeps the code simple and the
  look the same across surfaces; the owner can tune it in the browser walk (spec Assumptions).
  FR-019 explicitly allows a higher opacity rather than failing; FR-006 is met only this way.
- **Alternatives considered**: 80% plus a stronger blur (blur does not bound the worst case, a
  large white photo stays white); 80% for the bar with `--muted` banned from bars (the title's
  details chip and kitchen chrome use `--muted`).

## R5. Fallbacks (FR-007)

- **Decision**:
  - `@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))`: frost
    uses the colour at 97%.
  - `@media (prefers-reduced-transparency: reduce)`: frost uses the solid colour, no blur.
  - `@media (prefers-reduced-motion: reduce)`: `transition: none`.
  - Write both `backdrop-filter` and `-webkit-backdrop-filter` (SCSS modules are not run through
    Tailwind's prefixer; Safari < 18 needs the prefix).
- **Rationale**: Direct mapping of the spec's edge cases; all are CSS-only, so no hydration flash.

## R6. Splitting the main colour from filled buttons (FR-012)

- **Decision**: Keep `--accent` as the **main colour** role (links, icons, selection, focus, "in
  cart", selected tab) and make it orange. Add `--primary` / `--on-primary` (violet / white) and
  point `BaseButton .primary` and the ad-hoc filled buttons at it. `--secondary` becomes magenta.
- **Rationale**: About 70 files use `accent` for marks and selection; only `BaseButton.primary` and
  four ad-hoc buttons (`TextCaptureSheet`, `UrlCaptureSheet`, `RecipeFromNotebookSheet`,
  `ShoppingList/DoneButton`) use it as a filled action. Moving the few is far smaller than
  renaming the many.
- **Alternatives considered**: Rename `--accent` to `--main` everywhere (large churn for no
  behavioural gain); keep violet as `--accent` (contradicts the clarification).

## R7. Orange ink vs orange fill in light (FR-011)

- **Decision**: Add `--accent-fill` (always `#fd9c21`) used for orange areas, with
  `--on-accent: #141218`. `--accent` is the ink: `#fd9c21` in dark, `#a65400` in light
  (4.99:1 on the page, 5.40:1 on white; `#fd9c21` is 1.95:1). Today's orange fills that carry text
  (`Badge`, `LanguageChoice`, `SignedOutLanguageSwitch`, `DateRangeField` selected day) move to
  `bg-accent-fill text-on-accent`. Small marks with no text on them (the `Radio` dot, the
  `BoughtToggle` checked box, which need 3:1 against the page) keep `--accent`, the ink. Menu-row and selected-card tints mix
  `--accent-fill` into `--surface`.
- **Rationale**: FR-012 requires dark text on any orange fill; a deep orange fill with dark text
  fails, and the bright one as text fails. Two tokens, equal in dark, solve both.

## R8. Input borders (FR-013)

- **Decision**: Add `--field-border` (dark `#756e82`, light `#8b8497`, ≥3.3:1 on page and surface)
  for input, select, textarea and checkbox outlines (`MinimalInput`, `GhostTextField`,
  `soft-ledger/Select`, `SearchableSelect` search field, `BoughtToggle`, `CountField`, the
  shared `:focus` rule keeps `--accent`). `--border` stays a soft divider for cards and rules
  (dark `#36313f`, light `#e4e0ea`).
- **Rationale**: FR-013 sets 3:1 for input borders only; a 3:1 divider on every card would make the
  app heavy. The portfolio's own border (surface at 50%) is near invisible, so both are derived
  (FR-009).

## R9. Shades changed from the portfolio (FR-008, listed as required)

| Role | Portfolio | Melos dark | Melos light | Reason |
|------|-----------|------------|-------------|--------|
| Error text | `#ef4444` | `#f87171` | `#c42727` | `#ef4444` is 4.41:1 on the dark surface |
| Danger (delete) | `#ef4444` | `#f26363` | `#b91c1c` | same, plus light contrast |
| Main colour ink | `#fd9c21` | `#fd9c21` | `#a65400` | 1.95:1 on the light page |
| Magenta | `#d82591` | `#d82591` (fill only) | `#d82591` (fill only) | white on it 4.57:1 passes; it is never used as text today, so no ink shade is needed |
| Danger fill | n/a | `#d32f2f` | `#d32f2f` | white text on it (`.primaryDanger`): 4.98:1; `#ef4444` would be 3.76:1 |
| Focus ring | violet 50% | orange `--accent` | orange `--accent` | clarification: focus is the main colour |
| Text (light) | n/a | n/a | `#1d1a24` | violet-grey family of `#141218` (FR-010) |
| Quiet text (light) | n/a | n/a | `#5f596b` | 6.2:1 on the page, 6.7:1 on white |
| Warning | n/a | `#facc15` | `#8a6a00` | amber in a yellower shade than the orange, to tell them apart (FR-012) |
| Success | n/a | `#4ade80` | `#15803d` | green, 4.6–10.7:1 |

The full checked pair table is in [contracts/theme-tokens.md](contracts/theme-tokens.md).

## R10. Theme boot, old colours left over, and what stays

- **Theme boot (FR-014)**: unchanged mechanism. `themeBootScript` sets `html.light`/`html.dark`
  before paint; `globals.css` keeps three blocks (`:root` light, `html.dark`, and the
  `prefers-color-scheme: dark` copy for `html:not(.light):not(.dark)`). The new test asserts the
  two dark blocks declare identical values so they cannot drift.
- **Warm leftovers (SC-004)**: `IconButton.module.scss` has hard-coded warm `rgba(226,216,200,…)`
  and moss `rgba(63,107,69,…)` "fallbacks"; replace with `color-mix` on tokens.
  `soft-ledger/Select.tsx` has `aria-invalid:border-[#b33]` → `border-error`.
  `--wb-*` aliases are removed; `MenuSurface.test.ts` and `CauldronLoader/contrast.test.ts` read
  the new values.
- **Kept as is**: `lib/avatarColor.ts` generated-avatar palette (identity colours, picks black or
  white text itself), `app/icon.svg` and `CauldronMark` geometry (logo, FR-016), the recipe PDF,
  member images, `imageEncode.ts` white canvas fill.
- **Side panel, dialogs, sheets, toasts**: take the new tokens, stay solid (spec Assumptions).
