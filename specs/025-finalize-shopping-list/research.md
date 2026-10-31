# Research: Saved Shopping List

## R1. Reuse the S-023 list builder
- **Decision**: Move the cart-to-`ShoppingList` steps out of `GetShoppingListService` into one shared function used by the read and by the cart save.
- **Rationale**: FR-001 and SC-001 need one calculation.
- **Alternatives considered**: A copy in the save path, which could drift.

## R2. Line shape
- **Decision**: A stored line mirrors `MeasuredLine` / `YourCallEntry`: `kind`, `size`, and `amounts`, `notes` and `recipes` as JSON. It has no single quantity, unit or preparation.
- **Rationale**: A consolidated line can hold several amounts (`1 cup + 3 tbsp`), and S-023 drops preparation by design. This corrects PRD §1.6 and spec FR-005.
- **Alternatives considered**: One row per amount, which adds joins and gains nothing.

## R3. One active list
- **Decision**: A partial unique index on `kitchen_id` where `closing_date IS NULL`, plus get-or-create that re-reads on conflict.
- **Rationale**: The database enforces FR-006 under concurrency.
- **Alternatives considered**: An application check alone, which races.

## R4. Refresh inside the cart save
- **Decision**: `SaveCartService` replaces the active list's cart lines in the same transaction as the cart write, row-locking the list. Hand items are untouched.
- **Rationale**: A saved cart and its list must not disagree.
- **Alternatives considered**: Refresh on read, which would change the list without a save.

## R5. The editor's view
- **Decision**: While a member holds the cart lock, the read returns their draft's lines plus stored hand items, unsaved. Nothing is written.
- **Rationale**: Keeps the S-023 clarification (the editor's list follows their draft) with FR-002.

## R6. Recipe references
- **Decision**: `recipes` stores id and title as JSON with no foreign key.
- **Rationale**: A saved line must survive recipe deletion. The UI links only when the recipe still exists: `exists` comes from one lookup per read, so saved data never changes.

## R7. Closing date
- **Decision**: The browser sends the member's local day with Done. The server takes it if it is within one day of the UTC day, else 422 `invalid_date`, and uses the UTC day when none is sent. The write is a conditional update on `closing_date IS NULL`.
- **Rationale**: The member sees the date they pressed Done, also in the evening in the Americas, where the UTC day is already tomorrow. Every time zone is within a day of UTC, so a wrong clock cannot backdate a list. A second Done changes nothing and answers 409.
