"""Migration 0005_recipes: upgrade, downgrade, upgrade, and the table checks (spec 020).

Requires DATABASE_URL. Skips when unset. Uses its own scratch schema database state through
the shared test database, so it restores head before it returns.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def engine() -> Iterator[Engine]:
    url = database_url()
    assert url is not None
    eng = create_engine(url)
    command.upgrade(_config(url), "head")
    yield eng
    command.upgrade(_config(url), "head")
    eng.dispose()


def _tables(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("select table_name from information_schema.tables where table_schema = 'public'")
        )
        return {row[0] for row in rows}


def test_upgrade_downgrade_upgrade_keeps_notebooks_and_catalogs(engine: Engine) -> None:
    url = database_url()
    assert url is not None
    notebook_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("insert into notebook (id, name) values (:id, 'Migration check')"),
            {"id": notebook_id},
        )
        conn.execute(
            text("insert into ingredient (notebook_id, name) values (:id, 'onion')"),
            {"id": notebook_id},
        )
    try:
        command.downgrade(_config(url), "0004_drop_kitchen_hide")
        assert not {"source", "recipe", "recipe_ingredient", "step"} & _tables(engine)
        command.upgrade(_config(url), "head")
        assert {"source", "recipe", "recipe_ingredient", "step"} <= _tables(engine)
        with engine.connect() as conn:
            names = conn.execute(
                text("select name from ingredient where notebook_id = :id"), {"id": notebook_id}
            ).scalars().all()
        assert names == ["onion"]
    finally:
        with engine.begin() as conn:
            conn.execute(text("delete from notebook where id = :id"), {"id": notebook_id})


@pytest.fixture
def recipe_id(engine: Engine) -> Iterator[str]:
    notebook_id = uuid4()
    recipe = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("insert into notebook (id, name) values (:id, 'Checks')"), {"id": notebook_id}
        )
        conn.execute(
            text(
                "insert into recipe (id, notebook_id, title, base_servings)"
                " values (:r, :n, 'Soup', 4)"
            ),
            {"r": recipe, "n": notebook_id},
        )
    yield str(recipe)
    with engine.begin() as conn:
        conn.execute(text("delete from notebook where id = :id"), {"id": notebook_id})


def _insert_line(engine: Engine, recipe: str, **values: object) -> None:
    row = {"name": "onion", "quantity": 1, "unit": "unit", "size": None, "vague": None}
    row.update(values)
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into recipe_ingredient (recipe_id, position, name, quantity, unit, size,"
                " vague_note) values (:r, 0, :name, :quantity, :unit, :size, :vague)"
            ),
            {"r": recipe, **row},
        )


@pytest.mark.parametrize(
    "values",
    [
        {"quantity": 0},
        {"unit": "pint"},
        {"unit": "cup", "size": "large"},
        {"size": "huge"},
        {"vague": "a pinch"},
        {"quantity": None, "unit": None, "vague": None},
        {"name": "  "},
    ],
)
def test_line_checks_reject_broken_rows(engine: Engine, recipe_id: str, values: dict) -> None:
    with pytest.raises(IntegrityError):
        _insert_line(engine, recipe_id, **values)


def test_a_vague_line_and_a_measured_line_are_accepted(engine: Engine, recipe_id: str) -> None:
    _insert_line(engine, recipe_id, quantity=None, unit=None, vague="to taste", name="salt")


def test_recipe_checks_reject_blank_title_and_zero_servings(engine: Engine, recipe_id: str) -> None:
    with engine.begin() as conn:
        notebook = conn.execute(
            text("select notebook_id from recipe where id = :r"), {"r": recipe_id}
        ).scalar_one()
    for title, servings in (("  ", 4), ("Soup", 0)):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "insert into recipe (notebook_id, title, base_servings) values (:n, :t, :s)"
                ),
                {"n": notebook, "t": title, "s": servings},
            )


def test_step_checks_reject_blank_text_and_repeated_positions(
    engine: Engine, recipe_id: str
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("insert into step (recipe_id, position, text) values (:r, 0, 'Stir')"),
            {"r": recipe_id},
        )
    for position, body in ((1, "  "), (0, "Again")):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text("insert into step (recipe_id, position, text) values (:r, :p, :t)"),
                {"r": recipe_id, "p": position, "t": body},
            )


def test_source_type_is_limited(engine: Engine) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("insert into source (type) values ('video')"))
