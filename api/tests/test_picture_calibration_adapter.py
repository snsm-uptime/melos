"""The calibration table loads from its JSON file, and a bad file fails at load (spec 041, R3)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from adapters.image import calibration
from adapters.image.calibration import load_calibration_table


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    load_calibration_table.cache_clear()


def _write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    path = tmp_path / "picture_calibration.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(calibration, "CALIBRATION_PATH", path)
    load_calibration_table.cache_clear()


def _valid() -> dict:
    return {
        "low": 100,
        "high": 500,
        "labelled_set": "test-set",
        "calibrated_on": "2026-11-07",
        "status": "calibrated",
    }


def test_shipped_file_loads_as_provisional() -> None:
    table = load_calibration_table()
    assert table.status == "provisional"
    assert table.low == 100
    assert table.high == 500


def test_calibrated_on_is_a_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path, monkeypatch, _valid())
    assert load_calibration_table().calibrated_on == date(2026, 11, 7)


def test_missing_low_is_a_clear_error_at_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid()
    del payload["low"]
    _write(tmp_path, monkeypatch, payload)
    with pytest.raises(ValueError, match="low"):
        load_calibration_table()


def test_unknown_status_is_a_clear_error_at_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid()
    payload["status"] = "done"
    _write(tmp_path, monkeypatch, payload)
    with pytest.raises(ValueError, match="status"):
        load_calibration_table()
