"""Gemini embedder tests with a stubbed SDK client (spec 019). Never the network, except one
live check that is skipped without GEMINI_API_KEY (research R1).
"""

from __future__ import annotations

import logging
import math
import os
from types import SimpleNamespace

import httpx
import pytest
from adapters.llm import gemini_embedder
from adapters.llm.gemini_embedder import GeminiEmbedder
from application.ports import Embedded
from application.recipe_extraction import (
    AIProviderError,
    InvalidOutput,
    LimitReached,
    Unavailable,
)
from google.genai.errors import ClientError, ServerError

SECRET_KEY = "SECRET-KEY-123"
RECIPE_SECRET = "RECIPE-SECRET-TEXT"
SERVICE_SECRET = "SERVICE-BODY-SECRET"
DIM = 768


def _vector(scale: float = 0.5) -> list[float]:
    return [scale] * DIM


def _response(*vectors: list[float], token_count=None, truncated=None):  # noqa: ANN001, ANN202
    statistics = SimpleNamespace(token_count=token_count, truncated=truncated)
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=v, statistics=statistics) for v in vectors]
    )


class _StubModels:
    def __init__(self, behaviour, tokens=None) -> None:  # noqa: ANN001
        self.behaviour = behaviour
        self.tokens = tokens
        self.calls: list[dict] = []
        self.count_calls: list[dict] = []

    def embed_content(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        if isinstance(self.behaviour, BaseException):
            raise self.behaviour
        return self.behaviour

    def count_tokens(self, **kwargs):  # noqa: ANN003, ANN201
        self.count_calls.append(kwargs)
        if isinstance(self.tokens, BaseException):
            raise self.tokens
        return SimpleNamespace(total_tokens=self.tokens)


class _StubClient:
    def __init__(self, behaviour, tokens=None) -> None:  # noqa: ANN001
        self.models = _StubModels(behaviour, tokens)


def embedder(behaviour, *, tokens=None, key: str = SECRET_KEY, model: str = "gemini-embedding-001"):  # noqa: ANN001, ANN201, E501
    client = _StubClient(behaviour, tokens)
    return GeminiEmbedder(api_key=key, model=model, dimension=DIM, client=client), client


def api_error(cls, code: int, response=None):  # noqa: ANN001, ANN201
    return cls(code, {"error": {"code": code, "message": SERVICE_SECRET}}, response)


@pytest.fixture(autouse=True)
def _logger_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_embedder.logger, "disabled", False)


def test_documents_use_retrieval_document_title_and_768() -> None:
    embedder_, client = embedder(_response(_vector()))

    result = embedder_.embed_documents([RECIPE_SECRET], ["tomato rice"], 10.0)

    assert isinstance(result, Embedded)
    call = client.models.calls[0]
    assert call["model"] == "gemini-embedding-001"
    assert call["contents"] == [RECIPE_SECRET]
    assert call["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert call["config"].title == "tomato rice"
    assert call["config"].output_dimensionality == DIM
    assert call["config"].http_options.retry_options.attempts == 1
    assert call["config"].http_options.timeout == 10_000


def test_queries_use_retrieval_query_and_no_title() -> None:
    embedder_, client = embedder(_response(_vector()))

    embedder_.embed_query("arroz", 10.0)

    config = client.models.calls[0]["config"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert config.title is None
    assert config.output_dimensionality == DIM


def test_vectors_are_normalized() -> None:
    embedder_, _ = embedder(_response(_vector(0.02)))

    result = embedder_.embed_query("arroz", 10.0)

    assert isinstance(result, Embedded)
    assert math.isclose(math.sqrt(sum(v * v for v in result.vectors[0])), 1.0)


def test_statistics_are_read_when_present() -> None:
    embedder_, _ = embedder(_response(_vector(), token_count=42, truncated=True))

    result = embedder_.embed_documents(["x"], ["x"], 10.0)

    assert isinstance(result, Embedded)
    assert result.token_counts == (42,)
    assert result.truncated == (True,)


def test_missing_statistics_give_none_and_false() -> None:
    embedder_, _ = embedder(_response(_vector()))

    result = embedder_.embed_documents(["x"], ["x"], 10.0)

    assert isinstance(result, Embedded)
    assert result.token_counts == (None,)
    assert result.truncated == (False,)


@pytest.mark.parametrize("length", [767, 3072, 0])
def test_a_wrong_length_is_invalid_output(length: int) -> None:
    embedder_, _ = embedder(_response([0.1] * length))

    assert embedder_.embed_documents(["x"], ["x"], 10.0) == InvalidOutput()


def test_a_missing_vector_is_invalid_output() -> None:
    embedder_, _ = embedder(SimpleNamespace(embeddings=[]))

    assert embedder_.embed_query("x", 10.0) == InvalidOutput()


def test_a_zero_vector_is_invalid_output() -> None:
    embedder_, _ = embedder(_response([0.0] * DIM))

    assert embedder_.embed_query("x", 10.0) == InvalidOutput()


def test_429_is_limit_reached_with_retry_after() -> None:
    response_ = httpx.Response(429, headers={"retry-after": "30"})
    embedder_, _ = embedder(api_error(ClientError, 429, response=response_))

    assert embedder_.embed_query("x", 10.0) == LimitReached(retry_after_seconds=30)


@pytest.mark.parametrize(
    "error",
    [
        api_error(ServerError, 500),
        api_error(ServerError, 503),
        httpx.ConnectError("down"),
        httpx.ReadTimeout("slow"),
    ],
)
def test_server_and_transport_errors_are_unavailable(error: Exception) -> None:
    embedder_, _ = embedder(error)

    assert embedder_.embed_documents(["x"], ["x"], 10.0) == Unavailable()


@pytest.mark.parametrize("code", [401, 403, 404])
def test_rejected_key_is_ai_provider_error(code: int) -> None:
    embedder_, _ = embedder(api_error(ClientError, code))

    assert embedder_.embed_query("x", 10.0) == AIProviderError()


@pytest.mark.parametrize(("key", "model"), [("", "gemini-embedding-001"), (SECRET_KEY, "  ")])
def test_no_key_or_model_is_ai_provider_error_without_a_call(key: str, model: str) -> None:
    embedder_, client = embedder(_response(_vector()), key=key, model=model)

    assert embedder_.embed_query("x", 10.0) == AIProviderError()
    assert embedder_.embed_documents(["x"], ["x"], 10.0) == AIProviderError()
    assert embedder_.count_tokens("x", 10.0) is None
    assert client.models.calls == [] and client.models.count_calls == []


def test_count_tokens_returns_the_total() -> None:
    embedder_, client = embedder(_response(_vector()), tokens=17)

    assert embedder_.count_tokens(RECIPE_SECRET, 10.0) == 17
    assert client.models.count_calls[0]["model"] == "gemini-embedding-001"


def test_count_tokens_failure_is_none() -> None:
    embedder_, _ = embedder(_response(_vector()), tokens=api_error(ServerError, 503))

    assert embedder_.count_tokens("x", 10.0) is None


def test_logs_hold_no_text_key_or_service_message(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    for behaviour in (api_error(ServerError, 503), api_error(ClientError, 429), _response([1.0])):
        embedder_, _ = embedder(behaviour, tokens=api_error(ServerError, 503))
        embedder_.embed_documents([RECIPE_SECRET], [RECIPE_SECRET], 10.0)
        embedder_.count_tokens(RECIPE_SECRET, 10.0)

    assert caplog.records, "failures should be logged"
    for text in (SECRET_KEY, RECIPE_SECRET, SERVICE_SECRET, "0.5"):
        assert text not in caplog.text
    assert "class=Unavailable" in caplog.text


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="live check needs GEMINI_API_KEY")
def test_live_model_returns_768_values() -> None:
    live = GeminiEmbedder(
        api_key=os.environ["GEMINI_API_KEY"],
        model=os.environ.get("GEMINI_EMBED_MODEL") or "gemini-embedding-001",
        dimension=DIM,
    )

    result = live.embed_documents(["arroz con tomate"], ["arroz"], 10.0)

    assert isinstance(result, Embedded)
    assert len(result.vectors[0]) == DIM
    assert math.isclose(math.sqrt(sum(v * v for v in result.vectors[0])), 1.0)
