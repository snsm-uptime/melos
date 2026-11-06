"""Migration 0018_shopping_places: upgrade, downgrade, upgrade (spec 070).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _bought(engine) -> bool:  # noqa: ANN001
    columns = inspect(engine).get_columns("shopping_list_item")
    return any(c["name"] == "bought" for c in columns)


def test_up_down_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        assert inspect(engine).has_table("place")
        assert inspect(engine).has_table("ingredient_place")
        assert _bought(engine)
        command.downgrade(cfg, "0017_merge_0016_heads")
        engine.dispose()
        assert not inspect(engine).has_table("place")
        assert not inspect(engine).has_table("ingredient_place")
        assert not _bought(engine)
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
