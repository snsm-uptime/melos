"""Migration 0009_shopping_lists: upgrade, downgrade, upgrade (spec 025).

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


def test_up_down_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        assert inspect(engine).has_table("shopping_list_item")
        command.downgrade(cfg, "0008_cart_servings")
        assert not inspect(engine).has_table("shopping_list")
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
