# Contract: Cart and lock UI

All text in `ui/lib/i18n/cart.ts`, Spanish and English (spec FR-024); the parity test covers it.

## Cart page — `/kitchens/{kitchenId}/cart`

Reached from a "Cart" entry beside the kitchen's Notebook tab.

- **Saved view** (nobody or someone else editing): people number, list of entries (title link → recipe detail, notebook name, "Serves 4", "Meals 1", "×0.5"). People shows "(members)" while it follows the member count.
- **Editor notice**: "{alias} is editing the cart" (es: "{alias} está editando el carrito"); all controls disabled.
- **Edit** button (free cart, not archived) → editing view.
- **Editing view** (my draft): steppers/fields for people and each meals (whole 1–99; invalid input keeps the last valid value and shows "Enter a whole number from 1 to 99"), Remove per entry, Clear (confirm dialog), factors recomputed live with `lib/cartFactor.ts` (same rounding as the api), **Save** and **Discard**. A banner lists recipes dropped because they were deleted.
- **Empty**: hint "Add recipes from the kitchen's notebooks", with a link to the Notebook tab.
- **Archived kitchen**: saved view, no Edit.

## Editing bar (FR-017a, research R12, R13)

`CartEditingBar` shows **only on the Cart page**, while my session holds the cart lock, fixed above the tab bar at the bottom of the screen body: "You're editing the cart. Others can't change it until you save or discard." with **Save** and **Discard**. One minute before `idle_expires_at` it turns into a warning, "Your cart changes will be discarded in 1 minute", with **Keep editing**. After expiry it says "Your cart changes were discarded" and the page reloads the saved cart. The kitchen recipe list and recipe pages show no bar.

## Toasts (FR-017b, FR-017d, research R13)

One viewport in `AppShell`, at the bottom of the screen body directly above the tab bar (above the safe-area inset when there is no tab bar); toasts stack above the Cart page's editing bar. `role="status"`, polite.

| When | Text | Closes |
|---|---|---|
| A card or recipe-page add/remove gets 409 `cart_locked` | "{alias} is editing the cart" ("unknown" without alias) | after 4 s or on tap |
| I hold the cart lock, on the kitchen list or a kitchen recipe page, 1 min before `idle_expires_at` | "Your cart changes will be discarded in 1 minute" + **Keep editing** | on Keep editing (keep-alive) or expiry |
| Same pages, after expiry | "Your cart changes were discarded" (replaces the warning) | after 4 s or on tap |

A successful add or remove shows no toast.

## Cart-icon button (FR-017c, research R14)

On kitchen recipe cards (spec 021 list) and kitchen recipe pages, replacing the checkbox: an `IconButton` (ghost) with `CartPlusIcon`. Not in the cart (my draft while I hold the lock, else the saved cart): a cart with "+" in the basket, label "Add to cart". In the cart: the "+" turned 45° into "×", label "Remove from cart", `aria-pressed="true"`. Tapping toggles through the draft item routes. It stays **enabled** while someone else edits; the refusal shows the toast above, and the state does not change. No inline editor notice on cards or the recipe page. Personal notebook cards and recipes have no button.

## Recipe detail (spec 027)

- Kitchen recipes: the cart-icon button above.
- When another session holds the recipe lock: Edit and Delete disabled, notice "{alias} is editing this recipe".

## Recipe edit page (spec 027)

On open, takes the recipe lock. If refused: read-only page with the notice and a link back. Save and Cancel release the lock; leaving the page releases it best effort. A 409 on save shows the notice and keeps the typed edits on screen.

## Activity

Typing or selecting in the Cart editing view or the recipe Edit page sends a keep-alive at most every 30 s. A page that is merely open sends nothing, so a forgotten tab loses the lock after 5 minutes.
