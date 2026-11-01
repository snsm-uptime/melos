# ruff: noqa: F401, F811 - fixtures are imported from the invite suite and named as parameters.
"""Leaving a notebook and removing a member over HTTP with Postgres (spec 057 User Story 3)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import (
    IngredientModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeEditLockModel,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_notebook_invites_integration import (
    _accept,
    _invite,
    _join,
    _names,
    _register,
    _role,
    _token,
    _use,
    ana,
    client,
    mailer,
)
from tests.test_notebook_snapshots_integration import _kitchen, _personal, _recipe
from tests.test_recipe_manage_integration import _edit_body
from tests.test_recipe_save_integration import _body

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _locks(db: Session, user_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(RecipeEditLockModel)
            .where(RecipeEditLockModel.user_id == user_id)
        )
        or 0
    )


def _assert_shut_out(client, notebook_id: UUID, recipe_id: UUID) -> None:
    assert client.get(f"/notebooks/{notebook_id}").status_code == 404
    assert client.get(f"/notebooks/{notebook_id}/recipes").status_code == 404
    assert client.get(f"/notebooks/{notebook_id}/members").status_code == 404
    assert client.get(f"/recipes/{recipe_id}").status_code == 404
    assert client.post("/recipes", json=_body(str(notebook_id))).status_code == 404
    listed = [row["id"] for row in client.get("/notebooks").json()["notebooks"]]
    assert str(notebook_id) not in listed


@pytest.mark.parametrize("how", ["leave", "remove"])
def test_access_ends_and_the_work_stays(client, db_session: Session, mailer, ana, how: str) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    own_recipe = _recipe(db_session, notebook_id, owner)
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    added = client.post("/recipes", json=_body(str(notebook_id)))
    assert added.status_code == 201
    ben_recipe = added.json()["recipe"]["id"]
    names = _names(db_session, notebook_id)
    assert names

    assert client.post(f"/recipes/{own_recipe}/edit-lock").status_code == 200
    assert _locks(db_session, ben_id) == 1

    if how == "leave":
        assert client.delete(f"/notebooks/{notebook_id}/members/me").status_code == 204
    else:
        _use(client, cookie)
        response = client.delete(f"/notebooks/{notebook_id}/members/{ben_id}")
        assert response.status_code == 204
        members = client.get(f"/notebooks/{notebook_id}/members").json()["members"]
        assert str(ben_id) not in [row["user_id"] for row in members]

    assert _role(db_session, notebook_id, ben_id) is None
    assert _locks(db_session, ben_id) == 0

    _use(client, ben_cookie)
    _assert_shut_out(client, notebook_id, own_recipe)

    _use(client, cookie)
    kept = client.get(f"/recipes/{ben_recipe}").json()
    assert kept["author_alias"].startswith("ben")
    assert _names(db_session, notebook_id) == names
    assert client.post(f"/recipes/{own_recipe}/edit-lock").status_code == 200


def test_a_save_after_removal_is_not_found(client, db_session: Session, mailer, ana) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    recipe_id = _recipe(db_session, notebook_id, owner)
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    recipe = client.get(f"/recipes/{recipe_id}").json()
    client.post(f"/recipes/{recipe_id}/edit-lock")

    _use(client, cookie)
    client.delete(f"/notebooks/{notebook_id}/members/{ben_id}")

    _use(client, ben_cookie)
    save = client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe, title="Too late"))
    assert save.status_code == 404
    _use(client, cookie)
    assert client.get(f"/recipes/{recipe_id}").json()["title"] == recipe["title"]


def test_owner_cannot_leave_or_be_removed(client, mailer, ana) -> None:
    owner, cookie, notebook_id = ana
    _use(client, cookie)
    leave = client.delete(f"/notebooks/{notebook_id}/members/me")
    assert (leave.status_code, leave.json()["code"]) == (403, "notebook_owner_stays")
    remove = client.delete(f"/notebooks/{notebook_id}/members/{owner}")
    assert (remove.status_code, remove.json()["code"]) == (403, "notebook_owner_stays")


def test_removing_someone_not_in_the_notebook(client, ana) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    response = client.delete(f"/notebooks/{notebook_id}/members/{uuid4()}")
    assert (response.status_code, response.json()["code"]) == (404, "notebook_member_not_found")


def test_a_member_cannot_remove_another(client, db_session: Session, mailer, ana) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    carla_id, carla_cookie, carla_email = _register(client, "carla")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    _join(client, mailer, notebook_id, cookie, carla_cookie, carla_email)
    response = client.delete(f"/notebooks/{notebook_id}/members/{ben_id}")
    assert (response.status_code, response.json()["code"]) == (403, "notebook_owner_only")
    assert _role(db_session, notebook_id, ben_id) == "member"


def test_rejoining_gets_a_new_join_date_and_merges_again(
    client, db_session: Session, mailer
) -> None:
    owner, cookie, _ = _register(client, "ana")
    notebook_id = _personal(db_session, owner)
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    own = _personal(db_session, ben_id, "Ben's", names=("saffron",))
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    first = db_session.get(NotebookMembershipModel, (notebook_id, ben_id))
    first.created_at = first.created_at.replace(year=2020)
    db_session.flush()
    joined_first = first.created_at
    assert client.delete(f"/notebooks/{notebook_id}/members/me").status_code == 204
    db_session.expire_all()

    db_session.add(IngredientModel(notebook_id=own, name="cumin"))
    db_session.flush()
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    again = db_session.get(NotebookMembershipModel, (notebook_id, ben_id))
    assert again.created_at > joined_first
    assert _names(db_session, notebook_id) == ["cumin", "saffron"]


def test_a_used_link_does_not_let_a_removed_member_back_in(
    client, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    token = _token(mailer)
    _use(client, cookie)
    client.delete(f"/notebooks/{notebook_id}/members/{ben_id}")
    _use(client, ben_cookie)
    assert _accept(client, token).status_code == 410
    assert _role(db_session, notebook_id, ben_id) is None


def test_member_list_has_aliases_and_no_email(client, mailer, ana) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    response = client.get(f"/notebooks/{notebook_id}/members")
    assert response.status_code == 200
    assert "@" not in response.text
    rows = response.json()["members"]
    assert [row["role"] for row in rows] == ["owner", "member"]
    assert rows[0]["user_id"] == str(owner) and rows[0]["is_self"] is False
    assert rows[1]["user_id"] == str(ben_id) and rows[1]["is_self"] is True
    assert set(rows[0]) == {"user_id", "alias", "role", "is_self"}


def test_kitchen_notebook_has_no_member_routes(client, db_session: Session, ana) -> None:
    owner, cookie, _ = ana
    kitchen = _kitchen(db_session, owner)
    notebook_id = uuid4()
    db_session.add(NotebookModel(id=notebook_id, name="Home", kitchen_id=kitchen))
    db_session.flush()
    _use(client, cookie)
    for method, path in (
        ("GET", f"/notebooks/{notebook_id}/members"),
        ("DELETE", f"/notebooks/{notebook_id}/members/me"),
        ("DELETE", f"/notebooks/{notebook_id}/members/{owner}"),
        ("GET", f"/notebooks/{notebook_id}/invites"),
    ):
        response = client.request(method, path)
        assert (response.status_code, response.json()["code"]) == (403, "notebook_not_shareable")
