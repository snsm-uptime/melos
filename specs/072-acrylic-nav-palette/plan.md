# Implementation Plan: Acrylic App Chrome and the Portfolio Palette

**Branch**: `072-acrylic-nav-palette` (planned on `main`) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/072-acrylic-nav-palette/spec.md`

## Summary

Two changes, both in `ui/` only.

1. **Acrylic chrome.** The app's top bar moves inside the page's scroll container and sticks to its
   top, so content really passes under it (FR-004). A small hook reports whether that container has
   scrolled; while it has, the bar (and the phone-only sticky headers of the recipe, recipe edit and
   draft review pages) shows the page colour at 88%, an 8px backdrop blur and a small shadow, fading
   over 300 ms. The frost is painted on a `::before` layer, not the bar itself, so menus opened from
   the bar can still blur the page. The shared menu surface (dots menus, `Select`,
   `SearchableSelect`) is always frosted the same way, on `--surface`.
2. **Palette.** The warm "Warm Balance" tokens in `ui/app/globals.css` are replaced by the
   portfolio's dark palette and a derived light one. Two roles are split: `--accent` stays the main
   colour (now orange) for text, icons, selection and focus, and a new `--primary` (violet) fills
   buttons; light gets a deeper orange ink plus an `--accent-fill` for orange areas. A new
   `--field-border` gives inputs a 3:1 border. Every text/ground pair is checked by a vitest that
   reads `globals.css`, as the loader's contrast test already does.

No api, mcp, database, auth or dependency change.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 16 (App Router), CSS (Tailwind 4 + SCSS modules)

**Primary Dependencies**: Tailwind 4 (`@theme` tokens in `ui/app/globals.css`), existing `MenuSurface`
module, `PreferencesProvider` theme boot script. No new library.

**Storage**: N/A (theme choice already stored on the account; unchanged)

**Testing**: vitest + Testing Library (`cd ui && npm test`), eslint, typecheck; browser walk per
[quickstart.md](quickstart.md) (Playwright on the host, see memory "Browser walk on WSL")

**Target Platform**: Modern mobile and desktop browsers (Chrome/Edge, Safari incl. iOS, Firefox)

**Project Type**: Web application (ui BFF of the four-service Compose stack); this story touches `ui/` only

**Performance Goals**: Scrolling a 100-recipe notebook stays at the current frame rate on a mid-range
phone (SC-006): one passive scroll listener, state set only when the at-top flag flips, blur limited
to the bar's own box

**Constraints**: AA contrast (FR-013) in both themes including over the darkest and lightest content
under a frosted surface; no flash of theme on first paint (FR-014); bar keeps position, height and
safe-area insets (FR-005); solid fallback without `backdrop-filter` or with reduced transparency;
no fade with reduced motion (FR-007)

**Scale/Scope**: 1 token file, 1 shell component, 3 page headers, 1 shared menu surface, about 15
components with ad-hoc `bg-accent` fills or `border-border` inputs, 3 tests pinned to old values

All unknowns resolved in [research.md](research.md); none remain.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| 1. Simplicity and Reuse | No new service, no auth change; reuses `MenuSurface`, `ChromeBack` context and the theme boot script | Pass |
| 2. Tech Stack Stability | Tailwind 4 tokens and SCSS only; no library added | Pass |
| 3. Hexagonal Architecture | api untouched | Pass (N/A) |
| 4. Security and Privacy | No secrets, no data; portfolio colours are the owner's own | Pass |
| 5. No AI Shortcuts | No AI flow touched | Pass (N/A) |
| 6. Testing and Quality | vitest contrast test over every pair (SC-003), component tests for the frost state, browser walk in both themes before done | Pass |
| 7. Deployment | No infra change | Pass (N/A) |
| 8. Git discipline | Small commits (tokens, frost, menus, call-site fixes); no push without review | Pass |
| 9. Product scope | S-072 is in the backlog (`in_design`, should) with this spec; no PRD rule lifted | Pass |

**Post-design re-check (after Phase 1)**: unchanged, all pass. The design adds three CSS tokens
(`--primary`, `--accent-fill`, `--field-border`) and one hook; no violation to justify.

## Project Structure

### Documentation (this feature)

```text
specs/072-acrylic-nav-palette/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: palette roles, frost settings, top bar state
├── quickstart.md        # Phase 1: validation walk
├── contracts/
│   ├── theme-tokens.md  # CSS custom properties, values, contrast table (SC-003)
│   └── frost-surface.md # Frosted bar/menu CSS + hook contract
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
ui/
├── app/
│   ├── globals.css                    # palette tokens (light :root, html.dark, prefers-color-scheme copy),
│   │                                  #   new --primary/--accent-fill/--field-border, frost tokens, .frost-bar utility
│   └── palette.test.ts                # NEW: every pair in contracts/theme-tokens.md meets FR-013; dark blocks match
├── components/
│   ├── AppShell.tsx                   # header moves inside the scroller (sticky top-0); data-frosted from the hook
│   ├── AppShell.test.tsx              # frost state on scroll / at top
│   ├── ChromeScroll.tsx               # NEW: ChromeScrollProvider + useChromeScrolled() (scroller ref → boolean)
│   ├── MenuSurface/MenuSurface.module.scss   # .panel frosted (surface @ --frost-alpha, blur, fallback)
│   ├── MenuSurface/MenuSurface.test.ts       # updated to the new tokens
│   ├── CauldronLoader/contrast.test.ts       # still green against new tokens (values change, logic stays)
│   ├── RecipeDetail/RecipeDetailView.tsx     # phone sticky header → frost-bar + data-frosted
│   ├── RecipeEdit/RecipeEditForm.tsx         # same
│   ├── RecipeDraft/RecipeDraftEditor.tsx     # same
│   ├── soft-ledger/BaseButton.module.scss    # .primary fills with --primary/--on-primary
│   ├── IconButton/IconButton.module.scss     # drop warm rgba fallbacks
│   └── …call sites                           # bg-accent fills → bg-accent-fill / bg-primary; input borders → border-field-border
└── app/icon.test.ts                   # unchanged (logo out of scope, FR-016)
```

**Structure Decision**: Web application, ui only. All work sits in existing folders
(`ui/app/`, `ui/components/`); the one new component file (`ChromeScroll.tsx`) sits beside
`ChromeBack.tsx`, which it mirrors.

## Complexity Tracking

No constitution violations.
