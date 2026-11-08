"""Picture tiers and the encoding ladder (spec 041, FR-025, FR-026, research R5).

Pure: no I/O. The calibration table is passed in; loading it is the adapter's job.
Sizes are integer pixels; the ladder uses integer arithmetic so it is exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal


class Tier(StrEnum):
    TIER_1 = "tier_1"  # aggressive: max side 1600, quality 70, cap 300 KB
    TIER_2 = "tier_2"  # balanced:   max side 2000, quality 80, cap 300 KB
    TIER_3 = "tier_3"  # high:       max side 2400, quality 90, cap 500 KB


@dataclass(frozen=True, slots=True)
class CalibrationTable:
    """Sharpness thresholds for printed pictures. `provisional` is not for release."""

    low: float
    high: float
    labelled_set: str
    calibrated_on: date
    status: Literal["provisional", "calibrated"]


@dataclass(frozen=True, slots=True)
class EncodingStep:
    quality: int
    max_side: int


_START = {
    Tier.TIER_1: (1600, 70),
    Tier.TIER_2: (2000, 80),
    Tier.TIER_3: (2400, 90),
}
_FLOOR_SIDE = {
    Tier.TIER_1: 1000,
    Tier.TIER_2: 1000,
    Tier.TIER_3: 1200,
}
_FLOOR_QUALITY = 60
_QUALITY_STEP = 5
_CAPS = {
    Tier.TIER_1: 300_000,
    Tier.TIER_2: 300_000,
    Tier.TIER_3: 500_000,
}


def choose_tier(handwritten: bool, sharpness: float | None, table: CalibrationTable) -> Tier:
    """Handwritten is always Tier 3 (FR-025). Printed pictures follow the sharpness."""
    if handwritten:
        return Tier.TIER_3
    if sharpness is None:
        raise ValueError("a printed picture needs a sharpness to choose its tier")
    if sharpness < table.low:
        return Tier.TIER_3
    if sharpness >= table.high:
        return Tier.TIER_1
    return Tier.TIER_2


def plan_encoding(tier: Tier) -> tuple[EncodingStep, ...]:
    """Quality steps down at the starting side, then the side shrinks by 10% to the floor."""
    start_side, start_quality = _START[tier]
    steps = [
        EncodingStep(quality, start_side)
        for quality in range(start_quality, _FLOOR_QUALITY - 1, -_QUALITY_STEP)
    ]
    floor = _FLOOR_SIDE[tier]
    side = start_side
    while side > floor:
        side = max(floor, side * 9 // 10)
        steps.append(EncodingStep(_FLOOR_QUALITY, side))
    return tuple(steps)


def cap_bytes(tier: Tier) -> int:
    return _CAPS[tier]


def require_calibrated(table: CalibrationTable) -> None:
    """The release check: a provisional table is refused."""
    if table.status != "calibrated":
        raise ValueError("picture tiers are provisional; calibrate before release")
