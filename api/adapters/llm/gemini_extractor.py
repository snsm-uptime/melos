"""Gemini adapter for the RecipeExtractor port (google-genai).

One attempt per call (SDK retries are switched off). Every SDK or transport
error is mapped to a result class here, and no exception text, key or service
body leaves this module (FR-003 to FR-005, FR-009, FR-014, SC-006).
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Sequence
from typing import Any, Literal

import httpx
from application.recipe_extraction import (
    ONE_RECIPE_REASON,
    AIProviderError,
    Draft,
    ExtractionResult,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    Unavailable,
)
from domain.recipe_draft import DraftRecipe, IngredientLine, Vocabulary
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from pydantic import BaseModel, ValidationError

from adapters.llm.prompt import build_contents, system_instruction

logger = logging.getLogger(__name__)

MAX_REASON_CHARS = 120
RETRY_DELAY_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*s?\s*$")

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["recipe", "not_a_recipe", "multiple_recipes"]},
        "reason": {"type": "string"},
        "recipe": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "base_servings": {"type": "integer"},
                "main_ingredients": {"type": "array", "items": {"type": "string"}},
                "ingredient_lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "vague": {"type": "boolean"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string"},
                            "size": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["name", "vague"],
                    },
                },
                "steps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "ingredient_lines", "steps"],
        },
    },
    "required": ["outcome"],
}


class _LinePayload(BaseModel):
    name: str
    vague: bool
    quantity: float | None = None
    unit: str | None = None
    size: str | None = None
    note: str | None = None


class _RecipePayload(BaseModel):
    title: str
    base_servings: int | None = None
    main_ingredients: list[str] = []
    ingredient_lines: list[_LinePayload]
    steps: list[str]


class _ExtractionPayload(BaseModel):
    outcome: Literal["recipe", "not_a_recipe", "multiple_recipes"]
    reason: str | None = None
    recipe: _RecipePayload | None = None


def _payload_to_result(payload: _ExtractionPayload) -> ExtractionResult:
    if payload.outcome == "multiple_recipes":
        return NotARecipe(reason=ONE_RECIPE_REASON)
    if payload.outcome == "not_a_recipe":
        reason = (payload.reason or "").strip()
        if not reason or len(reason) > MAX_REASON_CHARS or "\n" in reason:
            return InvalidOutput()
        return NotARecipe(reason=reason)
    if payload.recipe is None:
        return InvalidOutput()

    recipe = payload.recipe
    return Draft(
        recipe=DraftRecipe(
            title=recipe.title,
            base_servings=recipe.base_servings,
            servings_estimated=False,
            main_ingredients=tuple(recipe.main_ingredients),
            cuisines=(),
            ingredient_lines=tuple(
                IngredientLine(
                    name=line.name,
                    vague=line.vague,
                    quantity=line.quantity,
                    unit=line.unit,
                    size=line.size,
                    note=line.note,
                )
                for line in recipe.ingredient_lines
            ),
            steps=tuple(recipe.steps),
        )
    )


def _find_retry_delay(node: object) -> str | None:
    """Look for a RetryInfo `retryDelay` value (for example "30s") anywhere in error details."""
    if isinstance(node, dict):
        if isinstance(node.get("retryDelay"), str):
            return node["retryDelay"]
        for value in node.values():
            found = _find_retry_delay(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_retry_delay(value)
            if found is not None:
                return found
    return None


def _retry_after_seconds(exc: APIError) -> int | None:
    """Whole seconds from the Retry-After header or RetryInfo; None when absent or not positive."""
    raw: str | None = None
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers is not None:
        raw = headers.get("retry-after")
    if raw is None:
        raw = _find_retry_delay(getattr(exc, "details", None))
    if raw is None:
        return None
    match = RETRY_DELAY_PATTERN.match(raw)
    if match is None:
        return None
    seconds = float(match.group(1))
    if not math.isfinite(seconds) or seconds <= 0:
        return None
    return round(seconds)


class GeminiRecipeExtractor:
    """Production RecipeExtractor. The key and model come from settings only (FR-009)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        vocabulary: Vocabulary,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._system_instruction = system_instruction(vocabulary)
        self._client = client

    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
    ) -> ExtractionResult:
        if not self._api_key.strip() or not self._model.strip():
            logger.error("recipe extraction not configured: class=AIProviderError")
            return AIProviderError()

        request_ref = str(uuid.uuid4())
        try:
            response = self._client_or_default().models.generate_content(
                model=self._model,
                contents=build_contents(text, ingredient_names),
                config=self._config(timeout_s),
            )
        except Exception as exc:
            result = self._classify(exc)
            logger.warning(
                "recipe extraction failed: class=%s request=%s", type(result).__name__, request_ref
            )
            return result

        result = self._read(response)
        if isinstance(result, (InvalidOutput, AIProviderError)):
            logger.warning(
                "recipe extraction failed: class=%s request=%s", type(result).__name__, request_ref
            )
        return result

    def _client_or_default(self) -> Any:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _config(self, timeout_s: float) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=self._system_instruction,
            response_mime_type="application/json",
            response_json_schema=RESPONSE_SCHEMA,
            http_options=types.HttpOptions(
                timeout=round(timeout_s * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def _read(self, response: Any) -> ExtractionResult:
        body = getattr(response, "text", None)
        if not body:
            return InvalidOutput()
        try:
            payload = _ExtractionPayload.model_validate_json(body)
        except ValidationError:
            return InvalidOutput()
        return _payload_to_result(payload)

    def _classify(self, exc: Exception) -> ExtractionResult:
        if isinstance(exc, httpx.TransportError):
            return Unavailable()
        if isinstance(exc, ServerError):
            return Unavailable()
        if isinstance(exc, ClientError):
            if exc.code == 429:
                return LimitReached(retry_after_seconds=_retry_after_seconds(exc))
            if exc.code in (401, 403, 404):
                return AIProviderError()
            return InvalidOutput()
        return Unavailable()
