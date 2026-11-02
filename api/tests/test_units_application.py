"""Available units, the keep rule and removal, against a fake repository (spec 055)."""

from __future__ import annotations

from uuid import uuid4

from application.units import (
    RemoveUserFromUnitsCommand,
    RemoveUserFromUnitsService,
    allowed_for_save,
    available_units,
    kept_units_to_add,
)
from domain.recipe_draft import ALLOWED_UNITS, IngredientLine
from tests.unit_fakes import FakeUnits


def line(unit: str | None) -> IngredientLine:
    return IngredientLine(name="frijoles", vague=False, quantity=1.0, unit=unit)


def test_available_units_are_the_ten_in_order_then_the_rest_sorted() -> None:
    assert available_units(["sobre", "lata"]) == (*ALLOWED_UNITS, "lata", "sobre")


def test_a_kept_word_a_line_uses_joins() -> None:
    assert kept_units_to_add(["Latas"], [line("lata")], available_units([])) == ("lata",)


def test_a_kept_word_no_line_uses_is_ignored() -> None:
    assert kept_units_to_add(["lata"], [line("g")], available_units([])) == ()


def test_a_kept_word_already_covered_is_ignored() -> None:
    assert kept_units_to_add(["lata"], [line("lata")], available_units(["lata"])) == ()
    assert kept_units_to_add(["tazas"], [line("cup")], available_units([])) == ()


def test_a_kept_word_that_cannot_be_offered_is_ignored() -> None:
    assert kept_units_to_add(["<b>"], [line("<b>")], available_units([])) == ()


def test_a_kept_word_counts_once() -> None:
    assert kept_units_to_add(["lata", "Latas"], [line("lata")], available_units([])) == ("lata",)


def test_allowed_for_save_adds_only_offerable_kept_words() -> None:
    assert allowed_for_save(available_units([]), ["Latas", "<b>"]) == (*ALLOWED_UNITS, "lata")


def test_removal_asks_the_repository_for_the_person_and_nothing_else() -> None:
    units = FakeUnits()
    person = uuid4()
    RemoveUserFromUnitsService(units).execute(RemoveUserFromUnitsCommand(person))
    assert units.removed == [person]
    assert units.added == []
