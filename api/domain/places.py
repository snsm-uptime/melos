"""Places to buy things (spec 070): default places, name rules and the place of a name.

Default places are code constants: the api sends their keys and the ui names them (research R4).
A person's custom places and their choice per ingredient name are stored by the adapters.
Pure: no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from domain.errors import (
    IngredientNameInvalidError,
    PlaceLimitError,
    PlaceNameInvalidError,
    PlaceNameTakenError,
)
from domain.ingredient_catalog import normalize_name

DefaultKey = Literal[
    "supermarket", "farmers_market", "butcher", "fish_market", "bakery", "pharmacy", "other"
]

# The order tabs are shown in (research R9).
DEFAULT_PLACE_KEYS: tuple[DefaultKey, ...] = (
    "supermarket",
    "farmers_market",
    "butcher",
    "fish_market",
    "bakery",
    "pharmacy",
    "other",
)
FALLBACK: DefaultKey = "supermarket"

NAME_MAX = 40
PLACE_LIMIT = 30

# English and Spanish names of the defaults, only to refuse a custom place that repeats one.
# The ui holds the names it shows (ui/lib/i18n/places.ts).
_DEFAULT_NAMES: Mapping[DefaultKey, tuple[str, ...]] = {
    "supermarket": ("Supermarket", "Supermercado"),
    "farmers_market": ("Farmers market", "Mercado de agricultores"),
    "butcher": ("Butcher", "Carnicería"),
    "fish_market": ("Fish market", "Pescadería"),
    "bakery": ("Bakery", "Panadería"),
    "pharmacy": ("Pharmacy or drugstore", "Farmacia o droguería"),
    "other": ("Other", "Otro"),
}

_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class PlaceRef:
    """A default place (key set) or a custom place (id and name set)."""

    key: DefaultKey | None = None
    id: UUID | None = None
    name: str | None = None

    @property
    def is_default(self) -> bool:
        return self.key is not None


SUPERMARKET = PlaceRef(key=FALLBACK)


@dataclass(frozen=True, slots=True)
class CustomPlace:
    id: UUID
    name: str


def fold(name: str) -> str:
    """The form two place names are compared in: lower case, no accents, single spaces."""
    return normalize_name(name)


def clean_place_name(name: object) -> str:
    """Trimmed, spaces collapsed; 1 to 40 characters or PlaceNameInvalidError."""
    if not isinstance(name, str):
        raise PlaceNameInvalidError()
    clean = _SPACES.sub(" ", name).strip()
    if not clean or len(clean) > NAME_MAX:
        raise PlaceNameInvalidError()
    return clean


_DEFAULT_FOLDED = frozenset(fold(n) for names in _DEFAULT_NAMES.values() for n in names)


def check_new_name(name: object, own_keys: Iterable[str], count: int | None = None) -> str:
    """A clean name for a new or renamed place; `count` is the person's places before an add.

    Refuses a name equal to a default place in English or Spanish, or to one of `own_keys`
    (folded names of the person's other places), ignoring case and accents.
    """
    clean = clean_place_name(name)
    key = fold(clean)
    if key in _DEFAULT_FOLDED or key in set(own_keys):
        raise PlaceNameTakenError()
    if count is not None and count >= PLACE_LIMIT:
        raise PlaceLimitError()
    return clean


def ingredient_key(name: object) -> str:
    """The stored form of an ingredient name; IngredientNameInvalidError when empty."""
    if not isinstance(name, str):
        raise IngredientNameInvalidError()
    key = normalize_name(name)
    if not key:
        raise IngredientNameInvalidError()
    return key


def resolve_place(name: str, choices: Mapping[str, PlaceRef]) -> PlaceRef:
    """The person's place for an ingredient name, Supermarket when they chose none (FR-008)."""
    return choices.get(normalize_name(name), SUPERMARKET)
