"""Stand-in RecipeExtractor for tests and S-016 development. No network access (FR-010)."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, field

from application.recipe_extraction import ExtractionResult


@dataclass(frozen=True, slots=True)
class ExtractionCall:
    text: str
    ingredient_names: tuple[str, ...]
    timeout_s: float


@dataclass(slots=True)
class FakeRecipeExtractor:
    """Returns one fixed result, or the given results in order, and records every call.

    A single result is returned for every call. A list or tuple is consumed
    in order; once it runs out, the last result repeats.
    """

    script: ExtractionResult | Sequence[ExtractionResult]
    calls: list[ExtractionCall] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _index: int = 0

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
    ) -> ExtractionResult:
        with self._lock:
            self.calls.append(ExtractionCall(text, tuple(ingredient_names), timeout_s))
            if isinstance(self.script, (list, tuple)):
                result = self.script[min(self._index, len(self.script) - 1)]
                self._index += 1
                return result
            return self.script
