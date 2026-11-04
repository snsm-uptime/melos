"""SDK and transport errors of google-genai as result classes, shared by every Gemini adapter.

One mapping for every Gemini call (spec 019 research R11): moved unchanged from the extractor.
No exception text, key or service body leaves this module.
"""

from __future__ import annotations

import math
import re

import httpx
from application.recipe_extraction import (
    AIProviderError,
    InvalidOutput,
    LimitReached,
    Unavailable,
)
from google.genai.errors import APIError, ClientError, ServerError

RETRY_DELAY_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*s?\s*$")

GeminiFailure = Unavailable | LimitReached | InvalidOutput | AIProviderError


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
    if not math.isfinite(seconds):
        return None
    whole = round(seconds)
    return whole if whole > 0 else None


def classify(exc: Exception) -> GeminiFailure:
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
