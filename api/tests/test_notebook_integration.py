"""Postgres integration tests for notebooks and the ingredient catalog (spec 055).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset.
"""

from __future__ import annotations

import threading
from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalogReader
from adapters.persistence.models import (
    IngredientModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookModel,
    UserModel,
)
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.repositories import SqlAlchemyAuthUserRepository
from application.notebooks import GetDefaultNotebookCommand, GetDefaultNotebookService
from domain.notebook import Notebook
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import alias_from_email, claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _user(session: Session, alias: str | None = None) -> UUID:
    user_id = uuid4()
    session.add(
        UserModel(
            id=user_id,
            email=f"{user_id.hex[:12]}@example.com",
            alias=alias,
            password_hash="not-a-real-hash",
        )
    )
    session.flush()
    return user_id


def _kitchen(session: Session, owner_id: UUID) -> UUID:
    kitchen_id = uuid4()
    session.add(KitchenModel(id=kitchen_id, name="Test Kitchen", owner_id=owner_id))
    session.flush()
    return kitchen_id


def _notebook_count(session: Session, **owner: UUID) -> int:
    stmt = select(func.count()).select_from(NotebookModel)
    for column, value in owner.items():
        stmt = stmt.where(getattr(NotebookModel, column) == value)
    return session.scalar(stmt) or 0


def _register(client: TestClient, email: str) -> UUID:
    response = client.post("/auth/register", json={"email": email, "password": "password1"})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"])


# --- Schema and repositories (T007) -----------------------------------------


def test_second_notebook_for_same_kitchen_rejected(db_session: Session) -> None:
    kitchen_id = _kitchen(db_session, _user(db_session))
    db_session.add(NotebookModel(id=uuid4(), kitchen_id=kitchen_id))
    db_session.flush()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(NotebookModel(id=uuid4(), kitchen_id=kitchen_id))
        db_session.flush()


def test_repository_create_skips_second_kitchen_notebook(db_session: Session) -> None:
    kitchen_id = _kitchen(db_session, _user(db_session))
    repo = SqlAlchemyNotebookRepository(db_session)
    first = Notebook(id=uuid4(), kitchen_id=kitchen_id)
    repo.create(first)
    repo.create(Notebook(id=uuid4(), kitchen_id=kitchen_id))

    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 1
    found = repo.for_kitchen(kitchen_id)
    assert found is not None and found.id == first.id


def test_schema_allows_many_notebooks_per_member(db_session: Session) -> None:
    user_id = _user(db_session, alias="nb_many")
    repo = SqlAlchemyNotebookRepository(db_session)
    repo.create(Notebook(id=uuid4(), user_id=user_id, name="one"))
    repo.create(Notebook(id=uuid4(), user_id=user_id, name="two"))

    assert _notebook_count(db_session, user_id=user_id) == 2


@pytest.mark.parametrize("both", [True, False])
def test_notebook_needs_exactly_one_owner(db_session: Session, both: bool) -> None:
    user_id = _user(db_session)
    kitchen_id = _kitchen(db_session, user_id)
    owners = {"kitchen_id": kitchen_id, "user_id": user_id} if both else {}

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(NotebookModel(id=uuid4(), **owners))
        db_session.flush()


def test_catalog_reader_returns_only_that_notebooks_names(db_session: Session) -> None:
    user_id = _user(db_session)
    mine = NotebookModel(id=uuid4(), kitchen_id=_kitchen(db_session, user_id))
    other = NotebookModel(id=uuid4(), kitchen_id=_kitchen(db_session, user_id))
    db_session.add_all([mine, other])
    db_session.flush()
    db_session.add_all(
        [
            IngredientModel(id=uuid4(), notebook_id=mine.id, name="onion"),
            IngredientModel(id=uuid4(), notebook_id=mine.id, name="garlic"),
            IngredientModel(id=uuid4(), notebook_id=other.id, name="rice"),
        ]
    )
    db_session.flush()

    reader = SqlAlchemyIngredientCatalogReader(db_session)
    assert reader.names_for_notebook(mine.id) == ["garlic", "onion"]
    assert reader.names_for_notebook(other.id) == ["rice"]


def test_duplicate_ingredient_name_in_one_notebook_rejected(db_session: Session) -> None:
    notebook = NotebookModel(id=uuid4(), user_id=_user(db_session))
    db_session.add(notebook)
    db_session.flush()
    db_session.add(IngredientModel(id=uuid4(), notebook_id=notebook.id, name="onion"))
    db_session.flush()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(IngredientModel(id=uuid4(), notebook_id=notebook.id, name="onion"))
        db_session.flush()


def test_deleting_kitchen_or_user_removes_notebook_and_ingredients(db_session: Session) -> None:
    user_id = _user(db_session)
    kitchen_id = _kitchen(db_session, _user(db_session))
    kitchen_nb = NotebookModel(id=uuid4(), kitchen_id=kitchen_id)
    member_nb = NotebookModel(id=uuid4(), user_id=user_id)
    db_session.add_all([kitchen_nb, member_nb])
    db_session.flush()
    db_session.add_all(
        [
            IngredientModel(id=uuid4(), notebook_id=kitchen_nb.id, name="onion"),
            IngredientModel(id=uuid4(), notebook_id=member_nb.id, name="onion"),
        ]
    )
    db_session.flush()
    notebook_ids = (kitchen_nb.id, member_nb.id)

    db_session.execute(delete(KitchenModel).where(KitchenModel.id == kitchen_id))
    db_session.execute(delete(UserModel).where(UserModel.id == user_id))
    db_session.expire_all()

    for notebook_id in notebook_ids:
        assert db_session.get(NotebookModel, notebook_id) is None
        remaining = db_session.scalar(
            select(func.count())
            .select_from(IngredientModel)
            .where(IngredientModel.notebook_id == notebook_id)
        )
        assert remaining == 0


# --- Kitchen notebook (T009, T010) ------------------------------------------


def test_kitchen_route_for_members_and_404_for_others(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "nb_owner@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    assert created.status_code == 201, created.text
    kitchen_id = created.json()["id"]

    owner_read = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert owner_read.status_code == 200, owner_read.text
    body = owner_read.json()
    assert body["kind"] == "kitchen"
    assert body["kitchen_id"] == kitchen_id
    assert body["name"] == "Household"
    assert body["is_archived"] is False
    assert set(body) == {"id", "kind", "kitchen_id", "name", "is_archived"}

    client.post("/auth/sign-out")
    member_id = _register(client, "nb_member@example.com")

    outsider = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert outsider.status_code == 404
    assert outsider.json()["code"] == "kitchen_not_found"
    missing = client.get(f"/notebooks/kitchens/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json() == outsider.json()

    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=UUID(kitchen_id), user_id=member_id, role="member"
        )
    )
    db_session.flush()
    member_read = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert member_read.status_code == 200
    assert member_read.json()["id"] == body["id"]


def test_signup_personal_kitchen_gets_notebook_on_first_read(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "nb_personal@example.com")
    personal = client.get("/kitchens").json()["kitchens"][0]
    assert personal["name"] == "My kitchen"
    assert _notebook_count(db_session, kitchen_id=UUID(personal["id"])) == 0

    first = client.get(f"/notebooks/kitchens/{personal['id']}")
    second = client.get(f"/notebooks/kitchens/{personal['id']}")

    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    assert _notebook_count(db_session, kitchen_id=UUID(personal["id"])) == 1


# --- Member notebooks (T013) ------------------------------------------------


def test_default_notebook_created_once_and_read_by_id(
    client: TestClient, db_session: Session
) -> None:
    email = "nb_default@example.com"
    user_id = _register(client, email)
    assert db_session.get(UserModel, user_id).default_notebook_id is None

    first = client.get(f"/notebooks/members/{user_id}")
    second = client.get(f"/notebooks/members/{user_id}")

    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body == {"id": body["id"], "kind": "member", "user_id": str(user_id)}

    db_session.expire_all()
    assert str(db_session.get(UserModel, user_id).default_notebook_id) == body["id"]
    row = db_session.get(NotebookModel, UUID(body["id"]))
    assert row.name == f"{alias_from_email(email)}'s Notebook"
    assert _notebook_count(db_session, user_id=user_id) == 1

    by_id = client.get(f"/notebooks/members/{user_id}/{body['id']}")
    assert by_id.status_code == 200
    assert by_id.json() == body


def test_member_routes_404_for_others_and_missing(client: TestClient) -> None:
    owner_id = _register(client, "nb_private@example.com")
    notebook_id = client.get(f"/notebooks/members/{owner_id}").json()["id"]

    client.post("/auth/sign-out")
    other_id = _register(client, "nb_snoop@example.com")

    responses = [
        client.get(f"/notebooks/members/{owner_id}"),
        client.get(f"/notebooks/members/{owner_id}/{notebook_id}"),
        client.get(f"/notebooks/members/{other_id}/{notebook_id}"),
        client.get(f"/notebooks/members/{other_id}/{uuid4()}"),
    ]
    for response in responses:
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "notebook_not_found"
    assert len({r.text for r in responses}) == 1


def test_deleted_default_is_recreated_with_same_shape(
    client: TestClient, db_session: Session
) -> None:
    user_id = _register(client, "nb_recreate@example.com")
    first = client.get(f"/notebooks/members/{user_id}").json()

    db_session.execute(delete(NotebookModel).where(NotebookModel.id == UUID(first["id"])))
    db_session.expire_all()
    assert db_session.get(UserModel, user_id).default_notebook_id is None

    again = client.get(f"/notebooks/members/{user_id}")
    assert again.status_code == 200
    body = again.json()
    assert set(body) == set(first)
    assert body["id"] != first["id"]
    db_session.expire_all()
    assert str(db_session.get(UserModel, user_id).default_notebook_id) == body["id"]


def test_simultaneous_first_calls_make_one_notebook(engine: Engine) -> None:
    """Two connections race the first call; the user-row lock lets one create (SC-002)."""
    factory = sessionmaker(bind=engine)
    with factory() as setup:
        user_id = _user(setup, alias=f"race_{uuid4().hex[:8]}")
        setup.commit()

    both_read = threading.Barrier(2, timeout=10)

    class RacingRepo(SqlAlchemyNotebookRepository):
        def for_member(self, user_id: UUID) -> Notebook | None:
            found = super().for_member(user_id)
            both_read.wait()
            return found

    results: list[UUID] = []
    errors: list[BaseException] = []

    def first_call() -> None:
        with factory() as session:
            try:
                service = GetDefaultNotebookService(
                    RacingRepo(session),
                    SqlAlchemyUserDefaultNotebook(session),
                    SqlAlchemyAuthUserRepository(session),
                )
                notebook = service.execute(
                    GetDefaultNotebookCommand(actor_user_id=user_id, user_id=user_id)
                )
                session.commit()
                results.append(notebook.id)
            except BaseException as exc:  # surfaced in the main thread
                session.rollback()
                errors.append(exc)

    threads = [threading.Thread(target=first_call) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        assert not errors, errors
        assert len(results) == 2
        assert results[0] == results[1]
        with factory() as check:
            assert _notebook_count(check, user_id=user_id) == 1
            assert check.get(UserModel, user_id).default_notebook_id == results[0]
    finally:
        with factory() as cleanup:
            cleanup.execute(delete(UserModel).where(UserModel.id == user_id))
            cleanup.commit()
