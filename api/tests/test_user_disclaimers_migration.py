"""Migration 0022_user_disclaimers: default true, downgrade, upgrade (spec 041).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def test_disclaimers_default_true_then_down_and_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "0021_catalog_other_names")
        engine.dispose()

        before = uuid4()
        with engine.begin() as db:
            db.execute(
                text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'x')"),
                {"id": before, "email": f"m0022-before-{before}@example.com"},
            )

        command.upgrade(cfg, "head")
        engine.dispose()

        assert "disclaimers" in {c["name"] for c in inspect(engine).get_columns("users")}
        with engine.begin() as db:
            assert (
                db.execute(
                    text("SELECT disclaimers FROM users WHERE id = :id"), {"id": before}
                ).scalar_one()
                is True
            )

            after = uuid4()
            db.execute(
                text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'x')"),
                {"id": after, "email": f"m0022-after-{after}@example.com"},
            )
            assert (
                db.execute(
                    text("SELECT disclaimers FROM users WHERE id = :id"), {"id": after}
                ).scalar_one()
                is True
            )

        command.downgrade(cfg, "0021_catalog_other_names")
        engine.dispose()
        assert "disclaimers" not in {c["name"] for c in inspect(engine).get_columns("users")}
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
