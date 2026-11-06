"""The saved shopping list (spec 025): stored lines, items added by hand, closing.

Cart lines are copies of what `domain.cart.build_shopping_list` built; nothing is recalculated
here. Pure: no I/O, no FastAPI, no SQLAlchemy.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
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
from domain.errors import ShoppingDateError, ShoppingItemError

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
    # Shared by the kitchen (spec 070 FR-001).
    bought: bool = False
    # The ingredient's word per language, (language, name) pairs; () for hand items (spec 043).
    names: tuple[tuple[str, str], ...] = ()


# Kept name -> its word per language, for the lines of one list (spec 043 R7).
ListNames = Mapping[str, Mapping[str, str]]


def shown_list_name(kept: str, names: ListNames, language: str | None) -> str:
    """The word a viewer sees for a line: theirs when the ingredient has one, else kept."""
    if language is None:
        return kept
    return names.get(kept, {}).get(language, kept)


def line_names(lines: Sequence[SavedLine]) -> dict[str, dict[str, str]]:
    """The stored words of a list's cart lines, by kept name (closed lists keep theirs)."""
    return {line.name: dict(line.names) for line in lines if line.names}


@dataclass(frozen=True, slots=True)
class SavedList:
    id: UUID
    kitchen_id: UUID
    # None while the list is active.
    closing_date: date | None
    created_at: datetime
    # Cart lines in list order, then hand items in the order they were added.
    items: tuple[SavedLine, ...]


def cart_lines(
    shopping_list: ShoppingList, names: ListNames | None = None
) -> tuple[SavedLine, ...]:
    """A built list as stored lines, keeping its order, each with its words (spec 043)."""
    words = names or {}

    def of(name: str) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(words.get(name, {}).items()))

    measured = tuple(
        SavedLine(
            "cart",
            "measured",
            ln.name,
            ln.kind,
            ln.size,
            ln.amounts,
            (),
            ln.recipes,
            names=of(ln.name),
        )
        for ln in shopping_list.lines
    )
    your_call = tuple(
        SavedLine("cart", "your_call", e.name, None, None, (), e.notes, e.recipes, names=of(e.name))
        for e in shopping_list.your_call
    )
    return measured + your_call


def _amount_map(amounts: Sequence[Amount]) -> dict[str, Decimal] | None:
    try:
        return {a.unit: Decimal(a.quantity) for a in amounts}
    except InvalidOperation:
        return None


def _not_grown(old: SavedLine, new: SavedLine) -> bool:
    if old.section == "your_call":
        return set(new.notes) == set(old.notes)
    before = _amount_map(old.amounts)
    after = _amount_map(new.amounts)
    if before is None or after is None:
        return False
    return all(unit in before and qty <= before[unit] for unit, qty in after.items())


def carry_bought(old: Sequence[SavedLine], new: Sequence[SavedLine]) -> tuple[SavedLine, ...]:
    """New cart lines, bought where an old bought line is the same and has not grown (070 R2).

    Same means the same section, name, kind and size. Grown means a unit was added or an amount
    is larger; a "Your call" line has no amounts and stays bought only with the same notes.
    """
    bought = {(line.section, line.name, line.kind, line.size): line for line in old if line.bought}
    result: list[SavedLine] = []
    for line in new:
        before = bought.get((line.section, line.name, line.kind, line.size))
        keep = before is not None and _not_grown(before, line)
        result.append(replace(line, bought=keep))
    return tuple(result)


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


def closing_date(sent: date | None, utc_today: date) -> date:
    """The member's local day, or the UTC day when none is sent.

    Every time zone is within a day of UTC, so anything further is refused (R7).
    """
    if sent is None:
        return utc_today
    if abs(sent - utc_today) > timedelta(days=1):
        raise ShoppingDateError()
    return sent


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
