"""Entry point of the jobs service: configuration gate and exit codes (spec 073, T041)."""

from __future__ import annotations

import pytest
from application.translate_ingredients import RunSummary
from jobs import __main__ as entry


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("GEMINI_TRANSLATE_MODEL", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_missing_model_name_stops_at_startup(clean_env: pytest.MonkeyPatch, capsys) -> None:  # noqa: ANN001
    clean_env.setenv("GEMINI_API_KEY", "key")
    assert entry.main() == 2
    assert "GEMINI_TRANSLATE_MODEL is required" in capsys.readouterr().err


def test_missing_api_key_stops_at_startup(clean_env: pytest.MonkeyPatch, capsys) -> None:  # noqa: ANN001
    clean_env.setenv("GEMINI_TRANSLATE_MODEL", "model")
    assert entry.main() == 2
    assert "GEMINI_API_KEY is required" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("status", "code"),
    [("succeeded", 0), ("skipped", 0), ("failed", 1)],
)
def test_run_once_exit_code(status: str, code: int) -> None:
    assert entry._exit_code(RunSummary(status=status)) == code  # type: ignore[arg-type]
