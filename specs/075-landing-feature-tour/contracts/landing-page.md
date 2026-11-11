# Contract: signed-out landing page

Route: `/` (`ui/app/page.tsx`), server component, `dynamic = "force-dynamic"` as today.

## Behaviour kept

- A signed-in visitor is redirected exactly as today (`resolveServerAuthenticatedLanding`,
  `requireAlias`, `RedirectIfAuthenticated`) (FR-014).
- Language from `getServerLocale()` (spec 063); the floating `SignedOutLanguageSwitch` stays.
- "Create an account" links to `/signup`, "Sign in" to `/sign-in`.

## Structure, top to bottom

| # | Region | Content | Anchor |
|---|---|---|---|
| 1 | Hero | `h1` with `CauldronMark` + headline, intro, account buttons, overview demo | — |
| 2 | Index | `nav` labelled by the page language, six links in group order | — |
| 3–8 | Group sections | `section` with `h2` title, lede, `ul` of available features (name + summary), demo | `#capture`, `#notebooks`, `#together`, `#shop`, `#ingredients`, `#home` |
| 9 | Coming soon | `h2`, `ul` of planned features (name + summary); not rendered when empty | `#coming-soon` |
| 10 | Closing CTA | Short line, "Create an account", "Sign in" | — |

Exactly one `h1`. Section titles are `h2`. Anchors are the same in both languages.

## DemoFrame (client component)

Props: `id: DemoId`, `title: string`, `description: string`, `pauseLabel: string`,
`playLabel: string`, `children` (the server-rendered scene).

| Condition | Result |
|---|---|
| Frame less than 35% in view | `data-playing="false"`; all animations paused |
| In view and not paused by the visitor | `data-playing="true"` |
| Pause button pressed | `aria-pressed="true"`, label switches to play, animations paused in place |
| `prefers-reduced-motion: reduce` | No animation declared (CSS); pause button not rendered; final state shown |
| No IntersectionObserver / before hydration | Final state shown (animations only run under `data-playing="true"`) |

Accessibility: root `role="group"` + `aria-label={title}`; scene wrapper `aria-hidden="true"`;
visually hidden `<p>` with `description`.

## Scenes (final state, i.e. what reduced motion shows)

| Demo | Final state shows (en / es) |
|---|---|
| overview | One shopping line "flour — 1 cup + 3 tbsp" / "harina — 1 taza + 3 cdas" with two recipe chips, after capture, notebook and cart steps |
| capture | Draft lines: salt with a vague note; "onion 2 unit large" / "cebolla 2 unidad grande" |
| notebooks | Recipe page with servings 2 (from 4) and halved amounts |
| together | Kitchen with two invented members and their notebooks; "Sent to Leo" style confirmation |
| shop | Store tab selected, "flour — 1 cup + 3 tbsp" with chips A and B, two lines marked bought |
| ingredients | "onions" merged into "onion", Spanish variant "cebolla" shown |
| home | The same card in Spanish and dark theme beside English and light |

Scenes are the app's own components with invented data (research R5), inside an `inert`,
`aria-hidden` wrapper. No scene makes a network request, links to an app route, or uses a real
name or recipe. Units show as the app shows them in both languages ("1 cup + 3 tbsp", "2 unit
large").

## Surface band edges (FR-018)

The full-width surface band (`SurfaceBand`, `data-landing-band`) behind "Cook together" and "Plan
the week and shop" has curved top and bottom edges instead of straight borders. The hero keeps its
waves; no other section has background decoration.

- Each edge is an `<svg data-landing-band-edge="top|bottom" aria-hidden="true" focusable="false">`
  with `pointer-events-none`, as wide as the band, reaching 32 px (48 px from md) into the
  neighbouring section's padding and overlapping the band by 1 px so no seam shows.
- The svg fills the band side of the curve with `--surface` and draws `--border` along the curve
  (a non-scaling 1 px stroke). Still; no animation. The fill, stroke and the outside position are
  inline styles, not utility classes, so an edge is never drawn black or inside the band while a
  stylesheet lacks new classes (seen on a dev server that had not recompiled).
- The page test checks the two edges sit around the band's sections, are hidden and still, and
  that no straight `border-y` or glow remains.
