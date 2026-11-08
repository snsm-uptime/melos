"""Stand-in RecipeExtractor for tests and S-016 development. No network access (FR-010)."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, field

from application.ports import Picture
from application.recipe_extraction import ExtractionMode, ExtractionResult


@dataclass(frozen=True, slots=True)
class ExtractionCall:
    text: str
    ingredient_names: tuple[str, ...]
    timeout_s: float
    mode: ExtractionMode = ExtractionMode.WHOLE
    part: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class PictureCall:
    """One picture call. Records the media type and byte count, never the bytes."""

    media_type: str
    byte_count: int
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
    picture_calls: list[PictureCall] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _index: int = 0

    def extract_picture(
        self,
        picture: Picture,
        ingredient_names: Sequence[str],
        timeout_s: float,
    ) -> ExtractionResult:
        with self._lock:
            self.picture_calls.append(
                PictureCall(
                    picture.media_type,
                    len(picture.data),
                    tuple(ingredient_names),
                    timeout_s,
                )
            )
            return self._next_result()

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
            return self._next_result()

    def _next_result(self) -> ExtractionResult:
        """The next scripted result; the caller holds the lock."""
        if isinstance(self.script, (list, tuple)):
            result = self.script[min(self._index, len(self.script) - 1)]
            self._index += 1
            return result
        return self.script
