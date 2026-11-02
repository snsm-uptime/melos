# Research: Custom Units and Admin Dashboard

Every decision below was checked against the code on 2026-11-01. No unknown is left open.

## R1. One `unit` table with a native list and a computed count

- **Decision**: One row per name, with `name` as the primary key, `user_references uuid[]`, `is_default`, and `reference_count` as `GENERATED ALWAYS AS (cardinality(user_references)) STORED`. No extra index: the unique name covers the writes, and a person's list is a scan of a table that holds tens of rows.
- **Rationale**: The clarified spec chose this shape. Nothing points at a unit by id, because recipe lines hold plain text, so `name` is enough as a key. A generated column meets FR-020a with no separate step and cannot be written by mistake.
- **Alternatives considered**: A `user_unit` join table gives real foreign keys and cascade, but the owner chose the list. A GIN index on `user_references` can be added later with no schema change, and at this size Postgres would ignore it.

## R2. Adding a person to a unit is one statement

- **Decision**:

  ```sql
  INSERT INTO unit (name, user_references) VALUES (:name, ARRAY[:user_id]::uuid[])
  ON CONFLICT (name) DO UPDATE
    SET user_references = array_append(unit.user_references, :user_id)
    WHERE NOT (:user_id = ANY (unit.user_references))
  ```

  Names go in sorted order, so two saves that add the same two words cannot deadlock.
- **Rationale**: `ON CONFLICT` takes the row lock and re-checks the `WHERE` on the newest row. Two people confirming the same word both land on one row, and one person in two tabs counts once, with no error (edge case "Race").
- **Alternatives considered**: Read then write needs a lock and a retry. A check constraint can't stop duplicates in an array, so this statement is the only code that adds to the list.

## R3. Removal is a rule that account deletion calls

- **Decision**: `RemoveUserFromUnitsService` in `application/units.py`, built the way S-058 was: it never commits, it runs in the caller's transaction, and it has no route. It locks the person's rows in name order, removes the id, then deletes non-default rows left empty.
- **Rationale**: Arrays can't have foreign keys, so nothing removes the id by itself, which is why FR-020b exists. A concurrent add either waits and sees the row still has references, or waits for the delete and inserts a new row. Both are correct.
- **Alternatives considered**: A trigger on `users` would make the step impossible to forget, but the repo has no triggers and the spec makes this S-054's duty. The backlog note on S-054 already says so.

## R4. The person's units are not sent to the AI

- **Decision**: The model keeps reporting the measure word as written. The app compares it to the person's units in code. The prompt gains only a rule against folding a container word into a plain count (FR-002). The `RecipeExtractor` port does not change.
- **Rationale**: The prompt already asks for the unit as written, and `lookup_unit` already maps spellings in code. Sending stored words adds cost and an injection path for no gain. FR-021 is met in the strongest way: no stored unit reaches the model. A test pins this. If a later story sends them, FR-021 still applies.
- **Alternatives considered**: A delimited units block in the user turn, like the catalog names. It would help the model spot a custom word only in ways the code already does.

## R5. The in-flight key must cover the caller's lists

- **Decision**: `RecipeExtraction` hashes the text, the catalog names and the available units together.
- **Rationale**: Today the key is the text alone, and the rules run inside the shared flight, using the first caller's lists. With per-person units, a second account pasting the same text at the same moment would receive a draft judged by the first account's units, which breaks SC-003 and leaks a unit (FR-018). The same line of code also fixes the existing leak of one notebook's catalog matches into another's draft.
- **Alternatives considered**: Running `check_draft` outside the flight keeps the single model call for different people but needs a larger change to a use case other stories depend on.

## R6. The table check on recipe lines goes

- **Decision**: Drop `ck_recipe_ingredient_unit` and `UNITS_SQL`, and add a not-blank check. The app enforces FR-007.
- **Rationale**: The check allows only the ten units, so `lata` can't be stored at all. Availability depends on the person, and a table check can't express that. `ck_recipe_ingredient_size` stays: a size still needs unit `unit`.

## R7. An unknown word no longer refuses the capture

- **Decision**: Today `UNIT_NOT_RECOGNIZED` makes the whole capture answer `ingredient_line_problem`, with no draft. From now on, `check_draft` keeps the line, writes the normalized word as its unit and returns `unknown_units`, each with the word and its line indexes. A word that can't be offered (R8) keeps today's refusal.
- **Rationale**: The question lives in the draft, so a draft must exist. Keeping the refusal for odd words is the smallest change that meets the "Long or odd input" edge case.
- **Alternatives considered**: Clearing the unit on odd words and opening the draft. It is kinder, but it is a behaviour change nobody asked for.

## R8. Normalizing a word

- **Decision**: New pure `custom_unit_name(raw)` in `domain/recipe_draft.py`. It applies NFC, trims, collapses spaces and lower-cases, then makes each word singular: `-es` is dropped after `ch`, `sh`, `x`, `z` or `ss`; otherwise a final `s` is dropped from words over 3 letters that don't end in `ss`, `us` or `is`. It returns `None` when the result is empty, over 32 characters, has no letter, or holds anything but letters, digits, spaces, hyphens and apostrophes. Accents are kept for display and ignored when comparing.
- **Rationale**: Ingredient names get their singular from the model, but a word typed by hand has no model, and one rule must serve both paths so the same word can't get two spellings. `singular_forms` returns candidates, not one answer, so it can't be reused here. The rule handles `latas`, `botes`, `paquetes`, `sobres`, `cans`, `jars`, `slices` and `bunches`.
- **Known limit**: Spanish `-ón`/`-ones` comes out wrong (`latones` → `latone`). The person sees the word in the question and can decline. `cucharon` and `cucharón` from two people are two rows, which a later promotion count should merge.

## R9. Lookup order

- **Decision**: `lookup_unit(raw, extra=())` checks, in order: the default spellings, an exact match in `extra` (accents ignored, after `custom_unit_name`), then the near-miss rule over both. Near-miss keeps its limits: one edit, 5 or more characters, and ambiguity is invalid output.
- **Rationale**: This is the edge cases "Word already covered" and "Near misses". The exact step comes first, so a stored word one letter from a default stays itself.

## R10. What Save receives

- **Decision**: Save and update take `keep_units: list[str]`. The server allows `available ∪ kept`, runs the line rules, and adds to the account only kept words that a saved line actually uses, after the write and in the same transaction, beside `add_names`. A word that a default or the person's list already covers is ignored.
- **Rationale**: This covers FR-005 and FR-007. A person who accepts a word and then picks another unit doesn't gain it. A replayed save returns before this point, and a refused save writes nothing, which matters because `get_db` commits after error responses.
- **Alternatives considered**: A `POST /units` at the moment of accepting. A discarded draft would then have added the word, against FR-005.

## R11. "Already on that stored line" means on that recipe

- **Decision**: On update, allowed units are the person's available units plus every unit on the stored recipe.
- **Rationale**: Lines have no ids: an update replaces all of them, and they can be moved or removed, so a line can't be followed from the old recipe to the new one. Comparing at recipe level lets a member reorder lines without a false refusal (US3 scenario 2). The looser rule only allows a word that's already in the recipe, and it changes nobody's list. The picker still follows the spec: own units plus the line's current one.

## R12. The check for a word typed by hand

- **Decision**: `POST /recipe-vocabulary/unit-check` answers `known`, `new` or `not_a_unit`.
- **Rationale**: Normalizing and matching are domain rules, and copying them to TypeScript would let the two drift. It follows the name-match route from spec 027. It reads the caller's list only (FR-011, FR-018).

## R13. A new `custom` kind on the shopping list

- **Decision**: `unit_kind` answers `custom` for any unit outside the ten. A custom line groups by name, sums per unit, and rounds each sum up. `ck_shopping_list_item_kind` gains `custom`. The sort rank puts it after `count`.
- **Rationale**: Using `count` would be wrong in three places. `_measured_lines` reads `per_unit["unit"]` and would raise `KeyError`. `formatLine` in the ui hides the unit on a count, so the list would read "frijoles — 3" with no "lata". And a size belongs to the group key of counts only. With its own kind, `formatLine` already prints `3 lata`, and 1 lata + 200 g shows as two lines, like mass and volume today (FR-014).
- **Alternatives considered**: Teaching `count` about many units touches more code and every place that reads `kind`.

## R14. Hand items need no change

- **Decision**: `hand_item` keeps `_UNITS`, and it checks that set before calling `unit_kind`, so FR-016 holds. `HandItems.tsx` keeps its fixed list.

## R15. Unit picker in the ui

- **Decision**: The shared row's `<select>` lists the available units, plus the line's current unit if missing, plus "Other…", which swaps in a text field. Leaving the field calls `unit-check`. A new `UnknownUnitQuestion` shows above the lines in both the draft and the edit form. Questions are derived from the lines and the answers, so a question goes away once no line uses its word. `RecipeEditForm` stops using the fixed `ALLOWED_UNITS` and loads the vocabulary.
- **Rationale**: Both screens share `IngredientLineRow`, so one change serves both. `checkDraft` must take the allowed list as an argument, or every shared recipe with `lata` would be unsaveable for other members (US3).

## R16. The admin flag stays out of the auth routes

- **Decision**: `is_admin` is exposed through `GET /side-panel`, not `/auth/me`. `/admin/*` answers an identical 404 for anyone signed out or not an admin. The check is in `application/admin.py`. The flag is set with one SQL line on the server, documented in the README.
- **Rationale**: The owner approved a column, not a change to the auth routes (constitution §1). No body or route writes the flag, so FR-017a holds without a new guard. The side panel is already per-person and is where the entry appears.

## R17. Dashboard reads

- **Decision**: Four GET routes, one per section, loaded when the section opens. Plain SQL aggregates, no stored totals. No paging.
  - **ingredients**: all names from `recipe_ingredient` and `ingredient`, so a catalog name no recipe uses shows with 0. `COUNT(DISTINCT recipe_id)` and `COUNT(DISTINCT author_id)`, so a deleted author doesn't count.
  - **recipes**: the people figure is notebook members for a personal notebook and kitchen members for a kitchen notebook.
  - **users**: id and alias, no email. Open sessions have `expires_at > now()`. The newest start date reads all session rows.
- **Rationale**: These are rare reads over household-sized data, and a full answer is what makes SC-006 testable. Paging can be added per section later. The id lets the admin read `user_references` against the users section.

## R18. Cart activity

- **Decision**: New `cart_activity` table and `CartActivityLog` port. `domain.cart.cart_save_action(before, after)` is pure: empty to filled is `created`; any other difference, including emptying the cart, is `edited`; no difference is nothing. `SaveCartService` passes the items it read under the cart lock. `CloseShoppingListService` records `closed`.
- **Rationale**: This follows FR-017f. Close empties the cart through `carts.save` directly, not through `SaveCartService`, so it records one `closed` and no `edited` (US4 scenario 7). "First recipe" counts at Save: a draft is private and may be discarded, and discarding records nothing.
- **Details**: The rows hold only person, action and time. There is no kitchen id, so a deleted kitchen leaves a person's counts intact, and `ON DELETE CASCADE` on the user gives "go with the account".

## R19. Migration and downgrade

- **Decision**: One migration, `0013_custom_units`. Its downgrade refuses, with a clear message, if any recipe line or list item uses a custom unit.
- **Rationale**: Old code silently skips those lines on the shopping list, so a quiet downgrade would lose items. Changing the rows would destroy what people wrote. Dev databases are shared across worktrees (see 057's note on 0012), so this will come up: clear the test rows first.

## R20. Order of the list

- **Decision**: `available_units` returns the ten in today's order, then the rest sorted. The repository returns only the extras; the ten come from `ALLOWED_UNITS`, which stays as the base of the spelling table.
- **Rationale**: The picker stays familiar. A later promotion needs no code change, because a promoted row comes back from the same query (`is_default OR referenced`). The ten rows are seeded for the dashboard and for that later rule.
