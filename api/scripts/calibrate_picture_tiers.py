"""Calibrate the picture tier thresholds on a labelled set (spec 041, research R3, SC-008b).

Reads every image listed in LABELS.md (one `name: sharp` or `name: blurred` per line), measures
its Laplacian sharpness, and writes the thresholds to domain/picture_calibration.json:

- low: halfway between the sharpest blurred picture and the least sharp printed one;
- high: the least sharp printed picture.

The table is marked `calibrated` only when the two groups separate (every blurred score is
below every sharp one). Otherwise the file stays `provisional` and the script says why. The
release gate (`require_calibrated`) refuses a provisional table.

    docker compose exec api uv run python -m scripts.calibrate_picture_tiers \
        tests/fixtures/ai_eval/pictures
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from adapters.image.laplacian import laplacian_sharpness
from PIL import Image, ImageOps

CALIBRATION_FILE = Path(__file__).resolve().parents[1] / "domain" / "picture_calibration.json"


def read_labels(labels_path: Path) -> dict[str, str]:
    """`name: sharp` or `name: blurred` per line; other lines are ignored."""
    labels: dict[str, str] = {}
    for raw in labels_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("-").strip()
        if ":" not in line:
            continue
        name, _, label = line.partition(":")
        label = label.strip().strip("`")
        if label in ("sharp", "blurred"):
            labels[name.strip().strip("`")] = label
    return labels


def score(path: Path) -> float:
    """The Laplacian sharpness of a picture, in the same way the pipeline measures it."""
    with Image.open(path) as image:
        gray = np.asarray(ImageOps.exif_transpose(image).convert("L"), dtype=np.float32)
    return laplacian_sharpness(gray)


def thresholds(blurred: list[float], sharp: list[float]) -> tuple[float, float] | None:
    """(low, high) when the groups separate; None when they overlap or one is empty."""
    if not blurred or not sharp:
        return None
    least_sharp = min(sharp)
    if max(blurred) >= least_sharp:
        return None
    return (max(blurred) + least_sharp) / 2, least_sharp


def calibrate(images_dir: Path, *, labelled_set: str, out: Path = CALIBRATION_FILE) -> str:
    """Measure the labelled set and write the table. Returns a one-line report."""
    labels = read_labels(images_dir / "LABELS.md")
    blurred: list[float] = []
    sharp: list[float] = []
    for name, label in sorted(labels.items()):
        path = images_dir / name
        if not path.exists():
            continue
        (blurred if label == "blurred" else sharp).append(score(path))

    found = thresholds(blurred, sharp)
    table = {
        "low": found[0] if found else _previous(out, "low", 100.0),
        "high": found[1] if found else _previous(out, "high", 500.0),
        "labelled_set": labelled_set,
        "calibrated_on": dt.date.today().isoformat(),
        "status": "calibrated" if found else "provisional",
    }
    out.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    if found:
        return f"calibrated: low={table['low']:.2f} high={table['high']:.2f} ({len(labels)} images)"
    reason = (
        "no blurred pictures"
        if not blurred
        else "no sharp pictures"
        if not sharp
        else (f"the groups overlap (most blurred {max(blurred):.2f}, least sharp {min(sharp):.2f})")
    )
    return f"provisional: the groups did not separate: {reason}"


def _previous(out: Path, key: str, default: float) -> float:
    try:
        return float(json.loads(out.read_text(encoding="utf-8"))[key])
    except (OSError, KeyError, ValueError):
        return default


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: calibrate_picture_tiers.py <labelled-images-dir> [labelled-set-id]")
        return 2
    images_dir = Path(argv[0])
    labelled_set = argv[1] if len(argv) > 1 else images_dir.name
    print(calibrate(images_dir, labelled_set=labelled_set))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
