"""Gemini translator adapter with a fake SDK client (spec 073, T015). No network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from adapters.llm.gemini_translator import GeminiIngredientTranslator
from domain.ingredient_translation import (
    IngredientTranslationRequest,
    TranslationQuotaExceeded,
    TranslationUnavailable,
    TranslationUnparseable,
)

REQUEST = IngredientTranslationRequest(name="onion", source_language="en", target_language="es")


class FakeModels:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


def translator(
    models: FakeModels, model: str = "fake-translate-model"
) -> GeminiIngredientTranslator:
    client = SimpleNamespace(models=models)
    return GeminiIngredientTranslator(api_key="k", model=model, timeout_s=5, client=client)


def test_valid_answer_becomes_a_result() -> None:
    models = FakeModels(text='{"valid": true, "translation": "cebolla"}')
    result = translator(models).translate(REQUEST)
    assert (result.valid, result.translation) == (True, "cebolla")


def test_invalid_answer_has_no_translation() -> None:
    models = FakeModels(text='{"valid": false, "translation": null}')
    result = translator(models).translate(REQUEST)
    assert (result.valid, result.translation) == (False, None)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        '{"valid": true}',
        '{"valid": "yes", "translation": "cebolla"}',
        '{"valid": true, "translation": ""}',
        '{"valid": true, "translation": "onion\\nsalt"}',
        '{"valid": false, "translation": "cebolla"}',
        'Here is the answer: {"valid": true, "translation": "cebolla"}',
    ],
)
def test_unexpected_shape_is_unparseable(text: str) -> None:
    with pytest.raises(TranslationUnparseable):
        translator(FakeModels(text=text)).translate(REQUEST)


@pytest.mark.parametrize(
    "error",
    [TimeoutError("slow"), ConnectionError("down"), RuntimeError("429 RESOURCE_EXHAUSTED quota")],
)
def test_timeout_network_and_quota_are_unavailable(error: Exception) -> None:
    with pytest.raises(TranslationUnavailable):
        translator(FakeModels(error=error)).translate(REQUEST)


class FakeApiError(Exception):
    def __init__(self, code: int, status: str) -> None:
        super().__init__("quota")
        self.code = code
        self.status = status


def test_a_429_is_quota_exceeded() -> None:
    with pytest.raises(TranslationQuotaExceeded):
        translator(FakeModels(error=FakeApiError(429, "RESOURCE_EXHAUSTED"))).translate(REQUEST)


def test_model_name_comes_from_settings() -> None:
    models = FakeModels(text='{"valid": false, "translation": null}')
    translator(models, model="settings-model").translate(REQUEST)
    assert models.calls[0]["model"] == "settings-model"


def test_only_the_name_and_languages_are_sent() -> None:
    models = FakeModels(text='{"valid": false, "translation": null}')
    translator(models).translate(REQUEST)
    assert models.calls[0]["contents"] == "<<<INGREDIENT_NAME\nonion\nINGREDIENT_NAME>>>"
