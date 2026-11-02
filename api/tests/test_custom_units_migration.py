"""Migration 0013_custom_units: tables, checks, and a downgrade that refuses (spec 055 R19).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

TEN = {"g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"}


def _config() -> Config:
    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="module")
def migrated() -> Iterator[Engine]:
    url = database_url()
    assert url is not None
    command.upgrade(_config(), "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def conn(migrated: Engine) -> Iterator[Connection]:
    """Every write rolls back."""
    with migrated.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def _user(conn: Connection) -> uuid.UUID:
    user_id = uuid.uuid4()
    conn.execute(
        text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'x')"),
        {"id": user_id, "email": f"{user_id}@example.com"},
    )
    return user_id


def _recipe(conn: Connection) -> uuid.UUID:
    notebook_id = conn.execute(
        text("INSERT INTO notebook (name) VALUES ('Test notebook') RETURNING id")
    ).scalar_one()
    return conn.execute(
        text(
            "INSERT INTO recipe (notebook_id, title, base_servings)"
            " VALUES (:notebook, 'Beans', 4) RETURNING id"
        ),
        {"notebook": notebook_id},
    ).scalar_one()


def _line(conn: Connection, recipe_id: uuid.UUID, unit: str | None) -> None:
    conn.execute(
        text(
            "INSERT INTO recipe_ingredient (recipe_id, position, name, quantity, unit)"
            " VALUES (:recipe, 0, 'frijoles', 1, :unit)"
        ),
        {"recipe": recipe_id, "unit": unit},
    )


def _list_item(conn: Connection, kind: str) -> None:
    kitchen_owner = _user(conn)
    kitchen_id = conn.execute(
        text("INSERT INTO kitchens (id, name, owner_id) VALUES (:id, 'K', :o) RETURNING id"),
        {"id": uuid.uuid4(), "o": kitchen_owner},
    ).scalar_one()
    list_id = conn.execute(
        text("INSERT INTO shopping_list (id, kitchen_id) VALUES (:id, :k) RETURNING id"),
        {"id": uuid.uuid4(), "k": kitchen_id},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO shopping_list_item"
            " (id, shopping_list_id, origin, section, name, kind, amounts, notes, recipes,"
            "  position)"
            " VALUES (:id, :list, 'cart', 'measured', 'frijoles', :kind, CAST(:a AS jsonb),"
            "  '[]', '[]', 0)"
        ),
        {
            "id": uuid.uuid4(),
            "list": list_id,
            "kind": kind,
            "a": json.dumps([{"quantity": "3", "unit": "lata"}]),
        },
    )


def test_ten_defaults_are_seeded_with_no_references(conn: Connection) -> None:
    rows = conn.execute(
        text("SELECT name, reference_count FROM unit WHERE is_default ORDER BY name")
    ).all()
    assert {row.name for row in rows} >= TEN
    assert all(row.reference_count == 0 for row in rows if row.name in TEN)


def test_reference_count_follows_the_list(conn: Connection) -> None:
    people = [uuid.uuid4(), uuid.uuid4()]
    conn.execute(
        text("INSERT INTO unit (name, user_references) VALUES ('lata', :people)"),
        {"people": people},
    )
    assert (
        conn.execute(text("SELECT reference_count FROM unit WHERE name = 'lata'")).scalar_one()
        == 2
    )


def test_reference_count_refuses_a_direct_write(conn: Connection) -> None:
    conn.execute(text("INSERT INTO unit (name) VALUES ('lata')"))
    with pytest.raises(DBAPIError), conn.begin_nested():
        conn.execute(text("UPDATE unit SET reference_count = 9 WHERE name = 'lata'"))


@pytest.mark.parametrize("name", ["Lata", " lata", "lata ", "", "x" * 33])
def test_unit_name_shape_is_refused(conn: Connection, name: str) -> None:
    with pytest.raises(DBAPIError), conn.begin_nested():
        conn.execute(text("INSERT INTO unit (name) VALUES (:name)"), {"name": name})


def test_a_recipe_line_takes_a_custom_unit_and_no_blank_one(conn: Connection) -> None:
    recipe_id = _recipe(conn)
    _line(conn, recipe_id, "lata")
    other = _recipe(conn)
    with pytest.raises(DBAPIError), conn.begin_nested():
        _line(conn, other, "   ")


def test_custom_is_a_list_item_kind(conn: Connection) -> None:
    _list_item(conn, "custom")
    with pytest.raises(DBAPIError), conn.begin_nested():
        _list_item(conn, "other")


def test_cart_activity_allows_three_actions(conn: Connection) -> None:
    user_id = _user(conn)
    for action in ("created", "edited", "closed"):
        conn.execute(
            text("INSERT INTO cart_activity (user_id, action) VALUES (:u, :a)"),
            {"u": user_id, "a": action},
        )
    with pytest.raises(DBAPIError), conn.begin_nested():
        conn.execute(
            text("INSERT INTO cart_activity (user_id, action) VALUES (:u, 'opened')"),
            {"u": user_id},
        )


def test_deleting_a_user_removes_their_cart_activity(conn: Connection) -> None:
    user_id = _user(conn)
    conn.execute(
        text("INSERT INTO cart_activity (user_id, action) VALUES (:u, 'closed')"), {"u": user_id}
    )
    conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
    assert (
        conn.execute(
            text("SELECT count(*) FROM cart_activity WHERE user_id = :u"), {"u": user_id}
        ).scalar_one()
        == 0
    )


def test_is_admin_defaults_to_false(conn: Connection) -> None:
    user_id = _user(conn)
    assert (
        conn.execute(text("SELECT is_admin FROM users WHERE id = :u"), {"u": user_id}).scalar_one()
        is False
    )


def _commit_then_refuse_downgrade(migrated: Engine, write) -> None:
    """Commit the write, prove the downgrade refuses, then remove every row it made."""
    with migrated.begin() as connection:
        write(connection)
    try:
        with pytest.raises(RuntimeError, match="custom unit"):
            command.downgrade(_config(), "0012_notebook_invite")
    finally:
        with migrated.begin() as connection:
            connection.execute(text("DELETE FROM recipe WHERE title = 'Beans'"))
            connection.execute(text("DELETE FROM notebook WHERE name = 'Test notebook'"))
            connection.execute(text("DELETE FROM kitchens WHERE name = 'K'"))
            connection.execute(text("DELETE FROM users WHERE email ~ '^[0-9a-f-]{36}@example[.]com$'"))
    assert inspect(migrated).has_table("unit")


def test_downgrade_refuses_while_a_recipe_line_uses_a_custom_unit(migrated: Engine) -> None:
    _commit_then_refuse_downgrade(migrated, lambda c: _line(c, _recipe(c), "lata"))


def test_downgrade_refuses_while_a_list_item_uses_a_custom_unit(migrated: Engine) -> None:
    _commit_then_refuse_downgrade(migrated, lambda c: _list_item(c, "custom"))


def test_up_down_up(migrated: Engine) -> None:
    try:
        command.downgrade(_config(), "0012_notebook_invite")
        inspector = inspect(migrated)
        assert not inspector.has_table("unit")
        assert not inspector.has_table("cart_activity")
        assert "is_admin" not in {c["name"] for c in inspector.get_columns("users")}
    finally:
        command.upgrade(_config(), "head")
