# Research: Shopping by Store (S-070)

## R1. Where the bought state lives

- **Decision**: a boolean `bought` column on `shopping_list_item`, default false. Toggled only while the list is active.
- **Rationale**: bought belongs to the item, shared by the kitchen (spec assumption); closed lists keep it for free (FR-004).
- **Alternatives**: a separate `shopping_item_bought` table (extra join, no gain); per-person bought (contradicts FR-002).

## R2. Keeping bought across a cart refresh (FR-003)

- **Decision**: `replace_cart_lines` deletes and re-inserts cart lines, so the repository reads the old cart lines first and the pure function `domain.shopping_list.carry_bought(old, new)` sets `bought` on each new line. A new line is bought when an old bought line has the same `(section, name, kind, size)` and, for every unit in the new amounts, the old amount in that unit is present and not smaller. Quantities are compared as decimals; a unit missing before means "grew". A "Your call" line has no amounts: it keeps bought only when its notes are the same set as before.
- **Rationale**: keeps S-025's replace strategy; the rule is unit-testable without a database.
- **Alternatives**: updating rows in place by key (bigger change to S-025's repository).

## R3. Only the stored active list has items to mark

- **Decision**: GET `/kitchens/{id}/shopping-list` returns `status` `live`, `active` or `draft` (S-025). Bought toggles are offered only when `status` is `active`, which is when lines have stored ids. Cart lines gain `id` and `bought` in the response (nullable/false for `live` and `draft`).
- **Rationale**: a derived list has no stored rows to mark.

## R4. Default places

- **Decision**: seven keys in code, in this order: `supermarket`, `farmers_market`, `butcher`, `fish_market`, `bakery`, `pharmacy`, `other`. The api sends keys; the ui translates them (`ui/lib/i18n/places.ts`, en and es). `supermarket` is the fallback (clarification Q2).
- **Rationale**: defaults cannot be renamed or deleted (FR-009) and must be translated (US2 scenario 6); rows would add nothing.
- **Alternatives**: seed rows per user (migration and signup coupling; signup is in the auth layer).

## R5. Ingredient place storage

- **Decision**: `ingredient_place(user_id, name, default_key, place_id)` with primary key `(user_id, name)`; exactly one of `default_key` and `place_id` is set. No row means `supermarket`. Choosing Supermarket stores a row with `default_key = 'supermarket'` so the name stays on the catalog page (needed for hand-added names, FR-016a). `place_id` references `place` with `ON DELETE CASCADE`, so deleting a custom place sends its ingredients back to Supermarket (US2 scenario 4).
- **Names** are stored normalized with `domain.ingredient_catalog.normalize_name`; list items are resolved by the same function (FR-016).

## R6. Custom place names

- **Decision**: 1 to 40 characters after trimming and collapsing spaces; uniqueness compared on a folded form (lower case, accents removed) against the person's other custom places and against both the English and the Spanish names of the defaults. At most 30 per person. Rules in `domain/places.py`; the folded form is also stored (`name_key`) with a unique index `(user_id, name_key)` for races.

## R7. Catalog page contents (FR-010, FR-016a)

- **Decision**: names = union of (a) ingredient names in notebooks the person can read: personal notebooks they own or are a member of, and kitchen notebooks of kitchens they belong to (non-archived and archived alike), and (b) names in their `ingredient_place` rows. Sorted alphabetically, unique. Filtering by text is done in the ui (a few hundred names); the api returns the whole list in one call.
- **Rationale**: SC-003 needs the page fast to scan; a single query with UNION.

## R8. Copy from another member (FR-010a)

- **Decision**: `GET /me/place-sources` lists people who share at least one kitchen or one personal notebook with the caller (alias only, no email). `POST /me/places/copy {source_user_id}` in one transaction deletes the caller's `place` and `ingredient_place` rows and copies the source's, giving custom places new ids and remapping `place_id`. A source not in the caller's list answers 404.
- **Rationale**: snapshot semantics with no link back; the 404 keeps places private from strangers (constitution 4).

## R9. Tab order and counts

- **Decision**: computed in the ui from the items' resolved places: defaults in R4 order, then custom places alphabetically (locale compare); a tab shows only if it has at least one item; the count is items not bought. The api sends each item's `place` and the caller's custom place names. The "Your call" items take part like any other.

## R10. Concurrent toggles

- **Decision**: the PATCH sets the value sent (`{"bought": true}`), it does not flip, so two members tapping at once converge on the last write. No lock (S-022's cart lock is for cart editing, not the list).

## R11. Side panel entry

- **Decision**: an "Ingredients" `SidePanelEntry` linking to `/ingredients`, placed after the Notebook entry (`ui/components/SidePanel/SidePanel.tsx`, near `href="/notebooks"`), with `current` set on that page.
