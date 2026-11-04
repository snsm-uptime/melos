"""The retry rule for background jobs (spec 019 FR-009, FR-009a).

The default for every background job of the app that may fail and try again later: retry
forever; the first wait is `first_s`, each next wait is the last one times `growth`, up to
`cap_s`; a longer wait asked by the service ("retry after") wins. A job keeps its own last wait,
and a success forgets it, so the next failure starts from `first_s` again.

Pure: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    first_s: float = 60.0
    growth: float = 1.5
    cap_s: float = 7200.0

    def __post_init__(self) -> None:
        if self.first_s <= 0:
            raise ValueError(f"first wait must be > 0, got {self.first_s}")
        if self.growth <= 1:
            raise ValueError(f"growth must be > 1, got {self.growth}")
        if self.cap_s < self.first_s:
            raise ValueError(f"cap {self.cap_s} is below the first wait {self.first_s}")


DEFAULT_POLICY = RetryPolicy()


def next_wait(
    previous_s: float | None,
    policy: RetryPolicy = DEFAULT_POLICY,
    service_wait_s: float | None = None,
) -> float:
    """Seconds to wait after a failure, given the wait used after the previous one (or None)."""
    if previous_s is None or previous_s <= 0:
        wait = policy.first_s
    else:
        wait = min(previous_s * policy.growth, policy.cap_s)
    if service_wait_s is not None and service_wait_s > wait:
        return float(service_wait_s)
    return wait
