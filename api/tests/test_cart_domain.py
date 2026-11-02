"""Cart rules (spec 022, domain/cart.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from fractions import Fraction
from uuid import uuid4

import pytest
from domain.cart import (
    ScaledRecipe,
    ShoppingLine,
    build_shopping_list,
    cart_save_action,
    check_count,
    format_factor,
    idle_expires_at,
    lock_is_idle,
    scale_factor,
    unit_kind,
)
from domain.errors import CartValueError


def test_scale_factor_is_exact() -> None:
    assert scale_factor(2, 4) == Fraction(1, 2)
    assert scale_factor(6, 4) == Fraction(3, 2)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (Fraction(1, 2), "0.5"),
        (Fraction(3, 2), "1.5"),
        (Fraction(2, 3), "0.67"),
        (Fraction(1, 3), "0.33"),
        (Fraction(2), "2"),
        (Fraction(3, 4), "0.75"),
        (Fraction(1, 200), "0.01"),
        (Fraction(10), "10"),
    ],
)
def test_format_factor(value: Fraction, text: str) -> None:
    assert format_factor(value) == text


@pytest.mark.parametrize("value", [1, 99])
def test_check_count_accepts_bounds(value: int) -> None:
    assert check_count(value, "meals") == value


@pytest.mark.parametrize("value", [0, 100, -1, 1.5, "3", None, True])
def test_check_count_rejects(value: object) -> None:
    with pytest.raises(CartValueError) as info:
        check_count(value, "people")
    assert info.value.field == "people"


def test_lock_idle_limit_is_five_minutes() -> None:
    start = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
    assert not lock_is_idle(start, start + timedelta(minutes=4, seconds=59))
    assert lock_is_idle(start, start + timedelta(minutes=5))
    assert idle_expires_at(start) == start + timedelta(minutes=5)


# --- custom units on the shopping list (spec 055 R13) ----------------------------------------


def _scaled(*lines: ShoppingLine, factor: Fraction = Fraction(1)) -> ScaledRecipe:
    return ScaledRecipe(uuid4(), "Beans", factor, lines)


def _line(name: str, quantity: int, unit: str) -> ShoppingLine:
    return ShoppingLine(name, Fraction(quantity), unit, None, None)


def _amounts(result) -> list[tuple[str, str, tuple[tuple[str, str], ...]]]:
    return [
        (ln.name, ln.kind, tuple((a.quantity, a.unit) for a in ln.amounts)) for ln in result.lines
    ]


def test_unit_kind_answers_custom_outside_the_ten() -> None:
    assert unit_kind("lata") == "custom"


def test_one_custom_unit_adds_up() -> None:
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata")), _scaled(_line("frijoles", 2, "lata"))]
    )
    assert _amounts(result) == [("frijoles", "custom", (("3", "lata"),))]


def test_a_custom_sum_rounds_up_to_a_whole_number() -> None:
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata"), factor=Fraction(3, 2))]
    )
    assert _amounts(result) == [("frijoles", "custom", (("2", "lata"),))]


def test_a_sum_rounds_up_once_after_adding() -> None:
    half = Fraction(1, 2)
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata"), factor=half) for _ in range(3)]
    )
    assert _amounts(result) == [("frijoles", "custom", (("2", "lata"),))]


def test_a_custom_unit_and_grams_stay_apart_with_no_conversion() -> None:
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata")), _scaled(_line("frijoles", 200, "g"))]
    )
    assert _amounts(result) == [
        ("frijoles", "mass", (("200", "g"),)),
        ("frijoles", "custom", (("1", "lata"),)),
    ]


def test_two_custom_units_of_one_ingredient_share_a_line_by_unit_name() -> None:
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata"), _line("frijoles", 2, "bote"))]
    )
    assert _amounts(result) == [("frijoles", "custom", (("2", "bote"), ("1", "lata")))]


def test_custom_sorts_after_count() -> None:
    result = build_shopping_list(
        [_scaled(_line("frijoles", 1, "lata"), _line("frijoles", 2, "unit"))]
    )
    assert [ln.kind for ln in result.lines] == ["count", "custom"]


# --- cart activity (spec 055 R18) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("before", "after", "action"),
    [
        ((), ("a",), "created"),
        (("a",), ("a", "b"), "edited"),
        (("a",), (), "edited"),
        (("a", "b"), ("b", "a"), "edited"),
        (("a",), ("a",), None),
        ((), (), None),
    ],
)
def test_cart_save_action(before: tuple, after: tuple, action: str | None) -> None:
    assert cart_save_action(before, after) == action
