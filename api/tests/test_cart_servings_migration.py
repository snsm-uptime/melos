"""Migration 0008_cart_servings: saved carts keep their amounts (spec 023 FR-018, R10, R11).

Requires DATABASE_URL. Skips when unset. Runs on the shared test database and restores head
before it returns. All names are invented.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

BEFORE = "0007_cart_and_edit_locks"
_MAIL = "@servings-migration.test"
_KITCHENS: list[UUID] = []


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
    command.downgrade(_config(url), BEFORE)
    yield eng
    command.upgrade(_config(url), "head")
    # Other suites count rows across the shared database, so nothing stays behind.
    with eng.begin() as conn:
        conn.execute(text("delete from kitchens where id = any(:ids)"), {"ids": _KITCHENS})
        conn.execute(text("delete from users where email like :mail"), {"mail": f"%{_MAIL}"})
    _KITCHENS.clear()
    eng.dispose()


def _insert(conn: Connection, sql: str, **values: object) -> None:
    conn.execute(text(sql), values)


def _cart(conn: Connection, user: UUID, people: int | None, *meals: int) -> list[UUID]:
    """A kitchen with two members and a cart holding one recipe per meals value."""
    kitchen, notebook, cart = uuid4(), uuid4(), uuid4()
    _KITCHENS.append(kitchen)
    other = uuid4()
    _insert(
        conn,
        "insert into users (id, email, password_hash) values (:id, :email, 'x')",
        id=other,
        email=f"{other}{_MAIL}",
    )
    _insert(
        conn,
        "insert into kitchens (id, name, owner_id) values (:id, 'Home', :user)",
        id=kitchen,
        user=user,
    )
    for member in (user, other):
        _insert(
            conn,
            "insert into kitchen_memberships (id, kitchen_id, user_id, role)"
            " values (:id, :kitchen, :user, 'owner')",
            id=uuid4(),
            kitchen=kitchen,
            user=member,
        )
    _insert(
        conn,
        "insert into notebook (id, name, kitchen_id) values (:id, 'N', :kitchen)",
        id=notebook,
        kitchen=kitchen,
    )
    _insert(
        conn,
        "insert into cart (id, kitchen_id, people) values (:id, :kitchen, :people)",
        id=cart,
        kitchen=kitchen,
        people=people,
    )
    recipes = []
    for number in meals:
        recipe = uuid4()
        recipes.append(recipe)
        _insert(
            conn,
            "insert into recipe (id, notebook_id, title, base_servings)"
            " values (:id, :notebook, 'R', 4)",
            id=recipe,
            notebook=notebook,
        )
        _insert(
            conn,
            "insert into cart_item (cart_id, recipe_id, meals) values (:cart, :recipe, :meals)",
            cart=cart,
            recipe=recipe,
            meals=number,
        )
    return recipes


def _value(conn: Connection, column: str, recipe: UUID) -> int:
    return conn.scalar(
        text(f"select {column} from cart_item where recipe_id = :id"),  # noqa: S608
        {"id": recipe},
    )


def test_saved_carts_convert_and_open_drafts_end(engine: Engine) -> None:
    url = database_url()
    assert url is not None
    user, session = uuid4(), uuid4()
    with engine.begin() as conn:
        _insert(
            conn,
            "insert into users (id, email, password_hash) values (:id, :email, 'x')",
            id=user,
            email=f"{user}{_MAIL}",
        )
        _insert(
            conn,
            "insert into sessions (id, token, user_id, expires_at)"
            " values (:id, :token, :user, now() + interval '1 hour')",
            id=session,
            token=str(session),
            user=user,
        )
        set_people = _cart(conn, user, 3, 2, 50)
        default_people = _cart(conn, user, None, 2)
        cart_id = conn.scalar(
            text("select cart_id from cart_item where recipe_id = :id"), {"id": set_people[0]}
        )
        membership = conn.scalar(
            text(
                "select m.id from kitchen_memberships m join cart c on c.kitchen_id = m.kitchen_id"
                " where c.id = :cart and m.user_id = :user"
            ),
            {"cart": cart_id, "user": user},
        )
        _insert(
            conn,
            "insert into cart_edit_lock (cart_id, session_id, user_id, membership_id,"
            " last_active_at, draft) values (:cart, :session, :user, :membership, now(),"
            ' \'{"people": 3, "items": []}\')',
            cart=cart_id,
            session=session,
            user=user,
            membership=membership,
        )

    command.upgrade(_config(url), "0008_cart_servings")

    with engine.connect() as conn:
        assert _value(conn, "servings", set_people[0]) == 6
        assert _value(conn, "servings", set_people[1]) == 99  # 150, capped
        assert _value(conn, "servings", default_people[0]) == 4  # two members × 2
        assert conn.scalar(text("select count(*) from cart_edit_lock")) == 0
        people = conn.scalar(
            text(
                "select count(*) from information_schema.columns"
                " where table_name = 'cart' and column_name = 'people'"
            )
        )
        assert people == 0

    command.downgrade(_config(url), BEFORE)

    with engine.connect() as conn:
        assert _value(conn, "meals", set_people[0]) == 6
        assert conn.scalar(text("select people from cart where id = :id"), {"id": cart_id}) == 1

    command.upgrade(_config(url), "0008_cart_servings")
