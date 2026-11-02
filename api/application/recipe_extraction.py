"""Recipe extraction: the result set, the RecipeExtractor port and the use case (FR-001 to FR-016).

The use case is the only caller of the port. It refuses empty or over-length
input before any call, applies the domain rules to any draft, and shares one
in-progress call between concurrent identical texts. Nothing is stored.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from domain.errors import DomainError
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    InvalidDraftError,
    check_draft,
)

logger = logging.getLogger(__name__)
MAX_TEXT_CHARS = 10_000


class RecipeTextRefusedError(DomainError):
    """Input refused before any call: empty or over the length limit. Not a service failure."""

    EMPTY = "Paste the recipe text first."
    TOO_LONG = "The text is longer than 10,000 characters. Paste one recipe at a time."

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class Draft:
    recipe: DraftRecipe


class NotRecipeReason(StrEnum):
    QUESTION_OR_REQUEST = "question_or_request"
    NOT_FOOD = "not_food"
    STORY_OR_ARTICLE = "story_or_article"
    MULTIPLE_RECIPES = "multiple_recipes"


@dataclass(frozen=True, slots=True)
class NotARecipe:
    reason: NotRecipeReason
    ingredient: str | None = None


@dataclass(frozen=True, slots=True)
class DraftIncomplete:
    problems: DraftProblems


@dataclass(frozen=True, slots=True)
class Unavailable:
    pass


@dataclass(frozen=True, slots=True)
class LimitReached:
    retry_after_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class InvalidOutput:
    pass


@dataclass(frozen=True, slots=True)
class AIProviderError:
    pass


ExtractionResult = (
    Draft
    | NotARecipe
    | DraftIncomplete
    | Unavailable
    | LimitReached
    | InvalidOutput
    | AIProviderError
)


class RecipeExtractor(Protocol):
    """Port: one service call per text. Never raises for service, network or output problems."""

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
    ) -> ExtractionResult: ...


@dataclass(slots=True)
class _InFlight:
    done: threading.Event = field(default_factory=threading.Event)
    result: ExtractionResult | None = None
    error: BaseException | None = None


def _flight_key(text: str, ingredient_names: Sequence[str], available_units: Sequence[str]) -> str:
    """Only calls judged by the same lists may share a result (spec 055 R5)."""
    parts = json.dumps([text, sorted(ingredient_names), sorted(available_units)])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


class RecipeExtraction:
    """Use case: text in, one checked ExtractionResult out."""

    def __init__(self, extractor: RecipeExtractor) -> None:  # MVP-OUT: vocabulary: Vocabulary
        self._extractor = extractor
        # MVP-OUT: self._vocabulary = vocabulary
        self._lock = threading.Lock()
        self._in_flight: dict[str, _InFlight] = {}

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
        available_units: Sequence[str] = (),
    ) -> ExtractionResult:
        trimmed = text.strip()
        if not trimmed:
            raise RecipeTextRefusedError(RecipeTextRefusedError.EMPTY)
        if len(trimmed) > MAX_TEXT_CHARS:
            raise RecipeTextRefusedError(RecipeTextRefusedError.TOO_LONG)

        key = _flight_key(trimmed, ingredient_names, available_units)
        with self._lock:
            flight = self._in_flight.get(key)
            owner = flight is None
            if flight is None:
                flight = _InFlight()
                self._in_flight[key] = flight

        if not owner:
            flight.done.wait()
            if flight.error is not None:
                raise flight.error
            assert flight.result is not None
            return flight.result

        try:
            flight.result = self._evaluate(trimmed, ingredient_names, timeout_s, available_units)
        except BaseException as exc:
            flight.error = exc
            raise
        finally:
            with self._lock:
                self._in_flight.pop(key, None)
            flight.done.set()
        return flight.result

    def _evaluate(
        self,
        trimmed: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
        available_units: Sequence[str],
    ) -> ExtractionResult:
        # The units stay here: they are compared in code and never reach the model (spec 055 R4).
        result = self._extractor.extract(trimmed, ingredient_names, timeout_s)
        if not isinstance(result, Draft):
            return result
        try:
            recipe = check_draft(result.recipe, ingredient_names, available_units)
        except DraftProblems as exc:
            # Names and kinds only, never the ingredient name or title (constitution §4).
            logger.warning(
                "draft incomplete: missing=%s line_problems=%s",
                ",".join(exc.missing),
                ",".join(problem.kind.value for problem in exc.line_problems),
            )
            return DraftIncomplete(problems=exc)
        except InvalidDraftError as exc:
            # The rule that broke, by name only: no values and no text.
            logger.warning("draft rejected by a recipe rule: %s", exc.MESSAGE)
            return InvalidOutput()
        return Draft(recipe=recipe)
