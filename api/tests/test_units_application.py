"""Available units, the keep rule and removal, against a fake repository (spec 055)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from application.units import allowed_for_save, available_units, kept_units_to_add
from domain.recipe_draft import ALLOWED_UNITS, IngredientLine


class FakeUnits:
    def __init__(self, extras: Sequence[str] = ()) -> None:
        self.extras = list(extras)
        self.added: list[tuple[list[str], UUID]] = []

    def extras_for(self, user_id: UUID) -> list[str]:
        return list(self.extras)

    def add_user(self, names: Sequence[str], user_id: UUID) -> None:
        self.added.append((list(names), user_id))


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
