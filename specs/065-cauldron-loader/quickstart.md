# Quickstart: Validate the Cauldron Loader

## Prerequisites

- The stack running with `./scripts/compose-up.sh -d` (UI at <http://localhost:3000>), never a second Compose project with the main `.env`.
- A signed-in test account with a kitchen, a notebook and a recipe.
- Browser dev tools, with network throttling set to Slow 3G to hold waits open.

## Automated

```bash
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: all pass, including the tilt rules in the [data model](data-model.md) and the props in the [contract](contracts/cauldron-loader.md).

```bash
grep -rnE 'SpinnerIcon|animate-spin|animate-pulse' ui/app ui/components
```

Expected: no output (SC-007).

## Browser walk

| # | Do | Expect | Covers |
|---|---|---|---|
| 1 | Open the cart with throttling on and watch for 60 seconds, holding the wait open if needed | Bubbles rise and fade; no visible restart | SC-001 |
| 2 | Pause the animation in dev tools at both ends of a swing and read the rotation | 25 degrees each way, within 1 | SC-002 |
| 3 | Sign in with throttling on | Button loader rocks 10 degrees; button keeps its fill and height | SC-002, SC-003 |
| 4 | Check a primary, an accent and a ghost button, and the recipe Save header action, in both themes | Cauldron, bubbles and drip are all readable | SC-003 |
| 5 | Show a page loader on a card and on the page, in both themes | Cauldron is clear on both; the drip stands apart from the body | SC-003 |
| 6 | Switch theme during a wait | Colors change; the motion does not restart | User Story 3 |
| 7 | Record 30 seconds on a phone, or with 4× CPU slowdown | No visible stutter | SC-004 |
| 8 | Use a screen reader in Spanish and in English | The loading message is read in that language | SC-005 |
| 9 | Turn on reduce motion | Still cauldron and bubbles for 30 seconds | SC-006 |
| 10 | Open a notebook, the notebook tab and a kitchen's notebooks with throttling on | Loader shows instead of a blank area | FR-015 |
| 11 | Load a page on a fast connection | Loader shows at once and leaves at once, with nothing left behind | FR-016 |
| 12 | Look at the loader at button size next to the label | The shape still reads as a cauldron | Open risk, research R5 |

## If something fails

If step 7 stutters, use the fallback in research R1. If step 12 fails, take it back to the owner: the clarified decision keeps the cauldron in buttons, so changing that is their call.
