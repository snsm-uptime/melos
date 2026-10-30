# Research: Consolidated Shopping List (S-023)

No `NEEDS CLARIFICATION` remains from the spec. Each item below is a decision the plan relies on.

## R1 · Where the list is computed

- **Decision**: On the server, in `domain/cart.py` (a pure `build_shopping_list`), called by a new `GetShoppingListService`. The route returns structured data; the ui does the wording.
- **Rationale**: PRD §1.5 C and backlog S-023 put the consolidation in `domain/cart.py`. The rules are exact arithmetic with ordering and rounding; they should exist once. The same function can later feed export (S-024), finalize (S-025) and the MCP tool (S-032).
- **Alternatives**: Compute in the ui (duplicate rules, two answers). Store the list (forbidden by FR-002 / PRD §1.5 C).

## R2 · One endpoint, the caller's view

- **Decision**: `GET /kitchens/{kitchen_id}/shopping-list`. If the caller's session holds the live cart lock and has a draft, the list is built from the draft (its People, meals, recipes). Otherwise from the saved cart. The route never takes, renews or releases a lock.
- **Rationale**: FR-001 and clarification 2026-10-29: the editor's list follows the draft; nobody else sees a draft. The server already knows the session (`require_session_ref`) and the draft (`EditLockRepository.cart_draft`), the same way `recipe_cart_status` picks "my draft while I edit, else the saved cart". FR-014: a read must not count as lock activity.
- **Alternatives**: Put the list inside the cart response (every add/remove call pays for it; cart payload grows). A `?draft=true` flag (the server must still check the session; the flag adds nothing).

## R3 · How the ui follows the draft

- **Decision**: `ShoppingListSection` takes the cart state from `CartScreen` and fetches the list again whenever that state is replaced (load, focus refresh, draft PUT answer, save, discard, start edit). A request counter ignores an answer that arrives after a newer request. The previous list stays on screen while a new one loads.
- **Rationale**: `CartScreen` already sends the whole draft after a 300 ms pause and replaces its state with the answer, so "the draft the server holds" and "the cart state on screen" change together. SC-006 (no manual refresh) is met by the existing focus refresh. The list lags a draft change by the debounce plus one request; the spec's "at once" is read as "without leaving the page or saving".
- **Alternatives**: Fetch on every keystroke (many requests, same result after the PUT). Compute in the browser (R1).

## R4 · Reading ingredient lines

- **Decision**: A new port `IngredientLineReader.lines_for(recipe_ids) -> dict[UUID, tuple[CartIngredientLine, ...]]`, implemented in `adapters/persistence/carts.py` with one `SELECT … WHERE recipe_id IN (…) ORDER BY recipe_id, position`. Titles and base servings come from the existing `CartRepository.recipe_facts` (which also tells which recipes still exist and belong to this kitchen).
- **Rationale**: 2000 rows in one query meets SC-003. A separate port leaves the spec 022 fakes untouched. Recipes missing from `recipe_facts`, or whose notebook is not this kitchen's, are skipped, as the cart view does today (a draft may still hold a recipe deleted since).
- **Alternatives**: Add the method to `CartRepository` (every fake must change). One query per recipe (N+1, breaks SC-003).

## R5 · Exact numbers

- **Decision**: `quantity` is read as `Decimal` (the column is `Numeric`) and turned into `Fraction` exactly. The line amount is `quantity × factor` with `factor = scale_factor(people, meals, base_servings)`. Totals are `Fraction` sums. Counts: `ceil` of the sum. Mass and volume: `format_factor` of the per-unit sum (half up, at most 2 decimals, trailing zeros removed).
- **Rationale**: FR-003/FR-005: no rounding before the sums; "two lines of 0.5 egg give 1, not 2". `format_factor` already implements the spec's rounding and is covered by spec 022 tests. `Fraction(Decimal)` is exact; a `float` would not be.
- **Alternatives**: `Decimal` sums (1/3 factors lose precision before the sum). Rounding each line (violates FR-003).
- **Open edge, for the owner's review**: a total below 0.005 of a unit (for example 0.25 tsp at factor 1/99) formats as `0`. FR-006 says "at most 2 decimals", so the plan follows it literally. If `0 tsp` is unwanted, the fix is one rule in `format_amount` (show `0.01`), with a spec change first.

## R6 · Kind of measure and unit order

- **Decision**: Constants in `domain/cart.py`: `MASS_UNITS = ("kg", "lb", "oz", "g")`, `VOLUME_UNITS = ("l", "cup", "tbsp", "tsp", "ml")`, `COUNT_UNIT = "unit"`; the kind is derived from the unit. The tuple order is the display order, largest first (PRD §1.6).
- **Rationale**: FR-004/FR-006. The domain already allows exactly these ten units (`ALLOWED_UNITS`, table check `ck_recipe_ingredient_unit`), so every stored unit has a kind. An unknown unit cannot reach the domain; if one did, it is skipped with a logged count, not guessed.
- **Alternatives**: Read order from the ui (second copy of a domain rule).

## R7 · Grouping, sizes and vague lines

- **Decision**: Measured key = `(name, kind)`; count lines add `size` (None is its own key). Preparation is ignored. Vague key = `name` only; notes are kept in first-met order and compared after trimming and ignoring letter case; the first spelling is shown. The same name can be in both sections (FR-007).
- **Rationale**: FR-004, FR-005, FR-007; spec edge case "names merge exactly as stored". Comparing notes ignoring case is a small reading of "the same note appears once"; "a pinch" and "A pinch" would otherwise look like two notes to a person.
- **Alternatives**: Exact string match for notes (visible duplicates for trivial differences). Normalizing names further (the catalog already does that, S-018; spec says do not).

## R8 · Order of lines and chips

- **Decision**: Chips: each recipe once per line, in cart order (saved: `added_at`; draft: draft order), keyed by `recipe_id`, so two recipes with the same title give two chips. Lines: sort key `(name key, kind rank, size rank)`, where the name key is NFKD-decomposed, accent-stripped and case-folded, with the stored name as a final tie-break; kind rank mass < volume < count; size rank large < medium < small < none. "Your call": by name key.
- **Rationale**: FR-008, FR-010. Sorting in Python (not in SQL) makes the order independent of the database collation and testable in the domain.
- **Alternatives**: `ORDER BY` in SQL with a collation (depends on the server's locale, not testable without Postgres).

## R9 · What the route returns

- **Decision**: Structured, not preformatted. A measured line is `{name, kind, size, amounts: [{quantity, unit}], recipes: [{recipe_id, title}]}`; a count line has one amount whose `quantity` is a whole-number string and `unit` is `unit`. A "Your call" entry is `{name, notes, recipes}`. `is_empty` is true when the cart has no recipes. Quantities are strings (as `factor` is in spec 022) so no precision is lost in JSON.
- **Rationale**: FR-013: Spanish and English wording belongs to the ui. Export (S-024) and MCP (S-032) can reuse the structure.
- **Alternatives**: Preformatted `"flour — 1 cup + 3 tbsp"` strings (the api would need the language and the "—" wording; ui could not style the parts).

## R10 · Chip navigation and Back

- **Decision**: A chip is a link to `/recipes/{id}?from=/kitchens/{kitchenId}/cart`, the same as the cart rows. `safeReturnPath` already trusts `/kitchens/…` paths, so Back returns to the Cart page with no change to `recipeReturnPath.ts`.
- **Rationale**: FR-008, US2 scenario 2; reuses spec 027's rule.

## R11 · Access, archived kitchens, empty cart

- **Decision**: Access follows the cart reads: unknown kitchen or non-member → `KitchenNotFoundError` → 404 `kitchen_not_found`. An archived kitchen is read normally. An empty cart returns `is_empty: true` and the ui renders nothing for the list, leaving the cart's own empty hint (FR-011).
- **Rationale**: FR-012; reuses `_kitchen_is_archived`-style access (`get_kitchen` + `get_membership`).

## R12 · Test data for SC-004 and SC-003

- **Decision**: SC-004 is covered by a table of 20 invented carts in `test_shopping_list_domain.py`, each with a hand-calculated expected result written in the test (no code that recomputes the answer). SC-003 is covered by an integration test that builds 100 recipes × 20 lines, counts SQL statements (as spec 022's 100-entry test does) and asserts a fixed small bound.
- **Rationale**: Constitution §6; spec 022 already has the statement-count pattern. Invented names only (§4).
