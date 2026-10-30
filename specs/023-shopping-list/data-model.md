# Data Model: Consolidated Shopping List (S-023)

**No tables, columns or migrations are added.** The shopping list is derived on every read and never stored (FR-002). This file lists what is read, and the in-memory types the domain and the route use.

## Read from existing data

| Source | Fields used | Notes |
|---|---|---|
| `cart` | `people` (null: follow the member count) | Saved cart. Spec 022. |
| `cart_item` | `recipe_id`, `meals`, `added_at` | Cart order is `added_at`. |
| `cart_edit_lock.draft` | `people`, items `{recipe_id, meals}` | Only for the caller's live session (FR-001). |
| `kitchen_memberships` | count | Default People (`effective_people`). |
| `recipe` | `id`, `title`, `base_servings`, `notebook_id` | Via `CartRepository.recipe_facts`. |
| `notebook` | `kitchen_id` | A recipe whose notebook is not this kitchen's is skipped. |
| `recipe_ingredient` | `recipe_id`, `position`, `name`, `quantity`, `unit`, `size`, `vague_note` | `preparation` is not read (FR-004). Ordered by `recipe_id, position`. |

Existing guarantees the domain relies on (table checks from spec 020): a line is either vague (`vague_note` set, `quantity` and `unit` null) or measured (`quantity > 0` and `unit` set); `size` only with `unit = 'unit'`; `unit` is one of the ten allowed units.

## Port value type (`application/ports.py`)

```text
CartIngredientLine
  name: str                    as stored, already a catalog name
  quantity: Decimal | None     null when vague
  unit: str | None             null when vague
  size: "small" | "medium" | "large" | None
  vague_note: str | None
```

`IngredientLineReader.lines_for(recipe_ids) -> dict[UUID, tuple[CartIngredientLine, ...]]` returns each recipe's lines in `position` order; a recipe with no lines is absent or empty.

## Domain types (`domain/cart.py`, pure)

```text
Kind = "mass" | "volume" | "count"

ShoppingLine (input)
  name, quantity: Fraction | None, unit: str | None, size: str | None, vague_note: str | None

ScaledRecipe (input, one per cart entry, in cart order)
  recipe_id: UUID
  title: str
  factor: Fraction             scale_factor(people, meals, base_servings)
  lines: tuple[ShoppingLine, ...]

RecipeRef                       recipe_id, title

Amount                          quantity: str, unit: str
MeasuredLine
  name: str
  kind: Kind
  size: str | None             counts only
  amounts: tuple[Amount, ...]  largest unit first; one entry for a count
  recipes: tuple[RecipeRef, ...]   cart order, each recipe once

YourCallEntry
  name: str
  notes: tuple[str, ...]       distinct, first-met order
  recipes: tuple[RecipeRef, ...]

ShoppingList
  lines: tuple[MeasuredLine, ...]       sorted (FR-010)
  your_call: tuple[YourCallEntry, ...]  sorted by name
```

`build_shopping_list(recipes: Sequence[ScaledRecipe]) -> ShoppingList` is the only entry point. `is_empty` is decided by the use case (no cart recipes), not by the domain.

## Rules and where they are enforced

| Rule | Spec | Where |
|---|---|---|
| line amount = quantity × recipe factor, exact | FR-003 | `build_shopping_list` (Fraction) |
| group by `(name, kind)`; counts by `(name, size)`; preparation ignored | FR-004, FR-005 | `build_shopping_list` |
| count total: sum then `ceil` | FR-005 | `build_shopping_list` |
| mass/volume: sum per unit, no conversion, largest first, ≤2 decimals half up | FR-006 | `build_shopping_list` + `format_factor` |
| vague lines unscaled, one entry per name, distinct notes in first-met order; also in measured list when measured elsewhere | FR-007 | `build_shopping_list` |
| chips: titles, each recipe once, cart order | FR-008 | `build_shopping_list` |
| order of lines and entries | FR-010 | sort key in `build_shopping_list` |
| draft for the editor, saved cart for others | FR-001 | `GetShoppingListService` |
| not stored, no side effects | FR-002, FR-014 | read-only port and route |
| 404 for non-members | FR-012 | `GetShoppingListService` |

## State transitions

None. The list has no state of its own; it changes when the cart, its People or Meals, or a recipe's lines change.

## Amendment 2026-10-30: cart by servings

Migration `0008_cart_servings` (revises `0007_cart_and_edit_locks`). Rules are in [research.md](./research.md) R9 to R11.

| Table | Change |
|---|---|
| `cart` | Drop `people` and `ck_cart_people` |
| `cart_item` | Rename `meals` to `servings`, whole, 1 to 99, NOT NULL, no server default; replace `ck_cart_item_meals` with `ck_cart_item_servings` |
| `cart_edit_lock` | Delete all rows. The `draft` JSON becomes `{"items": [{"recipe_id", "servings"}]}` |

**Scale factor** (derived, never stored): `servings / base_servings`.

**Order in the upgrade**: set the converted values while `people` still exists, then rename, then drop.
