"""The pair suggester adapter with a stand-in client (spec 043)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest
from adapters.llm.gemini_pair_suggester import (
    NAMES_CLOSE,
    GeminiPairSuggester,
    names_toon,
    pairs_system_instruction,
)
from domain.errors import AIUnavailableError


@dataclass
class _Models:
    replies: list[Any]
    calls: list[dict] = field(default_factory=list)

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(text=reply)


def _client(*replies: Any) -> SimpleNamespace:
    return SimpleNamespace(models=_Models(list(replies)))


def _suggester(client: SimpleNamespace, key: str = "k") -> GeminiPairSuggester:
    return GeminiPairSuggester(api_key=key, model="m", timeout_s=5, client=client)


def test_names_go_as_one_toon_table_and_never_close_the_block() -> None:
    table = names_toon(
        [("onion", "en"), ("ajo", None), ("salt, coarse", "en"), (NAMES_CLOSE, None)]
    )
    assert table.splitlines() == [
        "names[4]{name,language}:",
        "  onion,en",
        "  ajo,",
        '  "salt, coarse",en',
        "  ,",
    ]
    assert "Never invent a name" in pairs_system_instruction()


def test_pairs_come_back_and_big_catalogs_go_in_batches() -> None:
    client = _client(json.dumps({"pairs": [{"en": "garlic", "es": "ajo"}]}))
    names = [(f"name{i}", None) for i in range(301)]
    assert _suggester(client).suggest(names) == [("garlic", "ajo"), ("garlic", "ajo")]
    assert len(client.models.calls) == 2


@pytest.mark.parametrize("reply", ["not json", json.dumps({"other": 1}), RuntimeError("down")])
def test_any_model_failure_is_unavailable(reply: Any) -> None:
    with pytest.raises(AIUnavailableError):
        _suggester(_client(reply)).suggest([("garlic", "en"), ("ajo", "es")])


def test_no_key_is_unavailable_without_a_call() -> None:
    client = _client("{}")
    with pytest.raises(AIUnavailableError):
        _suggester(client, key=" ").suggest([("garlic", "en")])
    assert client.models.calls == []
