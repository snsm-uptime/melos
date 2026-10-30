"""Cart rules (spec 022, domain/cart.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from fractions import Fraction

import pytest
from domain.cart import (
    check_count,
    format_factor,
    idle_expires_at,
    lock_is_idle,
    scale_factor,
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
