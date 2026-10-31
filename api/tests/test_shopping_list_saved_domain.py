"""The saved list rules (spec 025)."""

from __future__ import annotations

from fractions import Fraction
from uuid import uuid4

import pytest
from domain.cart import (
    RecipeRef,
    ScaledRecipe,
    ShoppingLine,
    build_shopping_list,
)
from domain.errors import ShoppingItemError
from domain.shopping_list import (
    cart_lines,
    hand_item,
    hand_lines,
    recipe_titles,
    stored_cart_list,
)


def built():  # noqa: ANN201
    return build_shopping_list(
        [
            ScaledRecipe(
                uuid4(),
                "Bread",
                Fraction(1),
                (
                    ShoppingLine("flour", Fraction(1), "cup", None, None),
                    ShoppingLine("flour", Fraction(3), "tbsp", None, None),
                    ShoppingLine("salt", None, None, None, "to taste"),
                ),
            )
        ]
    )


def test_stored_lines_give_back_the_same_list() -> None:
    original = built()
    lines = cart_lines(original)
    assert [ln.section for ln in lines] == ["measured", "your_call"]
    assert stored_cart_list(lines) == original


def test_hand_item_with_no_amount_keeps_its_accents() -> None:
    item = hand_item("  Jabón   de PLATOS ")
    assert item.name == "jabón de platos"
    assert (item.origin, item.kind, item.amounts) == ("hand", None, ())


def test_hand_item_with_an_amount() -> None:
    item = hand_item("egg", "2,50", "unit", "large")
    assert item.kind == "count"
    assert item.size == "large"
    assert (item.amounts[0].quantity, item.amounts[0].unit) == ("2.5", "unit")


@pytest.mark.parametrize(
    ("args", "field"),
    [
        (("",), "name"),
        (("   ",), "name"),
        ((None,), "name"),
        (("x" * 121,), "name"),
        (("egg", "2"), "unit"),
        (("egg", None, "g"), "quantity"),
        (("egg", "0", "g"), "quantity"),
        (("egg", "-1", "g"), "quantity"),
        (("egg", "0.001", "g"), "quantity"),
        (("egg", "lots", "g"), "quantity"),
        (("egg", "NaN", "g"), "quantity"),
        (("egg", 2, "g"), "quantity"),
        (("egg", "2", "stone"), "unit"),
        (("egg", "2", "g", "large"), "size"),
        (("egg", "2", "unit", "huge"), "size"),
        (("egg", None, None, "large"), "size"),
    ],
)
def test_bad_hand_items_name_the_field(args: tuple, field: str) -> None:
    with pytest.raises(ShoppingItemError) as refused:
        hand_item(*args)
    assert refused.value.field == field


def test_hand_lines_and_titles() -> None:
    recipe = RecipeRef(uuid4(), "Bread")
    lines = cart_lines(built())
    assert recipe_titles(lines) == ("Bread",)
    assert hand_lines((*lines, hand_item("soap")))[0].name == "soap"
    assert recipe.title == "Bread"
