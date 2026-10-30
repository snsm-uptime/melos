# Contract: Shopping List on the Cart page (ui)

The list is a section of the existing Cart page (`/kitchens/{kitchenId}/cart`), **below the cart's recipes** (clarification 2026-10-29, FR-012). There is no new route or tab.

## Placement and visibility

- Rendered by `CartScreen` after `CartView`, for every kitchen member, in an archived kitchen, and while another member edits.
- Not rendered when the cart (or my draft) is empty: only the Cart page's own empty hint and link to the notebooks show (FR-011). The server's `is_empty` decides.
- The cart button in the kitchen page's header (`KitchenDetailChrome`, the one that opens this page) carries a circular `Badge` (`ui/components/Badge`, size "sm") on the bottom right corner of its cart icon, with the number of recipes in the cart as I see it (my draft while I edit, else the saved cart). The notebooks section, which loads the cart, publishes the count through `app/kitchens/cartCount.tsx`, so a quick add from a recipe card updates it at once. The button's accessible name includes the count ("Cart, 3 recipes" / "Carrito, 3 recetas"); above 99 the badge reads "99+"; it is hidden for an empty or unknown cart.
- The section has a heading ("Shopping list" / "Lista de compras") and, when there are vague entries, a second heading "Your call" / "A tu criterio" (wording for the owner's review).

## Data and refresh

- Data: `GET /api/kitchens/{kitchenId}/shopping-list` ([shopping-list-api.md](./shopping-list-api.md)), through `ui/lib/shoppingListClient.ts`.
- Fetched again whenever `CartScreen` replaces its cart state: first load, focus/visibility refresh, an answer to the draft `PUT`, save, discard, start edit. So the editor's list follows their draft after the existing 300 ms pause; other members see changes when they focus the page (SC-006, no manual refresh).
- A request counter drops an answer older than the latest request. The previous list stays visible while a new one loads (no flicker, no empty flash).
- If the fetch fails, the section shows a short error with a "Retry" button; the cart above is unaffected. A 404 is handled by the cart itself (the whole page shows "not found").

## Measured lines

Order is the server's. Each line:

```text
{name}[, {size}] — {amounts}            chips
flour — 1 cup + 3 tbsp                  [Bread] [Pancakes]
onion, large — 2                        [Stew]
```

- `{amounts}`: each `{quantity} {unit}` joined with " + ". For `count`, the number only (FR-009).
- Units show as their stored codes (`cup`, `tbsp`, `g`); like names and titles, they are not translated (FR-013).
- `{size}` is shown after the name as stored for counts with a size (`onion, large`); a count with no size shows only the name.
- Wording lives in `ui/lib/shoppingListText.ts` so tests can check it without rendering.

## "Your call"

```text
salt — a pinch, to taste                [Bread] [Stew]
```

One entry per ingredient: the name, then its notes joined with ", ", then chips.

## Chips

- A chip shows a recipe's title and links to `/recipes/{recipe_id}?from=/kitchens/{kitchenId}/cart` (same as the cart rows), so Back returns to the Cart page (FR-008).
- The link is a real anchor, keyboard focusable, with a visible focus style, a touch target of at least 44 px height on phones, and the title as its accessible name. Long titles wrap or truncate with the full title in `title`.
- Chips wrap onto more lines at phone width; the page never scrolls sideways.

## States

| State | Shows |
|---|---|
| first load | a short loading line (`role="status"`) |
| list ready | the sections above |
| cart has recipes but no ingredient lines | the heading and a short "No ingredients in these recipes" line |
| fetch error | error line (`role="alert"`) and Retry |
| empty cart | nothing from this section |

## Text (es + en, `ui/lib/i18n/shoppingList.ts`)

`title`, `yourCall`, `loading`, `loadError`, `retry`, `noIngredients`, and any `aria-label` for the list and chips. Registered in `ui/lib/i18n/parity.test.ts` so a message missing in one language fails the build (spec 063). No error codes shown to the member.

## Tests

vitest: wording (`shoppingListText`), section states (loading, ready, empty cart renders nothing, error + retry), chip hrefs, refetch after a cart state change, ignoring a stale answer. The two-account browser walk is in [quickstart.md](../quickstart.md).
