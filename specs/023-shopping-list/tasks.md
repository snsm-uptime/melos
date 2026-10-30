# Tasks: Consolidated Shopping List from the Kitchen Cart

**Input**: Design documents from `specs/023-shopping-list/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R12), data-model.md, contracts/shopping-list-api.md, contracts/shopping-list-ui.md, quickstart.md

**Organization**: Grouped by user story (spec.md: US1 P1 combined scaled list, US2 P1 chips, US3 P1 "Your call", US4 P2 list matches the current cart and the editor's draft). The shared domain types, the new port with its SQL reader and the message set are Foundational (Phase 2). US1 delivers a working list for the saved cart end to end (measured lines only). The domain tracks each line's recipes from US1 on, because a line is not complete without its sources; US2 adds the chips in the ui and the tests that pin their rules. US3 adds the vague section. US4 adds the editor's draft and the live refetch.

**Tests**: The spec does not request TDD, but constitution §6 requires domain tests, application tests with fakes and integration tests in Compose, and the spec's SC-001/SC-004 require automated acceptance tests, so test tasks are included. Write each story's tests first and see them fail.

**No migration**: this story adds no table or column (plan.md). Nothing is written to the database by any task.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 (story phases only)
- Paths are repository-relative. api code runs from `api/`, so `domain/…` in imports means `api/domain/…` on disk.

## Path Conventions

- api: `api/domain/`, `api/application/`, `api/adapters/persistence/`, `api/api/routes/`, `api/api/schemas/`, `api/api/app.py`, `api/api/deps.py`, `api/tests/`
- ui: `ui/app/api/`, `ui/components/`, `ui/lib/`, `ui/lib/i18n/`
- Invented data only in tests (constitution §4): names such as `flour`, `onion`, `salt`; users `ana`, `ben`.

---

## Phase 1: Setup

- [X] T001 Record the baseline: run `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`, `cd api && uv run ruff check .`, and `cd ui && npm test && npm run lint && npm run typecheck`. Write the pass/fail counts under "Baseline" in `specs/023-shopping-list/notes.md` (create it). List the failures that already exist (the 5 api failures named in the S-022 verification in `dev/docs/backlog.yaml`, the 4 ruff errors already on HEAD); do not fix them.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the pure types and constants, the port and its SQL reader, and the ui message set that every story uses.

- [X] T002 [P] Extend `api/domain/cart.py` (pure; keep the existing functions untouched; no I/O, no FastAPI, no SQLAlchemy) with the types and constants of `data-model.md`, and no consolidation logic yet. Constants: `MASS_UNITS = ("kg", "lb", "oz", "g")`, `VOLUME_UNITS = ("l", "cup", "tbsp", "tsp", "ml")`, `COUNT_UNIT = "unit"` (tuple order is the display order, largest first, PRD §1.6); `SIZE_ORDER = ("large", "medium", "small")`; `Kind = Literal["mass", "volume", "count"]`; `unit_kind(unit: str) -> Kind` (raises `ValueError` for any unit outside these ten: `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`); `name_sort_key(name: str) -> tuple[str, str]` returning (the name NFKD-decomposed, combining marks removed, case-folded; the stored name as final tie-break) so accents and case are ignored (FR-010, research R8). Frozen slots dataclasses: `ShoppingLine(name: str, quantity: Fraction | None, unit: str | None, size: str | None, vague_note: str | None)`; `ScaledRecipe(recipe_id: UUID, title: str, factor: Fraction, lines: tuple[ShoppingLine, ...])`; `RecipeRef(recipe_id: UUID, title: str)`; `Amount(quantity: str, unit: str)`; `MeasuredLine(name: str, kind: Kind, size: str | None, amounts: tuple[Amount, ...], recipes: tuple[RecipeRef, ...])` ("`size` only for counts: `size` is only allowed when `unit = unit`"); `YourCallEntry(name: str, notes: tuple[str, ...], recipes: tuple[RecipeRef, ...])`; `ShoppingList(lines: tuple[MeasuredLine, ...], your_call: tuple[YourCallEntry, ...])`. Quantities arrive as exact `Fraction`, never `float`.
- [X] T003 [P] Append to `api/application/ports.py` (add only; do not rewrite existing content): frozen slots dataclass `CartIngredientLine(name: str, quantity: Decimal | None, unit: str | None, size: str | None, vague_note: str | None)` (a line is either vague — `vague_note` set with `quantity` and `unit` null — or measured — `quantity > 0` and `unit` set; `preparation` is not part of it, FR-004) and Protocol `IngredientLineReader` with `lines_for(recipe_ids: Sequence[UUID]) -> dict[UUID, tuple[CartIngredientLine, ...]]` documented as "each recipe's lines in `position` order; a recipe with no lines is absent or empty; read only".
- [X] T004 [P] Add `SqlAlchemyIngredientLineReader` to `api/adapters/persistence/carts.py` implementing T003: one `select(RecipeIngredientModel.recipe_id, name, quantity, unit, size, vague_note).where(recipe_id.in_(ids)).order_by(recipe_id, position)` for all ids at once (no per-recipe query, SC-003); return `{}` for no ids; keep `quantity` as the `Decimal` the `Numeric` column returns (do not convert to `float`); do not select `preparation`. Read only: no `flush`, no write.
- [X] T005 [P] Create `ui/lib/i18n/shoppingList.ts` exporting `shoppingListMessages = { en: {...}, es: {...} }` (same style as `ui/lib/i18n/cart.ts`) with these keys, every one different in the two languages: `title` ("Shopping list" / "Lista de compras"), `yourCall` ("Your call" / "A tu criterio", Spanish wording is for the owner's review), `loading` ("Loading the shopping list" / "Cargando la lista de compras"), `loadError` ("Could not load the shopping list. Try again." / "No se pudo cargar la lista de compras. Inténtalo de nuevo."), `retry` ("Try again" / "Reintentar"), `noIngredients` ("These recipes have no ingredients" / "Estas recetas no tienen ingredientes"), `recipesLabel` ("Recipes" / "Recetas", the accessible name of a line's chip group). Register it in `ui/lib/i18n/parity.test.ts` (`shoppingList: shoppingListMessages`, import it) so spec 063's both-languages test covers it.

**Checkpoint**: types, port, reader and messages exist. No story logic yet.

---

## Phase 3: User Story 1 - See one combined shopping list for the week (Priority: P1) 🎯 MVP

**Goal**: A member opens the Cart page and sees one scaled, combined list of measured lines for the saved cart (AC5.1–AC5.4).

**Independent Test**: Put two recipes that share an ingredient in the cart, open the Cart page, and check the combined, scaled line `flour — 1 cup + 3 tbsp`.

### Tests for User Story 1 ⚠️ (write first, see them fail)

- [X] T006 [P] [US1] Create `api/tests/test_shopping_list_domain.py` for `build_shopping_list` (import from `domain.cart`), pure pytest, invented data: AC5.1 (3 tbsp + 1 cup flour, factor 1 → one volume line, amounts `1 cup`, `3 tbsp` in that order); AC5.2 (base servings 4, People 3, Meals 1, 2 eggs → factor `Fraction(3, 4)`, count total `1.5` → `"2"`); AC5.3 (rice 200 g and 1 cup → two lines, `mass` and `volume`, never converted); AC5.4 (1 large onion in two recipes and 1 small in a third → `onion` large `"2"`, `onion` small `"1"`); preparation ignored (chopped and sliced onion → one line); count with no size is its own line beside its sized lines; rounding happens once after the sum (two lines of 0.5 egg → `"1"`, and 2 + 1 eggs → `"3"`, not rounded twice); 1/3 factor kept exact across three recipes before formatting; mass and volume amounts at most 2 decimals, half up, trailing zeros removed (`"0.33"`, `"1.5"`, `"2"`); units summed per unit and never carried over (`1 cup + 20 tbsp` stays); unit order largest first for every mass unit (`kg, lb, oz, g`) and every volume unit (`l, cup, tbsp, tsp, ml`); FR-010 order (accents and case ignored: `Ñame` vs `nata`; same name: mass before volume before count; counts large, medium, small, no size); the same name string from recipes of two notebooks merges (the domain sees only strings). A vague line in the input is ignored by these tests (US3 covers it).
- [X] T007 [P] [US1] Create `api/tests/test_shopping_list_carts.py` (SC-004): a table of 20 invented carts, each parametrized with its recipes (People × Meals ÷ base servings given as the `Fraction` factor), lines and the **expected result written out by hand in the test** (no helper that recomputes the answer). Cover mixed units of one kind, counts that need rounding up, counts that are already whole, sizes, 1/3 and 2/3 factors, large factors (Meals 99), and a recipe contributing two lines of the same ingredient.
- [X] T008 [P] [US1] Create `api/tests/test_shopping_list_application.py` for `GetShoppingListService` against fake ports (reuse the `World` and kitchen/notebook helpers and the fake `CartRepository`/`EditLockRepository` from `api/tests/test_carts_application.py` by import; add a `FakeIngredientLineReader`): the saved cart's recipes are scaled with `effective_people(saved.people, member_count)` and each entry's meals and base servings; recipes missing from `recipe_facts` or whose `kitchen_id` is not this kitchen's are skipped; chips order is cart order; a non-member and an unknown kitchen raise `KitchenNotFoundError`; an archived kitchen is readable; `is_empty` is true for a cart with no recipes; the service never calls any lock write method (the fake records calls and the test asserts none).
- [X] T009 [P] [US1] Create `api/tests/test_shopping_list_integration.py` (Postgres, skip when `DATABASE_URL` is unset, same header and `pytestmark` as `api/tests/test_carts_integration.py`; reuse its `People`, `_home`, `_save`, `_join` helpers by import). Section "US1": over HTTP, `ana` saves Bread (flour 3 tbsp) and Pancakes (flour 1 cup, egg 2) into the cart, People 4 → `GET /kitchens/{id}/shopping-list` answers 200 with the shape in `contracts/shopping-list-api.md` (`is_empty`, `lines[]` with `name`, `kind`, `size`, `amounts[]`, `recipes[]`, `your_call[]`); a non-member and an unknown kitchen both answer 404 `kitchen_not_found`; an archived kitchen answers 200; the read leaves `cart_item`, `recipe.cart_add_count` and the ingredient catalog unchanged (FR-014); a cart of 100 recipes × 20 lines (insert `RecipeModel` and `RecipeIngredientModel` rows directly) is read with the number of SQL statements touching `cart`, `recipe` or `recipe_ingredient` bounded by a small fixed number (assert `<= 10`, listing the statements in the failure message, as the 100-entry test of spec 022 does) and the response arrives under 1 second (SC-003).
- [X] T010 [P] [US1] Create `ui/lib/shoppingListText.test.ts` and `ui/lib/shoppingListClient.test.ts`. Text: `formatLine` returns `flour — 1 cup + 3 tbsp` for amounts `[1 cup, 3 tbsp]`; `onion, large — 2` for a sized count (number only, no unit word); `onion — 1` for a count with no size; names are returned as stored. Client: `fetchShoppingList` returns `{ok: true, value}` for a valid body, keeps `status` and `code` on 404, returns status 0 on a network failure, and rejects a body without `lines` as `{ok: false}` (same shape as `cartClient.test.ts`).
- [X] T011 [P] [US1] Create `ui/components/ShoppingList/ShoppingListSection.test.tsx` (use `mount` from `ui/components/Cart/testRoot.tsx`, jsdom): shows the loading status, then the lines; an empty cart (`is_empty: true`) renders nothing at all (no heading); a failed fetch shows the error with a Retry button that fetches again; an ingredient name such as `<b>x</b>` renders as text, not markup. Add `ui/app/api/kitchens/[kitchenId]/shopping-list/route.test.ts` modelled on `ui/app/api/kitchens/[kitchenId]/cart/route.test.ts` (forwards `GET` to `/kitchens/{id}/shopping-list` with cookies, passes status and body back).

### Implementation for User Story 1

- [X] T012 [US1] In `api/domain/cart.py` add `build_shopping_list(recipes: Sequence[ScaledRecipe]) -> ShoppingList` for measured lines (vague lines are skipped here; US3 adds them): scale each measured line as `quantity × recipe.factor` in `Fraction`, no rounding before the sums (FR-003); group by `(name, kind)` and, for `count`, by `(name, size)` with `None` its own key; ignore `preparation` (not in the input); sum per unit as `Fraction`; a `count` total is `math.ceil` of its sum, shown as one `Amount(str(n), "unit")` (FR-005); mass and volume amounts are listed in `MASS_UNITS`/`VOLUME_UNITS` order, each `Amount(format_factor(total), unit)` with at most 2 decimals, half up, trailing zeros removed, never converted or carried over (FR-006); each line records its recipes as `RecipeRef`, each recipe once, in input (cart) order, keyed by `recipe_id` (FR-008); sort lines by `(name_sort_key(name), kind rank mass<volume<count, size rank large<medium<small<None)` (FR-010). A unit outside the ten allowed is skipped, not guessed (research R6). Make T006 and T007 pass.
- [X] T013 [US1] Create `api/application/shopping_list.py` with `GetShoppingListService(kitchens: KitchenRepository, carts: CartRepository, locks: EditLockRepository, lines: IngredientLineReader)` and `execute(ref: SessionRef, kitchen_id: UUID) -> ShoppingListView` where `ShoppingListView` is a frozen slots dataclass `(is_empty: bool, shopping_list: ShoppingList)`. Access as in `application/carts.py`: `kitchens.get_kitchen` and `kitchens.get_membership(kitchen_id, ref.user_id)`; unknown kitchen or non-member → `KitchenNotFoundError` (404); an archived kitchen is read normally. For now read the **saved** cart (`carts.read`); US4 adds the draft. People = `effective_people(saved.people, carts.member_count(kitchen_id))`. Load `carts.recipe_facts(ids)` and `lines.lines_for(ids)` once for all recipes; skip a recipe absent from the facts or whose `kitchen_id` differs; build `ScaledRecipe` per entry in cart order with `factor = scale_factor(people, meals, base_servings)` and each line's `quantity` as `Fraction(Decimal)` (exact; never via `float`); call `build_shopping_list`. `is_empty` is true when the cart has no recipes. Never call a lock or cart write method (FR-014). Log outcome and counts only (`"shopping list outcome=built recipes=%d lines=%d"`), never names or titles (constitution §4). Make T008 pass.
- [X] T014 [P] [US1] Create `api/api/schemas/shopping_list.py`: pydantic models `AmountResponse(quantity: str, unit: str)`, `RecipeRefResponse(recipe_id: UUID, title: str)`, `ShoppingLineResponse(name, kind: Literal["mass", "volume", "count"], size: Literal["small", "medium", "large"] | None, amounts: list[AmountResponse], recipes: list[RecipeRefResponse])`, `YourCallResponse(name, notes: list[str], recipes: list[RecipeRefResponse])`, `ShoppingListResponse(is_empty: bool, lines: list[ShoppingLineResponse], your_call: list[YourCallResponse])`, and a `shopping_list_response(view: ShoppingListView) -> ShoppingListResponse` mapper, exactly as in `contracts/shopping-list-api.md`.
- [X] T015 [US1] Add `get_get_shopping_list(db: Session = Depends(get_db)) -> GetShoppingListService` to `api/api/deps.py` next to `_cart` (build it from `SqlAlchemyKitchenRepository(db)`, `SqlAlchemyCartRepository(db)`, `SqlAlchemyEditLockRepository(db)`, `SqlAlchemyIngredientLineReader(db)`; import the new reader).
- [X] T016 [US1] Create `api/api/routes/shopping_list.py` with `router = APIRouter(tags=["shopping-list"])` and `GET /kitchens/{kitchen_id}/shopping-list` using `require_session_ref` and `get_get_shopping_list`, answering `JSONResponse(shopping_list_response(view).model_dump(mode="json"))`; map `KitchenNotFoundError` to 404 `{"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"}` with the same helper shape as `api/api/routes/carts.py`. Include the router in `api/api/app.py` next to the cart router. Make T009 (US1 section) pass.
- [X] T017 [P] [US1] Create the BFF route `ui/app/api/kitchens/[kitchenId]/shopping-list/route.ts` (`GET`, `forwardRecipeRequest` to `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list`, same as `ui/app/api/kitchens/[kitchenId]/cart/route.ts`). Make the route test of T011 pass.
- [X] T018 [P] [US1] Create `ui/lib/shoppingListClient.ts`: types `ShoppingAmount`, `ShoppingRecipeRef`, `ShoppingLine`, `YourCallEntry`, `ShoppingList` matching `contracts/shopping-list-api.md`, and `fetchShoppingList(kitchenId): Promise<ShoppingListResult>` (`GET /api/kitchens/{id}/shopping-list`, `credentials: "same-origin"`, failure shape `{ok: false, status, code}` as in `ui/lib/cartClient.ts`; a body without `lines` array or `is_empty` boolean is a failure). Make the client test of T010 pass.
- [X] T019 [P] [US1] Create `ui/lib/shoppingListText.ts` with `formatLine(line: ShoppingLine): string` = `{name}[, {size}] — {amounts}`: each amount `{quantity} {unit}` joined with " + "; for `kind: "count"` the quantity only (FR-009); name and size as stored (untranslated, FR-013). Make the text test of T010 pass.
- [X] T020 [US1] Create `ui/components/ShoppingList/ShoppingLine.tsx` (a list item showing `formatLine(line)`; chips come in US2), `ShoppingListSection.tsx` (`"use client"`; props `kitchenId`, `locale`; fetches on mount; states: loading line with `role="status"`, ready, error line with `role="alert"` and a Retry button; renders `null` when `is_empty`; a heading `shoppingListMessages[locale].title`; a `<ul>` of lines; layout styled like the Cart page: Tailwind classes, same text tokens as `CartView`; no sideways scroll at 360 px) and `index.ts` exporting `ShoppingListSection`. Make T011 pass.
- [X] T021 [US1] In `ui/components/Cart/CartScreen.tsx` render `<ShoppingListSection kitchenId={kitchenId} locale={locale} />` after `<CartView … />` inside the ready state's container. In `ui/components/Cart/CartScreen.test.tsx` add `vi.mock("@/lib/shoppingListClient", …)` so existing tests do not hit the network, and one test that the section is rendered below the cart for a ready cart.
- [X] T022 [US1] Checkpoint: run `cd api && uv run pytest tests/test_shopping_list_domain.py tests/test_shopping_list_carts.py tests/test_shopping_list_application.py`, the integration file in the Compose test overlay, and `cd ui && npm test -- ShoppingList shoppingList CartScreen && npm run lint && npm run typecheck`. All pass, and the 5 api failures of the baseline are the only api failures.

**Checkpoint**: US1 works alone: a combined, scaled list of measured lines for the saved cart, on the Cart page.

---

## Phase 4: User Story 2 - See which recipes each line is for (Priority: P1)

**Goal**: Every line shows chips with its recipes' titles; tapping one opens the recipe, and Back returns to the Cart page.

**Independent Test**: A line made from two recipes shows both titles in cart order; a line from one recipe shows one; tapping a chip opens that recipe and Back returns to the Cart page.

### Tests for User Story 2 ⚠️

- [X] T023 [P] [US2] Add to `api/tests/test_shopping_list_domain.py` chips tests: flour from recipes A and B lists `[A, B]` in input (cart) order, not alphabetical; a recipe that contributes two lines of one ingredient appears once on that line; two recipes with the same title give two `RecipeRef`s with different `recipe_id`s; a line from one recipe has exactly one chip; every line of a built list has at least one recipe (SC-005, assert over the 20 carts of `test_shopping_list_carts.py` via a parametrized check).
- [X] T024 [P] [US2] Add to the US1 section of `api/tests/test_shopping_list_integration.py` (new "US2" section): over HTTP the flour line lists the Bread and Pancakes `recipe_id`s and titles in cart (added) order; two recipes with the same title in the cart give two entries.
- [X] T025 [P] [US2] Create `ui/components/ShoppingList/RecipeChips.test.tsx` and extend `ShoppingListSection.test.tsx`: each recipe renders as an anchor whose `href` is `/recipes/{recipe_id}?from=/kitchens/{kitchenId}/cart` with the `from` value `encodeURIComponent`-encoded exactly as `ui/components/Cart/CartEntryRow.tsx` does; the chip group has the accessible name `shoppingListMessages[locale].recipesLabel`; each chip's `title` attribute holds the full recipe title; two chips with the same title both render; a line shows one chip per recipe.

### Implementation for User Story 2

- [X] T026 [US2] Confirm `build_shopping_list` (T012) records recipes as T023 requires; fix `api/domain/cart.py` only if a T023 test fails (the logic is expected to exist already).
- [X] T027 [P] [US2] Create `ui/components/ShoppingList/RecipeChips.tsx`: props `kitchenId`, `recipes: ShoppingRecipeRef[]`, `locale`; a `<ul aria-label=…>` of `Link` anchors (`next/link`) to `/recipes/${encodeURIComponent(recipe_id)}?from=${encodeURIComponent(`/kitchens/${kitchenId}/cart`)}`; pill style from the existing chip/label styles in the app (search `ui/components` for the existing pill class before inventing one); touch target at least 44 px high; visible keyboard focus; chips wrap (`flex-wrap`) so the page never scrolls sideways at 360 px; long titles truncate with the full title in `title`. Make T025 pass.
- [X] T028 [US2] Render `<RecipeChips …/>` in `ui/components/ShoppingList/ShoppingLine.tsx` below or beside the line text, passing `kitchenId` and `locale` down from `ShoppingListSection.tsx`; update `ShoppingLine`'s props and the existing tests of T011.
- [ ] T029 [US2] Checkpoint: run the T023–T025 tests and the US1 suites again; open the Cart page on the dev stack and confirm a chip opens the recipe with `?from=` and Back returns to the Cart page (US2 scenario 2). **Open:** the automated part passed; the dev-stack/browser part was not run (no browser in the implementing session, see `notes.md` "Not done").

**Checkpoint**: US1 and US2 work: every measured line is traceable to its recipes.

---

## Phase 5: User Story 3 - Vague amounts in their own "Your call" section (Priority: P1)

**Goal**: Ingredients given without an amount appear once each under "Your call", with every distinct note and their chips; an ingredient both vague and measured appears in both places.

**Independent Test**: A cart with `salt — a pinch` in one recipe and `salt — to taste` in another shows one `salt` entry under "Your call" with both notes and both chips.

### Tests for User Story 3 ⚠️

- [X] T030 [P] [US3] Add to `api/tests/test_shopping_list_domain.py` vague-line tests: salt "a pinch" in A and "to taste" in B → one `YourCallEntry` named `salt`, notes `("a pinch", "to taste")`, recipes `[A, B]`; butter vague in A and 100 g in B → `lines` has `butter` 100 g with recipe B only and `your_call` has `butter` with recipe A only; the same note in two recipes appears once, also when it differs only by letter case or surrounding spaces (`"A pinch"` vs `"a pinch "`; the first spelling is kept, research R7); notes keep first-met order across recipes in cart order and lines in `position` order; entries sorted by `name_sort_key`; a vague line is never scaled (factor 3 leaves the note unchanged and adds no amount); a recipe whose only lines are vague adds no measured line.
- [X] T031 [P] [US3] Add a "US3" section to `api/tests/test_shopping_list_integration.py`: over HTTP, insert vague ingredient rows (`quantity` and `unit` null, `vague_note` set, as the table check `ck_recipe_ingredient_vague_or_measured` requires) and assert `your_call` for the salt and butter cases above.
- [X] T032 [P] [US3] Add to `ui/lib/shoppingListText.test.ts` the case `formatYourCall`: `salt — a pinch, to taste` (name, then notes joined with ", "). Add to `ShoppingListSection.test.tsx`: the "Your call" heading (`shoppingListMessages[locale].yourCall`) appears only when `your_call` is not empty; each entry shows its chips; both sections render for a response with `lines` and `your_call`; when `is_empty` is false and both arrays are empty the section shows the `noIngredients` line.

### Implementation for User Story 3

- [X] T033 [US3] Extend `build_shopping_list` in `api/domain/cart.py` for vague lines (FR-007): lines with `vague_note` are not scaled and carry no amount; group them by `name` only (exact string as stored); keep each distinct note once, comparing after `strip()` and case-folding, showing the first spelling, in the order first met; record recipes as for measured lines (each once, cart order); a name that is also measured stays in `lines` too; return the entries sorted by `name_sort_key` in `ShoppingList.your_call`. Make T030 pass without changing the T006/T007 results.
- [X] T034 [US3] Confirm `application/shopping_list.py` (T013) passes `ShoppingLine.vague_note` through from `CartIngredientLine` and returns `your_call` from the domain result; adjust only if T031 fails.
- [X] T035 [P] [US3] Add `formatYourCall(entry: YourCallEntry): string` to `ui/lib/shoppingListText.ts` (T032 text case) and create `ui/components/ShoppingList/YourCallList.tsx` (a sub-heading `yourCall`, then a `<ul>` of entries: the formatted text and `RecipeChips`; renders `null` for no entries).
- [X] T036 [US3] In `ui/components/ShoppingList/ShoppingListSection.tsx` render `<YourCallList …/>` after the measured lines, and the `noIngredients` line when `is_empty` is false and both `lines` and `your_call` are empty. Make T032 pass.
- [ ] T037 [US3] Checkpoint: run the US3 api and ui tests and the earlier suites; in the dev stack confirm the salt and butter cases from `quickstart.md` step 2–3. **Open:** the automated part passed; the dev-stack/browser part was not run (no browser in the implementing session, see `notes.md` "Not done").

**Checkpoint**: US1–US3 work: measured lines, chips and the "Your call" section.

---

## Phase 6: User Story 4 - The list always matches the current cart (Priority: P2)

**Goal**: The list follows the cart: the editor's list follows their draft, everyone else sees the saved cart's list, and a saved or discarded change shows on the next open with no manual refresh.

**Independent Test**: Change People from 2 to 4 on the Cart page and save; the list's measured amounts double (counts rounded up again). While `ana` edits, `ben` still sees the saved cart's list.

### Tests for User Story 4 ⚠️

- [X] T038 [P] [US4] Add to `api/tests/test_shopping_list_application.py`: when the caller's session holds the live cart lock and has a draft, the list is built from the draft's People (`effective_people(draft.people, member_count)`), recipes and meals; another session (no lock, or another holder) gets the saved cart's list; after `release_cart` the saved list returns; a drafted recipe that was deleted or is not in the kitchen is skipped; an empty draft gives `is_empty: true` even when the saved cart has recipes; the fake lock repository records no `touch_*`, `take_*`, `set_*` or `release_*` call during `execute`.
- [X] T039 [P] [US4] Add a "US4" section to `api/tests/test_shopping_list_integration.py`: with two members: `ana` starts editing and `PUT`s a draft with People changed; `ana`'s `GET …/shopping-list` shows the draft's scaled amounts while `ben`'s shows the saved cart's; `ana` discards → her list returns to the saved one; `ana` saves → `ben`'s next read shows the new amounts; doubling People doubles every measured amount (counts rounded up again after the sum); editing a recipe's ingredient rows (update the `recipe_ingredient` row directly) shows on the next read; reading the list leaves `cart_edit_lock.last_active_at` unchanged (FR-014); the reader is not able to keep a lock alive.
- [X] T040 [P] [US4] Extend `ui/components/ShoppingList/ShoppingListSection.test.tsx` and `ui/components/Cart/CartScreen.test.tsx`: the section takes a `cart` prop and fetches again when that prop changes identity (after a draft `PUT` answer, a save, a discard, a start-edit, or a focus refresh in `CartScreen`); an answer to an older request that arrives after a newer one is ignored (resolve the two fetches out of order); the previous list stays on screen while a new one loads (no loading status replaces it, no empty flash); the section renders nothing for an empty cart.

### Implementation for User Story 4

- [X] T041 [US4] In `api/application/shopping_list.py` choose the cart the caller sees (FR-001, research R2) the same way `recipe_cart_status` in `api/application/carts.py` does: `holder = locks.cart_holder(kitchen_id)`; if `holder` is not None and `holder.session_id == ref.session_id`, use `locks.cart_draft(kitchen_id, ref.session_id)` (its `people` and `items`) when it is not None; otherwise the saved cart. Keep it read only: call only `cart_holder` and `cart_draft`. Make T038 and T039 pass.
- [X] T042 [US4] In `ui/components/ShoppingList/ShoppingListSection.tsx` add the `cart: Cart` prop (type from `ui/lib/cartClient.ts`) and fetch again whenever it changes identity (effect keyed on `cart`); keep a `useRef` request counter so only the latest answer is applied; do not clear the previous list or show the loading line while a refetch runs (the loading line is for the first load only). In `ui/components/Cart/CartScreen.tsx` pass `cart={state.cart}` to the section. Make T040 pass.
- [ ] T043 [US4] Checkpoint: run the US4 tests and all earlier suites; confirm `quickstart.md` steps 6–10 on the dev stack with two accounts (draft follows People live for `ana`, `ben` sees the saved list, discard returns it, save shows on focus, an emptied cart shows no list section). **Open:** the automated part passed; the dev-stack/browser part was not run (no browser in the implementing session, see `notes.md` "Not done").

**Checkpoint**: all four stories work and the list matches the cart.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 [P] Run `cd api && uv run ruff check .` and `uv run ruff format --check .`; fix only the files this story touched or added; the 4 ruff errors already on HEAD stay.
- [X] T045 [P] Run `cd ui && npm test && npm run lint && npm run typecheck`; confirm `ui/lib/i18n/parity.test.ts` passes with `shoppingList` registered (no key missing in one language, none identical in both) and that no ui test hits the network.
- [X] T046 Run the full api suite in the Compose test overlay (`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`) and record counts in `specs/023-shopping-list/notes.md` against the baseline: no new failure.
- [ ] T047 Walk `quickstart.md` section 2 in the browser with two accounts, at phone width (about 360 px: chips wrap, no sideways scroll) and desktop width, with keyboard only (Tab reaches each chip, Enter opens it) and in Spanish (headings and "A tu criterio" shown; names and titles untranslated). Record what was seen, and anything not done, in `specs/023-shopping-list/notes.md` (constitution §6: check the ui in a browser before claiming success). **Open:** the automated part passed; the dev-stack/browser part was not run (no browser in the implementing session, see `notes.md` "Not done").
- [ ] T048 Time the 100-recipe × 20-line read on the dev stack (`quickstart.md` section 4): `GET /api/kitchens/{id}/shopping-list` answers in under 1 second (SC-003). Record the time in `specs/023-shopping-list/notes.md`. **Open:** the automated part passed; the dev-stack/browser part was not run (no browser in the implementing session, see `notes.md` "Not done").
- [X] T049 Security and privacy check (constitution §4): the route reads a draft only for the caller's own session (T039 covers `ben` never seeing `ana`'s draft); logs contain counts only (grep the new modules for `logger.` calls and confirm no name, note or title is logged); no real personal data in tests or fixtures.
- [X] T050 Update `dev/docs/backlog.yaml` S-023: `status: done` and a `verification` text in the style of S-022 (what ran, counts, what was not done), only after T046–T048 are recorded. Do not mark it done if the browser walk (T047) or the timed read (T048) was not run; say so in `verification` instead.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup; blocks all stories. T002, T003, T004 and T005 touch different files and can run together (T004 imports the type from T003, so write T003 first if working alone).
- **US1 (Phase 3)**: after Phase 2. MVP.
- **US2 (Phase 4)**: after US1 (adds chips to the US1 section and tests to its files).
- **US3 (Phase 5)**: after US1; independent of US2 except that `YourCallList` reuses `RecipeChips` (T027), so do US2 first or stub the chips.
- **US4 (Phase 6)**: after US1; best after US3 so the integration and ui tests cover the whole list.
- **Polish (Phase 7)**: after the stories wanted.

### Within each story

- Tests first, seen failing, then domain → application → schema/deps/route → BFF/client → components.
- `api/domain/cart.py` is edited by T002, T012, T033 (sequential, never parallel); `api/application/shopping_list.py` by T013, T034, T041; `ShoppingListSection.tsx` by T020, T028, T036, T042; `test_shopping_list_integration.py` by T009, T024, T031, T039; `test_shopping_list_domain.py` by T006, T023, T030. Tasks that touch the same file run in order.

### Parallel opportunities

- Phase 2: T002, T003, T004, T005.
- US1 tests: T006, T007, T008, T009, T010, T011 (six different files).
- US1 implementation after T013: T014; T017, T018 and T019 (different ui files) alongside the api route work T015–T016.
- US2: T023, T024, T025 together; T027 alone in its file.
- US3: T030, T031, T032 together; T035 with T033.
- US4: T038, T039, T040 together.
- Polish: T044 and T045.

### Parallel example: User Story 1 tests

```text
Task: "Domain tests in api/tests/test_shopping_list_domain.py"          (T006)
Task: "20 hand-calculated carts in api/tests/test_shopping_list_carts.py" (T007)
Task: "Service tests in api/tests/test_shopping_list_application.py"    (T008)
Task: "HTTP tests in api/tests/test_shopping_list_integration.py"       (T009)
Task: "Text and client tests in ui/lib/shoppingList*.test.ts"           (T010)
Task: "Section and BFF route tests in ui/components/ShoppingList/ and ui/app/api/…/shopping-list/" (T011)
```

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): tests, domain, service, route, BFF, client, section, Cart page.
3. **Stop and validate**: AC5.1–AC5.4 pass in automated tests (T006, T007, T009) and the combined line shows on the Cart page.
4. The list is already useful, though without chips or "Your call".

### Incremental delivery

1. Foundation → US1 (combined list) → US2 (chips and links) → US3 ("Your call") → US4 (draft and live refetch) → Polish.
2. Each story adds its own tests and does not change an earlier story's results (T033 must keep T006/T007 green).

### Notes

- This story only reads; do not add a migration, a table, a lock write or a cart write (FR-002, FR-014).
- Do not convert units, ever (constitution §5): `1 cup + 20 tbsp` stays as is.
- Leave unrelated uncommitted changes in the working tree as they are; add to a shared file (`ports.py`, `deps.py`, `app.py`, `CartScreen.tsx`) only where a task says so.
- Commit after each task or logical group; wait for review before pushing (constitution §8).
