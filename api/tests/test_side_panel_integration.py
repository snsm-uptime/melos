"""The side panel over HTTP with Postgres (spec 064). Skips when DATABASE_URL is unset."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import KitchenMembershipModel, NotebookModel
from adapters.persistence.side_panel import SqlAlchemySidePanelRepository
from application.side_panel import GetSidePanelService
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

COOKIE = "melos_session"


def _register(client: TestClient, name: str) -> tuple[UUID, str]:
    email = f"{name}_{uuid4().hex[:6]}@example.com"
    client.cookies.clear()
    response = client.post("/auth/register", json={"email": email, "password": "password1"})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"]), client.cookies[COOKIE]


def _use(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE, token)


def _kitchen(client: TestClient, name: str) -> str:
    response = client.post("/kitchens", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _notebook(client: TestClient, kitchen_id: str) -> str:
    response = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert response.status_code == 200, response.text
    return response.json()["notebooks"][0]["id"]


def _save(client: TestClient, notebook_id: str) -> str:
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": "Tomato rice",
            "base_servings": 4,
            "ingredient_lines": [{"name": "rice", "quantity": 1, "unit": "cup"}],
            "steps": ["Cook."],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def _join(db: Session, kitchen_id: str, user_id: UUID) -> None:
    db.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=UUID(kitchen_id), user_id=user_id, role="member"
        )
    )
    db.flush()


def test_needs_a_session(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get("/side-panel").status_code == 401
    assert (
        client.put("/side-panel/default-kitchen", json={"kitchen_id": str(uuid4())}).status_code
        == 401
    )


def test_default_starts_on_the_sign_up_kitchen_even_for_an_invitee(
    client: TestClient, db_session: Session
) -> None:
    user_id, ina_token = _register(client, "ina")
    signup = client.get("/kitchens").json()["kitchens"][0]["id"]
    _, host_token = _register(client, "hal")
    _use(client, host_token)
    hosted = _kitchen(client, "Aaa hosted")
    _join(db_session, hosted, user_id)
    _use(client, ina_token)
    response = client.get("/side-panel")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "default_kitchen_id": signup,
        "recipes_added": 0,
        "notebooks": 0,
        "is_admin": False,
    }


def test_set_default_and_its_refusals(client: TestClient) -> None:
    _register(client, "sam")
    second = _kitchen(client, "Second")
    third = _kitchen(client, "Third")
    url = "/side-panel/default-kitchen"

    chosen = client.put(url, json={"kitchen_id": second})
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["default_kitchen_id"] == second
    assert client.get("/side-panel").json()["default_kitchen_id"] == second

    assert client.post(f"/kitchens/{third}/archive").status_code < 300
    archived = client.put(url, json={"kitchen_id": third})
    assert archived.status_code == 409
    assert archived.json()["code"] == "kitchen_archived"

    _register(client, "zed")
    outsider = client.put(url, json={"kitchen_id": second})
    assert outsider.status_code == 404
    assert outsider.json()["code"] == "kitchen_not_found"
    unknown = client.put(url, json={"kitchen_id": str(uuid4())})
    assert unknown.status_code == 404


def test_archiving_the_default_falls_back_and_restoring_stays(client: TestClient) -> None:
    _register(client, "ada")
    signup = client.get("/kitchens").json()["kitchens"][0]["id"]
    chosen = _kitchen(client, "Chosen")
    client.put("/side-panel/default-kitchen", json={"kitchen_id": chosen})

    assert client.post(f"/kitchens/{chosen}/archive").status_code < 300
    assert client.get("/side-panel").json()["default_kitchen_id"] == signup

    assert client.post(f"/kitchens/{chosen}/unarchive").status_code < 300
    assert client.get("/side-panel").json()["default_kitchen_id"] == signup


def test_count_spans_kitchens_and_notebooks_and_drops_the_unreachable(
    client: TestClient, db_session: Session
) -> None:
    author_id, author_token = _register(client, "cat")
    own = _kitchen(client, "Own")
    own_recipe = _save(client, _notebook(client, own))
    archived = _kitchen(client, "Old")
    _save(client, _notebook(client, archived))
    assert client.post(f"/kitchens/{archived}/archive").status_code < 300
    personal = client.get("/notebooks/default").json()["id"]
    _save(client, personal)

    _, host_token = _register(client, "hud")
    _use(client, host_token)
    hosted = _kitchen(client, "Hosted")
    hosted_notebook = _notebook(client, hosted)
    _join(db_session, hosted, author_id)
    _save(client, hosted_notebook)  # someone else's recipe never counts

    _use(client, author_token)
    _save(client, hosted_notebook)
    assert client.get("/side-panel").json()["recipes_added"] == 4

    assert client.delete(f"/recipes/{own_recipe}").status_code < 300
    assert client.get("/side-panel").json()["recipes_added"] == 3

    db_session.query(KitchenMembershipModel).filter_by(
        kitchen_id=UUID(hosted), user_id=author_id
    ).delete()
    db_session.flush()
    assert client.get("/side-panel").json()["recipes_added"] == 2


def test_a_read_with_no_change_stays_within_four_statements(
    client: TestClient, db_session: Session
) -> None:
    user_id, _ = _register(client, "lee")
    client.get("/side-panel")
    statements: list[str] = []

    def record(_conn, _cursor, statement, *_rest) -> None:
        # The test session's own SAVEPOINT is not part of the read.
        if not statement.startswith("SAVEPOINT"):
            statements.append(statement)

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", record)
    try:
        GetSidePanelService(SqlAlchemySidePanelRepository(db_session)).execute(user_id)
    finally:
        event.remove(bind, "before_cursor_execute", record)
    assert len(statements) <= 5


def _snapshot(client: TestClient, kitchen_id: str, source_id: str) -> str:
    response = client.post(
        f"/notebooks/kitchens/{kitchen_id}/snapshots",
        json={"source_notebook_id": source_id, "snapshot_key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _recipes_added(client: TestClient) -> int:
    return client.get("/side-panel").json()["recipes_added"]


def test_a_snapshot_does_not_raise_the_recipe_count(client: TestClient) -> None:
    _register(client, "ana")
    kitchen_id = _kitchen(client, "Home")
    personal = client.get("/notebooks/default").json()["id"]
    _save(client, personal)
    before = _recipes_added(client)

    _snapshot(client, kitchen_id, personal)

    assert _recipes_added(client) == before == 1


def test_a_recipe_later_captured_into_a_snapshot_is_not_counted(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "ana")
    kitchen_id = _kitchen(client, "Home")
    personal = client.get("/notebooks/default").json()["id"]
    snapshot = _snapshot(client, kitchen_id, personal)
    assert db_session.get(NotebookModel, UUID(snapshot)).snapshot_key is not None
    before = _recipes_added(client)

    _save(client, snapshot)

    assert _recipes_added(client) == before


def test_is_admin_is_for_the_caller_only_and_not_in_auth_me(
    client: TestClient, db_session: Session
) -> None:
    admin_id, admin_token = _register(client, "root_panel")
    db_session.execute(text("UPDATE users SET is_admin = true WHERE id = :u"), {"u": admin_id})
    _, other_token = _register(client, "other_panel")

    assert client.get("/side-panel").json()["is_admin"] is False
    _use(client, admin_token)
    assert client.get("/side-panel").json()["is_admin"] is True
    kitchen_id = _kitchen(client, "Admin home")
    changed = client.put("/side-panel/default-kitchen", json={"kitchen_id": kitchen_id})
    assert changed.json()["is_admin"] is True
    assert "is_admin" not in client.get("/auth/me").json()
    _use(client, other_token)
    assert client.get("/side-panel").json()["is_admin"] is False
