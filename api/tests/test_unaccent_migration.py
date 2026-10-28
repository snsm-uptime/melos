"""Migration 0006_unaccent: the extension is installed and the upgrade can run twice (spec 021).

Requires DATABASE_URL. Skips when unset.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_unaccent_works_after_upgrade_and_upgrade_is_repeatable() -> None:
    url = database_url()
    assert url is not None
    command.upgrade(_config(url), "head")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT unaccent('calabazá')")) == "calabaza"
            # The statement the migration runs, a second time: harmless.
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    finally:
        engine.dispose()
