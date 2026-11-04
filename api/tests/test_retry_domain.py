"""The shared retry rule for background jobs (spec 019 FR-009, FR-009a)."""

from __future__ import annotations

import pytest
from domain.retry import RetryPolicy, next_wait


def test_waits_grow_by_half_from_one_minute() -> None:
    waits: list[float] = []
    previous: float | None = None
    for _ in range(4):
        previous = next_wait(previous)
        waits.append(previous)
    assert waits == [60.0, 90.0, 135.0, 202.5]


def test_waits_never_pass_two_hours() -> None:
    previous: float | None = None
    for _ in range(40):
        previous = next_wait(previous)
        assert previous <= 7200.0
    assert previous == 7200.0
    assert next_wait(7200.0) == 7200.0


def test_a_longer_service_wait_wins() -> None:
    assert next_wait(None, service_wait_s=300) == 300.0
    assert next_wait(60.0, service_wait_s=600) == 600.0


def test_a_shorter_service_wait_does_not() -> None:
    assert next_wait(None, service_wait_s=5) == 60.0
    assert next_wait(60.0, service_wait_s=30) == 90.0


def test_custom_policy_is_respected() -> None:
    policy = RetryPolicy(first_s=10, growth=2, cap_s=35)
    assert next_wait(None, policy) == 10
    assert next_wait(10, policy) == 20
    assert next_wait(20, policy) == 35
    assert next_wait(35, policy) == 35


@pytest.mark.parametrize(
    "kwargs",
    [
        {"growth": 1.0},
        {"growth": 0.5},
        {"first_s": 120, "cap_s": 60},
        {"first_s": 0},
    ],
)
def test_invalid_policies_are_refused(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        RetryPolicy(**kwargs)
