# Contract: `CauldronLoader`

Imported from `@/components/CauldronLoader`. It renders on the server or the client.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `label` | `string` | none | The loading message for screen readers, in the person's language. |
| `placement` | `"page" \| "button"` | `"page"` | Sets the colors, the default tilt and the size. |
| `tiltDegrees` | `number` | By placement | Overrides the default for this use. See [data-model.md](../data-model.md). |
| `className` | `string` | none | Sets the size and spacing from the place using it. |

## Behaviour by placement

| | `page` | `button` |
|---|---|---|
| Default tilt | 25 | 10 |
| Body color | `--cauldron-body` | `currentColor` |
| Bubbles and drip | `--accent` | `currentColor` at 80% |
| Default size | `size-16` | `1.25em`, with no change to the button's height |

## Accessibility

- With `label`: the root has `role="status"`, the text is screen-reader-only, and the drawing is `aria-hidden`.
- Without `label`: the whole loader is `aria-hidden`. Only for use where the wait is already announced, such as inside a button with `aria-busy` and its own text.

## Rules for places that use it

- A button showing the loader sets `aria-busy` and keeps its normal colors (research R4).
- A page wait passes the most specific message it has, such as "Loading the cart".
- It takes no focus and no input.
- It is not wrapped in another `role="status"`.

## Removed

`SpinnerIcon`, the `Spinner` in `BaseButton`, and all use of `animate-spin` and `animate-pulse`.
