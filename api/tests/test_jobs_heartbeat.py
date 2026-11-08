"""Heartbeat file for the jobs healthcheck (spec 073, T042). No database."""

from __future__ import annotations

from pathlib import Path

import pytest
from jobs import heartbeat


def test_a_written_heartbeat_is_fresh(tmp_path: Path) -> None:
    path = tmp_path / "hb"
    heartbeat.write(str(path), now=1_000.0)
    assert heartbeat.is_fresh(str(path), now=1_000.0 + 60)


def test_a_heartbeat_older_than_7200_seconds_is_stale(tmp_path: Path) -> None:
    path = tmp_path / "hb"
    heartbeat.write(str(path), now=1_000.0)
    assert not heartbeat.is_fresh(str(path), now=1_000.0 + 7200)


def test_a_missing_heartbeat_is_stale(tmp_path: Path) -> None:
    assert not heartbeat.is_fresh(str(tmp_path / "missing"))


def test_write_creates_the_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "hb"
    heartbeat.write(str(path), now=1_000.0)
    assert path.is_file()


@pytest.mark.parametrize(("age", "code"), [(60, 0), (7200, 1)])
def test_main_exit_code_follows_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, age: int, code: int
) -> None:
    path = tmp_path / "hb"
    heartbeat.write(str(path), now=1_000.0)
    monkeypatch.setenv("JOBS_HEARTBEAT_PATH", str(path))
    monkeypatch.setattr(heartbeat.time, "time", lambda: 1_000.0 + age)
    assert heartbeat.main() == code
