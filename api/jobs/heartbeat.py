"""Heartbeat file for the jobs service healthcheck (spec 073, research R8).

The job has no HTTP server. Every loop iteration writes the current time to a file; Compose's
healthcheck calls `python -m jobs.heartbeat` and it fails when the file is missing or older than
the stale limit.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

STALE_AFTER_SECONDS = 7200


def write(path: str, now: float | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(now if now is not None else time.time()), encoding="utf-8")
    os.utime(target, (now, now) if now is not None else None)


def is_fresh(path: str, now: float | None = None) -> bool:
    target = Path(path)
    if not target.is_file():
        return False
    current = now if now is not None else time.time()
    return current - target.stat().st_mtime < STALE_AFTER_SECONDS


def main(argv: list[str] | None = None) -> int:
    """Exit 0 when fresh, 1 when stale or missing. The path comes from JOBS_HEARTBEAT_PATH."""
    path = os.environ.get("JOBS_HEARTBEAT_PATH") or "/tmp/jobs-heartbeat"
    return 0 if is_fresh(path) else 1


if __name__ == "__main__":
    sys.exit(main())
