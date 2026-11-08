"""Postgres advisory lock: one scheduled job run at a time (spec 073, FR-012, research R2).

The lock lives on one connection for the whole run. It is released in `finally`, and closing the
connection releases it too, so a crashed run cannot hold it forever.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine

# One fixed key for the translation job. Spec 073 feature number, so it cannot collide with
# another use of advisory locks in this database.
TRANSLATE_JOB_LOCK_KEY = 73_000_001


class JobLock:
    def __init__(self, engine: Engine, key: int = TRANSLATE_JOB_LOCK_KEY) -> None:
        self._engine = engine
        self._key = key

    @contextmanager
    def try_acquire(self) -> Iterator[bool]:
        """Yields True when this process holds the lock, False when another run is active."""
        connection = self._engine.connect()
        try:
            acquired = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": self._key}
                ).scalar()
            )
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": self._key})
        finally:
            connection.close()
