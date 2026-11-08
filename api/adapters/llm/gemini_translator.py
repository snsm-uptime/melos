"""Gemini IngredientTranslator: validate one ingredient name and translate it (spec 073).

Only the name and the two language codes are sent (constitution 4). The model name comes from
settings, never from code (FR-015). Errors become domain errors (contracts/translation-port.md):
a timeout, network error, or quota or rate limit is TranslationUnavailable; an answer that is not
the expected shape is TranslationUnparseable. No exception text or key is logged.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from domain.ingredient_translation import (
    IngredientTranslationRequest,
    IngredientTranslationResult,
    InvalidTranslationResult,
    TranslationQuotaExceeded,
    TranslationUnavailable,
    TranslationUnparseable,
)
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, ValidationError

from adapters.llm.prompt_templates import render

logger = logging.getLogger(__name__)

NAME_OPEN = "<<<INGREDIENT_NAME"
NAME_CLOSE = "INGREDIENT_NAME>>>"

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "translation": {"type": "string", "nullable": True},
    },
    "required": ["valid", "translation"],
}


def _is_quota(exc: Exception) -> bool:
    """A 429 from the API, by its status code or its status name. Never the message text."""
    code = getattr(exc, "code", None)
    status = str(getattr(exc, "status", "") or "")
    return code == 429 or status == "RESOURCE_EXHAUSTED"


class _Answer(BaseModel):
    # Strict: "yes" is not a boolean, so a loose answer is unparseable rather than coerced.
    model_config = ConfigDict(strict=True)

    valid: bool
    translation: str | None


def system_instruction(request: IngredientTranslationRequest) -> str:
    return render(
        "ingredient_translation",
        NAME_OPEN=NAME_OPEN,
        NAME_CLOSE=NAME_CLOSE,
        SOURCE_LANGUAGE=request.source_language,
        TARGET_LANGUAGE=request.target_language,
    )


def contents(request: IngredientTranslationRequest) -> str:
    # The name is the only recipe-derived text sent. Its delimiter is removed so it cannot close
    # the block early.
    name = request.name.replace(NAME_CLOSE, "").strip()
    return f"{NAME_OPEN}\n{name}\n{NAME_CLOSE}"


class GeminiIngredientTranslator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_s: float,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._client = client
        self._lock = threading.Lock()

    def translate(self, request: IngredientTranslationRequest) -> IngredientTranslationResult:
        request_ref = str(uuid.uuid4())
        try:
            response = self._client_or_default().models.generate_content(
                model=self._model,
                contents=contents(request),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction(request),
                    response_mime_type="application/json",
                    response_json_schema=RESPONSE_SCHEMA,
                    http_options=types.HttpOptions(
                        timeout=round(self._timeout_s * 1000),
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                ),
            )
            answer = _Answer.model_validate_json(getattr(response, "text", None) or "")
            return IngredientTranslationResult(valid=answer.valid, translation=answer.translation)
        except (ValidationError, InvalidTranslationResult):
            logger.warning("translation answer unusable request=%s", request_ref)
            raise TranslationUnparseable() from None
        except Exception as exc:
            logger.warning(
                "translation unavailable: class=%s request=%s", type(exc).__name__, request_ref
            )
            if _is_quota(exc):
                raise TranslationQuotaExceeded() from None
            raise TranslationUnavailable() from None

    def _client_or_default(self) -> genai.Client:
        with self._lock:
            if self._client is None:
                self._client = genai.Client(api_key=self._api_key)
            return self._client
