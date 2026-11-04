"""Gemini adapter for the Embedder port (google-genai, spec 019).

One attempt per call (SDK retries are switched off, PRD 1.7). Recipes are embedded as
RETRIEVAL_DOCUMENT with their title, questions as RETRIEVAL_QUERY, both at the configured
dimension. A vector of another length is refused (FR-025), and every vector is L2-normalized:
the Developer API returns truncated vectors that are not (notes.md, T001).

Logs carry the result class and a request ref only: never text, vectors, keys or service
messages (FR-023).
"""

from __future__ import annotations

import logging
import math
import uuid
from collections.abc import Sequence
from typing import Any

from application.ports import Embedded, EmbedResult
from application.recipe_extraction import AIProviderError, InvalidOutput
from google import genai
from google.genai import types

from adapters.llm.gemini_errors import classify

logger = logging.getLogger(__name__)


def normalize(values: Sequence[float]) -> tuple[float, ...] | None:
    """The vector scaled to length 1; None when it has no length or holds a non-number."""
    floats = [float(value) for value in values]
    if not all(math.isfinite(value) for value in floats):
        return None
    norm = math.sqrt(sum(value * value for value in floats))
    if norm == 0:
        return None
    return tuple(value / norm for value in floats)


class GeminiEmbedder:
    """Production Embedder. The key and model come from settings only."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimension: int,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def configured(self) -> bool:
        return bool(self._api_key.strip()) and bool(self._model.strip())

    def embed_documents(
        self, texts: Sequence[str], titles: Sequence[str], timeout_s: float
    ) -> EmbedResult:
        if len(texts) != len(titles):
            raise ValueError("one title per text")
        if not texts:
            return Embedded(vectors=(), token_counts=(), truncated=())
        if len(texts) == 1:
            # The title is per request; one text per call keeps it exact (research R2a).
            return self._embed(list(texts), "RETRIEVAL_DOCUMENT", titles[0], timeout_s)
        return self._embed(list(texts), "RETRIEVAL_DOCUMENT", None, timeout_s)

    def embed_query(self, text: str, timeout_s: float) -> EmbedResult:
        return self._embed([text], "RETRIEVAL_QUERY", None, timeout_s)

    def count_tokens(self, text: str, timeout_s: float) -> int | None:
        if not self.configured:
            return None
        try:
            response = self._client_or_default().models.count_tokens(
                model=self._model,
                contents=text,
                config=types.CountTokensConfig(http_options=self._http_options(timeout_s)),
            )
        except Exception as exc:
            logger.warning("embedding token count failed: class=%s", type(classify(exc)).__name__)
            return None
        total = getattr(response, "total_tokens", None)
        return total if isinstance(total, int) and total >= 0 else None

    def _embed(
        self, texts: list[str], task_type: str, title: str | None, timeout_s: float
    ) -> EmbedResult:
        if not self.configured:
            logger.error("embeddings not configured: class=AIProviderError")
            return AIProviderError()

        request_ref = str(uuid.uuid4())
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self._dimension,
            http_options=self._http_options(timeout_s),
        )
        if title is not None:
            config.title = title
        try:
            response = self._client_or_default().models.embed_content(
                model=self._model, contents=texts, config=config
            )
        except Exception as exc:
            result = classify(exc)
            logger.warning(
                "embedding failed: class=%s request=%s", type(result).__name__, request_ref
            )
            return result

        result = self._read(response, len(texts))
        if isinstance(result, InvalidOutput):
            logger.warning("embedding failed: class=InvalidOutput request=%s", request_ref)
        return result

    def _read(self, response: Any, expected: int) -> EmbedResult:
        embeddings = getattr(response, "embeddings", None) or []
        if len(embeddings) != expected:
            return InvalidOutput()
        vectors: list[tuple[float, ...]] = []
        counts: list[int | None] = []
        truncated: list[bool] = []
        for embedding in embeddings:
            values = getattr(embedding, "values", None) or []
            if len(values) != self._dimension:
                return InvalidOutput()
            vector = normalize(values)
            if vector is None:
                return InvalidOutput()
            vectors.append(vector)
            statistics = getattr(embedding, "statistics", None)
            count = getattr(statistics, "token_count", None)
            counts.append(int(count) if isinstance(count, (int, float)) and count >= 0 else None)
            truncated.append(bool(getattr(statistics, "truncated", False)))
        return Embedded(
            vectors=tuple(vectors), token_counts=tuple(counts), truncated=tuple(truncated)
        )

    def _client_or_default(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @staticmethod
    def _http_options(timeout_s: float) -> types.HttpOptions:
        return types.HttpOptions(
            timeout=round(timeout_s * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        )
