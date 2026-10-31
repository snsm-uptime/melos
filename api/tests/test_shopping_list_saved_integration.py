"""The saved shopping list over HTTP with Postgres (spec 025).

Requires DATABASE_URL with migrations at head. Skips when unset.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from adapters.persistence.models import KitchenModel, ShoppingListModel, UserModel
from adapters.persistence.shopping_lists import SqlAlchemyShoppingListRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import database_url
from tests.test_carts_integration import _home
from tests.test_shopping_list_integration import (
    _cart,
    _list,
    bread_and_pancakes,
    measured,
    recipe,
    save_cart,
    shown,
    vague,
)

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _done(client: TestClient, kitchen_id: str):  # noqa: ANN202
    list_id = client.get(_list(kitchen_id)).json()["list_id"]
    return client.post(_list(kitchen_id) + "/done", json={"list_id": list_id})


def _add(client: TestClient, kitchen_id: str, **body: object):  # noqa: ANN202
    return client.post(_list(kitchen_id) + "/items", json=body)


def _history(kitchen_id: str) -> str:
    return f"/kitchens/{kitchen_id}/shopping-lists"


def test_a_saved_cart_makes_a_shared_list_equal_to_the_live_one(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    assert ana.get(_list(kitchen)).json()["status"] == "live"
    assert ana.post(_cart(kitchen, "/edit")).status_code == 200
    ana.put(
        _cart(kitchen, "/draft"),
        json={"items": [{"recipe_id": r, "servings": 2} for r in (bread, pancakes)]},
    )
    draft = ana.get(_list(kitchen)).json()
    assert draft["status"] == "draft"
    assert ana.post(_cart(kitchen, "/save")).status_code == 200

    saved = people.as_("ben").get(_list(kitchen)).json()
    assert saved["status"] == "active"
    assert saved["list_id"]
    assert (saved["lines"], saved["your_call"]) == (draft["lines"], draft["your_call"])


def test_the_list_follows_a_save_but_not_a_draft_or_recipe_edit(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    # as_ switches one client, so each step names its member.
    save_cart(people.as_("ana"), kitchen, [bread])
    before = people.as_("ben").get(_list(kitchen)).json()
    ana = people.as_("ana")
    ana.post(_cart(kitchen, "/edit"))
    ana.put(_cart(kitchen, "/draft"), json={"items": [{"recipe_id": pancakes, "servings": 2}]})
    assert people.as_("ben").get(_list(kitchen)).json() == before
    people.as_("ana").post(_cart(kitchen, "/save"))
    assert [ln[0] for ln in shown(people.as_("ben").get(_list(kitchen)).json())] == [
        "egg",
        "flour",
    ]


def test_hand_items_and_their_refusals(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb = _home(client, db_session)
    ana = people.as_("ana")
    assert ana.get(_list(kitchen)).json()["is_empty"] is True

    added = _add(ana, kitchen, name="Jabón")
    assert added.status_code == 201, added.text
    body = people.as_("ben").get(_list(kitchen)).json()
    assert (body["status"], body["is_empty"]) == ("active", False)
    item = body["hand_items"][0]
    assert (item["name"], item["quantity"]) == ("jabón", None)

    bad = _add(people.as_("ana"), kitchen, name=" ")
    assert (bad.status_code, bad.json()["code"]) == (422, "invalid_item")

    url = _list(kitchen) + f"/items/{item['id']}"
    ben = people.as_("ben")
    assert ben.delete(url).status_code == 200
    gone = ben.delete(url)
    assert (gone.status_code, gone.json()["code"]) == (404, "item_not_found")
    assert _done(people.as_("ana"), kitchen).json()["code"] == "list_empty"


def test_done_empties_the_cart_and_freezes_the_list(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread, pancakes])
    _add(ana, kitchen, name="soap", quantity="2", unit="unit")
    list_id = ana.get(_list(kitchen)).json()["list_id"]
    closed = _done(ana, kitchen)
    assert closed.status_code == 200, closed.text
    frozen = closed.json()
    assert frozen["closing_date"]

    again = ana.post(_list(kitchen) + "/done", json={"list_id": list_id})
    assert (again.status_code, again.json()["code"]) == (409, "list_not_active")

    assert ana.get(_cart(kitchen)).json()["entries"] == []
    after = ana.get(_list(kitchen)).json()
    assert (after["status"], after["is_empty"]) == ("live", True)

    assert ana.delete(f"/recipes/{bread}").status_code in (200, 204)
    read = ana.get(f"{_history(kitchen)}/{list_id}").json()
    assert read["hand_items"] == frozen["hand_items"]
    assert [ln["name"] for ln in read["lines"]] == [ln["name"] for ln in frozen["lines"]]
    chips = {r["title"]: r["exists"] for ln in read["lines"] for r in ln["recipes"]}
    assert chips == {"Bread": False, "Pancakes": True}

    save_cart(ana, kitchen, [pancakes])
    fresh = ana.get(_list(kitchen)).json()
    assert fresh["status"] == "active"
    assert fresh["list_id"] != list_id
    assert fresh["hand_items"] == []


def test_done_while_someone_else_edits(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _p = bread_and_pancakes(client, db_session)
    save_cart(people.as_("ana"), kitchen, [bread])
    assert people.as_("ben").post(_cart(kitchen, "/edit")).status_code == 200
    assert _done(people.as_("ana"), kitchen).status_code == 200
    assert people.as_("ben").post(_cart(kitchen, "/save")).status_code == 200
    assert people.as_("ana").get(_list(kitchen)).json()["status"] == "active"


def test_history_order_contents_and_access(client: TestClient, db_session: Session) -> None:
    people, kitchen, nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    salt = recipe(ana, nb, "Salad", [vague("salt", "to taste")])
    save_cart(ana, kitchen, [bread])
    _done(ana, kitchen)
    save_cart(ana, kitchen, [salt])
    _done(ana, kitchen)

    rows = ana.get(_history(kitchen)).json()["items"]
    assert [r["recipe_titles"] for r in rows] == [["Salad"], ["Bread"]]
    detail = ana.get(f"{_history(kitchen)}/{rows[0]['id']}").json()
    assert detail["your_call"][0]["name"] == "salt"

    missing = ana.get(f"{_history(kitchen)}/{uuid4()}")
    assert (missing.status_code, missing.json()["code"]) == (404, "list_not_found")
    people.register("zoe")
    outsider = people.as_("zoe")
    assert outsider.get(_history(kitchen)).status_code == 404
    assert outsider.get(f"{_history(kitchen)}/{rows[0]['id']}").status_code == 404
    assert _add(outsider, kitchen, name="x").status_code == 404


def test_another_kitchens_list_is_not_found(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _p = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    list_id = ana.get(_list(kitchen)).json()["list_id"]
    _done(ana, kitchen)
    other = ana.post("/kitchens", json={"name": "Other"}).json()
    other_id = other.get("id") or other["kitchen"]["id"]
    assert ana.get(f"{_history(other_id)}/{list_id}").status_code == 404


def test_archived_kitchen_reads_and_refuses(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _p = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    assert ana.post(f"/kitchens/{kitchen}/archive").status_code in (200, 204)
    body = ana.get(_list(kitchen)).json()
    assert body["kitchen_is_archived"] is True
    assert (_add(ana, kitchen, name="x").status_code) == 403
    assert _done(ana, kitchen).status_code == 403


def test_kitchen_delete_takes_its_lists(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _p = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    assert ana.get(_list(kitchen)).json()["list_id"]
    assert ana.delete(f"/kitchens/{kitchen}").status_code in (200, 204)
    db_session.expire_all()
    count = db_session.scalar(
        select(func.count())
        .select_from(ShoppingListModel)
        .where(ShoppingListModel.kitchen_id == kitchen)
    )
    assert count == 0


def test_two_simultaneous_first_lists_leave_one_active(engine: Engine) -> None:
    """Without the cart lock, so this reaches the partial unique index itself (R3)."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    kitchen_id, user_id = uuid4(), uuid4()
    with factory() as setup:
        setup.add(
            UserModel(
                id=user_id,
                email=f"list_{user_id.hex[:6]}@example.com",
                alias=f"list_{user_id.hex[:6]}",
                password_hash="x",
            )
        )
        setup.flush()
        setup.add(KitchenModel(id=kitchen_id, name="Race", owner_id=user_id))
        setup.commit()

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def create() -> None:
        try:
            with factory() as db:
                barrier.wait(timeout=5)
                SqlAlchemyShoppingListRepository(db).get_or_create_active(kitchen_id)
                db.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    try:
        threads = [threading.Thread(target=create) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert errors == []
        with factory() as check:
            count = check.scalar(
                select(func.count())
                .select_from(ShoppingListModel)
                .where(ShoppingListModel.kitchen_id == kitchen_id)
            )
        assert count == 1
    finally:
        with factory() as cleanup:
            cleanup.delete(cleanup.get(KitchenModel, kitchen_id))
            cleanup.delete(cleanup.get(UserModel, user_id))
            cleanup.commit()


def test_a_saved_list_of_100_recipes_opens_fast(client: TestClient, db_session: Session) -> None:
    people, kitchen, nb = _home(client, db_session)
    ana = people.as_("ana")
    ids = [
        recipe(ana, nb, f"Recipe {n}", [measured(f"item {n} {i}", 1, "cup") for i in range(5)])
        for n in range(100)
    ]
    save_cart(ana, kitchen, ids)
    started = time.perf_counter()
    response = ana.get(_list(kitchen))
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert len(response.json()["lines"]) == 500
    assert elapsed < 1


def test_done_uses_the_members_date_and_refuses_another_day(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _nb, bread, _p = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    list_id = ana.get(_list(kitchen)).json()["list_id"]
    today = datetime.now(UTC).date()

    far = ana.post(
        _list(kitchen) + "/done",
        json={"list_id": list_id, "closing_date": str(today - timedelta(days=5))},
    )
    assert (far.status_code, far.json()["code"]) == (422, "invalid_date")
    assert ana.get(_list(kitchen)).json()["list_id"] == list_id

    yesterday = str(today - timedelta(days=1))
    done = ana.post(
        _list(kitchen) + "/done", json={"list_id": list_id, "closing_date": yesterday}
    )
    assert done.status_code == 200, done.text
    assert done.json()["closing_date"] == yesterday
