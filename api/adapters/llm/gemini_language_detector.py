"""Gemini LanguageDetector: the language most of a saved recipe is in (spec 043 FR-005a).

Used only by the one-time `scripts.recipe_languages detect` command. The answer is a proposal:
the command stores it for a person to apply. Any model error, or an unsure answer, is None.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Literal

from domain.ingredient_catalog import as_language
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from adapters.llm.prompt_templates import render

logger = logging.getLogger(__name__)

TEXT_OPEN = "<<<RECIPE"
TEXT_CLOSE = "RECIPE>>>"

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"language": {"type": "string", "enum": ["en", "es", "unsure"]}},
    "required": ["language"],
}


class _Payload(BaseModel):
    language: Literal["en", "es", "unsure"]


def language_system_instruction() -> str:
    return render("recipe_language_system", TEXT_OPEN=TEXT_OPEN, TEXT_CLOSE=TEXT_CLOSE)


def language_contents(text: str) -> str:
    return f"{TEXT_OPEN}\n{text.replace(TEXT_CLOSE, '')}\n{TEXT_CLOSE}"


class GeminiLanguageDetector:
    def __init__(
        self, *, api_key: str, model: str, timeout_s: float, client: Any | None = None
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._client = client
        self._lock = threading.Lock()

    def detect(self, text: str) -> str | None:
        if not self._api_key.strip() or not self._model.strip():
            logger.error("language detection not configured")
            return None
        request_ref = str(uuid.uuid4())
        try:
            response = self._client_or_default().models.generate_content(
                model=self._model,
                contents=language_contents(text),
                config=types.GenerateContentConfig(
                    system_instruction=language_system_instruction(),
                    response_mime_type="application/json",
                    response_json_schema=RESPONSE_SCHEMA,
                    http_options=types.HttpOptions(
                        timeout=round(self._timeout_s * 1000),
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                ),
            )
            payload = _Payload.model_validate_json(getattr(response, "text", None) or "")
        except ValidationError:
            logger.warning("language detection failed the schema: request=%s", request_ref)
            return None
        except Exception as exc:
            logger.warning(
                "language detection failed: class=%s request=%s", type(exc).__name__, request_ref
            )
            return None
        return as_language(payload.language)

    def _client_or_default(self) -> genai.Client:
        with self._lock:
            if self._client is None:
                self._client = genai.Client(api_key=self._api_key)
            return self._client
