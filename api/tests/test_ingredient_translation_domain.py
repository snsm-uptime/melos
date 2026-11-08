"""Pure tests for ingredient translation rules (spec 073, T009 and T026). No database."""

from __future__ import annotations

import pytest
from domain.ingredient_translation import (
    MAX_TRANSLATION_LENGTH,
    IngredientTranslationResult,
    InvalidTranslationResult,
    MissingLanguageError,
    target_language,
)


def test_valid_result_keeps_its_translation() -> None:
    result = IngredientTranslationResult(valid=True, translation="cebolla")
    assert result.translation == "cebolla"


@pytest.mark.parametrize("translation", [None, "", "   ", " onion"])
def test_valid_result_needs_a_non_empty_trimmed_translation(translation: str | None) -> None:
    with pytest.raises(InvalidTranslationResult):
        IngredientTranslationResult(valid=True, translation=translation)


def test_valid_result_allows_exactly_80_characters() -> None:
    IngredientTranslationResult(valid=True, translation="x" * MAX_TRANSLATION_LENGTH)


def test_valid_result_rejects_81_characters() -> None:
    with pytest.raises(InvalidTranslationResult):
        IngredientTranslationResult(valid=True, translation="x" * (MAX_TRANSLATION_LENGTH + 1))


@pytest.mark.parametrize("translation", ["onion\nsalt", "onion\rsalt"])
def test_valid_result_rejects_a_newline(translation: str) -> None:
    with pytest.raises(InvalidTranslationResult):
        IngredientTranslationResult(valid=True, translation=translation)


def test_invalid_result_has_no_translation() -> None:
    assert IngredientTranslationResult(valid=False, translation=None).translation is None
    with pytest.raises(InvalidTranslationResult):
        IngredientTranslationResult(valid=False, translation="onion")


@pytest.mark.parametrize(("source", "target"), [("en", "es"), ("es", "en")])
def test_target_is_the_other_supported_language(source: str, target: str) -> None:
    assert target_language(source) == target  # type: ignore[arg-type]


def test_missing_language_has_no_target() -> None:
    with pytest.raises(MissingLanguageError):
        target_language(None)
