"""The kitchen cart and its edit lock over HTTP with Postgres (spec 022).

Requires DATABASE_URL (Compose db or CI Postgres 16) with migrations at head. Skips when unset.
Two members of one kitchen keep their own session cookies; the client switches between them.
The one true-concurrency test commits rows of its own on two connections and cleans them up.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.carts import SqlAlchemyCartRepository
from adapters.persistence.edit_locks import SqlAlchemyEditLockRepository
from adapters.persistence.models import (
    CartEditLockModel,
    CartItemModel,
    CartModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookModel,
    RecipeModel,
    SessionModel,
    UserModel,
)
from adapters.persistence.repositories import SqlAlchemyKitchenRepository
from application.carts import StartCartEditService
from application.ports import SessionRef
from domain.errors import CartLockedError
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
COOKIE = "melos_session"


class People:
    """Registered members and their session tokens; `as_(name)` switches the client."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.tokens: dict[str, str] = {}
        self.ids: dict[str, UUID] = {}

    def register(self, name: str) -> UUID:
        email = f"{name}_{uuid4().hex[:6]}@example.com"
        self.client.cookies.clear()
        response = self.client.post("/auth/register", json={"email": email, "password": PASSWORD})
        assert response.status_code == 201, response.text
        claim_alias(self.client, email)
        self.tokens[name] = self.client.cookies[COOKIE]
        self.ids[name] = UUID(self.client.get("/auth/me").json()["user_id"])
        return self.ids[name]

    def as_(self, name: str) -> TestClient:
        self.client.cookies.clear()
        self.client.cookies.set(COOKIE, self.tokens[name])
        return self.client


def _kitchen(client: TestClient) -> tuple[str, str]:
    kitchen = client.post("/kitchens", json={"name": "Home"})
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]
    listed = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert listed.status_code == 200, listed.text
    return kitchen_id, listed.json()["notebooks"][0]["id"]


def _join(db: Session, kitchen_id: str, user_id: UUID) -> UUID:
    membership_id = uuid4()
    db.add(
        KitchenMembershipModel(
            id=membership_id, kitchen_id=UUID(kitchen_id), user_id=user_id, role="member"
        )
    )
    db.flush()
    return membership_id


def _save(client: TestClient, notebook_id: str, title: str = "Tomato rice", base: int = 4) -> str:
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": title,
            "base_servings": base,
            "ingredient_lines": [{"name": "rice", "quantity": 1, "unit": "cup"}],
            "steps": ["Cook."],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def _home(client: TestClient, db: Session) -> tuple[People, str, str]:
    people = People(client)
    people.register("ana")
    kitchen_id, notebook_id = _kitchen(people.as_("ana"))
    _join(db, kitchen_id, people.register("ben"))
    return people, kitchen_id, notebook_id


def _url(kitchen_id: str, path: str = "") -> str:
    return f"/kitchens/{kitchen_id}/cart{path}"


def _locks(db: Session, kitchen_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(CartEditLockModel)
        .join(CartModel, CartModel.id == CartEditLockModel.cart_id)
        .where(CartModel.kitchen_id == UUID(kitchen_id))
    )


def _count(db: Session, recipe_id: str) -> int:
    return db.scalar(select(RecipeModel.cart_add_count).where(RecipeModel.id == UUID(recipe_id)))


# --- US1 ------------------------------------------------------------------------------------


def test_add_save_see_and_remove(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    empty = ana.get(_url(kitchen_id))
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["entries"] == [] and "people" not in body
    assert body["editor"] is None and body["can_edit"]

    a = _save(ana, notebook_id, "A")
    b = _save(ana, notebook_id, "B")
    for recipe_id in (a, b):
        added = ana.post(_url(kitchen_id, "/draft/items"), json={"recipe_id": recipe_id})
        assert added.status_code == 200, added.text
    assert added.json()["entries"] == []
    assert [e["title"] for e in added.json()["draft"]["entries"]] == ["A", "B"]
    saved = ana.post(_url(kitchen_id, "/save"))
    assert saved.status_code == 200, saved.text
    entries = ana.get(_url(kitchen_id)).json()["entries"]
    assert [(e["title"], e["servings"], e["factor"]) for e in entries] == [
        ("A", 4, "1"),
        ("B", 4, "1"),
    ]

    assert ana.delete(_url(kitchen_id, f"/draft/items/{a}")).status_code == 200
    ana.post(_url(kitchen_id, "/save"))
    assert [e["recipe_id"] for e in ana.get(_url(kitchen_id)).json()["entries"]] == [b]


def test_personal_recipe_and_non_member(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    ana = people.as_("ana")
    personal = _save(ana, ana.get("/notebooks/default").json()["id"])
    refused = ana.post(_url(kitchen_id, "/draft/items"), json={"recipe_id": personal})
    assert refused.status_code == 404 and refused.json()["code"] == "recipe_not_found"

    people.register("cat")
    cat = people.as_("cat")
    outsider = cat.get(_url(kitchen_id))
    unknown = cat.get(_url(str(uuid4())))
    assert outsider.status_code == unknown.status_code == 404
    assert outsider.json() == unknown.json()


def test_discard_is_idempotent(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    ana = people.as_("ana")
    assert ana.delete(_url(kitchen_id, "/edit")).status_code == 204
    ana.post(_url(kitchen_id, "/edit"))
    assert ana.delete(_url(kitchen_id, "/edit")).status_code == 204
    assert ana.delete(_url(kitchen_id, "/edit")).status_code == 204
    assert _locks(db_session, kitchen_id) == 0


# --- US2 ------------------------------------------------------------------------------------


def test_servings_and_factor(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = _save(ana, notebook_id)
    ana.post(_url(kitchen_id, "/edit"))
    put = ana.put(_url(kitchen_id, "/draft"), json={"items": [{"recipe_id": a, "servings": 6}]})
    assert put.status_code == 200, put.text
    bad = ana.put(_url(kitchen_id, "/draft"), json={"items": [{"recipe_id": a, "servings": 0}]})
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_value"
    assert bad.json()["field"] == "servings"
    draft = ana.get(_url(kitchen_id)).json()["draft"]
    assert draft["entries"][0]["servings"] == 6
    ana.post(_url(kitchen_id, "/save"))
    assert ana.get(_url(kitchen_id)).json()["entries"][0]["factor"] == "1.5"


# --- US3 ------------------------------------------------------------------------------------


def test_one_editor_and_sign_out_frees_the_cart(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    assert people.as_("ana").post(_url(kitchen_id, "/edit")).status_code == 200
    refused = people.as_("ben").post(_url(kitchen_id, "/edit"))
    assert refused.status_code == 409 and refused.json()["code"] == "cart_locked"
    assert refused.json()["editor_alias"].startswith("ana")
    seen = people.as_("ben").get(_url(kitchen_id)).json()
    assert seen["editor"]["is_me"] is False and seen["can_edit"] is False
    assert seen["draft"] is None and seen["editor"]["idle_expires_at"] is None

    people.as_("ana").post("/auth/sign-out")
    assert _locks(db_session, kitchen_id) == 0
    assert people.as_("ben").post(_url(kitchen_id, "/edit")).status_code == 200
    people.as_("ben").post(_url(kitchen_id, "/save"))
    assert _locks(db_session, kitchen_id) == 0


def test_expired_session_and_idle_lock_free_the_cart(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    people.as_("ana").post(_url(kitchen_id, "/edit"))
    db_session.execute(
        update(SessionModel)
        .where(SessionModel.token == people.tokens["ana"])
        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    assert people.as_("ben").post(_url(kitchen_id, "/edit")).status_code == 200

    db_session.execute(
        update(CartEditLockModel).values(last_active_at=func.now() - timedelta(minutes=5))
    )
    people.register("ana2")
    _join(db_session, kitchen_id, people.ids["ana2"])
    assert people.as_("ana2").post(_url(kitchen_id, "/edit")).status_code == 200
    lost = people.as_("ben").post(_url(kitchen_id, "/save"))
    assert lost.status_code == 409 and lost.json()["code"] == "cart_locked"
    people.as_("ana2").delete(_url(kitchen_id, "/edit"))
    lost = people.as_("ben").post(_url(kitchen_id, "/save"))
    assert lost.status_code == 409 and lost.json()["code"] == "not_editing"


def test_archive_ends_the_lock_for_good(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = _save(ana, notebook_id)
    ana.post(_url(kitchen_id, "/draft/items"), json={"recipe_id": a})
    assert ana.post(f"/kitchens/{kitchen_id}/archive").status_code == 200
    assert _locks(db_session, kitchen_id) == 0
    refused = ana.post(_url(kitchen_id, "/edit"))
    assert refused.status_code == 403 and refused.json()["code"] == "kitchen_archived"
    assert ana.get(_url(kitchen_id)).status_code == 200
    assert ana.post(f"/kitchens/{kitchen_id}/unarchive").status_code == 200
    body = ana.get(_url(kitchen_id)).json()
    assert body["editor"] is None and body["draft"] is None


def test_removed_membership_deletes_the_lock(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    people.as_("ben").post(_url(kitchen_id, "/edit"))
    membership = db_session.scalar(
        select(KitchenMembershipModel).where(
            KitchenMembershipModel.user_id == people.ids["ben"],
            KitchenMembershipModel.kitchen_id == UUID(kitchen_id),
        )
    )
    db_session.delete(membership)
    db_session.flush()
    assert _locks(db_session, kitchen_id) == 0
    _join(db_session, kitchen_id, people.ids["ben"])
    assert _locks(db_session, kitchen_id) == 0
    assert people.as_("ben").get(_url(kitchen_id)).json()["editor"] is None


# --- US5 ------------------------------------------------------------------------------------


def test_deletes_cascade_out_of_the_cart(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a, b = _save(ana, notebook_id, "A"), _save(ana, notebook_id, "B")
    ana.post(_url(kitchen_id, "/edit"))
    ana.put(
        _url(kitchen_id, "/draft"),
        json={"items": [{"recipe_id": a, "servings": 1}, {"recipe_id": b, "servings": 1}]},
    )
    ana.post(_url(kitchen_id, "/save"))
    assert ana.delete(f"/recipes/{a}").status_code == 204
    body = ana.get(_url(kitchen_id)).json()
    assert [e["recipe_id"] for e in body["entries"]] == [b]

    db_session.delete(db_session.get(NotebookModel, UUID(notebook_id)))
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(CartItemModel)) == 0

    ana.post(_url(kitchen_id, "/edit"))
    db_session.delete(db_session.get(KitchenModel, UUID(kitchen_id)))
    db_session.flush()
    for model in (CartModel, CartItemModel, CartEditLockModel):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0


def test_add_count_counts_saved_additions(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = _save(ana, notebook_id)
    for path, method in (
        ("/draft/items", "add"),
        ("/save", "save"),
        (f"/draft/items/{a}", "remove"),
        ("/save", "save"),
        ("/draft/items", "add"),
        ("/save", "save"),
        ("/draft/items", "add"),
        ("/save", "save"),
    ):
        if method == "add":
            ana.post(_url(kitchen_id, path), json={"recipe_id": a})
        elif method == "remove":
            ana.delete(_url(kitchen_id, path))
        else:
            ana.post(_url(kitchen_id, path))
    b = _save(ana, notebook_id)
    ana.post(_url(kitchen_id, "/draft/items"), json={"recipe_id": b})
    ana.delete(_url(kitchen_id, "/edit"))
    assert (_count(db_session, a), _count(db_session, b)) == (2, 0)


def test_a_cart_of_100_reads_in_few_statements(
    client: TestClient, db_session: Session, engine: Engine
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    ids = [uuid4() for _ in range(100)]
    db_session.add_all(
        RecipeModel(id=rid, notebook_id=UUID(notebook_id), title=f"R{n}", base_servings=4)
        for n, rid in enumerate(ids)
    )
    cart_id = uuid4()
    db_session.add(CartModel(id=cart_id, kitchen_id=UUID(kitchen_id)))
    db_session.flush()
    db_session.add_all(CartItemModel(cart_id=cart_id, recipe_id=rid, servings=2) for rid in ids)
    db_session.flush()

    statements: list[str] = []

    def count(conn, cursor, statement, *args) -> None:  # noqa: ANN001
        if "cart" in statement or "recipe" in statement:
            statements.append(statement)

    connection = db_session.connection()
    event.listen(connection, "before_cursor_execute", count)
    try:
        body = ana.get(_url(kitchen_id)).json()
    finally:
        event.remove(connection, "before_cursor_execute", count)
    assert len(body["entries"]) == 100 and all(e["factor"] == "0.5" for e in body["entries"])
    # cart row + items, recipe facts, member count, live lock (auth reads are not counted).
    assert len(statements) <= 5, statements


# --- Concurrency: two members start editing at once -----------------------------------------


def test_two_concurrent_starts_have_one_winner(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    kitchen_id = uuid4()
    users = [uuid4(), uuid4()]
    sessions = [uuid4(), uuid4()]
    with factory() as setup:
        for n, user_id in enumerate(users):
            setup.add(
                UserModel(
                    id=user_id,
                    email=f"race{n}_{user_id.hex[:6]}@example.com",
                    alias=f"race{n}_{user_id.hex[:6]}",
                    password_hash="x",
                )
            )
        setup.flush()
        setup.add(KitchenModel(id=kitchen_id, name="Race", owner_id=users[0]))
        setup.flush()
        for n, user_id in enumerate(users):
            setup.add(
                KitchenMembershipModel(
                    id=uuid4(), kitchen_id=kitchen_id, user_id=user_id, role="member"
                )
            )
            setup.add(
                SessionModel(
                    id=sessions[n],
                    token=uuid4().hex,
                    user_id=user_id,
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                )
            )
        setup.commit()

    def service(db: Session) -> StartCartEditService:
        return StartCartEditService(
            SqlAlchemyKitchenRepository(db),
            SqlAlchemyCartRepository(db),
            SqlAlchemyEditLockRepository(db),
        )

    outcome: dict[str, str] = {}
    try:
        first = factory()
        service(first).execute(SessionRef(users[0], sessions[0]), kitchen_id)

        def second_start() -> None:
            with factory() as second:
                try:
                    service(second).execute(SessionRef(users[1], sessions[1]), kitchen_id)
                    second.commit()
                    outcome["result"] = "locked"
                except CartLockedError:
                    second.rollback()
                    outcome["result"] = "refused"

        worker = threading.Thread(target=second_start)
        worker.start()
        worker.join(timeout=1.0)
        assert worker.is_alive(), "the second start should wait for the first one's row lock"
        first.commit()
        first.close()
        worker.join(timeout=10.0)
        assert outcome["result"] == "refused"
    finally:
        with factory() as cleanup:
            cleanup.execute(delete(KitchenModel).where(KitchenModel.id == kitchen_id))
            cleanup.execute(delete(UserModel).where(UserModel.id.in_(users)))
            cleanup.commit()
