"""Loads the picture calibration table from its JSON file (spec 041, research R3).

The file is read once and cached. A file that is missing a field, or has an unknown
status, fails here at load, not on a request.
"""

from __future__ import annotations

import json
from datetime import date
from functools import cache
from pathlib import Path
from typing import Literal, cast

from domain.picture_tiers import CalibrationTable

CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "domain" / "picture_calibration.json"

_STATUSES = ("provisional", "calibrated")
_FIELDS = ("low", "high", "labelled_set", "calibrated_on", "status")


@cache
def load_calibration_table() -> CalibrationTable:
    raw = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    for field in _FIELDS:
        if field not in raw:
            raise ValueError(f"picture calibration file is missing '{field}'")
    if raw["status"] not in _STATUSES:
        raise ValueError(
            f"picture calibration status must be one of {_STATUSES}, got {raw['status']!r}"
        )
    return CalibrationTable(
        low=float(raw["low"]),
        high=float(raw["high"]),
        labelled_set=str(raw["labelled_set"]),
        calibrated_on=date.fromisoformat(raw["calibrated_on"]),
        status=cast(Literal["provisional", "calibrated"], raw["status"]),
    )
