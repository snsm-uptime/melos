# Quickstart: validating S-072

## Prerequisites

- The hot-reload stack running (`./scripts/compose-up.sh -d`), UI at <http://localhost:3000>, or
  for the browser walk the isolated stack described in the memory notes "Browser walk on WSL" and
  "Compose shares pgdata" (never a second Compose project on the main `.env`).
- A signed-in test account with one notebook of many recipes (seed data or invented recipes), a
  recipe with a photo, a kitchen with something in the cart.

## 1. Automated checks

```bash
cd ui && npm test && npm run lint && npm run typecheck
```

Expected:

- `app/palette.test.ts`: every pair in [contracts/theme-tokens.md](contracts/theme-tokens.md) passes
  in both themes; the two dark blocks match; no old Warm Balance hex remains in `globals.css`.
- `components/CauldronLoader/contrast.test.ts` and `MenuSurface.test.ts`: green on the new tokens.
- `AppShell.test.tsx` and the recipe view tests: `data-frosted` flips `false → true → false`
  with the scroller's `scrollTop` (contract [frost-surface.md](contracts/frost-surface.md)).
- No grep hits for warm leftovers:
  `grep -rnE "wb-|#3f6b45|#f7f3ec|#17140f|rgba\(63, 107, 69|rgba\(226, 216, 200" ui/app ui/components`

## 2. Browser walk: acrylic bar (story 1)

At 390×844 (phone) and 1440×900 (desktop), in dark and in light:

1. Open a long notebook at the top: the bar has no background or shadow (FR-002).
2. Scroll a little: within ~0.3 s the bar is the page colour, see-through, the cards under it
   blurred, a small shadow below (FR-003). Scroll back: it fades back.
3. Scroll a recipe photo under the bar: title, Back and icons stay readable (FR-006).
4. Phone, recipe page: its own header (Back, cart, source link, dots) frosts the same way. Desktop,
   recipe page: the header never frosts (FR-001).
5. Phone with a notch (iOS simulator or devtools safe-area): the frost fills behind the status
   bar; the bar's height and position did not change from `main` (FR-005).
6. Capture draft review: the progress bar stays at the top inside the frosted area.
7. A short page (empty notebook): the bar never frosts.
8. Devtools → Rendering → emulate `prefers-reduced-motion: reduce`: the switch has no fade.
   Emulate `prefers-reduced-transparency: reduce` (Chrome): the frosted bar is solid.
9. Side by side with the portfolio's scrolled nav in dark (SC-002): owner judges it the same effect.

## 3. Browser walk: menus (FR-017, SC-007)

Open a dots menu over a recipe photo and over plain text, a `Select` (settings), and a
`SearchableSelect` (notebook picker): each is see-through and blurred, items readable, hovered and
selected rows clearly marked in orange tint.

## 4. Browser walk: palette (stories 2 and 3, SC-004, SC-005)

In each theme, walk: sign-in, notebooks, a notebook, a recipe, the recipe editor, a kitchen, the
cart and shopping list, settings, a dialog, a dots menu, a toast, the side panel and phone drawer,
the loader, the admin dashboard.

- No cream, brown, moss green or blue from the old palette anywhere.
- Filled buttons violet with white text; links, selected cards, "in cart", the selected tab and
  focus rings orange; `AccentButton` and the loader magenta.
- An error, a warning and a success message are red, amber and green; the warning has its icon
  or wording.
- Switch light → dark → system in the account menu: every colour changes without a reload.
- Hard-reload a page with each of the three settings (and with the OS in light and in dark for
  "system"): no flash of the other theme or of the old colours.

## 5. Performance (SC-006)

Devtools → Performance, CPU 4× slowdown, scroll a 100-recipe notebook for a few seconds with the bar
frosted: no long frames compared with `main`; the scroll listener fires no React render except on
the at-top flip.
