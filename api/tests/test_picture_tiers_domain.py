"""Picture tiers, encoding ladder and size caps (spec 041, FR-025, FR-026, research R5)."""

from __future__ import annotations

from datetime import date

import pytest
from domain.picture_tiers import (
    CalibrationTable,
    EncodingStep,
    Tier,
    cap_bytes,
    choose_tier,
    plan_encoding,
    require_calibrated,
)

# KB are read as 1000 bytes, as the contract says.
KB = 1_000


def _table(status: str = "calibrated", low: float = 100.0, high: float = 500.0) -> CalibrationTable:
    return CalibrationTable(
        low=low,
        high=high,
        labelled_set="test-set",
        calibrated_on=date(2026, 11, 7),
        status=status,  # type: ignore[arg-type]
    )


def test_handwritten_is_tier_3_whatever_the_sharpness() -> None:
    assert choose_tier(handwritten=True, sharpness=None, table=_table()) is Tier.TIER_3
    assert choose_tier(handwritten=True, sharpness=9_999.0, table=_table()) is Tier.TIER_3


def test_printed_without_a_sharpness_is_an_error() -> None:
    with pytest.raises(ValueError):
        choose_tier(handwritten=False, sharpness=None, table=_table())


def test_printed_sharpness_picks_the_tier_by_the_thresholds() -> None:
    table = _table(low=100.0, high=500.0)
    assert choose_tier(False, 99.9, table) is Tier.TIER_3
    assert choose_tier(False, 100.0, table) is Tier.TIER_2
    assert choose_tier(False, 300.0, table) is Tier.TIER_2
    assert choose_tier(False, 499.9, table) is Tier.TIER_2
    assert choose_tier(False, 500.0, table) is Tier.TIER_1


def test_tier_1_ladder_is_exact() -> None:
    assert plan_encoding(Tier.TIER_1) == (
        EncodingStep(70, 1600),
        EncodingStep(65, 1600),
        EncodingStep(60, 1600),
        EncodingStep(60, 1440),
        EncodingStep(60, 1296),
        EncodingStep(60, 1166),
        EncodingStep(60, 1049),
        EncodingStep(60, 1000),
    )


def test_tier_3_ladder_starts_high_and_ends_at_the_floor() -> None:
    steps = plan_encoding(Tier.TIER_3)
    assert steps[0] == EncodingStep(90, 2400)
    assert steps[-1] == EncodingStep(60, 1200)
    assert [step.quality for step in steps[:7]] == [90, 85, 80, 75, 70, 65, 60]


def test_tier_2_ladder_ends_at_the_floor() -> None:
    steps = plan_encoding(Tier.TIER_2)
    assert steps[0] == EncodingStep(80, 2000)
    assert steps[-1] == EncodingStep(60, 1000)


@pytest.mark.parametrize("tier", list(Tier))
def test_ladder_never_grows(tier: Tier) -> None:
    steps = plan_encoding(tier)
    qualities = [step.quality for step in steps]
    sides = [step.max_side for step in steps]
    assert qualities == sorted(qualities, reverse=True)
    assert sides == sorted(sides, reverse=True)


def test_caps() -> None:
    assert cap_bytes(Tier.TIER_3) == 500 * KB
    assert cap_bytes(Tier.TIER_1) == 300 * KB
    assert cap_bytes(Tier.TIER_2) == 300 * KB


def test_require_calibrated_refuses_provisional() -> None:
    with pytest.raises(ValueError):
        require_calibrated(_table(status="provisional"))


def test_require_calibrated_accepts_calibrated() -> None:
    require_calibrated(_table(status="calibrated"))
