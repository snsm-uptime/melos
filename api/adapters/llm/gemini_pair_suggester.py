"""Gemini IngredientPairSuggester: likely English and Spanish pairs of catalog names (spec 043 R9).

Only names and their languages are sent, never recipe text (constitution 4). Catalogs over 300
names go in batches of 300. The domain filters the answer (`filter_pairs`); this adapter only
reads it. Any model error raises AIUnavailableError, so the person sees "no suggestions" and
manual merge still works.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections.abc import Sequence
from typing import Any

from domain.errors import AIUnavailableError
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from adapters.llm.prompt_templates import render

logger = logging.getLogger(__name__)

NAMES_OPEN = "<<<CATALOG_NAMES"
NAMES_CLOSE = "CATALOG_NAMES>>>"
BATCH_SIZE = 300

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"en": {"type": "string"}, "es": {"type": "string"}},
                "required": ["en", "es"],
            },
        }
    },
    "required": ["pairs"],
}


class _Pair(BaseModel):
    en: str
    es: str


class _Payload(BaseModel):
    pairs: list[_Pair]


def _cell(value: str) -> str:
    # TOON quotes a value only when it would break the row.
    return json.dumps(value, ensure_ascii=False) if any(c in value for c in ',"\n') else value


def names_toon(names: Sequence[tuple[str, str | None]]) -> str:
    """The names as one TOON table: `names[N]{name,language}:` then one row each."""
    rows = [
        f"  {_cell(name.replace(NAMES_CLOSE, ''))},{language or ''}" for name, language in names
    ]
    return "\n".join([f"names[{len(names)}]{{name,language}}:", *rows])


def pairs_system_instruction() -> str:
    return render("ingredient_pairs_system", NAMES_OPEN=NAMES_OPEN, NAMES_CLOSE=NAMES_CLOSE)


def pairs_contents(names: Sequence[tuple[str, str | None]]) -> str:
    return f"{NAMES_OPEN}\n{names_toon(names)}\n{NAMES_CLOSE}"


class GeminiPairSuggester:
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

    def suggest(self, names: Sequence[tuple[str, str | None]]) -> list[tuple[str, str]]:
        if not self._api_key.strip() or not self._model.strip():
            logger.error("pair suggestions not configured")
            raise AIUnavailableError()
        pairs: list[tuple[str, str]] = []
        for start in range(0, len(names), BATCH_SIZE):
            pairs.extend(self._batch(names[start : start + BATCH_SIZE]))
        return pairs

    def _batch(self, names: Sequence[tuple[str, str | None]]) -> list[tuple[str, str]]:
        request_ref = str(uuid.uuid4())
        try:
            response = self._client_or_default().models.generate_content(
                model=self._model,
                contents=pairs_contents(names),
                config=types.GenerateContentConfig(
                    system_instruction=pairs_system_instruction(),
                    response_mime_type="application/json",
                    response_json_schema=RESPONSE_SCHEMA,
                    http_options=types.HttpOptions(
                        timeout=round(self._timeout_s * 1000),
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                ),
            )
            payload = _Payload.model_validate_json(getattr(response, "text", None) or "")
        except ValidationError as exc:
            logger.warning(
                "pair suggestions failed the schema: %s request=%s",
                [(error["loc"], error["type"]) for error in exc.errors()],
                request_ref,
            )
            raise AIUnavailableError() from None
        except Exception as exc:
            logger.warning(
                "pair suggestions failed: class=%s request=%s", type(exc).__name__, request_ref
            )
            raise AIUnavailableError() from None
        return [(pair.en, pair.es) for pair in payload.pairs]

    def _client_or_default(self) -> genai.Client:
        with self._lock:
            if self._client is None:
                self._client = genai.Client(api_key=self._api_key)
            return self._client
