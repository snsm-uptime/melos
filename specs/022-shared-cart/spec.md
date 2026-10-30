# Feature Specification: Shared Kitchen Cart with People, Meals, Scale Factor and Single-Editor Locks

**Feature Branch**: not created by this command

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml @dev/docs/prd.md S-022" (Shared cart with people and per-recipe meals; scale factor)

**Related**: PRD J4 (Plan), 1.5 C, 1.6 (`cart`, `cart_item`, `recipe.cart_add_count`, decided "Cart frequency"), Appendix A (Cart, CartItem). Builds on spec 056 (notebooks and their access rules), spec 021 (kitchen recipe list), spec 027 (recipe detail and Edit; FR-016 requires a cart entry to go with its deleted recipe; this spec amends its Edit with a single-editor lock) and spec 062 (the detail page's view-only servings control, which is separate from the cart's scale). Out of this feature: the consolidated shopping list (S-023), its Markdown and PDF export (S-024), finalizing a list (S-025), the cart-frequency sort and richer kitchen cards (S-047), MCP cart tools (S-032) and the chat (S-030).

> **Superseded in part (2026-10-30):** spec 023's amendment replaces this spec's People and Meals rules with per-recipe Servings (factor = Servings ÷ base servings; no People number). See `specs/023-shopping-list/spec.md`, FR-015 to FR-019.

## Clarifications

### Session 2026-10-29

- Q: What is the cart's default people number? → A: The number of members of the kitchen (replaces the PRD's default of 2).
- Q: Can two members edit at the same time? → A: No. Once a member is editing, no other member can edit at the same time. If the editing member signs out or their session ends, their unsaved draft is discarded and the item is open for edits again.
- Q: Does that lock apply to the cart, to recipes, or both? → A: Both: the kitchen's cart and each recipe.
- Q: How does a member start editing the shared cart? → A: Two ways: the Edit button on the Cart page, or ticking "Add to cart" on a card or recipe page. Ticking adds the recipe to the member's draft and adds the recipe to the member's draft. Nothing reaches the shared cart until saved. (Where the editing bar shows: see the 2026-10-29 UI clarification below.)
- Q: Should a lock end on its own when the editor is idle, and after how long? → A: Yes, after 5 minutes with no activity from the editor; their unsaved draft is discarded.
- Q: If an editor loses access and later gets it back, do their lock and draft come back? → A: No. Losing access ends the lock for good and permanently deletes the draft; restored access starts with no lock.
- Q: How are the editing bar and toast shown? → A: The editing bar shows only on the Cart page while the member is editing, fixed above the tab bar at the bottom of the screen body. A successful add or remove shows no message. An add or remove refused because another member edits the cart shows a toast above the tab bar: "{alias} is editing the cart".
- Q: How does the add-to-cart control look and show that a recipe is in the cart? → A: An icon button (a cart with a "+" in the basket, an SVG in `ui/app/icons/`) on kitchen recipe cards and the recipe page, replacing the checkbox. When the recipe is in the cart (my draft while I edit, else the saved cart), the "+" turns 45° into an "×"; tapping toggles add/remove. Its accessible label reads "Add to cart" or "Remove from cart".
- Q: While another member edits the cart, is the cart-icon button disabled? → A: No. It stays enabled with no inline notice on cards or the recipe page; a tap is refused and shows the "{alias} is editing the cart" toast.
- Q: What does a member see about the idle limit on the kitchen list or a recipe page, where there is no editing bar? → A: The toast above the tab bar: "Your cart changes will be discarded in 1 minute" with Keep editing, then "Your cart changes were discarded" when the lock expires.
- Q: May the member who is editing a recipe delete it? → A: Yes. The lock holder may delete the recipe; the delete ends their edit and its lock. Only other people are blocked from Delete while the lock is held (documentation fix from analysis C1).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add kitchen recipes to the kitchen's cart and see them there (Priority: P1)

A member plans the week. From the kitchen's recipe list, or from a recipe's detail page, they add the recipes they want to cook to the kitchen's cart. They open the kitchen's Cart and see every recipe in it, with its title and the notebook it comes from. They remove a recipe they changed their mind about.

**Why this priority**: Without a cart there is nothing to scale and no shopping list (S-023). This is the smallest slice that gives value: a shared plan of what the kitchen will cook.

**Independent Test**: In a kitchen with two recipes in its notebooks, add both to the cart, open the Cart, see both; remove one, save, see only the other.

**Acceptance Scenarios**:

1. **Given** a kitchen recipe not in the cart and nobody else editing the cart, **When** a member adds it from the kitchen's list or from its detail page, **Then** it goes into that member's cart draft with meals 1 and the member becomes the cart's editor, with no message shown; on the Cart page the editing bar tells them they are editing the cart and others cannot change it until they save or discard.
2. **Given** that draft, **When** the member saves it, **Then** the recipe appears in the kitchen's saved cart for every member; until then other members do not see it.
3. **Given** a recipe already in the cart, **When** the list or the detail page is shown, **Then** it shows the recipe as already in the cart and offers to remove it instead of adding it again; the cart never holds the same recipe twice.
4. **Given** a cart with two recipes, **When** a member removes one and saves, **Then** the cart shows only the other and the removed recipe itself is unchanged.
5. **Given** a recipe in a personal notebook, **When** a person views it, **Then** no add-to-cart action is offered; only recipes of the kitchen's notebooks go to a kitchen's cart.
6. **Given** a kitchen with 3 members whose cart has never been changed, **When** a member opens the Cart, **Then** it is empty, shows people 3 and a hint to add recipes from the kitchen's notebooks.

---

### User Story 2 - Set people and meals and see each recipe's scale factor (Priority: P1)

The member sets how many people will eat (one number for the whole cart, by default the number of members of the kitchen) and, for each recipe, how many meals they will eat it (default 1). Next to each recipe the cart shows its scale factor, people × meals / base servings, so they can see how much of each recipe they will make.

**Why this priority**: The scale factor is the reason the cart exists in the PRD: the shopping list (S-023) multiplies every line by it.

**Independent Test**: A recipe with base servings 4 in the cart; set people 3 and meals 2; the cart shows a factor of 1.5. Change people to 4: the factor shows 2.

**Acceptance Scenarios**:

1. **Given** a kitchen with 2 members and a recipe with base servings 4 in the cart with meals 1, **When** the cart is shown and people was never changed, **Then** people reads 2 and the factor reads 0.5.
2. **Given** that recipe, **When** a member sets people to 3 and the recipe's meals to 2, **Then** its factor reads 1.5 and every other recipe's factor is recomputed from the new people number, in the draft before saving.
3. **Given** base servings 3, people 2 and meals 1, **When** the cart is shown, **Then** the factor reads 0.67 (at most 2 decimals, no trailing zeros).
4. **Given** a member enters 0, a blank value, a decimal or text for people or meals, **When** they leave the field, **Then** the value is not accepted, the last valid value stays and the field says what is accepted.
5. **Given** a recipe whose saved base servings later change through Edit, **When** the cart is shown again, **Then** its factor uses the new base servings.
6. **Given** the recipe detail page's servings control (spec 062) set to another number, **When** the cart is shown, **Then** the factor still uses the saved base servings; the view-only control never affects the cart.
7. **Given** people was never changed and a third member joins a 2-member kitchen, **When** the cart is shown, **Then** people reads 3; **given** a member had set people to 4, **then** it stays 4 when members join or leave.

---

### User Story 3 - The cart is shared, and one member edits it at a time (Priority: P1)

Members of a kitchen share one cart. A member who starts changing it (adding or removing recipes, changing people or meals) becomes its editor: their changes form a draft that only they see until they save it. While they edit, every other member sees the saved cart, read-only, with a note naming who is editing. When the editor saves or discards, or signs out, or their session ends, the cart is open again; signing out or a session ending discards the unsaved draft.

**Why this priority**: The PRD's user is a couple planning together; a shared cart without protection lets one person silently undo the other's plan.

**Independent Test**: Member A starts editing the cart and changes people to 4 without saving. Member B opens the Cart: it shows the saved people number, read-only, and says A is editing. A saves: B, after refreshing, sees 4 and can edit. A starts editing again and signs out: the draft is gone and B can edit.

**Acceptance Scenarios**:

1. **Given** nobody is editing the cart of kitchen K, **When** member A makes a change, **Then** A becomes the cart's editor and the change is held in A's draft, shown to A only.
2. **Given** A is editing K's cart, **When** member B opens the Cart, **Then** B sees the last saved cart, the Cart page's actions are unavailable, and a plain note says that A is editing the cart. **When** B taps the cart-icon button on a card or recipe page, **Then** the add or remove is refused, nothing changes, and a toast says "A is editing the cart".
3. **Given** A saves the draft, **When** B opens or refreshes the Cart, **Then** B sees A's changes and can start editing.
4. **Given** A discards the draft, **When** anyone opens the Cart, **Then** it shows the cart as last saved and is open for editing.
5. **Given** A has unsaved changes, **When** A signs out or A's session ends, **Then** the draft is discarded, the saved cart is unchanged and the cart is open for editing by any member.
6. **Given** a person who is not a member of K, **When** they ask for K's cart or try to change it, **Then** they get "not found", the same answer as for a kitchen that does not exist.
7. **Given** A is editing and leaves or is removed from K, **When** anyone opens the Cart, **Then** A's draft is discarded and the cart is open for editing; A gets "not found".
8. **Given** an archived kitchen, **When** a member opens its Cart, **Then** they can read it but cannot start editing.

---

### User Story 4 - One member edits a recipe at a time (Priority: P1)

The same rule applies to recipes (amends spec 027 Edit). When someone who can write to a recipe opens its Edit, they hold the recipe: anyone else who can write to it sees the saved recipe and a note naming who is editing, and cannot open Edit or Delete. Saving or cancelling the edit frees it. If the editor signs out or their session ends, their unsaved edit is discarded and the recipe is open for edits again.

**Why this priority**: Explicitly requested; it replaces spec 027's after-the-fact conflict check with prevention, for both kitchen and shared personal notebooks.

**Independent Test**: Member A opens Edit on recipe R. Member B opens R: Edit and Delete are unavailable and a note says A is editing. A signs out: B can now open Edit and sees the saved recipe without A's unsaved changes.

**Acceptance Scenarios**:

1. **Given** nobody is editing recipe R, **When** member A opens its Edit, **Then** A holds R until A saves, cancels, signs out or A's session ends.
2. **Given** A holds R, **When** B (who can also write to R) opens R, **Then** B sees the saved recipe, Edit and Delete are unavailable, and a plain note says A is editing it.
3. **Given** A holds R, **When** A saves or cancels, **Then** R is open for edits by anyone who can write to it.
4. **Given** A holds R with unsaved changes, **When** A signs out or A's session ends, **Then** the changes are discarded, R is unchanged and open for edits.
5. **Given** A holds R, **When** A loses write access to R (leaves the kitchen or notebook, or is removed), **Then** A's edit is discarded and R is open for edits.
6. **Given** A holds R, **When** someone tries to delete R's notebook or kitchen, **Then** those deletions still happen and A's edit is discarded (they are not blocked by the lock).
7. **Given** A holds R, **When** A opens R's Edit in a second tab of the same session, **Then** it is the same edit; the lock does not block A from their own work.

---

### User Story 5 - The cart stays consistent with the kitchen's recipes (Priority: P2)

When a recipe in the cart is deleted, it disappears from the cart and the rest stays. When the kitchen is deleted, its cart goes with it. Each time a recipe is added to the cart, the kitchen keeps count, for the frequency sort that comes later (S-047).

**Why this priority**: Required by PRD J4 edge cases and spec 027 FR-016, but it shows on screen only when something is deleted.

**Independent Test**: Put two recipes in the cart, delete one from its detail page, open the Cart: only the other remains with its meals unchanged.

**Acceptance Scenarios**:

1. **Given** a recipe in the saved cart, **When** a member deletes the recipe, **Then** it is gone from the cart and the other recipes, their meals and people are unchanged.
2. **Given** a recipe in A's unsaved cart draft, **When** the recipe is deleted, **Then** it is dropped from A's draft and A is told in plain words when they next view or save the draft.
3. **Given** a kitchen with a cart, **When** the kitchen is deleted, **Then** its cart, cart entries and any draft are deleted with it.
4. **Given** a kitchen notebook with recipes in the cart, **When** the notebook is deleted, **Then** those recipes leave the cart with it.
5. **Given** a recipe added to the cart and saved twice in total (added, removed, added again), **When** its add count is read, **Then** it is 2; removing it never lowers the count, and a discarded draft never raises it.
6. **Given** a member clears the cart in their draft and saves after confirming, **When** the Cart is shown, **Then** it has no recipes and people keeps its value.

---

### Edge Cases

- People and meals are whole numbers from 1 to 99. Anything else is refused with a plain message and the previous value is kept.
- A kitchen's member count above 99 gives a default people number of 99.
- A cart with no recipes shows a hint to add recipes; there is no shopping list or export in this feature (S-023 and S-024 disable export on an empty cart).
- A recipe added from a stale page after it was deleted: the add fails with "not found" and the cart is unchanged.
- A recipe from another kitchen's notebook, or from a personal notebook, cannot be added to this kitchen's cart, even by someone who can read it: the answer is "not found".
- Adding a recipe already in the cart changes nothing.
- A member who closes the browser tab without signing out keeps the lock for at most 5 more minutes (FR-020a); if they return within that time their draft is still there, after it the draft is gone and the item is open.
- A member's lock attempt that races another's: exactly one becomes the editor; the other sees who is editing.
- A recipe whose author's account is deleted stays in the cart; its author reads "unknown" where shown.
- A kitchen notebook that was a snapshot of a personal notebook behaves like any other kitchen notebook; the personal original is never in the cart.
- A very large cart (100 recipes) still opens and responds without noticeable delay.

## Requirements *(mandatory)*

### Functional Requirements

**Cart**

- **FR-001**: Each kitchen MUST have exactly one cart, shared by all its members, holding a people number (whole, 1 to 99) and zero or more cart entries.
- **FR-002**: Until a member saves a people number, the cart's people number MUST equal the kitchen's current number of members (capped at 99) and follow membership changes. Once a member saves a people number, that value MUST be kept regardless of later membership changes.
- **FR-003**: A cart entry MUST reference one recipe in one of the cart kitchen's notebooks, with a meals number (whole, 1 to 99, default 1). A cart MUST NOT hold the same recipe twice.
- **FR-004**: A kitchen member MUST be able to add a recipe to the kitchen's cart from the kitchen's recipe list and from the recipe's detail page, and to remove it from the same places and from the Cart.
- **FR-005**: Add-to-cart MUST be offered only for recipes in a kitchen notebook, and only for the cart of that recipe's kitchen. Any attempt to add another recipe MUST answer "not found".
- **FR-006**: A kitchen member MUST be able to open the kitchen's Cart and see, for each entry, the recipe title (linking to its detail), its notebook, its base servings, its meals and its scale factor, plus the cart's people number.
- **FR-007**: The scale factor of an entry MUST be people × meals / the recipe's saved base servings, recomputed on every read from current values (never stored), shown with at most 2 decimals and no trailing zeros.
- **FR-008**: The cart's editor MUST be able to change the people number and each entry's meals. Values outside FR-001 and FR-003 MUST be refused with a plain message and leave the previous value unchanged.
- **FR-009**: The cart's editor MUST be able to clear the cart in their draft after confirming; clearing removes every entry and keeps people.
- **FR-010**: A person who is not a member of the kitchen MUST get "not found" for its cart and every cart action, the same as for a kitchen that does not exist.
- **FR-011**: In an archived kitchen the Cart MUST be readable and MUST NOT be editable.
- **FR-012**: Deleting a recipe MUST remove its saved cart entry in the same action and leave the rest of the cart unchanged (spec 027 FR-016), and MUST drop it from any unsaved cart draft. Deleting a kitchen notebook MUST remove its recipes' cart entries. Deleting a kitchen MUST delete its cart and any draft.
- **FR-013**: Each recipe that a saved cart change adds (and that was not already in the saved cart) MUST raise the recipe's cart add count by one. Removing, clearing and discarding MUST NOT change it.
- **FR-014**: An empty Cart MUST show a hint to add recipes from the kitchen's notebooks.
- **FR-015**: The Cart MUST NOT show a consolidated ingredient list, export, or finalize action; those are S-023, S-024 and S-025.
- **FR-016**: The recipe detail page's view-only servings control (spec 062) MUST NOT change the cart, and the cart MUST NOT change the recipe's saved servings.

**Single-editor lock (cart and recipes)**

- **FR-017**: At most one person at a time MUST be the editor of a kitchen's cart, and at most one person at a time the editor of a recipe. A member MUST become the cart's editor in one of two ways only: the Edit button on the Cart page, or ticking "Add to cart" / "Remove from cart" on a kitchen recipe card or recipe page. A member becomes a recipe's editor by opening its Edit. Either MUST be refused if someone else is the editor.
- **FR-017a**: While a member is the cart's editor, the Cart page MUST show them an editing bar, fixed above the tab bar at the bottom of the screen body, saying they are editing the cart and that others cannot change it until they save or discard, with Save and Discard and the idle warning. The kitchen recipe list and recipe pages show no bar. A successful add or remove shows no message.
- **FR-017d**: While a member holds the cart lock and is on the kitchen recipe list or a kitchen recipe page, the app MUST show the idle warning as a toast above the tab bar one minute before the lock ends ("Your cart changes will be discarded in 1 minute", with Keep editing, which renews the lock), and "Your cart changes were discarded" as a toast once it has ended.
- **FR-017c**: The add/remove control on kitchen recipe cards and the recipe page MUST be an icon button showing a cart with a "+" in the basket when the recipe is not in the cart, and the same cart with the "+" turned 45° into an "×" when it is (my draft while I edit, else the saved cart). Tapping toggles add/remove; the button's accessible label MUST read "Add to cart" or "Remove from cart" to match.
- **FR-017b**: When an add or remove from a card or recipe page is refused because another member edits the cart, the app MUST show a toast above the tab bar at the bottom of the screen body saying "{alias} is editing the cart" ("unknown" when the alias is missing), and leave the recipe's cart state unchanged. The button stays enabled while someone else edits; cards and the recipe page show no inline editor notice.
- **FR-018**: The cart editor's changes MUST be held as a draft visible only to them until they save it; saving MUST apply the whole draft at once. Others MUST see only the last saved cart.
- **FR-019**: While someone else is the editor, every other person with access MUST see the saved cart or recipe read-only, with all editing actions (cart: add, remove, people, meals, clear; recipe: Edit, Delete) unavailable and a plain note naming the editor by alias. The lock holder may still delete the recipe they are editing; the delete ends the edit and its lock.
- **FR-020**: The editor role MUST end, and the item MUST be open for edits again, when the editor saves, discards or cancels; when they sign out; when their session ends; when they have been idle for 5 minutes; or when they lose access to the kitchen or notebook. In the last four cases any unsaved draft MUST be discarded and the saved item left unchanged.
- **FR-020a**: Activity that keeps a lock alive MUST be any change to the draft or edit, typing or selecting in the editing view, or choosing "Keep editing" in the warning; merely leaving the page open is not activity, so a forgotten open tab does not hold the lock. 5 minutes after the last activity the lock MUST end and the draft be discarded. Before that, the editor MUST be warned at least 1 minute ahead that their changes will be discarded, with a way to keep editing.
- **FR-020b**: Losing access (leaving or being removed from the kitchen or notebook, or the kitchen being archived) MUST end the lock permanently and delete the draft; if access is restored later (re-added, unarchived) the item MUST be unlocked and the old draft MUST NOT come back.
- **FR-021**: The lock MUST belong to the editor's session: the same session MUST be able to continue its own edit (another tab, or returning to the page), and a different session of the same person MUST be treated as another editor.
- **FR-022**: Deleting a kitchen or a notebook MUST NOT be blocked by a lock on its cart or recipes; it MUST discard any draft on them.
- **FR-023**: For recipes, this lock replaces spec 027 FR-011's check at save time as the primary protection; spec 027's other Edit and Delete rules are unchanged.

**Language**

- **FR-024**: All new screen text MUST be available in Spanish and English, following the account language (spec 063).

### Key Entities

- **Cart**: one per kitchen; the people number, and whether it was set by a member or still follows the member count. Belongs to the kitchen and is deleted with it.
- **Cart entry**: a recipe of one of the kitchen's notebooks plus how many meals it will be eaten. Removed when its recipe, notebook or kitchen is deleted.
- **Cart draft**: the editor's unsaved version of the cart (people, entries, meals); seen only by the editor; discarded on cancel, sign-out, session end or loss of access.
- **Edit lock**: who is editing a cart or a recipe, tied to that person's session; at most one per cart and per recipe.
- **Recipe cart add count**: a running count, on a kitchen notebook's recipe, of how many times it has been added to its kitchen's saved cart; never lowered.
- **Scale factor**: derived, never stored: people × meals / base servings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A member can add three recipes to the cart, set people and meals, and save in under 1 minute.
- **SC-002**: For every cart entry, the shown factor equals people × meals / base servings rounded to 2 decimals, in 100% of tested combinations (including base 4, 3 people, 1 meal → 0.75).
- **SC-003**: In 100% of tries, a second member cannot change a cart or recipe while another member is editing it, and sees who is editing.
- **SC-004**: In 100% of tries, after the editor signs out, their session ends, or 5 minutes pass with no activity, another member can start editing on their next open or refresh, and the saved item has none of the unsaved changes.
- **SC-005**: A saved change by one member is visible to another member of the same kitchen on their next open or refresh, in 100% of tries.
- **SC-006**: A non-member gets "not found" for 100% of cart reads and actions on a kitchen they do not belong to.
- **SC-007**: After a recipe in the cart is deleted, no cart shows it and the remaining entries are unchanged, in 100% of tries.
- **SC-008**: A cart with 100 recipes opens and shows every factor within 1 second on the running stack.

## Assumptions

- The Cart is a section reachable from the kitchen's pages, next to the kitchen's Notebook tab; its exact placement is a design choice for the plan.
- The "{alias} is editing the cart" and "changes were discarded" toasts close by themselves after about 4 seconds or when tapped; the idle-warning toast stays until Keep editing is tapped or the lock ends.
- Adding from the kitchen list uses an add-to-cart icon button on kitchen cards (FR-017c; replaces the PRD's J3 checkbox); the richer cards, filters and frequency sort remain S-047. How editing starts and how the member is told: FR-017 and FR-017a.
- The default people number (member count) replaces the PRD J4 default of 2; the PRD should be updated to match.
- People and meals upper bound of 99 is a sanity limit chosen here; the PRD sets only the lower bound (≥ 1).
- The cart exists from the kitchen's creation, or from first use for kitchens created before this feature; members never see a kitchen without a cart.
- No live push: other members see saved changes and lock changes when they open or refresh the page.
- A lock lasts while the editor is active, at most 5 minutes past their last activity (FR-020a), and never beyond their session. The session lifetime is the existing auth layer's, which this feature does not change.
- The add count lives on the recipe as the PRD decides (`cart_add_count`); recipes saved before this feature start at 0.
- MCP cart tools (S-032) will reuse these rules but are not built here.
- No route to leave a kitchen or remove a member exists yet. When those stories are built (kitchen member removal; S-057 for notebooks), they MUST delete the membership row rather than mark it inactive, because FR-020b relies on that deletion to end the person's locks (plan research R11).
