"""Cart rules (spec 022): the servings range, the scale factor and the edit-lock idle limit.
The shopping list built from a cart (spec 023) lives here too.

Pure: no I/O, no FastAPI, no SQLAlchemy.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Literal
from uuid import UUID

from domain.errors import CartValueError

SERVINGS_MIN = 1
SERVINGS_MAX = 99

# A lock ends this long after its holder's last activity (research R10).
LOCK_IDLE = timedelta(minutes=5)
# The ui warns this long before the idle limit.
LOCK_WARN = timedelta(minutes=1)


def scale_factor(servings: int, base_servings: int) -> Fraction:
    """servings / base servings, exact."""
    return Fraction(servings, base_servings)


def format_factor(value: Fraction) -> str:
    """Half-up to 2 decimals, trailing zeros removed: 3/2 → "1.5", 2/3 → "0.67", 2 → "2"."""
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    text = str(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return text.rstrip("0").rstrip(".") if "." in text else text


def check_count(value: object, field: str) -> int:
    """A whole number from 1 to 99, else CartValueError(field). A bool is not a number here."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise CartValueError(field)
    if not SERVINGS_MIN <= value <= SERVINGS_MAX:
        raise CartValueError(field)
    return value


def lock_is_idle(last_active_at: datetime, now: datetime) -> bool:
    """Whether a lock has gone LOCK_IDLE without activity, so it no longer counts."""
    return now - last_active_at >= LOCK_IDLE


def idle_expires_at(last_active_at: datetime) -> datetime:
    return last_active_at + LOCK_IDLE


# --- Shopping list (spec 023) ---------------------------------------------------------------

# Display order is largest first (PRD 1.6). The kind of a measure comes from its unit.
MASS_UNITS = ("kg", "lb", "oz", "g")
VOLUME_UNITS = ("l", "cup", "tbsp", "tsp", "ml")
COUNT_UNIT = "unit"
SIZE_ORDER = ("large", "medium", "small")

Kind = Literal["mass", "volume", "count"]
_KIND_RANK: dict[Kind, int] = {"mass": 0, "volume": 1, "count": 2}


def unit_kind(unit: str) -> Kind:
    """mass, volume or count for one of the ten allowed units, else ValueError."""
    if unit in MASS_UNITS:
        return "mass"
    if unit in VOLUME_UNITS:
        return "volume"
    if unit == COUNT_UNIT:
        return "count"
    raise ValueError(f"unknown unit: {unit}")


def name_sort_key(name: str) -> tuple[str, str]:
    """Order names ignoring accents and letter case; the stored name breaks ties (FR-010)."""
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    )
    return stripped.casefold(), name


@dataclass(frozen=True, slots=True)
class ShoppingLine:
    """One ingredient line of a cart recipe. Preparation is not part of it (FR-004)."""

    name: str
    quantity: Fraction | None
    unit: str | None
    size: str | None
    vague_note: str | None


@dataclass(frozen=True, slots=True)
class ScaledRecipe:
    """A cart recipe with its exact scale factor, in cart order."""

    recipe_id: UUID
    title: str
    factor: Fraction
    lines: tuple[ShoppingLine, ...]


@dataclass(frozen=True, slots=True)
class RecipeRef:
    recipe_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class Amount:
    quantity: str
    unit: str


@dataclass(frozen=True, slots=True)
class MeasuredLine:
    name: str
    kind: Kind
    # Counts only.
    size: str | None
    # Largest unit first; one entry for a count.
    amounts: tuple[Amount, ...]
    recipes: tuple[RecipeRef, ...]


@dataclass(frozen=True, slots=True)
class YourCallEntry:
    name: str
    notes: tuple[str, ...]
    recipes: tuple[RecipeRef, ...]


@dataclass(frozen=True, slots=True)
class ShoppingList:
    lines: tuple[MeasuredLine, ...]
    your_call: tuple[YourCallEntry, ...]


def _size_rank(size: str | None) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)


def _measured_lines(recipes: Sequence[ScaledRecipe]) -> tuple[MeasuredLine, ...]:
    """Scale, group by (name, kind) and for counts also size, sum per unit, then round counts up."""
    totals: dict[tuple[str, Kind, str | None], dict[str, Fraction]] = {}
    sources: dict[tuple[str, Kind, str | None], dict[UUID, RecipeRef]] = {}
    for recipe in recipes:
        ref = RecipeRef(recipe.recipe_id, recipe.title)
        for ln in recipe.lines:
            if ln.vague_note is not None or ln.quantity is None or ln.unit is None:
                continue
            try:
                kind = unit_kind(ln.unit)
            except ValueError:
                # The table check allows ten units only; never guess a kind for another.
                continue
            key = (ln.name, kind, ln.size if kind == "count" else None)
            per_unit = totals.setdefault(key, {})
            per_unit[ln.unit] = per_unit.get(ln.unit, Fraction(0)) + ln.quantity * recipe.factor
            sources.setdefault(key, {})[recipe.recipe_id] = ref

    lines: list[MeasuredLine] = []
    for key, per_unit in totals.items():
        name, kind, size = key
        if kind == "count":
            amounts = (Amount(str(math.ceil(per_unit[COUNT_UNIT])), COUNT_UNIT),)
        else:
            order = MASS_UNITS if kind == "mass" else VOLUME_UNITS
            amounts = tuple(Amount(format_factor(per_unit[u]), u) for u in order if u in per_unit)
        lines.append(MeasuredLine(name, kind, size, amounts, tuple(sources[key].values())))
    lines.sort(key=lambda ln: (name_sort_key(ln.name), _KIND_RANK[ln.kind], _size_rank(ln.size)))
    return tuple(lines)


def _your_call(recipes: Sequence[ScaledRecipe]) -> tuple[YourCallEntry, ...]:
    """One entry per ingredient name with every distinct vague note, never scaled (FR-007).

    Notes are compared after trimming and ignoring letter case; the first spelling is shown.
    """
    notes: dict[str, dict[str, str]] = {}
    sources: dict[str, dict[UUID, RecipeRef]] = {}
    for recipe in recipes:
        ref = RecipeRef(recipe.recipe_id, recipe.title)
        for ln in recipe.lines:
            if ln.vague_note is None:
                continue
            shown = ln.vague_note.strip()
            notes.setdefault(ln.name, {}).setdefault(shown.casefold(), shown)
            sources.setdefault(ln.name, {})[recipe.recipe_id] = ref
    entries = [
        YourCallEntry(name, tuple(found.values()), tuple(sources[name].values()))
        for name, found in notes.items()
    ]
    entries.sort(key=lambda entry: name_sort_key(entry.name))
    return tuple(entries)


def build_shopping_list(recipes: Sequence[ScaledRecipe]) -> ShoppingList:
    """The consolidated list for a cart, recipes in cart order (spec 023, PRD J5).

    Each measured line is scaled by its recipe's exact factor with no rounding before the sums.
    No unit is ever converted or carried over: `1 cup + 20 tbsp` stays as is. Vague lines go to
    `your_call`, and an ingredient that is vague in one recipe and measured in another is in both.
    """
    return ShoppingList(lines=_measured_lines(recipes), your_call=_your_call(recipes))
