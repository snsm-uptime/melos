"""Migration 0021_catalog_other_names: fallback language, downgrade, upgrade (spec 043).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head.
Rows are written at 0020 with plain SQL, since the ORM models already have the new columns.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _user(engine: Engine, language: str | None) -> UUID:
    user_id = uuid4()
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO users (id, email, password_hash, language) "
                "VALUES (:id, :email, 'x', :language)"
            ),
            {"id": user_id, "email": f"m0020-{user_id}@example.com", "language": language},
        )
    return user_id


def _recipe(engine: Engine, author: UUID, kitchen_id: UUID | None) -> UUID:
    notebook_id, recipe_id = uuid4(), uuid4()
    with engine.begin() as db:
        db.execute(
            text("INSERT INTO notebook (id, name, kitchen_id) VALUES (:id, 'm0020', :kitchen)"),
            {"id": notebook_id, "kitchen": kitchen_id},
        )
        db.execute(
            text(
                "INSERT INTO recipe (id, notebook_id, author_id, title, base_servings) "
                "VALUES (:id, :notebook, :author, 'Soup', 2)"
            ),
            {"id": recipe_id, "notebook": notebook_id, "author": author},
        )
    return recipe_id


def _languages(engine: Engine, ids: list[UUID]) -> list[str]:
    with engine.connect() as db:
        rows = dict(
            db.execute(
                text("SELECT id, language FROM recipe WHERE id = ANY(:ids)"), {"ids": ids}
            ).all()
        )
    return [rows[i] for i in ids]


def _columns(engine: Engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_fallback_language_then_down_and_up() -> None:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    users: list[UUID] = []
    try:
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "0020_ingredient_free_note")
        engine.dispose()

        owner = _user(engine, "es")
        english = _user(engine, "en-US")
        unset = _user(engine, None)
        users = [owner, english, unset]
        kitchen_id = uuid4()
        with engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO kitchens (id, name, owner_id, content_language) "
                    "VALUES (:id, 'm0020', :owner, 'en')"
                ),
                {"id": kitchen_id, "owner": owner},
            )
        # A kitchen recipe by a Spanish speaker still takes the kitchen's language.
        in_kitchen = _recipe(engine, owner, kitchen_id)
        personal_en = _recipe(engine, english, None)
        personal_unset = _recipe(engine, unset, None)

        command.upgrade(cfg, "0021_catalog_other_names")
        engine.dispose()
        assert _languages(engine, [in_kitchen, personal_en, personal_unset]) == ["en", "en", "es"]
        assert inspect(engine).has_table("ingredient_name")
        assert inspect(engine).has_table("ingredient_pair_dismissal")
        assert {"language", "language_detected_at", "proposed_language"} <= _columns(
            engine, "recipe"
        )
        assert "names" in _columns(engine, "shopping_list_item")

        command.downgrade(cfg, "0020_ingredient_free_note")
        engine.dispose()
        assert not inspect(engine).has_table("ingredient_name")
        assert not inspect(engine).has_table("ingredient_pair_dismissal")
        assert "language" not in _columns(engine, "recipe")
        assert "language" not in _columns(engine, "ingredient")
        assert "names" not in _columns(engine, "shopping_list_item")
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
        if users:
            with engine.begin() as db:
                db.execute(text("DELETE FROM kitchens WHERE owner_id = ANY(:ids)"), {"ids": users})
                db.execute(text("DELETE FROM notebook WHERE name = 'm0020'"))
                db.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": users})
        engine.dispose()
