"""Cart rules (spec 022): the people default, the scale factor and the edit-lock idle limit.

Pure: no I/O, no FastAPI, no SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from domain.errors import CartValueError

PEOPLE_MIN = MEALS_MIN = 1
PEOPLE_MAX = MEALS_MAX = 99

# A lock ends this long after its holder's last activity (research R10).
LOCK_IDLE = timedelta(minutes=5)
# The ui warns this long before the idle limit.
LOCK_WARN = timedelta(minutes=1)


def effective_people(saved: int | None, member_count: int) -> int:
    """The saved people number, or the kitchen's member count while none is saved (FR-002)."""
    if saved is not None:
        return saved
    return min(max(member_count, PEOPLE_MIN), PEOPLE_MAX)


def scale_factor(people: int, meals: int, base_servings: int) -> Fraction:
    """people × meals / base servings, exact."""
    return Fraction(people * meals, base_servings)


def format_factor(value: Fraction) -> str:
    """Half-up to 2 decimals, trailing zeros removed: 3/2 → "1.5", 2/3 → "0.67", 2 → "2"."""
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    text = str(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return text.rstrip("0").rstrip(".") if "." in text else text


def check_count(value: object, field: str) -> int:
    """A whole number from 1 to 99, else CartValueError(field). A bool is not a number here."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise CartValueError(field)
    if not PEOPLE_MIN <= value <= PEOPLE_MAX:
        raise CartValueError(field)
    return value


def lock_is_idle(last_active_at: datetime, now: datetime) -> bool:
    """Whether a lock has gone LOCK_IDLE without activity, so it no longer counts."""
    return now - last_active_at >= LOCK_IDLE


def idle_expires_at(last_active_at: datetime) -> datetime:
    return last_active_at + LOCK_IDLE
