"""JSON-line run log for the scheduled jobs service (spec 073, contracts/run-log.md).

One line per event on stdout, so Compose collects it with the other services' logs. Callers pass
ids and counts only: never an ingredient name, recipe text, author or key.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

SERVICE = "jobs"


def emit(event: str, *, stream: TextIO | None = None, **fields: Any) -> None:
    line = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "service": SERVICE,
        "event": event,
        **fields,
    }
    out = stream or sys.stdout
    out.write(json.dumps(line, default=str) + "\n")
    out.flush()
