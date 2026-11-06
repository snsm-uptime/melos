"""Stand-in RecipeExtractor for tests and S-016 development. No network access (FR-010)."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from application.recipe_extraction import Draft, ExtractionMode, ExtractionResult


@dataclass(frozen=True, slots=True)
class ExtractionCall:
    text: str
    ingredient_names: tuple[str, ...]
    timeout_s: float
    mode: ExtractionMode = ExtractionMode.WHOLE
    part: tuple[int, int] | None = None


@dataclass(slots=True)
class FakeRecipeExtractor:
    """Returns one fixed result, or the given results in order, and records every call.

    A single result is returned for every call. A list or tuple is consumed
    in order; once it runs out, the last result repeats. A draft with no language gets
    `language` (spec 043), 'en' unless told otherwise.
    """

    script: ExtractionResult | Sequence[ExtractionResult]
    language: str | None = "en"
    calls: list[ExtractionCall] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _index: int = 0

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
        *,
        mode: ExtractionMode = ExtractionMode.WHOLE,
        part: tuple[int, int] | None = None,
    ) -> ExtractionResult:
        with self._lock:
            self.calls.append(ExtractionCall(text, tuple(ingredient_names), timeout_s, mode, part))
            if isinstance(self.script, (list, tuple)):
                result = self.script[min(self._index, len(self.script) - 1)]
                self._index += 1
            else:
                result = self.script
        return self._with_language(result)

    def _with_language(self, result: ExtractionResult) -> ExtractionResult:
        if isinstance(result, Draft) and result.recipe.language is None and self.language:
            return Draft(recipe=replace(result.recipe, language=self.language))  # type: ignore[arg-type]
        return result
