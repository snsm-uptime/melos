"""Migration 0015_recipe_preview_image: upgrade, downgrade, upgrade (spec 026 T035).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _column(engine) -> dict | None:  # noqa: ANN001
    columns = {column["name"]: column for column in inspect(engine).get_columns("recipe")}
    return columns.get("preview_image_base64")


def test_up_down_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        column = _column(engine)
        assert column is not None
        assert column["nullable"] is True
        assert str(column["type"]).upper() == "TEXT"

        command.downgrade(cfg, "0014_recipe_embeddings")
        assert _column(engine) is None

        command.upgrade(cfg, "head")
        assert _column(engine) is not None
        with engine.connect() as connection:
            filled = connection.execute(
                text("SELECT count(*) FROM recipe WHERE preview_image_base64 IS NOT NULL")
            ).scalar_one()
        assert filled == 0
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
