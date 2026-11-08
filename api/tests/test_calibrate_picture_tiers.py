"""The calibration script on an invented three-image set (spec 041 T076, research R3)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from scripts import calibrate_picture_tiers as calibrate


def _checker(path: Path) -> None:
    pattern = (np.indices((64, 64)).sum(axis=0) % 2 * 255).astype(np.uint8)
    Image.fromarray(pattern, mode="L").save(path)


def _gradient(path: Path) -> None:
    ramp = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    Image.fromarray(ramp, mode="L").save(path)


@pytest.fixture
def labelled(tmp_path: Path) -> Path:
    directory = tmp_path / "pictures"
    directory.mkdir()
    _checker(directory / "sharp_a.png")
    _checker(directory / "sharp_b.png")
    _gradient(directory / "blurred.png")
    (directory / "LABELS.md").write_text(
        "- sharp_a.png: sharp\n- sharp_b.png: sharp\n- blurred.png: blurred\n",
        encoding="utf-8",
    )
    return directory


def test_separating_groups_are_calibrated(labelled: Path, tmp_path: Path) -> None:
    out = tmp_path / "picture_calibration.json"
    report = calibrate.calibrate(labelled, labelled_set="invented-3", out=out)
    table = json.loads(out.read_text(encoding="utf-8"))
    assert table["status"] == "calibrated"
    assert table["labelled_set"] == "invented-3"
    assert table["low"] < table["high"]
    assert report.startswith("calibrated")


def test_overlapping_groups_stay_provisional(labelled: Path, tmp_path: Path) -> None:
    # A "blurred" label on a sharp picture makes the groups overlap.
    (labelled / "LABELS.md").write_text(
        "- sharp_a.png: sharp\n- sharp_b.png: blurred\n- blurred.png: blurred\n",
        encoding="utf-8",
    )
    out = tmp_path / "picture_calibration.json"
    report = calibrate.calibrate(labelled, labelled_set="invented-3", out=out)
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "provisional"
    assert report.startswith("provisional")


def test_one_group_alone_is_provisional(tmp_path: Path) -> None:
    directory = tmp_path / "pictures"
    directory.mkdir()
    _checker(directory / "only.png")
    (directory / "LABELS.md").write_text("- only.png: sharp\n", encoding="utf-8")
    out = tmp_path / "picture_calibration.json"
    report = calibrate.calibrate(directory, labelled_set="one", out=out)
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "provisional"
    assert "no blurred" in report


def test_thresholds_split_halfway_between_the_groups() -> None:
    assert calibrate.thresholds([10.0, 20.0], [100.0, 140.0]) == (60.0, 100.0)
    assert calibrate.thresholds([10.0, 120.0], [100.0]) is None


def test_labels_ignore_other_lines(tmp_path: Path) -> None:
    labels = tmp_path / "LABELS.md"
    labels.write_text(
        "# Labels\n\n- `a.png`: sharp\nnot a label\n- b.png: blurred\n", encoding="utf-8"
    )
    assert calibrate.read_labels(labels) == {"a.png": "sharp", "b.png": "blurred"}
