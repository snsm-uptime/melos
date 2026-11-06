"""Bought on the saved shopping list over HTTP with Postgres (spec 070 US1).

Requires DATABASE_URL with migrations at head. Skips when unset.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_carts_integration import People
from tests.test_shopping_list_integration import (
    _list,
    bread_and_pancakes,
    measured,
    recipe,
    save_cart,
    vague,
)

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _mark(client: TestClient, kitchen_id: str, item_id: str, bought: bool):  # noqa: ANN202
    return client.patch(_list(kitchen_id) + f"/items/{item_id}", json={"bought": bought})


def _by_name(body: dict) -> dict[str, dict]:
    items = body["lines"] + body["your_call"] + body["hand_items"]
    return {item["name"]: item for item in items}


def test_a_member_marks_and_the_other_sees_it(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    save_cart(people.as_("ana"), kitchen, [bread, pancakes])
    egg = _by_name(people.as_("ana").get(_list(kitchen)).json())["egg"]
    marked = _mark(people.as_("ana"), kitchen, egg["id"], True)
    assert marked.status_code == 200, marked.text
    assert _by_name(marked.json())["egg"]["bought"] is True

    seen = _by_name(people.as_("ben").get(_list(kitchen)).json())
    assert seen["egg"]["bought"] is True and seen["flour"]["bought"] is False

    _mark(people.as_("ben"), kitchen, egg["id"], False)
    assert _by_name(people.as_("ana").get(_list(kitchen)).json())["egg"]["bought"] is False


def test_last_write_wins(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _ = bread_and_pancakes(client, db_session)
    save_cart(people.as_("ana"), kitchen, [bread])
    flour = _by_name(people.as_("ana").get(_list(kitchen)).json())["flour"]
    assert _mark(people.as_("ana"), kitchen, flour["id"], True).status_code == 200
    assert _mark(people.as_("ben"), kitchen, flour["id"], False).status_code == 200
    assert _by_name(people.as_("ana").get(_list(kitchen)).json())["flour"]["bought"] is False


def test_a_cart_save_keeps_unchanged_lines_and_resets_grown_ones(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    salty = recipe(ana, nb, "Soup", [measured("water", 1, "l"), vague("salt", "a pinch")])
    save_cart(ana, kitchen, [bread, salty])
    body = _by_name(ana.get(_list(kitchen)).json())
    for name in ("flour", "water", "salt"):
        assert _mark(ana, kitchen, body[name]["id"], True).status_code == 200
    ana.post(_list(kitchen) + "/items", json={"name": "soap"})
    soap = _by_name(ana.get(_list(kitchen)).json())["soap"]
    _mark(ana, kitchen, soap["id"], True)

    # Pancakes add a cup of flour (a unit added); the soup and salt do not change.
    save_cart(ana, kitchen, [bread, salty, pancakes])
    after = _by_name(ana.get(_list(kitchen)).json())
    assert after["flour"]["bought"] is False
    assert after["water"]["bought"] is True
    assert after["salt"]["bought"] is True
    assert after["egg"]["bought"] is False
    assert after["soap"]["bought"] is True

    # More servings: the water grows and goes back to not bought.
    save_cart(ana, kitchen, [bread, salty, pancakes], servings=8)
    assert _by_name(ana.get(_list(kitchen)).json())["water"]["bought"] is False


def test_done_keeps_the_flags_and_refuses_changes(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _ = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    body = ana.get(_list(kitchen)).json()
    flour = _by_name(body)["flour"]
    _mark(ana, kitchen, flour["id"], True)
    closed = ana.post(_list(kitchen) + "/done", json={"list_id": body["list_id"]})
    assert closed.status_code == 200, closed.text
    assert _by_name(closed.json())["flour"]["bought"] is True
    read = ana.get(f"/kitchens/{kitchen}/shopping-lists/{body['list_id']}").json()
    assert _by_name(read)["flour"]["bought"] is True

    refused = _mark(ana, kitchen, flour["id"], False)
    assert (refused.status_code, refused.json()["code"]) == (409, "list_closed")


def test_archived_unknown_and_stranger(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb, bread, _ = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen, [bread])
    flour = _by_name(ana.get(_list(kitchen)).json())["flour"]

    unknown = _mark(ana, kitchen, "00000000-0000-0000-0000-000000000000", True)
    assert (unknown.status_code, unknown.json()["code"]) == (404, "item_not_found")

    stranger = People(client)
    stranger.register("cleo")
    refused = _mark(stranger.as_("cleo"), kitchen, flour["id"], True)
    assert refused.status_code == 404

    assert people.as_("ana").post(f"/kitchens/{kitchen}/archive").status_code == 200
    archived = _mark(people.as_("ana"), kitchen, flour["id"], True)
    assert (archived.status_code, archived.json()["code"]) == (403, "kitchen_archived")
