"""Migration 0014_recipe_embeddings: upgrade, downgrade, upgrade (spec 019).

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

TABLES = ("recipe_embedding", "embedding_job", "search_event", "search_result")


def _delete_rules(engine) -> dict[tuple[str, str], str]:  # noqa: ANN001
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT tc.table_name, ccu.table_name AS target, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                  ON rc.constraint_name = tc.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name = ANY(:tables)
                """
            ),
            {"tables": list(TABLES)},
        ).all()
    return {(row.table_name, row.target): row.delete_rule for row in rows}


def test_up_down_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        for table in TABLES:
            assert inspector.has_table(table), table
        with engine.connect() as connection:
            column_type = connection.execute(
                text(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                    "WHERE attrelid = 'recipe_embedding'::regclass AND attname = 'embedding'"
                )
            ).scalar_one()
        assert column_type == "vector(768)"
        assert _delete_rules(engine) == {
            ("recipe_embedding", "recipe"): "CASCADE",
            ("embedding_job", "recipe"): "CASCADE",
            ("search_result", "recipe"): "CASCADE",
            ("search_result", "search_event"): "CASCADE",
        }

        command.downgrade(cfg, "0013_custom_units")
        inspector = inspect(engine)
        for table in TABLES:
            assert not inspector.has_table(table), table
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                ).scalar_one_or_none()
                == 1
            )
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
