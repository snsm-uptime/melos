"""Migration 0016_recipe_copied_from: upgrade, downgrade, upgrade (spec 069 T004).

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


def _column(engine) -> dict | None:  # noqa: ANN001
    columns = {column["name"]: column for column in inspect(engine).get_columns("recipe")}
    return columns.get("copied_from_recipe_id")


def _index_names(engine) -> set[str]:  # noqa: ANN001
    return {index["name"] for index in inspect(engine).get_indexes("recipe")}


def _foreign_key(engine) -> dict | None:  # noqa: ANN001
    return next(
        (
            fk
            for fk in inspect(engine).get_foreign_keys("recipe")
            if fk["constrained_columns"] == ["copied_from_recipe_id"]
        ),
        None,
    )


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
        assert "ix_recipe_copied_from_recipe_id" in _index_names(engine)
        fk = _foreign_key(engine)
        assert fk is not None
        assert fk["referred_table"] == "recipe"
        assert fk["options"].get("ondelete") == "SET NULL"

        command.downgrade(cfg, "0015_recipe_preview_image")
        assert _column(engine) is None
        assert "ix_recipe_copied_from_recipe_id" not in _index_names(engine)

        command.upgrade(cfg, "head")
        assert _column(engine) is not None
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
