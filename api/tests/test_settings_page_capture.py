"""Settings for link capture batches (spec 026 T018)."""

from __future__ import annotations

import pytest
from api.settings import load_recipe_page_batch_chars, load_recipe_page_max_batches


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RECIPE_PAGE_BATCH_CHARS", raising=False)
    monkeypatch.delenv("RECIPE_PAGE_MAX_BATCHES", raising=False)

    assert load_recipe_page_batch_chars() == 10_000
    assert load_recipe_page_max_batches() == 4


@pytest.mark.parametrize("value", ["1000", "4500", "10000"])
def test_batch_chars_in_range(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RECIPE_PAGE_BATCH_CHARS", value)

    assert load_recipe_page_batch_chars() == int(value)


@pytest.mark.parametrize("value", ["999", "10001", "0", "-5", "lots"])
def test_batch_chars_out_of_range(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RECIPE_PAGE_BATCH_CHARS", value)

    with pytest.raises(ValueError, match="RECIPE_PAGE_BATCH_CHARS"):
        load_recipe_page_batch_chars()


@pytest.mark.parametrize("value", ["1", "8"])
def test_max_batches_in_range(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RECIPE_PAGE_MAX_BATCHES", value)

    assert load_recipe_page_max_batches() == int(value)


@pytest.mark.parametrize("value", ["0", "9", "two"])
def test_max_batches_out_of_range(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RECIPE_PAGE_MAX_BATCHES", value)

    with pytest.raises(ValueError, match="RECIPE_PAGE_MAX_BATCHES"):
        load_recipe_page_max_batches()
