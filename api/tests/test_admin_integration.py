"""The dashboard over HTTP with Postgres (spec 055 contracts/admin-api.md, SC-006)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_carts_integration import People, _home, _join

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

SECTIONS = ("units", "ingredients", "recipes", "users")
KEYS = {
    "units": {"name", "user_references", "reference_count", "is_default", "created_at"},
    "ingredients": {"name", "recipes", "people"},
    "recipes": {
        "id",
        "title",
        "cart_adds",
        "notebook_name",
        "notebook_kind",
        "people_with_access",
    },
    "users": {
        "id",
        "alias",
        "open_sessions",
        "newest_session_at",
        "recipes_authored",
        "latest_recipe_at",
        "carts_created",
        "carts_edited",
        "carts_closed",
        "latest_cart_action_at",
    },
}


def _admin(db: Session, user_id: UUID) -> None:
    db.execute(text("UPDATE users SET is_admin = true WHERE id = :u"), {"u": user_id})
    db.flush()


def _recipe(client: TestClient, notebook_id: str, title: str, lines: list[dict], keep=()) -> str:
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": title,
            "base_servings": 4,
            "ingredient_lines": lines,
            "steps": ["a secret step"],
            "keep_units": list(keep),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def _line(name: str, unit: str = "g") -> dict:
    return {"name": name, "quantity": 1, "unit": unit}


def _cart(client: TestClient, kitchen_id: str, recipe_ids: list[str]) -> None:
    url = f"/kitchens/{kitchen_id}/cart"
    assert client.post(f"{url}/edit").status_code == 200
    items = [{"recipe_id": r, "servings": 2} for r in recipe_ids]
    assert client.put(f"{url}/draft", json={"items": items}).status_code == 200
    assert client.post(f"{url}/save").status_code == 200


def _section(client: TestClient, section: str) -> list[dict]:
    response = client.get(f"/admin/{section}")
    assert response.status_code == 200, response.text
    return response.json()[section]


def _one(rows: list[dict], key: str, value: object) -> dict:
    return next(row for row in rows if row[key] == value)


@pytest.mark.parametrize("section", SECTIONS)
def test_signed_out_and_non_admin_answers_equal_an_unknown_path(
    client: TestClient, section: str
) -> None:
    client.cookies.clear()
    unknown = client.get("/no-such-path")
    assert unknown.status_code == 404
    signed_out = client.get(f"/admin/{section}")
    people = People(client)
    people.register("plain")
    member = people.as_("plain").get(f"/admin/{section}")
    for response in (signed_out, member):
        assert response.status_code == 404
        assert response.content == unknown.content
        assert response.headers["content-type"] == unknown.headers["content-type"]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_a_write_method_shows_nothing_either(client: TestClient, method: str) -> None:
    client.cookies.clear()
    response = getattr(client, method)("/admin/units")
    assert response.status_code == 404
    assert response.content == client.get("/no-such-path").content


def test_no_body_can_set_the_flag(client: TestClient) -> None:
    people = People(client)
    people.register("sneak")
    me = people.as_("sneak")
    me.patch("/auth/me", json={"is_admin": True})
    assert me.get("/side-panel").json()["is_admin"] is False


@pytest.mark.parametrize("section", SECTIONS)
def test_response_keys_equal_the_contract(
    client: TestClient, db_session: Session, section: str
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    _admin(db_session, people.ids["ana"])
    recipe_id = _recipe(ana, notebook_id, "Keys", [_line("lentil")])
    _cart(ana, kitchen_id, [recipe_id])
    response = ana.get(f"/admin/{section}")
    assert set(response.json()) == {section}
    rows = response.json()[section]
    assert rows
    assert {key for row in rows for key in row} == KEYS[section]


def test_units_show_each_name_once_with_its_references(
    client: TestClient, db_session: Session
) -> None:
    people = People(client)
    for name in ("una", "dos", "tres"):
        people.register(name)
        person = people.as_(name)
        notebook = person.get("/notebooks/default").json()["id"]
        _recipe(person, notebook, "Beans", [_line("frijoles", "zlata")], keep=["zlata"])
    person = people.as_("una")
    notebook = person.get("/notebooks/default").json()["id"]
    _recipe(person, notebook, "Cream", [_line("crema", "zbote")], keep=["zbote"])
    _admin(db_session, people.ids["una"])

    rows = _section(person, "units")
    assert [row["name"] for row in rows].count("zlata") == 1
    lata = _one(rows, "name", "zlata")
    assert lata["reference_count"] == 3
    assert set(lata["user_references"]) == {str(uid) for uid in people.ids.values()}
    assert lata["is_default"] is False
    assert _one(rows, "name", "zbote")["reference_count"] == 1
    assert _one(rows, "name", "g")["is_default"] is True
    counts = [row["reference_count"] for row in rows]
    assert counts == sorted(counts, reverse=True)


def test_ingredients_count_recipes_and_authors_across_notebooks(
    client: TestClient, db_session: Session
) -> None:
    people = People(client)
    people.register("ana")
    people.register("ben")
    ana = people.as_("ana")
    notebook = ana.get("/notebooks/default").json()["id"]
    for title in ("One", "Two", "Three"):
        _recipe(ana, notebook, title, [_line("ztomate")])
    ben = people.as_("ben")
    _recipe(ben, ben.get("/notebooks/default").json()["id"], "Four", [_line("ztomate")])
    db_session.execute(
        text("INSERT INTO ingredient (notebook_id, name) VALUES (:n, 'zunused')"),
        {"n": notebook},
    )
    db_session.flush()
    _admin(db_session, people.ids["ana"])

    rows = _section(people.as_("ana"), "ingredients")
    assert _one(rows, "name", "ztomate") == {"name": "ztomate", "recipes": 4, "people": 2}
    assert _one(rows, "name", "zunused") == {"name": "zunused", "recipes": 0, "people": 0}
    assert [row["name"] for row in rows].count("ztomate") == 1


def test_a_deleted_author_does_not_count(client: TestClient, db_session: Session) -> None:
    people = People(client)
    people.register("ana")
    ana = people.as_("ana")
    notebook = ana.get("/notebooks/default").json()["id"]
    recipe_id = _recipe(ana, notebook, "Old", [_line("zgone")])
    db_session.execute(text("UPDATE recipe SET author_id = NULL WHERE id = :r"), {"r": recipe_id})
    db_session.flush()
    _admin(db_session, people.ids["ana"])
    rows = _section(ana, "ingredients")
    assert _one(rows, "name", "zgone") == {"name": "zgone", "recipes": 1, "people": 0}


def test_recipes_show_figures_and_no_content(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    recipe_id = _recipe(ana, notebook_id, "Sopa", [_line("zsecreto")])
    for _ in range(5):
        _cart(ana, kitchen_id, [recipe_id])
        _cart(ana, kitchen_id, [])
    _join(db_session, kitchen_id, people.register("cal"))
    personal_id = people.as_("cal").get("/notebooks/default").json()["id"]
    private = _recipe(people.as_("cal"), personal_id, "Privada", [_line("zotro")])
    _admin(db_session, people.ids["ana"])

    response = people.as_("ana").get("/admin/recipes")
    rows = response.json()["recipes"]
    sopa = _one(rows, "id", recipe_id)
    assert sopa["title"] == "Sopa" and sopa["cart_adds"] == 5
    assert sopa["notebook_kind"] == "kitchen" and sopa["people_with_access"] == 3
    other = _one(rows, "id", private)
    assert other["notebook_kind"] == "personal" and other["people_with_access"] == 1
    assert "zsecreto" not in response.text and "secret step" not in response.text


def test_users_show_activity_for_the_person_who_acted_only(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    first = _recipe(ana, notebook_id, "First", [_line("flour")])
    second = _recipe(ana, notebook_id, "Second", [_line("rice")])
    _cart(ana, kitchen_id, [first])
    _cart(ana, kitchen_id, [first, second])
    list_id = ana.get(f"/kitchens/{kitchen_id}/shopping-list").json()["list_id"]
    done = ana.post(f"/kitchens/{kitchen_id}/shopping-list/done", json={"list_id": list_id})
    assert done.status_code == 200, done.text
    # Discarding a draft records nothing.
    url = f"/kitchens/{kitchen_id}/cart"
    assert ana.post(f"{url}/edit").status_code == 200
    ana.put(f"{url}/draft", json={"items": [{"recipe_id": first, "servings": 2}]})
    assert ana.delete(f"{url}/edit").status_code in (200, 204)
    _admin(db_session, people.ids["ana"])

    response = ana.get("/admin/users")
    rows = response.json()["users"]
    row = _one(rows, "id", str(people.ids["ana"]))
    assert (row["carts_created"], row["carts_edited"], row["carts_closed"]) == (1, 1, 1)
    assert row["recipes_authored"] == 2
    assert row["open_sessions"] >= 1
    assert row["newest_session_at"] and row["latest_recipe_at"] and row["latest_cart_action_at"]
    ben = _one(rows, "id", str(people.ids["ben"]))
    assert (ben["carts_created"], ben["carts_edited"], ben["carts_closed"]) == (0, 0, 0)
    assert ben["latest_cart_action_at"] is None and ben["latest_recipe_at"] is None
    for private in ("password", "token", "@example.com"):
        assert private not in response.text


def test_users_come_by_alias_with_null_aliases_last(
    client: TestClient, db_session: Session
) -> None:
    people = People(client)
    people.register("zoe")
    db_session.execute(
        text(
            "INSERT INTO users (id, email, password_hash) VALUES (:i, 'noalias@example.com', 'x')"
        ),
        {"i": uuid4()},
    )
    db_session.flush()
    _admin(db_session, people.ids["zoe"])
    aliases = [row["alias"] for row in _section(people.as_("zoe"), "users")]
    assert aliases[-1] is None
    named = [alias for alias in aliases if alias is not None]
    assert named == sorted(named)
