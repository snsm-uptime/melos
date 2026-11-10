# Quickstart: validate the landing page feature tour

## Prerequisites

- Repo set up per AGENTS.md (`.env`, data dir, `cd ui && npm install`).
- Stack running: `./scripts/compose-up.sh -d`; ui at <http://localhost:3000>.

## Automated checks

```bash
cd ui
npm test -- featureInventory LandingTour page.home parity
npm run lint && npm run typecheck
```

Expected: inventory invariants pass ([contracts/feature-inventory.md](contracts/feature-inventory.md));
page tests show the regions in the order of [contracts/landing-page.md](contracts/landing-page.md)
in `en` and `es`; parity finds no one-language string; the English page contains "shopping list"
and not "Shopping kitchen", the Spanish page "lista de compras" and not "Cocina de compras".

## Browser walk (signed out, private window)

1. Open `/`. The hero shows the new headline, both account buttons and the overview demo playing.
   It ends on the "flour — 1 cup + 3 tbsp" line within 20 s and loops. (US1, FR-002a)
2. Press the overview's pause button; the scene stops in place; press again to resume. (FR-007)
3. Scroll down: six sections appear in order Capture, Notebooks, Cook together, Plan and shop,
   Ingredients, Home. Each lists its features and plays its demo only once in view; each loop is
   under 15 s. (FR-003, FR-006, SC-004)
4. Count the features listed in the six sections: at least 20, each feature once. Check them
   against the running app; any that do not work today are fixed in the inventory. (SC-001, SC-002)
5. The "Coming soon" strip lists the planned features with no demos; then the closing call to
   action shows both buttons. (FR-004, FR-012)
6. Choose each index entry: the page moves to that section, its title not hidden. Open
   `/#shop` in a new tab: it opens at Plan and shop. (US3)
7. Switch to English with the language switch, then back to Spanish: every title, list, demo text
   and screen-reader description changes language. (US4)
8. Turn on reduced motion (macOS: Accessibility > Display > Reduce motion). Reload: nothing moves,
   every demo shows its final state, no pause buttons. (FR-008)
9. DevTools at 320 px width, light and dark themes: no sideways scroll, demos fit. (FR-015)
10. DevTools Network tab while all demos play: no request to `/api/*`. (FR-010)
11. VoiceOver over a demo: reads its title and description, not the animated fragments. (FR-009)
12. Sign in, then open `/`: redirected to the usual start page as before. (FR-014)
