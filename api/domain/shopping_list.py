"""The saved shopping list (spec 025): stored lines, items added by hand, closing.

Cart lines are copies of what `domain.cart.build_shopping_list` built; nothing is recalculated
here. Pure: no I/O, no FastAPI, no SQLAlchemy.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Literal
from uuid import UUID

from domain.cart import (
    COUNT_UNIT,
    MASS_UNITS,
    SIZE_ORDER,
    VOLUME_UNITS,
    Amount,
    Kind,
    MeasuredLine,
    RecipeRef,
    ShoppingList,
    YourCallEntry,
    format_factor,
    unit_kind,
)
from domain.errors import ShoppingItemError

Origin = Literal["cart", "hand"]
Section = Literal["measured", "your_call"]

NAME_MAX = 120
_QUANTITY_MAX = Decimal(100000)
_UNITS = frozenset((*MASS_UNITS, *VOLUME_UNITS, COUNT_UNIT))
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class SavedLine:
    origin: Origin
    section: Section
    name: str
    kind: Kind | None
    size: str | None
    amounts: tuple[Amount, ...]
    notes: tuple[str, ...]
    recipes: tuple[RecipeRef, ...]
    # None until stored.
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SavedList:
    id: UUID
    kitchen_id: UUID
    # None while the list is active.
    closing_date: date | None
    created_at: datetime
    # Cart lines in list order, then hand items in the order they were added.
    items: tuple[SavedLine, ...]


def cart_lines(shopping_list: ShoppingList) -> tuple[SavedLine, ...]:
    """A built list as stored lines, keeping its order."""
    measured = tuple(
        SavedLine("cart", "measured", ln.name, ln.kind, ln.size, ln.amounts, (), ln.recipes)
        for ln in shopping_list.lines
    )
    your_call = tuple(
        SavedLine("cart", "your_call", e.name, None, None, (), e.notes, e.recipes)
        for e in shopping_list.your_call
    )
    return measured + your_call


def stored_cart_list(items: Sequence[SavedLine]) -> ShoppingList:
    """The cart lines of a saved list in the shape the list is shown in."""
    lines: list[MeasuredLine] = []
    your_call: list[YourCallEntry] = []
    for item in items:
        if item.origin != "cart":
            continue
        if item.section == "your_call":
            your_call.append(YourCallEntry(item.name, item.notes, item.recipes))
        else:
            assert item.kind is not None
            lines.append(MeasuredLine(item.name, item.kind, item.size, item.amounts, item.recipes))
    return ShoppingList(tuple(lines), tuple(your_call))


def hand_lines(items: Sequence[SavedLine]) -> tuple[SavedLine, ...]:
    return tuple(item for item in items if item.origin == "hand")


def recipe_titles(items: Sequence[SavedLine]) -> tuple[str, ...]:
    """Each recipe's title once, in list order."""
    titles = {ref.recipe_id: ref.title for item in items for ref in reversed(item.recipes)}
    seen = {ref.recipe_id: None for item in items for ref in item.recipes}
    return tuple(titles[recipe_id] for recipe_id in seen)


def hand_item(
    name: object,
    quantity: object = None,
    unit: object = None,
    size: object = None,
) -> SavedLine:
    """A checked item added by hand. Refuses with ShoppingItemError naming the field.

    The name is trimmed and lower-cased but keeps its accents, as a member will read it.
    """
    if not isinstance(name, str):
        raise ShoppingItemError("name")
    clean = _SPACES.sub(" ", name).strip().lower()
    if not clean or len(clean) > NAME_MAX:
        raise ShoppingItemError("name")
    if (quantity is None) != (unit is None):
        raise ShoppingItemError("unit" if unit is None else "quantity")
    if size is not None and (unit != COUNT_UNIT or size not in SIZE_ORDER):
        raise ShoppingItemError("size")
    if quantity is None:
        return SavedLine("hand", "measured", clean, None, None, (), (), ())
    if unit not in _UNITS:
        raise ShoppingItemError("unit")
    return SavedLine(
        "hand",
        "measured",
        clean,
        unit_kind(unit),  # type: ignore[arg-type]
        size,  # type: ignore[arg-type]
        (Amount(_quantity(quantity), unit),),  # type: ignore[arg-type]
        (),
        (),
    )


def _quantity(value: object) -> str:
    if not isinstance(value, str):
        raise ShoppingItemError("quantity")
    try:
        number = Decimal(value.strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ShoppingItemError("quantity") from exc
    if not number.is_finite() or number <= 0 or number > _QUANTITY_MAX:
        raise ShoppingItemError("quantity")
    shown = format_factor(Fraction(number))
    if Decimal(shown) == 0:
        raise ShoppingItemError("quantity")
    return shown
