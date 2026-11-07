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
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Protocol

from domain.errors import DomainError
from domain.ingredient_catalog import CatalogIndex, CatalogLike, as_language
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    InvalidDraftError,
    check_draft,
)

# Partial page mode results (spec 026), re-exported: they live in the domain for merge_parts.
from domain.recipe_page import DraftPart as DraftPart
from domain.recipe_page import NoRecipeContent as NoRecipeContent

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
    # The draft as the service gave it, so link capture can still open it in the form (spec 026).
    recipe: DraftRecipe | None = field(default=None, compare=False)


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


class ExtractionMode(StrEnum):
    """WHOLE: one whole recipe (text capture). PAGE_PART: one part of a web page (spec 026)."""

    WHOLE = "whole"
    PAGE_PART = "page_part"


ExtractionResult = (
    Draft
    | NotARecipe
    | DraftIncomplete
    | Unavailable
    | LimitReached
    | InvalidOutput
    | AIProviderError
    | DraftPart
    | NoRecipeContent
)


class RecipeExtractor(Protocol):
    """Port: one service call per text. Never raises for service, network or output problems.

    WHOLE mode never returns DraftPart or NoRecipeContent. `part` is (index from 1, total),
    given only in PAGE_PART mode.
    """

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
        *,
        mode: ExtractionMode = ExtractionMode.WHOLE,
        part: tuple[int, int] | None = None,
    ) -> ExtractionResult: ...


@dataclass(slots=True)
class _InFlight:
    done: threading.Event = field(default_factory=threading.Event)
    result: ExtractionResult | None = None
    error: BaseException | None = None


def _flight_key(
    text: str,
    ingredient_names: Sequence[str],
    available_units: Sequence[str],
    mode: ExtractionMode,
    part: tuple[int, int] | None,
) -> str:
    """Only calls judged by the same lists, mode and part may share a result (spec 055 R5)."""
    parts = json.dumps([text, sorted(ingredient_names), sorted(available_units), mode.value, part])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


def _all_names(catalog: CatalogLike) -> list[str]:
    """Every name the model may propose: kept and other names of an index (spec 043 R4)."""
    return catalog.all_names() if isinstance(catalog, CatalogIndex) else list(catalog)


class TextLanguage(Protocol):
    """The application's LanguageDetector port, named here so ports.py need not be imported."""

    def detect(self, text: str) -> str | None: ...


class RecipeExtraction:
    """Use case: text in, one checked ExtractionResult out.

    With `languages`, each draft (and each page part) gets the language of its text, found
    offline, never by the model (spec 043 FR-005a). Without it the draft has no language.
    """

    def __init__(
        self,
        extractor: RecipeExtractor,
        languages: TextLanguage | None = None,
    ) -> None:  # MVP-OUT: vocabulary: Vocabulary
        self._extractor = extractor
        self._languages = languages
        # MVP-OUT: self._vocabulary = vocabulary
        self._lock = threading.Lock()
        self._in_flight: dict[str, _InFlight] = {}

    def extract(
        self,
        text: str,
        ingredient_names: CatalogLike,
        timeout_s: float,
        available_units: Sequence[str] = (),
        *,
        mode: ExtractionMode = ExtractionMode.WHOLE,
        part: tuple[int, int] | None = None,
    ) -> ExtractionResult:
        trimmed = text.strip()
        if not trimmed:
            raise RecipeTextRefusedError(RecipeTextRefusedError.EMPTY)
        if len(trimmed) > MAX_TEXT_CHARS:
            raise RecipeTextRefusedError(RecipeTextRefusedError.TOO_LONG)

        key = _flight_key(trimmed, _all_names(ingredient_names), available_units, mode, part)
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
            flight.result = self._evaluate(
                trimmed, ingredient_names, timeout_s, available_units, mode, part
            )
        except BaseException as exc:
            flight.error = exc
            raise
        finally:
            with self._lock:
                self._in_flight.pop(key, None)
            flight.done.set()
        return flight.result

    def _language_of(self, text: str):  # noqa: ANN202
        assert self._languages is not None
        return as_language(self._languages.detect(text))

    def _evaluate(
        self,
        trimmed: str,
        ingredient_names: CatalogLike,
        timeout_s: float,
        available_units: Sequence[str],
        mode: ExtractionMode,
        part: tuple[int, int] | None,
    ) -> ExtractionResult:
        # The units stay here: they are compared in code and never reach the model (spec 055 R4).
        if mode is ExtractionMode.PAGE_PART:
            # A part may hold only steps or only lines: the merged draft is checked instead.
            part_result = self._extractor.extract(
                trimmed, _all_names(ingredient_names), timeout_s, mode=mode, part=part
            )
            if isinstance(part_result, DraftPart) and self._languages is not None:
                part_result = replace(part_result, language=self._language_of(trimmed))
            return part_result
        # Whole mode calls the port exactly as before spec 026.
        result = self._extractor.extract(trimmed, _all_names(ingredient_names), timeout_s)
        if not isinstance(result, Draft):
            return result
        if self._languages is not None:
            # Before matching: a line shows the name in the draft's language (FR-008).
            result = Draft(recipe=replace(result.recipe, language=self._language_of(trimmed)))
        try:
            recipe = check_draft(result.recipe, ingredient_names, available_units)
        except DraftProblems as exc:
            # Names and kinds only, never the ingredient name or title (constitution §4).
            logger.warning(
                "draft incomplete: missing=%s line_problems=%s",
                ",".join(exc.missing),
                ",".join(problem.kind.value for problem in exc.line_problems),
            )
            return DraftIncomplete(problems=exc, recipe=result.recipe)
        except InvalidDraftError as exc:
            # The rule that broke, by name only: no values and no text.
            logger.warning("draft rejected by a recipe rule: %s", exc.MESSAGE)
            return InvalidOutput()
        return Draft(recipe=recipe)
