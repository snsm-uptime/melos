# Research: Shared Kitchen Cart and Single-Editor Locks (S-022)

No item in the Technical Context was left as NEEDS CLARIFICATION. Each decision below was made from the current code (`api/adapters/persistence/models.py`, `sessions.py`, `api/api/deps.py`, `application/recipe_manage.py`) and the spec.

## R1. Cart tables and when the cart is created

- **Decision**: `cart(id, kitchen_id unique → kitchens ON DELETE CASCADE, people int NULL, updated_at, updated_by)` and `cart_item(cart_id → cart CASCADE, recipe_id → recipe CASCADE, meals, added_at, pk(cart_id, recipe_id))`. The cart row is created on first use with `INSERT … ON CONFLICT (kitchen_id) DO NOTHING`; the migration does not backfill.
- **Rationale**: The kitchen service and its tests are untouched; a kitchen with no row reads as an empty cart with the default people (spec Assumptions: members never see a kitchen without a cart). FK cascades give FR-012 for recipe, notebook (recipe cascades from notebook) and kitchen deletes with no extra code.
- **Alternatives**: Create the cart in the kitchen service (touches kitchen creation and signup's "My kitchen", for no visible gain). Explicit delete in `DeleteRecipeService` only (misses notebook and kitchen deletes).

## R2. People default = member count

- **Decision**: `cart.people` is NULL until a member saves a people number (FR-002). Reads use `domain.cart.effective_people(saved, member_count) = saved if saved is not None else min(member_count, 99)`; the count comes from `kitchen_memberships`.
- **Rationale**: "Follows membership until set" needs no trigger or job: it is computed on read. A saved value is never overwritten.
- **Alternatives**: Store the count at creation (stale after joins). A boolean `people_set` flag beside a stored number (two fields to keep in step).

## R3. Locks tied to the session without changing the auth layer

- **Decision**: `cart_edit_lock(cart_id pk → cart CASCADE, session_id → sessions.id CASCADE, user_id → users CASCADE, acquired_at, draft jsonb)` and `recipe_edit_lock(recipe_id pk → recipe CASCADE, session_id → sessions.id CASCADE, user_id, acquired_at)`. A new dependency `require_session_ref` resolves the cookie token to `(user_id, session_id)` with its own query in `adapters/persistence/edit_locks.py`; `sessions.py`, `SessionStore` and the auth routes are unchanged.
- **Rationale**: Sign-out (`revoke_session`) and the password-reset "sign out everywhere" (`revoke_all_sessions_for_user`) already delete session rows; the cascade drops the lock and its draft (FR-020) for free. Expired sessions are not deleted today, so every lock read joins `sessions` and ignores a lock whose `expires_at <= now()`. One lock per resource is the primary key.
- **Approval**: the owner approved `require_session_ref` on 2026-10-29.
- **Alternatives**: Hook sign-out to release locks (changes auth code, needs approval, misses expiry). Lock by user id (would block the same person's other device, against FR-021; would survive sign-out). One polymorphic `edit_lock` table (no FK to the resource, so no cascade on delete).

## R4. A lock is live only while its holder may still write (amended 2026-10-29, see R11)

- **Decision**: A lock counts as held only if its session exists and is not expired **and** its user can still write the resource: for the cart, a member of a non-archived kitchen; for a recipe, `can_write_recipes` on its notebook (spec 027). Dead locks are ignored on read and replaced on the next acquire.
- **Rationale**: Covers FR-020's "loses access" (leaving, removal, archive) without hooks in membership code, which has no leave/remove routes yet.
- **Alternatives**: Delete locks in every membership or archive path (spread over modules, easy to miss).
- **Amendment**: on its own, "ignore while dead" lets a lock come back when access is restored, which spec FR-020b forbids. R11 makes access loss delete the lock; the live check stays as a backstop.

## R5. Serializing concurrent lock attempts

- **Decision**: Acquire runs in one transaction: `SELECT … FOR UPDATE` on the cart row (created first if missing) or the recipe row, read the existing lock, and if none is live, upsert the caller's session as holder. Same session → returns the existing lock (FR-021).
- **Rationale**: Exactly one winner for racing members (spec edge case) with plain Postgres row locks; no advisory locks or retries.
- **Alternatives**: `INSERT … ON CONFLICT DO NOTHING` alone (cannot replace a dead lock atomically).

## R6. The cart draft

- **Decision**: The draft is `{people: int|null, items: [{recipe_id, meals}]}` in `cart_edit_lock.draft`, created as a copy of the saved cart when the lock is taken. The ui sends the whole draft on each change (`PUT …/cart/draft`), validated (bounds, kitchen-notebook recipes, no duplicates). Save, in one transaction: drop draft items whose recipe no longer exists (reported back as `dropped_recipe_ids`), replace `cart_item`, set `people`, add 1 to `cart_add_count` for each recipe newly present versus the saved cart (FR-013), delete the lock.
- **Rationale**: Whole-draft replace keeps the api small and the ui simple; the diff against the saved cart at save time is the exact "addition" the PRD counts. A discarded draft never touches counts.
- **Alternatives**: Per-item draft routes (more routes, same result). Counting at draft time (a discarded draft would raise the count).

## R7. Quick add from the list and detail page

- **Decision**: `POST /kitchens/{id}/cart/draft/items` takes the lock if free (or uses the caller's), adds the recipe with meals 1 to the draft, and answers with the draft. The cart-icon button on cards and on the recipe page calls it; removal calls `DELETE …/draft/items/{recipe_id}`. A successful add or remove shows no message (spec FR-017a). While someone else holds the lock the button stays enabled; the api answers 409 `cart_locked` with `editor_alias`, and the ui shows the toast (R13, spec FR-017b). *(Amended 2026-10-29, UI clarification: replaces the checkbox, the "review and save" prompt and the disabled state.)*
- **Rationale**: One rule for all cart writes (spec Assumptions); nothing reaches the shared cart without a save.
- **Alternatives**: Let quick add write straight to the saved cart when nobody edits (two write paths; races with someone starting an edit).

## R8. Recipe lock in the spec 027 flow

- **Decision**: The edit page calls `POST /recipes/{id}/edit-lock` on open; 409 shows the notice and a read-only view. `PUT /recipes/{id}` requires the caller's session to hold the lock (409 `recipe_locked` otherwise) and releases it on success; cancel and leaving the page call `DELETE /recipes/{id}/edit-lock` (best effort via `navigator.sendBeacon`, the session-scoped lock covers the rest). `DELETE /recipes/{id}` is refused with 409 while another live session holds the lock. `GET /recipes/{id}` gains `editor: {alias, is_me} | null`. Spec 027's `updated_at` version check stays as a backstop.
- **Save unlocks**: a successful save releases the lock in the same transaction as the write, for both the recipe (`PUT /recipes/{id}`) and the cart (`POST …/cart/save`, R6), so anyone else can open the new version for editing at once (owner, 2026-10-29).
- **Rationale**: Minimal change to spec 027's services; prevention first, version check second (spec FR-023).
- **Alternatives**: Lock implicitly on GET of the edit page (a reader who only looks would lock others out).

## R9. Scale factor representation

- **Decision**: `domain.cart.scale_factor(people, meals, base_servings) -> Fraction`; the api returns it as a string with at most 2 decimals and no trailing zeros (`"1.5"`, `"0.67"`, `"2"`) using half-up rounding, plus the raw parts so the ui can recompute in the draft. S-023 will use the exact `Fraction`.
- **Rationale**: Exact arithmetic avoids float drift in the shopping list; one formatting rule shared with spec 062's amounts.
- **Alternatives**: Float (drift: 3×1/9). Store the factor (spec says never stored).

## R10. Idle limit of 5 minutes (spec FR-020a, clarify 2026-10-29)

- **Decision**: Both lock tables get `last_active_at timestamptz not null`. A lock is live only if `now() - last_active_at < interval '5 minutes'` (constant `LOCK_IDLE = timedelta(minutes=5)` in `domain/cart.py`, used for both locks). `last_active_at` is set to now on acquire, on every draft write (`PUT …/cart/draft`, draft item add/remove), and on a keep-alive call: `POST …/cart/edit` and `POST /recipes/{id}/edit-lock` are idempotent for the holder and act as keep-alive. The api returns `idle_expires_at` (= `last_active_at + 5 min`) with every lock view. The ui sends a keep-alive at most every 30 s while the editor types or selects in the editing view, and shows the warning when `idle_expires_at - now <= 60 s`; "Keep editing" sends a keep-alive. Leaving the page open is **not** activity, so no timer-driven keep-alive is sent.
- **Rationale**: Expiry by time needs no job: liveness is checked on read, and a timed-out lock is overwritten by the next acquire (time only moves forward, so it cannot come back). Expired drafts are deleted at that moment, or by the holder's next call, which answers 409 `not_editing`.
- **Alternatives**: A periodic sweeper (needs a worker; the constitution allows none). A heartbeat while the page is visible (would keep a forgotten tab's lock alive, against the clarified spec).

## R11. Losing access deletes the lock for good (spec FR-020b)

- **Decision**: Make the lock rows depend on the access that allowed them, so the database deletes them when access goes:
  - `cart_edit_lock.membership_id → kitchen_memberships.id ON DELETE CASCADE` (the editor's kitchen membership).
  - `recipe_edit_lock.kitchen_membership_id → kitchen_memberships.id ON DELETE CASCADE` (kitchen notebook) **or** `(notebook_id, user_id) → notebook_membership(notebook_id, user_id) ON DELETE CASCADE` (personal notebook); a CHECK requires exactly one of the two.
  - Archive: `ArchiveKitchenService` (`api/application/kitchens.py`) deletes the kitchen's cart lock and the recipe locks of its notebooks' recipes in the same transaction, through a new `EditLockRepository.release_all_for_kitchen(kitchen_id)`.
  A re-added member gets a new membership row, so nothing points back to the deleted lock. Unarchiving finds no lock.
- **Rationale**: Leave/remove routes do not exist yet (S-057 and kitchen member removal come later); FK cascades cover them when they are built, with no hook to forget. Archive is the one existing access-loss path and gets one explicit call. **Constraint for later stories**: kitchen member removal and S-057 (notebook leave/remove) must delete the membership row, not soft-delete it; a soft delete would leave the lock row alive. Task T053 records it in the backlog notes of S-057.
- **Alternatives**: Lazy purge on next read (loses the race when access returns before anyone reads). An access "epoch" column compared on read (more state for the same result).

## R12. The editing bar (spec FR-017a)

- **Decision**: `GET /kitchens/{id}/cart` already says whether my session holds the lock (`editor.is_me`) and gives `idle_expires_at`. *(Amended 2026-10-29, UI clarification.)* `CartEditingBar` is shown **only on the Cart page** while `editor.is_me`, fixed above the tab bar at the bottom of the screen body (rendered into the toast host of R13, so it sits in the same place). It reads "You're editing the cart. Others can't change it until you save or discard." with **Save** and **Discard**, and hosts the idle warning. On the kitchen recipe list and recipe pages there is no bar: the idle warning and "changes were discarded" appear as toasts (spec FR-017d), driven by `useLockKeepAlive` from the `idle_expires_at` the pages already read.
- **Alternatives**: A toast after the first tick (easy to miss; does not persist across pages).

## R13. A toast host above the tab bar (spec FR-017b, FR-017d; 2026-10-29)

- **Decision**: One `ToastProvider` in `AppShell`, with its viewport absolutely positioned at the bottom of the shell's body container (the `relative flex-1` box that holds the header and the scrolling content, directly above `TabBar`). So a toast always sits above the tab bar, inside the screen body, at every width; with no tab bar it sits at the bottom of the screen, above the safe-area inset. Pages call `useToast().show({ text, action?, persistent?, id? })`. A toast with an `id` replaces the one with the same id (the idle warning becomes "discarded"). Non-persistent toasts close after 4 s or on tap; the idle warning is persistent until Keep editing or expiry (spec Assumptions). `role="status"`, `aria-live="polite"`. The Cart page's editing bar is a persistent element in the same viewport, so the two never overlap: toasts stack above the bar.
- **Rationale**: The ui has no toast yet; the shell is the only component that knows where the tab bar is. A portal-free context keeps it testable with `createRoot` like the other ui tests. No new library (constitution §2).
- **Alternatives**: A fixed `bottom: <tab bar height>` element per page (duplicates the tab bar height; breaks when the tab bar is hidden). A toast library (new dependency for one use).

## R14. The add-to-cart icon (spec FR-017c; 2026-10-29)

- **Decision**: `ui/app/icons/CartPlusIcon.tsx`, stroke-based, `viewBox 0 0 24 24`, `currentColor`, in the style of `PlusIcon` (stroke 2, round caps): handle, trapezoid basket, two wheels, and a "+" centred in the basket. Prop `inCart?: boolean` rotates only the "+" group 45° about the basket centre (`transform: rotate(45deg)`, `transform-box: fill-box`, `transform-origin: center`, 150 ms transition, none under `prefers-reduced-motion`), which turns it into an "×". Listed in `ui/app/icons/README.md` and `index.ts`. The button is the existing `IconButton` (ghost), label "Add to cart" / "Remove from cart", `aria-pressed={inCart}`.
- **Rationale**: One icon with a state matches the clarified look (the "+" turned 45°) and animates the change; one label per state keeps it accessible.
- **Alternatives**: Two separate icons (no animation, two files to keep in step).
