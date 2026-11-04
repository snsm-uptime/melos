"""Gemini adapter for the RecipeExtractor port (google-genai).

One attempt per call (SDK retries are switched off). Every SDK or transport
error is mapped to a result class here, and no exception text, key or service
body leaves this module (FR-003 to FR-005, FR-009, FR-014, SC-006).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import Any, Literal

from application.recipe_extraction import (
    AIProviderError,
    Draft,
    ExtractionResult,
    InvalidOutput,
    NotARecipe,
    NotRecipeReason,
)
from domain.recipe_draft import (
    DraftRecipe,
    IngredientLine,
    clean_display_name,
)
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from adapters.llm.gemini_errors import classify
from adapters.llm.prompt import build_contents, system_instruction

logger = logging.getLogger(__name__)

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "outcome": {
            "type": "string",
            "enum": ["recipe", "not_a_recipe", "multiple_recipes"],
        },
        "reason": {
            "type": "string",
            "enum": ["question_or_request", "not_food", "story_or_article"],
        },
        "ingredient": {"type": "string"},
        "recipe": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "base_servings": {"type": "integer"},
                # MVP-OUT: "main_ingredients": {"type": "array", "items": {"type": "string"}},
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
                            "preparation": {"type": "string"},
                            "text_name": {"type": "string"},
                            "catalog_match": {"type": "string"},
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
    preparation: str | None = None
    text_name: str | None = None
    catalog_match: str | None = None


class _RecipePayload(BaseModel):
    title: str
    base_servings: int | None = None
    # MVP-OUT: main_ingredients: list[str] = []
    ingredient_lines: list[_LinePayload]
    steps: list[str]


class _ExtractionPayload(BaseModel):
    outcome: Literal["recipe", "not_a_recipe", "multiple_recipes"]
    reason: str | None = None
    ingredient: str | None = None
    recipe: _RecipePayload | None = None


# The model may only pick one of these for a refusal; the app words the sentence itself.
_REFUSAL_REASONS = {
    reason.value
    for reason in (
        NotRecipeReason.QUESTION_OR_REQUEST,
        NotRecipeReason.NOT_FOOD,
        NotRecipeReason.STORY_OR_ARTICLE,
    )
}


def _payload_to_result(payload: _ExtractionPayload) -> ExtractionResult:
    if payload.outcome == "multiple_recipes":
        return NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES)
    if payload.outcome == "not_a_recipe":
        if payload.reason not in _REFUSAL_REASONS:
            return InvalidOutput()
        return NotARecipe(
            reason=NotRecipeReason(payload.reason),
            ingredient=clean_display_name(payload.ingredient),
        )
    if payload.recipe is None:
        return InvalidOutput()

    recipe = payload.recipe
    return Draft(
        recipe=DraftRecipe(
            title=recipe.title,
            base_servings=recipe.base_servings,
            servings_estimated=False,
            # MVP-OUT: main_ingredients=tuple(recipe.main_ingredients),
            # MVP-OUT: cuisines=(),
            ingredient_lines=tuple(
                IngredientLine(
                    name=line.name,
                    vague=line.vague,
                    quantity=line.quantity,
                    unit=line.unit,
                    size=line.size,
                    note=line.note,
                    preparation=line.preparation,
                    text_name=line.text_name,
                    catalog_match=line.catalog_match,
                )
                for line in recipe.ingredient_lines
            ),
            steps=tuple(recipe.steps),
        )
    )


class GeminiRecipeExtractor:
    """Production RecipeExtractor. The key and model come from settings only (FR-009)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        # MVP-OUT: vocabulary: Vocabulary,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._system_instruction = system_instruction()
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
                "recipe extraction failed: class=%s request=%s",
                type(result).__name__,
                request_ref,
            )
            return result

        result = self._read(response)
        if isinstance(result, (InvalidOutput, AIProviderError)):
            logger.warning(
                "recipe extraction failed: class=%s request=%s",
                type(result).__name__,
                request_ref,
            )
        return result

    def _client_or_default(self) -> genai.Client:
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
        except ValidationError as exc:
            # Field paths and error types only: never the values, never the pasted text.
            logger.warning(
                "extraction output failed the schema: %s",
                [(error["loc"], error["type"]) for error in exc.errors()],
            )
            return InvalidOutput()
        return _payload_to_result(payload)

    def _classify(self, exc: Exception) -> ExtractionResult:
        return classify(exc)
