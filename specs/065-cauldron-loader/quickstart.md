# Quickstart: Cauldron Loader

## Setup

```bash
./scripts/compose-up.sh -d
```

Sign in with the dev seed owner. In the browser dev tools, throttle the network to "Slow 3G" so loading states last long enough to watch.

## Automated checks

```bash
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: no failures beyond the baseline recorded for S-023. The new tests cover the tilt rule, the 45-degree bounds, contrast in both themes and every button variant, the markup and labels, and the swapped call sites. The parity test covers "Loading" and "Cargando".

## Browser walk

Run in light and dark, in English and Spanish, at 1280px and 360px.

1. **Loop** (US1, SC-001): On a page that loads slowly, watch one loader for 60 seconds. Bubbles keep leaving the mouth, fade out above, and no restart can be spotted.
2. **Tilt** (US2, SC-002): It rocks to about 25 degrees each side. Slow the animation in dev tools and check the ends ease in and out. In a loading button it rocks to about 10.
3. **Custom and odd angles**: Temporarily set `tilt` to 0, -10, 90 and a non-number on one call site. Expect upright, 10, 45 and the default.
4. **Colours** (US3, SC-003): Bubbles and drip are the accent, the cauldron stands out on the page and on a card. Switch theme while it runs: colours change, the loop does not restart.
5. **Buttons**: Trigger loading on a Primary, an Accent and a Ghost button (sign in, sign up, verify, forgot password). The button keeps its colours, and the cauldron, bubbles and drip are all visible on the fill. Measure the button's height idle and loading in dev tools for `sm`, `md` and `lg`: the two numbers are equal.
6. **Small and many**: Look at the 1.25rem header save action and at two loaders on one screen. Nothing is clipped, nothing pushes content around, and they run independently.
7. **Screen reader** (US4, SC-005): With VoiceOver in Safari on a throttled page, a page-level loader announces "Loading" in English and "Cargando" in Spanish, and a specific one (recipe list, kitchen, joining a kitchen) announces its own message. The drawing is not read out. If a page-level loader is not announced, apply the fallback in research R9. On a loading Primary button, focus it: it reads its label, the hidden loading text and "busy". Record the result.
8. **Reduced motion** (SC-006): Turn on "Reduce motion" in the OS. Over 30 seconds nothing moves, and the cauldron and bubbles are still shown.
9. **Short load**: With the network fast, the loader shows at once and is gone when the content arrives, with no leftover shape.
10. **Performance** (SC-004): Record 30 seconds on a phone or with 4x CPU throttle. No dropped frames; the frames panel shows no layout or paint per frame.
11. **Sweep** (SC-007): Run
    ```bash
    cd ui && grep -rnE "animate-spin|animate-pulse|SpinnerIcon|base-button-spin" app components
    ```
    Expected: no match.
