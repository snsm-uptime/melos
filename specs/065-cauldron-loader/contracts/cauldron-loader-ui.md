# Contract: Cauldron loader (UI)

## Component

`import { CauldronLoader } from "@/components/CauldronLoader";`

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `tone` | `"page" \| "button"` | `"page"` | Colour set and tilt default (see [data-model.md](../data-model.md)). |
| `tilt` | `number` | by tone: 25 page, 10 button | Degrees each way. Resolved by `resolveTilt` (0 to 45, sign ignored, non-number takes the tone default). |
| `size` | CSS length | `3rem` page, `1.2em` button | Page tone: the width, height follows the drawing. Button tone: the **height**, width follows the drawing, so a button never grows. |
| `label` | `string` | "Loading" / "Cargando" | Screen-reader text, for a more specific message. |
| `className` | `string` | none | Placement only (margin, alignment). |

No click, focus or keyboard behaviour. No children.

## Markup

```text
<!-- page tone -->
<span role="status" aria-live="polite" class="root" style="--cauldron-tilt: 25deg; width: 3rem">
  <svg aria-hidden="true" focusable="false" viewBox="…">
    <g class="bubbles">   two or more circles, different radii, no ids
    <g class="cauldron">  body, rim, two handles, two feet, drip
  </svg>
  <span class="sr-only">Loading</span>
</span>

<!-- button tone: no role, no aria-live; height is set, not width -->
<span class="root" style="--cauldron-tilt: 10deg; height: 1.2em"> … same children … </span>
```

The children of a `<button>` are presentational, so a nested `role="status"` would not be announced. In a button the hidden text joins the button's accessible name and the button's `aria-busy` says it is busy (research R9).

- No `id`, `clipPath`, `mask` or gradient. Several loaders on one screen are independent.
- The root is `display: inline-block`. Everything is drawn inside the `viewBox`, so nothing needs `overflow: visible`.

## CSS hooks

| Custom property | Set by | Used for |
|---|---|---|
| `--cauldron-tilt` | the component, from `tilt` | Rock keyframes. |
| `--loader-ink`, `--loader-fill` | `BaseButton.module.scss` per variant, or defaults | Button-tone colours. |

Animation rules live inside `@media (prefers-reduced-motion: no-preference)`. Outside it, the still pose shows: upright, bubbles visible.

## Behaviour checks

| Case | Result |
|---|---|
| No `tilt`, page tone | Rocks to ±25° |
| No `tilt`, button tone | Rocks to ±10° |
| `tilt={0}` | Upright, bubbles rise |
| `tilt={-10}` | Same as 10 |
| `tilt={90}` | Same as 45 |
| `tilt={NaN}`, `tilt="x"` | Tone default |
| Theme switch while running | Colours change, animation does not restart |
| Reduced motion | Still cauldron and bubbles |

## Call sites to replace (FR-015)

| # | File | Today | After |
|---|---|---|---|
| 1 | `components/soft-ledger/BaseButton.tsx` | private `Spinner` svg + `.spinner` CSS | `<CauldronLoader tone="button" />` |
| 2 | `components/ItemChipSelector/ItemChipSelector.tsx` | `SpinnerIcon` `animate-spin` in the dialog body | `<CauldronLoader />` |
| 3 | `components/RecipeEdit/RecipeEditForm.tsx` | `SpinnerIcon` in the save header action | `<CauldronLoader tone="button" size="1.25rem" label={t.saving} />` (height 1.25rem) |
| 4 | `components/RecipeDraft/RecipeDraftEditor.tsx` | same | same |
| 5 | `components/StackedListPanel/StackedListPanel.tsx` | `SpinnerIcon` in a `role="status"` box | `<CauldronLoader />` with the box's `loadingLabel` |
| 6 | `app/kitchens/[kitchenId]/loading.tsx` | `animate-pulse` blocks | one `<CauldronLoader label={t.loadingKitchen} />` |
| 7 | `app/signup/SignupForm.tsx` | text `t.loadingInvite` | `<CauldronLoader label={t.loadingInvite} />` |
| 8 | `components/RecipeList/RecipeList.tsx` | text `t.loading` | `<CauldronLoader label={t.loading} />` |
| 9 | `components/RecipeEdit/RecipeEditScreen.tsx` | text | same |
| 10 | `components/RecipeDetail/RecipeDetailScreen.tsx` | text | same |
| 11 | `components/Cart/CartScreen.tsx` | text | same |
| 12 | `components/ShoppingList/ShoppingListSection.tsx` | text | same |
| 13 | `components/ShoppingList/ClosedLists.tsx` | text, two places | same |
| 14 | `app/invites/accept/AcceptInvitePanel.tsx` | text `t.accepting` while `pending` | `<CauldronLoader label={t.accepting} />`; the success line stays |
| 15 | `components/RecipeEdit/RecipeEditForm.tsx` | text `t.checkingNames` while `checking` | `<CauldronLoader label={t.checkingNames} size="1.25rem" />` |

Status lines that show a **result** (invite sent, copied, saved, dropped, toasts, confirmations) are not loading states and stay. So do button label swaps such as "Saving…". Rows 8 to 15 keep their old message as the screen-reader label, and the visible text is dropped.

`NotebookTabScreen`, `NotebookRecipesScreen` and `KitchenNotebooksSection` keep a `"loading"` state that renders no loading element of its own (the list below them does), so they need no change. The sweep task confirms it.

Removed: `app/icons/SpinnerIcon.tsx`, its export in `app/icons/index.ts`, its section in `app/icons/README.md`, `.spinner` and `@keyframes base-button-spin` in `BaseButton.module.scss`.

## Loading button (BaseButton)

While `loading`, the button keeps its variant fill and text colour, with no hover lift. It stays `disabled`, keeps `aria-busy`, and gets `cursor: progress`. The grey disabled look still applies to buttons that are disabled without loading.

## Text

`ui/lib/i18n/loader.ts`, in the parity test:

| Key | English | Spanish |
|---|---|---|
| `loading` | Loading | Cargando |
