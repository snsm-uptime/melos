# Research: Cauldron Loader

Contrast figures were calculated from the color values in `ui/app/globals.css` and `BaseButton.module.scss`.

## R1. How to animate

- **Decision**: One inline SVG with CSS keyframes in an SCSS module. No JavaScript.
- **Rationale**: `ui/app/icons/README.md` says to prefer CSS. Transforms and fades cover this, and CSS leaves the component server-renderable for `loading.tsx`. Keyframes also keep running through a theme change, because only colors change (User Story 3).
- **Alternatives considered**: A frame loop in JavaScript needs a client boundary and stops when the main thread is busy, which is when a loader matters most. An animation library is a new dependency for no gain. Separate HTML layers might run more smoothly in some browsers, but they split one drawing into several pieces. If the browser walk shows stutter, this is the fallback.

## R2. A loop with no seam

- **Decision**: One 2.4 s loop. The cauldron swings from left to right in 1.2 s, then back. Each bubble takes 2.4 s; the second starts half a loop later through a negative delay. Bubble opacity is 0 at both ends of its keyframes. Rocking uses ease-in-out.
- **Rationale**: Equal periods make the whole picture repeat exactly, so it cannot drift over a long load. Zero opacity at both ends hides each bubble's jump back to the start. A negative delay means the second bubble is already moving on first paint. Ease-in-out gives the slow turn in FR-007. 2.4 s is a starting value, tuned by eye.
- **Alternatives considered**: Unrelated periods look more organic, but the picture would then only repeat after a long time and is harder to check.

## R3. Colors

- **Decision**: A theme token `--cauldron-body`, set in all three theme blocks of `globals.css`: light `color-mix(in srgb, var(--background) 10%, var(--foreground))`, dark the same with 60%. The drip sits in a slot cut through the body, wider than the drip, so a ring of whatever lies behind the loader surrounds it.
- **Rationale**: Both shades start from the theme's background, and both pass:

  | Theme | Shade | Against background | Against surface | Accent against shade |
  |---|---|---|---|---|
  | Light | `#3f3931` | 10.31 | 11.15 | 1.85 |
  | Dark | `#6e6961` | 3.37 | 3.05 | 2.51 |

  The accent column shows why the slot is needed: no shade passing 3:1 against the background also separates well from the accent, so the drip would blur into the body. The light shade is dark to match the supplied drawing. The dark theme's surface figure of 3.05 leaves little margin, so a later change to those colors needs a recheck.
- **Alternatives considered**: One shared mix for both themes passes only near 50%, which gives a grey light-theme cauldron with accent contrast of 1.84. A background color drawn over the body instead of a slot breaks on cards and buttons.

## R4. Inside buttons

- **Decision**: The body uses `currentColor`. The bubbles and drip use `currentColor` at 80%, through `color-mix` with transparent. Because the drip sits in the slot, it blends with the button fill and not with the body. A loading button keeps its normal colors instead of its disabled ones: `aria-busy="true"` overrides the disabled styling in `BaseButton`, and in `HeaderAction`, `TextCaptureSheet` and `HandItems`.
- **Rationale**: `BaseButton` disables itself while loading, and its disabled colors reach only 1.97 (light) and 2.16 (dark). `HeaderAction`'s `disabled:opacity-50` reaches 2.04 and 2.62. So SC-003 fails unless a busy button keeps its colors. It still cannot be pressed. A fixed 80% needs no knowledge of the fill. Figures for each tone against its fill:

  | Button | Theme | Body | Bubbles and drip |
  |---|---|---|---|
  | Primary | Light | 6.03 | 4.54 |
  | Primary | Dark | 8.45 | 5.82 |
  | Accent (secondary) | Light | 6.78 | 5.01 |
  | Accent (secondary) | Dark | 10.06 | 6.57 |
  | Ghost | Light | 5.40 | 3.58 |
  | Ghost | Dark | 6.57 | 4.76 |
  | `HeaderAction`, accent tone | Light | 5.58 | 3.69 |
  | `HeaderAction`, accent tone | Dark | 8.45 | 5.83 |

- **Alternatives considered**: Hosts declaring their fill color touches every host and is easy to forget. Below about 75% the ghost button falls under 3:1. This changes how a loading button looks: it stays full color instead of greying out.

## R5. Tilt and drawing box

- **Decision**: `tilt.ts` holds the two defaults (25 general, 10 button), the angle rules from the spec's Edge Cases, and the function that works out the drawing's square box from the angle. The component passes the angle to CSS as `--cauldron-tilt`, and the pivot is at the bottom centre of the body.
- **Rationale**: Working out the box from the angle fits the drawing as large as it can be: a 10-degree button loader is not shrunk to leave room for 45. This meets FR-013 and helps at icon size. Bubbles are drawn behind the body, starting inside it, so they rise out of the mouth at any lean.
- **Alternatives considered**: One fixed box sized for 45 degrees makes every loader smaller than it needs to be.

## R6. Sites to change

| Kind | Sites | Change |
|---|---|---|
| Spinner in a button | `BaseButton` (and so 6 forms and `ActionDialog`), `RecipeDraftEditor`, `RecipeEditForm` | Button placement |
| Text-swap button with no spinner | `TextCaptureSheet`, `HandItems` | Button placement beside the text |
| Icon submit | `InviteForm` through `FormIconField` | Glyph becomes a button-placement loader |
| Spinner in a panel | `ItemChipSelector`, `StackedListPanel` | Page placement |
| Pulsing placeholder | `app/kitchens/[kitchenId]/loading.tsx` | Page placement, with `animate-pulse` gone |
| "Loading…" text | `CartScreen`, `RecipeList`, `RecipeDetailScreen`, `RecipeEditScreen`, `ShoppingListSection`, `ClosedLists` (2 places), `SignupForm` | Page placement; text becomes the label |
| Progress text | `AcceptInvitePanel` (pending only), `RecipeEditForm` `checkingNames` | Loader beside the visible text |
| Shows nothing while loading | `NotebookTabScreen`, `NotebookRecipesScreen`, `KitchenNotebooksSection` | Page placement, new label |

- **Decision**: After the swap, `SpinnerIcon`, its README entry, the `Spinner` in `BaseButton` and its keyframes are deleted, and no `animate-spin` or `animate-pulse` remains (SC-007). The label moves to screen-reader-only text inside the `role="status"` element, so the sighted person sees only the cauldron and tests that find the text keep passing. The last row needs a new `loading` message in `ui/lib/i18n/notebooks.ts`, in Spanish and English.
- **Rationale**: The screens with no loading state are included because FR-015 calls for one consistent loader and a blank wait is the worst case. The kitchen page was the app's only placeholder that previewed the layout, and it now loses that, as the clarification decided.
- **Left alone**: `SidePanel`, which fills in quietly as a background part of the page. `TopProgressBar` shows measured progress, not a wait. `StackedListPanel` has no callers today; it gets the swap so `SpinnerIcon` can go, but no label is added.
- **Note**: `NotebookTabScreen.tsx`, its test, and `NotebookRecipesScreen.test.tsx` have uncommitted changes in the working tree. Commit or merge those first, so the two pieces of work do not mix.
