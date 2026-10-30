"""Twenty invented carts with hand-calculated shopping lists (spec 023, SC-004).

Every expected result below was worked out by hand (scale, then sum, then round counts up once);
nothing here recomputes the answer. A recipe is (factor, lines); a line is (name, quantity, unit,
size). Expected lines are (name, size, ((amount, unit), …)) in list order.
"""

from __future__ import annotations

from fractions import Fraction as F
from uuid import UUID

import pytest
from domain.cart import ScaledRecipe, ShoppingLine, build_shopping_list

Line = tuple[str, F, str, str | None]
Recipe = tuple[F, list[Line]]
Expected = list[tuple[str, str | None, tuple[tuple[str, str], ...]]]


def _cart(recipes: list[Recipe]) -> list[ScaledRecipe]:
    return [
        ScaledRecipe(
            UUID(int=n + 1),
            f"Recipe {n + 1}",
            factor,
            tuple(ShoppingLine(name, qty, unit, size, None) for name, qty, unit, size in lines),
        )
        for n, (factor, lines) in enumerate(recipes)
    ]


CARTS: list[tuple[str, list[Recipe], Expected]] = [
    (
        "one recipe, factor 1, two ingredients",
        [(F(1), [("flour", F(2), "cup", None), ("sugar", F(100), "g", None)])],
        [("flour", None, (("2", "cup"),)), ("sugar", None, (("100", "g"),))],
    ),
    (
        "factor 2 doubles a fractional amount: 1.5 cup × 2 = 3 cup",
        [(F(2), [("flour", F(3, 2), "cup", None)])],
        [("flour", None, (("3", "cup"),))],
    ),
    (
        "factor 1/2 halves a mass: 100 g × 1/2 = 50 g",
        [(F(1, 2), [("butter", F(100), "g", None)])],
        [("butter", None, (("50", "g"),))],
    ),
    (
        "factor 3/4 on 1 cup = 0.75 cup",
        [(F(3, 4), [("milk", F(1), "cup", None)])],
        [("milk", None, (("0.75", "cup"),))],
    ),
    (
        "factor 3/4 on 2 eggs = 1.5, rounded up to 2",
        [(F(3, 4), [("egg", F(2), "unit", None)])],
        [("egg", None, (("2", "unit"),))],
    ),
    (
        "two halves of an egg sum to 1, not 2",
        [(F(1, 2), [("egg", F(1), "unit", None)]), (F(1, 2), [("egg", F(1), "unit", None)])],
        [("egg", None, (("1", "unit"),))],
    ),
    (
        "three thirds of an onion sum to exactly 1",
        [(F(1, 3), [("onion", F(1), "unit", None)])] * 3,
        [("onion", None, (("1", "unit"),))],
    ),
    (
        "factor 2/3 on 1 tbsp = 0.666… shown as 0.67",
        [(F(2, 3), [("sugar", F(1), "tbsp", None)])],
        [("sugar", None, (("0.67", "tbsp"),))],
    ),
    (
        "factor 99 (Servings 99, base 1)",
        [(F(99), [("pepper", F(1), "tsp", None)])],
        [("pepper", None, (("99", "tsp"),))],
    ),
    (
        "mass units largest first: 1 lb + 8 oz + 500 g",
        [
            (
                F(1),
                [
                    ("beef", F(500), "g", None),
                    ("beef", F(8), "oz", None),
                    ("beef", F(1), "lb", None),
                ],
            )
        ],
        [("beef", None, (("1", "lb"), ("8", "oz"), ("500", "g")))],
    ),
    (
        "same unit across factors 1 and 2: 1 + 2 = 3 cup",
        [(F(1), [("rice", F(1), "cup", None)]), (F(2), [("rice", F(1), "cup", None)])],
        [("rice", None, (("3", "cup"),))],
    ),
    (
        "factor 5/2: 2 tbsp → 5 tbsp and 3 eggs → 7.5 → 8",
        [(F(5, 2), [("oil", F(2), "tbsp", None), ("egg", F(3), "unit", None)])],
        [("egg", None, (("8", "unit"),)), ("oil", None, (("5", "tbsp"),))],
    ),
    (
        "one recipe with two lines of one ingredient: 1 + 2 = 3",
        [(F(1), [("garlic", F(1), "unit", None), ("garlic", F(2), "unit", None)])],
        [("garlic", None, (("3", "unit"),))],
    ),
    (
        "sized counts at factor 1/2: 1.5 large → 2, 0.5 small → 1",
        [(F(1, 2), [("tomato", F(1), "unit", "small"), ("tomato", F(3), "unit", "large")])],
        [("tomato", "large", (("2", "unit"),)), ("tomato", "small", (("1", "unit"),))],
    ),
    (
        "sized and unsized onions: large 1 + 2 = 3, no size 1",
        [
            (F(1), [("onion", F(1), "unit", None)]),
            (F(1), [("onion", F(1), "unit", "large")]),
            (F(2), [("onion", F(1), "unit", "large")]),
        ],
        [("onion", "large", (("3", "unit"),)), ("onion", None, (("1", "unit"),))],
    ),
    (
        "1/4 cup + 1/3 cup = 7/12 = 0.5833… shown as 0.58",
        [(F(1), [("flour", F(1, 4), "cup", None)]), (F(1), [("flour", F(1, 3), "cup", None)])],
        [("flour", None, (("0.58", "cup"),))],
    ),
    (
        "5/8 cup = 0.625 rounds half up to 0.63",
        [(F(1), [("cream", F(5, 8), "cup", None)])],
        [("cream", None, (("0.63", "cup"),))],
    ),
    (
        "Servings 99, base 2 = factor 99/2: 10 g → 495 g, 1 egg → 49.5 → 50",
        [(F(99, 2), [("butter", F(10), "g", None), ("egg", F(1), "unit", None)])],
        [("butter", None, (("495", "g"),)), ("egg", None, (("50", "unit"),))],
    ),
    (
        "one name in three kinds: mass, volume, count in that order",
        [
            (
                F(1),
                [
                    ("sugar", F(1), "unit", None),
                    ("sugar", F(1), "cup", None),
                    ("sugar", F(100), "g", None),
                ],
            )
        ],
        [
            ("sugar", None, (("100", "g"),)),
            ("sugar", None, (("1", "cup"),)),
            ("sugar", None, (("1", "unit"),)),
        ],
    ),
    (
        "four recipes of flour: 1 + 2 cup, 3 + 0.5 tbsp",
        [
            (F(1, 2), [("flour", F(2), "cup", None)]),
            (F(1), [("flour", F(3), "tbsp", None)]),
            (F(2), [("flour", F(1), "cup", None)]),
            (F(1, 4), [("flour", F(2), "tbsp", None)]),
        ],
        [("flour", None, (("3", "cup"), ("3.5", "tbsp")))],
    ),
]


@pytest.mark.parametrize(
    ("recipes", "expected"),
    [pytest.param(recipes, expected, id=name) for name, recipes, expected in CARTS],
)
def test_hand_calculated_cart(recipes: list[Recipe], expected: Expected) -> None:
    result = build_shopping_list(_cart(recipes))
    got = [
        (ln.name, ln.size, tuple((a.quantity, a.unit) for a in ln.amounts)) for ln in result.lines
    ]
    assert got == expected
    assert result.your_call == ()
    # SC-005: every line names at least one recipe.
    assert all(ln.recipes for ln in result.lines)


def test_there_are_twenty_carts() -> None:
    assert len(CARTS) == 20
