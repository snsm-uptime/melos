"""The shopping list built from a cart (spec 023, domain/cart.py). Pure: no database."""

from __future__ import annotations

from fractions import Fraction
from uuid import UUID

import pytest
from domain.cart import (
    Amount,
    ScaledRecipe,
    ShoppingLine,
    ShoppingList,
    build_shopping_list,
    name_sort_key,
    unit_kind,
)

ONE = Fraction(1)


def rid(n: int) -> UUID:
    return UUID(int=n)


def line(
    name: str,
    quantity: Fraction | int | str,
    unit: str,
    size: str | None = None,
) -> ShoppingLine:
    return ShoppingLine(name, Fraction(quantity), unit, size, None)


def vague(name: str, note: str) -> ShoppingLine:
    return ShoppingLine(name, None, None, None, note)


def recipe(n: int, title: str, factor: Fraction, *lines: ShoppingLine) -> ScaledRecipe:
    return ScaledRecipe(rid(n), title, factor, tuple(lines))


def shown(result: ShoppingList) -> list[tuple[str, str | None, tuple[tuple[str, str], ...]]]:
    """(name, size, ((quantity, unit), …)) for each measured line, in order."""
    return [
        (ln.name, ln.size, tuple((a.quantity, a.unit) for a in ln.amounts)) for ln in result.lines
    ]


def titles(result: ShoppingList, index: int = 0) -> list[str]:
    return [r.title for r in result.lines[index].recipes]


def test_ac51_flour_in_two_units_is_one_line() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("flour", 3, "tbsp")),
            recipe(2, "B", ONE, line("flour", 1, "cup")),
        ]
    )
    assert shown(result) == [("flour", None, (("1", "cup"), ("3", "tbsp")))]
    assert result.lines[0].kind == "volume"
    assert titles(result) == ["A", "B"]


def test_ac52_count_is_rounded_up_after_scaling() -> None:
    # base servings 4, Servings 3: factor 3/4, 2 eggs → 1.5 → 2
    result = build_shopping_list([recipe(1, "A", Fraction(3, 4), line("egg", 2, "unit"))])
    assert shown(result) == [("egg", None, (("2", "unit"),))]
    assert result.lines[0].kind == "count"


def test_ac53_mass_and_volume_are_separate_lines_never_converted() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("rice", 200, "g")),
            recipe(2, "B", ONE, line("rice", 1, "cup")),
        ]
    )
    assert [ln.kind for ln in result.lines] == ["mass", "volume"]
    assert shown(result) == [("rice", None, (("200", "g"),)), ("rice", None, (("1", "cup"),))]


def test_ac54_counts_are_split_by_size() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("onion", 1, "unit", "large")),
            recipe(2, "B", ONE, line("onion", 1, "unit", "large")),
            recipe(3, "C", ONE, line("onion", 1, "unit", "small")),
        ]
    )
    assert shown(result) == [
        ("onion", "large", (("2", "unit"),)),
        ("onion", "small", (("1", "unit"),)),
    ]


def test_count_with_no_size_is_its_own_line() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("onion", 1, "unit")),
            recipe(2, "B", ONE, line("onion", 2, "unit", "large")),
            recipe(3, "C", ONE, line("onion", 1, "unit", "medium")),
            recipe(4, "D", ONE, line("onion", 1, "unit", "small")),
        ]
    )
    assert [(ln.size) for ln in result.lines] == ["large", "medium", "small", None]
    assert shown(result)[-1] == ("onion", None, (("1", "unit"),))


def test_same_name_from_different_recipes_merges_and_preparation_is_not_a_key() -> None:
    # Preparation never reaches the domain: "chopped onion" and "sliced onion" are both "onion".
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("onion", 1, "unit")),
            recipe(2, "B", ONE, line("onion", 1, "unit")),
        ]
    )
    assert shown(result) == [("onion", None, (("2", "unit"),))]


def test_count_is_rounded_up_once_after_the_sum() -> None:
    # Two lines of 0.5 egg give 1, not 2.
    half = recipe(1, "A", Fraction(1, 2), line("egg", 1, "unit"))
    other = recipe(2, "B", Fraction(1, 2), line("egg", 1, "unit"))
    assert shown(build_shopping_list([half, other])) == [("egg", None, (("1", "unit"),))]


def test_whole_count_total_is_not_rounded() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("egg", 2, "unit")),
            recipe(2, "B", ONE, line("egg", 1, "unit")),
        ]
    )
    assert shown(result) == [("egg", None, (("3", "unit"),))]


def test_factor_stays_exact_until_the_sum() -> None:
    # Three recipes at factor 1/3: 1 cup each is exactly 1 cup, not 0.33 × 3 = 0.99.
    third = Fraction(1, 3)
    result = build_shopping_list(
        [recipe(n, f"R{n}", third, line("milk", 1, "cup")) for n in (1, 2, 3)]
    )
    assert shown(result) == [("milk", None, (("1", "cup"),))]


@pytest.mark.parametrize(
    ("quantity", "factor", "text"),
    [
        (1, Fraction(1, 3), "0.33"),
        (3, Fraction(1, 2), "1.5"),
        (1, Fraction(2), "2"),
        (1, Fraction(2, 3), "0.67"),
        (Fraction(1, 8), ONE, "0.13"),  # 0.125 rounds half up
        (Fraction(5, 2), ONE, "2.5"),
    ],
)
def test_measured_amounts_show_at_most_two_decimals(
    quantity: Fraction | int, factor: Fraction, text: str
) -> None:
    result = build_shopping_list([recipe(1, "A", factor, line("milk", quantity, "cup"))])
    assert result.lines[0].amounts == (Amount(text, "cup"),)


def test_units_are_summed_per_unit_never_carried_over() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("milk", 1, "cup")),
            recipe(2, "B", ONE, line("milk", 20, "tbsp")),
            recipe(3, "C", ONE, line("milk", 1, "cup")),
        ]
    )
    assert shown(result) == [("milk", None, (("2", "cup"), ("20", "tbsp")))]


def test_mass_units_are_listed_largest_first() -> None:
    result = build_shopping_list(
        [recipe(1, "A", ONE, *(line("flour", 1, u) for u in ("g", "oz", "lb", "kg")))]
    )
    assert [a.unit for a in result.lines[0].amounts] == ["kg", "lb", "oz", "g"]


def test_volume_units_are_listed_largest_first() -> None:
    result = build_shopping_list(
        [recipe(1, "A", ONE, *(line("milk", 1, u) for u in ("ml", "tsp", "tbsp", "cup", "l")))]
    )
    assert [a.unit for a in result.lines[0].amounts] == ["l", "cup", "tbsp", "tsp", "ml"]


def test_lines_are_ordered_by_name_ignoring_accents_and_case() -> None:
    result = build_shopping_list(
        [
            recipe(
                1,
                "A",
                ONE,
                line("nata", 1, "cup"),
                line("Ñame", 1, "unit"),
                line("ajo", 1, "unit"),
                line("Zanahoria", 1, "unit"),
                line("árbol", 1, "unit"),
            )
        ]
    )
    assert [ln.name for ln in result.lines] == ["ajo", "árbol", "Ñame", "nata", "Zanahoria"]


def test_same_name_orders_mass_then_volume_then_count() -> None:
    result = build_shopping_list(
        [
            recipe(
                1,
                "A",
                ONE,
                line("tomato", 1, "unit"),
                line("tomato", 1, "cup"),
                line("tomato", 100, "g"),
            )
        ]
    )
    assert [ln.kind for ln in result.lines] == ["mass", "volume", "count"]


def test_same_name_in_two_notebooks_merges_by_exact_string() -> None:
    result = build_shopping_list(
        [
            recipe(1, "From notebook one", ONE, line("garlic", 2, "unit")),
            recipe(2, "From notebook two", ONE, line("garlic", 1, "unit")),
            recipe(3, "Plural", ONE, line("garlics", 1, "unit")),
        ]
    )
    # Spelling differences are separate lines (spec edge case).
    assert shown(result) == [
        ("garlic", None, (("3", "unit"),)),
        ("garlics", None, (("1", "unit"),)),
    ]


def test_an_empty_cart_gives_an_empty_list() -> None:
    assert build_shopping_list([]) == ShoppingList(lines=(), your_call=())


def test_unit_kind_covers_the_ten_allowed_units() -> None:
    assert [unit_kind(u) for u in ("kg", "lb", "oz", "g")] == ["mass"] * 4
    assert [unit_kind(u) for u in ("l", "cup", "tbsp", "tsp", "ml")] == ["volume"] * 5
    assert unit_kind("unit") == "count"
    with pytest.raises(ValueError):
        unit_kind("pinch")


def test_name_sort_key_ignores_accents_and_case() -> None:
    assert name_sort_key("Ñame")[0] == "name"
    assert name_sort_key("ÁRBOL")[0] == "arbol"


# --- Chips: the recipes a line comes from (US2, FR-008) -----------------------------------------


def test_chips_follow_cart_order_not_title_order() -> None:
    result = build_shopping_list(
        [
            recipe(1, "Zeta", ONE, line("flour", 1, "cup")),
            recipe(2, "Alpha", ONE, line("flour", 1, "cup")),
        ]
    )
    assert titles(result) == ["Zeta", "Alpha"]


def test_a_recipe_with_two_lines_of_one_ingredient_is_one_chip() -> None:
    result = build_shopping_list(
        [recipe(1, "Bread", ONE, line("flour", 1, "cup"), line("flour", 2, "tbsp"))]
    )
    assert [r.recipe_id for r in result.lines[0].recipes] == [rid(1)]


def test_recipes_with_the_same_title_are_two_chips() -> None:
    result = build_shopping_list(
        [
            recipe(1, "Soup", ONE, line("salt", 1, "tsp")),
            recipe(2, "Soup", ONE, line("salt", 1, "tsp")),
        ]
    )
    assert [(r.recipe_id, r.title) for r in result.lines[0].recipes] == [
        (rid(1), "Soup"),
        (rid(2), "Soup"),
    ]


def test_a_line_from_one_recipe_has_exactly_one_chip() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("rice", 1, "cup")),
            recipe(2, "B", ONE, line("beans", 1, "cup")),
        ]
    )
    assert [len(ln.recipes) for ln in result.lines] == [1, 1]
    assert titles(result, 0) == ["B"] and titles(result, 1) == ["A"]


def test_chips_only_list_recipes_that_feed_the_line() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, line("rice", 200, "g")),
            recipe(2, "B", ONE, line("rice", 1, "cup")),
            recipe(3, "C", ONE, line("rice", 100, "g")),
        ]
    )
    assert titles(result, 0) == ["A", "C"] and titles(result, 1) == ["B"]


# --- "Your call": vague lines (US3, FR-007) -----------------------------------------------------


def call(result: ShoppingList) -> list[tuple[str, tuple[str, ...], list[str]]]:
    return [(e.name, e.notes, [r.title for r in e.recipes]) for e in result.your_call]


def test_vague_notes_of_one_ingredient_are_one_entry_with_every_note() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("salt", "a pinch")),
            recipe(2, "B", ONE, vague("salt", "to taste")),
        ]
    )
    assert call(result) == [("salt", ("a pinch", "to taste"), ["A", "B"])]
    assert result.lines == ()


def test_an_ingredient_vague_in_one_recipe_and_measured_in_another_is_in_both_places() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("butter", "to taste")),
            recipe(2, "B", ONE, line("butter", 100, "g")),
        ]
    )
    assert shown(result) == [("butter", None, (("100", "g"),))]
    assert titles(result) == ["B"]
    assert call(result) == [("butter", ("to taste",), ["A"])]


def test_the_same_note_in_two_recipes_appears_once() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("salt", "to taste")),
            recipe(2, "B", ONE, vague("salt", "to taste")),
        ]
    )
    assert call(result) == [("salt", ("to taste",), ["A", "B"])]


def test_notes_that_differ_only_by_case_or_spaces_are_one_note_with_the_first_spelling() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("salt", "A pinch")),
            recipe(2, "B", ONE, vague("salt", "a pinch ")),
            recipe(3, "C", ONE, vague("salt", " A  PINCH")),
        ]
    )
    # The third differs by an inner double space, which is a different note.
    assert call(result) == [("salt", ("A pinch", "A  PINCH"), ["A", "B", "C"])]


def test_notes_keep_the_order_first_met() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("oil", "for frying"), vague("oil", "to taste")),
            recipe(2, "B", ONE, vague("oil", "a drizzle"), vague("oil", "for frying")),
        ]
    )
    assert call(result) == [("oil", ("for frying", "to taste", "a drizzle"), ["A", "B"])]


def test_vague_entries_are_sorted_by_name_ignoring_accents_and_case() -> None:
    result = build_shopping_list(
        [recipe(1, "A", ONE, vague("sal", "x"), vague("Ajo", "x"), vague("árbol", "x"))]
    )
    assert [e.name for e in result.your_call] == ["Ajo", "árbol", "sal"]


def test_a_vague_line_is_never_scaled_and_adds_no_amount() -> None:
    result = build_shopping_list([recipe(1, "A", Fraction(3), vague("pepper", "a pinch"))])
    assert result.lines == ()
    assert call(result) == [("pepper", ("a pinch",), ["A"])]


def test_a_recipe_with_only_vague_lines_adds_no_measured_line() -> None:
    result = build_shopping_list(
        [
            recipe(1, "A", ONE, vague("salt", "to taste"), vague("pepper", "to taste")),
            recipe(2, "B", ONE, line("rice", 1, "cup")),
        ]
    )
    assert [ln.name for ln in result.lines] == ["rice"]
    assert [e.name for e in result.your_call] == ["pepper", "salt"]


def test_vague_chips_list_each_recipe_once_even_with_two_notes() -> None:
    result = build_shopping_list(
        [recipe(1, "A", ONE, vague("salt", "a pinch"), vague("salt", "to taste"))]
    )
    assert call(result) == [("salt", ("a pinch", "to taste"), ["A"])]
