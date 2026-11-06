"""Bought carried across a cart refresh (spec 070 FR-003, research R2)."""

from __future__ import annotations

from dataclasses import replace

from domain.cart import Amount
from domain.shopping_list import SavedLine, carry_bought


def _line(name: str, *amounts: tuple[str, str], size: str | None = None) -> SavedLine:
    return SavedLine(
        "cart",
        "measured",
        name,
        "mass",
        size,
        tuple(Amount(q, u) for q, u in amounts),
        (),
        (),
    )


def _vague(name: str, *notes: str) -> SavedLine:
    return SavedLine("cart", "your_call", name, None, None, (), notes, ())


def _bought(line: SavedLine) -> SavedLine:
    return replace(line, bought=True)


def test_unchanged_line_stays_bought() -> None:
    old = [_bought(_line("flour", ("500", "g")))]
    assert carry_bought(old, [_line("flour", ("500", "g"))])[0].bought


def test_smaller_amount_stays_bought() -> None:
    old = [_bought(_line("flour", ("500", "g")))]
    assert carry_bought(old, [_line("flour", ("250", "g"))])[0].bought


def test_amount_grew_resets() -> None:
    old = [_bought(_line("flour", ("500", "g")))]
    assert not carry_bought(old, [_line("flour", ("750", "g"))])[0].bought


def test_unit_added_resets() -> None:
    old = [_bought(_line("flour", ("500", "g")))]
    assert not carry_bought(old, [_line("flour", ("500", "g"), ("1", "cup"))])[0].bought


def test_size_changed_resets() -> None:
    old = [_bought(_line("onion", ("2", "unit"), size="large"))]
    assert not carry_bought(old, [_line("onion", ("2", "unit"), size="small")])[0].bought


def test_unbought_stays_unbought() -> None:
    old = [_line("flour", ("500", "g"))]
    assert not carry_bought(old, [_line("flour", ("500", "g"))])[0].bought


def test_new_line_is_not_bought() -> None:
    old = [_bought(_line("flour", ("500", "g")))]
    result = carry_bought(old, [_line("flour", ("500", "g")), _line("sugar", ("1", "kg"))])
    assert [r.bought for r in result] == [True, False]


def test_your_call_same_notes_kept() -> None:
    old = [_bought(_vague("salt", "a pinch"))]
    assert carry_bought(old, [_vague("salt", "a pinch")])[0].bought


def test_your_call_new_note_resets() -> None:
    old = [_bought(_vague("salt", "a pinch"))]
    assert not carry_bought(old, [_vague("salt", "a pinch", "to taste")])[0].bought
