"""Place rules (spec 070 FR-006 to FR-009, research R4 to R6)."""

from __future__ import annotations

import uuid

import pytest
from domain.errors import (
    IngredientNameInvalidError,
    PlaceLimitError,
    PlaceNameInvalidError,
    PlaceNameTakenError,
)
from domain.places import (
    DEFAULT_PLACE_KEYS,
    SUPERMARKET,
    PlaceRef,
    check_new_name,
    fold,
    ingredient_key,
    resolve_place,
)


def test_default_order() -> None:
    assert DEFAULT_PLACE_KEYS == (
        "supermarket",
        "farmers_market",
        "butcher",
        "fish_market",
        "bakery",
        "pharmacy",
        "other",
    )


@pytest.mark.parametrize("name", ["", "   ", "x" * 41, None, 3])
def test_invalid_names(name: object) -> None:
    with pytest.raises(PlaceNameInvalidError):
        check_new_name(name, [])


def test_length_edges_and_spaces() -> None:
    assert check_new_name("a", []) == "a"
    assert check_new_name("x" * 40, []) == "x" * 40
    assert check_new_name("  Asian   market ", []) == "Asian market"


@pytest.mark.parametrize("name", ["Supermercado", "SUPERMARKET", "carniceria", "Otro", "other"])
def test_default_names_refused_in_both_languages(name: str) -> None:
    with pytest.raises(PlaceNameTakenError):
        check_new_name(name, [])


def test_own_name_refused_ignoring_accents() -> None:
    with pytest.raises(PlaceNameTakenError):
        check_new_name("cafe", [fold("Café")])


def test_limit() -> None:
    assert check_new_name("Deli", [], count=29) == "Deli"
    with pytest.raises(PlaceLimitError):
        check_new_name("Deli", [], count=30)


def test_ingredient_key() -> None:
    assert ingredient_key("  Tomátes ") == "tomates"
    with pytest.raises(IngredientNameInvalidError):
        ingredient_key("   ")


def test_resolve_place() -> None:
    custom = PlaceRef(id=uuid.uuid4(), name="Asian market")
    choices = {"tomato": PlaceRef(key="farmers_market"), "miso": custom}
    assert resolve_place("Tomato", choices) == PlaceRef(key="farmers_market")
    assert resolve_place("miso", choices) == custom
    assert resolve_place("flour", choices) == SUPERMARKET
