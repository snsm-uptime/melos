"""Postgres integration tests for notebooks, the capture step and the catalog (spec 056).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset.

The `client` fixture shares the test's session, so rows written by a request are
visible to the test and a failed request needs an explicit rollback. Tests that need
real concurrency or a commit that survives a rollback use the `engine` fixture with
their own sessions and clean up after themselves.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    IngredientModel,
    KitchenInviteTokenModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    UserModel,
)
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from application.notebooks import (
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    ListKitchenNotebooksCommand,
    ListKitchenNotebooksService,
    ResolveCaptureNotebookCommand,
    ResolveCaptureNotebookService,
)
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
)
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


def _kitchen(session: Session, owner_id: UUID, name: str = "Test Kitchen") -> UUID:
    kitchen_id = uuid4()
    session.add(KitchenModel(id=kitchen_id, name=name, owner_id=owner_id))
    session.flush()
    session.add(
        KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=owner_id, role="owner")
    )
    session.flush()
    return kitchen_id


def _personal_notebook(session: Session, owner_id: UUID, name: str) -> UUID:
    notebook = NotebookModel(id=uuid4(), name=name)
    session.add(notebook)
    session.flush()
    session.add(NotebookMembershipModel(notebook_id=notebook.id, user_id=owner_id, role="owner"))
    session.flush()
    return notebook.id


def _kitchen_notebook(
    session: Session, kitchen_id: UUID, name: str, owner_user_id: UUID | None = None
) -> UUID:
    notebook = NotebookModel(
        id=uuid4(), name=name, kitchen_id=kitchen_id, owner_user_id=owner_user_id
    )
    session.add(notebook)
    session.flush()
    return notebook.id


def _notebook_count(session: Session, **filters: object) -> int:
    stmt = select(func.count()).select_from(NotebookModel)
    for column, value in filters.items():
        stmt = stmt.where(getattr(NotebookModel, column) == value)
    return session.scalar(stmt) or 0


def _register(client: TestClient, email: str) -> UUID:
    response = client.post("/auth/register", json={"email": email, "password": "password1"})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"])


def _resolve_service(session: Session) -> ResolveCaptureNotebookService:
    return ResolveCaptureNotebookService(
        SqlAlchemyKitchenRepository(session),
        SqlAlchemyNotebookRepository(session),
        SqlAlchemyUserDefaultNotebook(session),
        SqlAlchemyAuthUserRepository(session),
        SqlAlchemyIngredientCatalog(session),
        SqlAlchemyTransactionCommitter(session),
    )


def _list_kitchen_service(session: Session) -> ListKitchenNotebooksService:
    return ListKitchenNotebooksService(
        SqlAlchemyKitchenRepository(session),
        SqlAlchemyNotebookRepository(session),
        SqlAlchemyAuthUserRepository(session),
        SqlAlchemyIngredientCatalog(session),
    )


def _cleanup(
    factory: sessionmaker[Session],
    *,
    notebooks: list[UUID],
    kitchens: list[UUID],
    users: list[UUID],
) -> None:
    with factory() as cleanup:
        cleanup.execute(delete(NotebookModel).where(NotebookModel.id.in_(notebooks)))
        cleanup.execute(delete(KitchenModel).where(KitchenModel.id.in_(kitchens)))
        cleanup.execute(delete(UserModel).where(UserModel.id.in_(users)))
        cleanup.commit()


def _race(
    factory: sessionmaker[Session], call: Callable[[Session], UUID], threads: int = 2
) -> tuple[list[UUID], list[BaseException]]:
    """Run `call` on `threads` connections at the same moment; each one commits its session."""
    start = threading.Barrier(threads, timeout=10)
    results: list[UUID] = []
    errors: list[BaseException] = []

    def run() -> None:
        with factory() as session:
            try:
                start.wait()
                results.append(call(session))
                session.commit()
            except BaseException as exc:  # surfaced in the main thread
                session.rollback()
                errors.append(exc)

    workers = [threading.Thread(target=run) for _ in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
    return results, errors


# --- Schema (FR-001 to FR-006) ----------------------------------------------


def test_two_owners_for_one_personal_notebook_rejected(db_session: Session) -> None:
    owner, other = _user(db_session), _user(db_session)
    notebook_id = _personal_notebook(db_session, owner, "ana's Notebook")

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            NotebookMembershipModel(notebook_id=notebook_id, user_id=other, role="owner")
        )
        db_session.flush()


def test_same_person_twice_in_one_notebook_rejected(db_session: Session) -> None:
    owner, member = _user(db_session), _user(db_session)
    notebook_id = _personal_notebook(db_session, owner, "ana's Notebook")
    db_session.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=member, role="member"))
    db_session.flush()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            NotebookMembershipModel(notebook_id=notebook_id, user_id=member, role="member")
        )
        db_session.flush()


def test_blank_notebook_name_rejected(db_session: Session) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(NotebookModel(id=uuid4(), name="   "))
        db_session.flush()


def test_origin_on_a_personal_notebook_rejected(db_session: Session) -> None:
    owner = _user(db_session)
    kitchen_notebook = _kitchen_notebook(db_session, _kitchen(db_session, owner), "Home notebook")

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            NotebookModel(id=uuid4(), name="ana's Notebook", source_notebook_id=kitchen_notebook)
        )
        db_session.flush()


def test_origin_equal_to_own_id_rejected(db_session: Session) -> None:
    owner = _user(db_session)
    notebook_id = uuid4()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            NotebookModel(
                id=notebook_id,
                name="self",
                kitchen_id=_kitchen(db_session, owner),
                source_notebook_id=notebook_id,
            )
        )
        db_session.flush()


def test_owner_on_a_personal_notebook_rejected(db_session: Session) -> None:
    owner = _user(db_session)

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(NotebookModel(id=uuid4(), name="ana's Notebook", owner_user_id=owner))
        db_session.flush()


def test_two_kitchen_notebooks_for_one_kitchen_allowed(db_session: Session) -> None:
    owner = _user(db_session)
    kitchen_id = _kitchen(db_session, owner)
    _kitchen_notebook(db_session, kitchen_id, "first", owner)
    _kitchen_notebook(db_session, kitchen_id, "second", owner)

    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 2


def test_deleting_a_kitchen_removes_its_notebooks_and_keeps_personal_ones(
    db_session: Session,
) -> None:
    owner = _user(db_session)
    kitchen_id = _kitchen(db_session, owner)
    kitchen_notebook = _kitchen_notebook(
        db_session, kitchen_id, "ana's (Test Kitchen) Notebook", owner
    )
    db_session.add(IngredientModel(id=uuid4(), notebook_id=kitchen_notebook, name="onion"))
    personal = _personal_notebook(db_session, owner, "ana's Notebook")
    db_session.flush()

    db_session.execute(delete(KitchenModel).where(KitchenModel.id == kitchen_id))
    db_session.expire_all()

    assert db_session.get(NotebookModel, kitchen_notebook) is None
    remaining_ingredients = db_session.scalar(
        select(func.count())
        .select_from(IngredientModel)
        .where(IngredientModel.notebook_id == kitchen_notebook)
    )
    assert remaining_ingredients == 0
    assert db_session.get(NotebookModel, personal) is not None


def test_deleting_a_personal_notebook_clears_default_and_origin(db_session: Session) -> None:
    owner = _user(db_session)
    personal = _personal_notebook(db_session, owner, "ana's Notebook")
    db_session.get(UserModel, owner).default_notebook_id = personal
    db_session.add(IngredientModel(id=uuid4(), notebook_id=personal, name="onion"))
    kitchen_id = _kitchen(db_session, owner)
    snapshot = NotebookModel(
        id=uuid4(),
        name="ana's (Test Kitchen) Notebook",
        kitchen_id=kitchen_id,
        source_notebook_id=personal,
    )
    db_session.add(snapshot)
    db_session.flush()

    db_session.execute(delete(NotebookModel).where(NotebookModel.id == personal))
    db_session.expire_all()

    assert db_session.get(UserModel, owner).default_notebook_id is None
    assert db_session.get(NotebookModel, personal) is None
    assert db_session.get(NotebookModel, snapshot.id) is not None
    assert db_session.get(NotebookModel, snapshot.id).source_notebook_id is None
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.notebook_id == personal)
        )
        == 0
    )


def test_deleting_a_user_removes_memberships_and_keeps_every_notebook(db_session: Session) -> None:
    owner, other = _user(db_session), _user(db_session)
    personal = _personal_notebook(db_session, owner, "ana's Notebook")
    kitchen_id = _kitchen(db_session, other)
    kitchen_notebook = _kitchen_notebook(
        db_session, kitchen_id, "ana's (Test Kitchen) Notebook", owner
    )
    db_session.flush()

    db_session.execute(delete(UserModel).where(UserModel.id == owner))
    db_session.expire_all()

    assert db_session.get(NotebookModel, personal) is not None
    assert db_session.get(NotebookModel, kitchen_notebook).owner_user_id is None
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.user_id == owner)
        )
        == 0
    )


# --- Catalog (FR-004, FR-012, FR-018) ---------------------------------------


def test_catalog_readers_return_the_right_names(db_session: Session) -> None:
    user_id = _user(db_session)
    first = _personal_notebook(db_session, user_id, "A")
    second = _personal_notebook(db_session, user_id, "B")
    kitchen_notebook = _kitchen_notebook(db_session, _kitchen(db_session, user_id), "Home", user_id)
    db_session.add_all(
        [
            IngredientModel(id=uuid4(), notebook_id=first, name="onion"),
            IngredientModel(id=uuid4(), notebook_id=first, name="garlic"),
            IngredientModel(id=uuid4(), notebook_id=second, name="onion"),
            IngredientModel(id=uuid4(), notebook_id=second, name="rice"),
            IngredientModel(id=uuid4(), notebook_id=kitchen_notebook, name="salt"),
        ]
    )
    db_session.flush()
    catalog = SqlAlchemyIngredientCatalog(db_session)

    assert catalog.names_for_notebook(first) == ["garlic", "onion"]
    assert catalog.names_for_person(user_id) == ["garlic", "onion", "rice"]

    seeded = NotebookModel(id=uuid4(), name="C")
    db_session.add(seeded)
    db_session.flush()
    catalog.seed_from_person(seeded.id, user_id)

    assert catalog.names_for_notebook(seeded.id) == ["garlic", "onion", "rice"]


# --- Default personal notebook (US1) ----------------------------------------


def test_first_default_call_creates_the_personal_notebook_once(
    client: TestClient, db_session: Session
) -> None:
    email = "nb_default@example.com"
    user_id = _register(client, email)
    alias = alias_from_email(email)
    assert db_session.get(UserModel, user_id).default_notebook_id is None

    first = client.get("/notebooks/default")
    second = client.get("/notebooks/default")

    assert first.status_code == 200, first.text
    assert second.status_code == 200
    body = first.json()
    assert body == second.json()
    assert body["name"] == f"Cuaderno de {alias}"
    assert body["kind"] == "personal"
    assert body["access"] == "owner"
    assert body["owner_alias"] == alias
    assert body["kitchen_id"] is None
    assert body["is_default"] is True

    db_session.expire_all()
    assert str(db_session.get(UserModel, user_id).default_notebook_id) == body["id"]
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(
                NotebookMembershipModel.notebook_id == UUID(body["id"]),
                NotebookMembershipModel.user_id == user_id,
                NotebookMembershipModel.role == "owner",
            )
        )
        == 1
    )


def test_default_notebook_needs_an_alias(client: TestClient, db_session: Session) -> None:
    client.post("/auth/register", json={"email": "nb_noalias@example.com", "password": "password1"})
    user_id = UUID(client.get("/auth/me").json()["user_id"])

    response = client.get("/notebooks/default")

    assert response.status_code == 403
    assert response.json()["code"] == "alias_required"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.user_id == user_id)
        )
        == 0
    )


def test_deleted_default_is_recreated_with_the_same_fields(
    client: TestClient, db_session: Session
) -> None:
    user_id = _register(client, "nb_recreate@example.com")
    first = client.get("/notebooks/default").json()

    db_session.execute(delete(NotebookModel).where(NotebookModel.id == UUID(first["id"])))
    db_session.expire_all()
    assert db_session.get(UserModel, user_id).default_notebook_id is None

    again = client.get("/notebooks/default")

    assert again.status_code == 200
    body = again.json()
    assert body["id"] != first["id"]
    assert {k: v for k, v in body.items() if k != "id"} == {
        k: v for k, v in first.items() if k != "id"
    }
    db_session.expire_all()
    assert str(db_session.get(UserModel, user_id).default_notebook_id) == body["id"]


def test_simultaneous_first_default_calls_make_one_notebook(engine: Engine) -> None:
    """Two connections race the first call; the user-row lock lets one create (SC-001)."""
    factory = sessionmaker(bind=engine)
    alias = f"race_{uuid4().hex[:8]}"
    with factory() as setup:
        user_id = _user(setup, alias=alias)
        setup.commit()

    def first_call(session: Session) -> UUID:
        service = GetDefaultNotebookService(
            SqlAlchemyNotebookRepository(session),
            SqlAlchemyUserDefaultNotebook(session),
            SqlAlchemyAuthUserRepository(session),
            SqlAlchemyIngredientCatalog(session),
        )
        return service.execute(GetDefaultNotebookCommand(actor_user_id=user_id)).id

    results, errors = _race(factory, first_call)
    try:
        assert not errors, errors
        assert len(results) == 2
        assert results[0] == results[1]
        with factory() as check:
            assert _notebook_count(check, name=f"Cuaderno de {alias}") == 1
            assert check.get(UserModel, user_id).default_notebook_id == results[0]
    finally:
        _cleanup(factory, notebooks=results, kitchens=[], users=[user_id])


# --- A kitchen's first notebook (US2) ---------------------------------------


def test_creating_a_kitchen_makes_no_notebook(client: TestClient, db_session: Session) -> None:
    _register(client, "nb_kitchen@example.com")

    created = client.post("/kitchens", json={"name": "Home"})

    assert created.status_code == 201, created.text
    assert _notebook_count(db_session, kitchen_id=UUID(created.json()["id"])) == 0


def test_first_open_creates_the_kitchen_notebook_and_second_open_lists_it(
    client: TestClient, db_session: Session
) -> None:
    email = "nb_opener@example.com"
    user_id = _register(client, email)
    alias = alias_from_email(email)
    kitchen_id = client.post("/kitchens", json={"name": "Home"}).json()["id"]

    first = client.get(f"/notebooks/kitchens/{kitchen_id}")
    second = client.get(f"/notebooks/kitchens/{kitchen_id}")

    assert first.status_code == 200, first.text
    assert second.json() == first.json()
    notebooks = first.json()["notebooks"]
    assert len(notebooks) == 1
    view = notebooks[0]
    assert view["name"] == f"Cuaderno de {alias} (Home)"
    assert view["kind"] == "kitchen"
    assert view["access"] == "kitchen_member"
    assert view["owner_alias"] == alias
    assert view["kitchen_id"] == kitchen_id
    assert view["kitchen_is_archived"] is False
    assert view["is_default"] is False

    row = db_session.get(NotebookModel, UUID(view["id"]))
    assert row.owner_user_id == user_id
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.notebook_id == row.id)
        )
        == 0
    )


def test_first_open_seeds_the_catalog_from_the_openers_personal_catalog(
    client: TestClient, db_session: Session
) -> None:
    user_id = _register(client, "nb_seed@example.com")
    default_id = UUID(client.get("/notebooks/default").json()["id"])
    db_session.add(IngredientModel(id=uuid4(), notebook_id=default_id, name="onion"))
    db_session.flush()
    kitchen_id = client.post("/kitchens", json={"name": "Home"}).json()["id"]

    notebook_id = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]["id"]

    names = db_session.scalars(
        select(IngredientModel.name).where(IngredientModel.notebook_id == UUID(notebook_id))
    ).all()
    assert list(names) == ["onion"]
    assert db_session.get(NotebookModel, UUID(notebook_id)).owner_user_id == user_id


def test_failed_seed_leaves_no_notebook(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _register(client, "nb_seed_fail@example.com")
    kitchen_id = UUID(client.post("/kitchens", json={"name": "Home"}).json()["id"])

    def failing_seed(self: SqlAlchemyIngredientCatalog, notebook_id: UUID, user_id: UUID) -> None:
        raise RuntimeError("seed failed")

    monkeypatch.setattr(SqlAlchemyIngredientCatalog, "seed_from_person", failing_seed)
    with pytest.raises(RuntimeError):
        client.get(f"/notebooks/kitchens/{kitchen_id}")
    db_session.rollback()

    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 0


def test_failed_kitchen_creation_leaves_neither_kitchen_nor_notebook(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = _register(client, "nb_kitchen_fail@example.com")
    original = SqlAlchemyKitchenRepository.create_owned_kitchen

    def kitchen_then_fail(self: SqlAlchemyKitchenRepository, **kwargs: object) -> None:
        original(self, **kwargs)  # kitchen and membership flushed
        raise RuntimeError("membership failed")

    monkeypatch.setattr(SqlAlchemyKitchenRepository, "create_owned_kitchen", kitchen_then_fail)
    with pytest.raises(RuntimeError):
        client.post("/kitchens", json={"name": "Home"})
    db_session.rollback()

    assert (
        db_session.scalar(
            select(func.count()).select_from(KitchenModel).where(KitchenModel.owner_id == user_id)
        )
        == 1  # only the signup kitchen
    )
    assert _notebook_count(db_session, owner_user_id=user_id) == 0


def test_signup_kitchen_has_no_notebook_until_its_first_open(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "nb_personal@example.com")
    personal = client.get("/kitchens").json()["kitchens"][0]
    assert personal["name"] == "Mi cocina"
    assert _notebook_count(db_session, kitchen_id=UUID(personal["id"])) == 0

    first = client.get(f"/notebooks/kitchens/{personal['id']}")

    assert first.status_code == 200, first.text
    assert len(first.json()["notebooks"]) == 1
    assert _notebook_count(db_session, kitchen_id=UUID(personal["id"])) == 1


def test_rename_keeps_the_kitchen_notebook_name(client: TestClient, db_session: Session) -> None:
    email = "nb_rename@example.com"
    _register(client, email)
    alias = alias_from_email(email)
    kitchen_id = UUID(client.post("/kitchens", json={"name": "Home"}).json()["id"])
    before = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]

    db_session.get(KitchenModel, kitchen_id).name = "Casa"
    db_session.flush()
    after = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]

    assert after["id"] == before["id"]
    assert after["name"] == f"Cuaderno de {alias} (Home)"


def test_archived_kitchen_without_notebook_lists_nothing(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "nb_archived@example.com")
    kitchen_id = UUID(client.post("/kitchens", json={"name": "Home"}).json()["id"])
    db_session.get(KitchenModel, kitchen_id).is_archived = True
    db_session.flush()

    response = client.get(f"/notebooks/kitchens/{kitchen_id}")

    assert response.status_code == 200
    assert response.json() == {"notebooks": []}
    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 0


def test_simultaneous_first_opens_make_one_kitchen_notebook(engine: Engine) -> None:
    factory = sessionmaker(bind=engine)
    with factory() as setup:
        ana = _user(setup, alias=f"ana_{uuid4().hex[:6]}")
        ben = _user(setup, alias=f"ben_{uuid4().hex[:6]}")
        kitchen_id = _kitchen(setup, ana, "Home")
        setup.add(
            KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=ben, role="member")
        )
        setup.commit()

    def first_open(session: Session, actor: UUID) -> UUID:
        service = _list_kitchen_service(session)
        return service.execute(
            ListKitchenNotebooksCommand(actor_user_id=actor, kitchen_id=kitchen_id)
        )[0].id

    results: list[UUID] = []
    errors: list[BaseException] = []
    start = threading.Barrier(2, timeout=10)

    def run(actor: UUID) -> None:
        with factory() as session:
            try:
                start.wait()
                results.append(first_open(session, actor))
                session.commit()
            except BaseException as exc:
                session.rollback()
                errors.append(exc)

    workers = [threading.Thread(target=run, args=(actor,)) for actor in (ana, ben)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
    try:
        assert not errors, errors
        assert len(results) == 2
        assert results[0] == results[1]
        with factory() as check:
            assert _notebook_count(check, kitchen_id=kitchen_id) == 1
    finally:
        _cleanup(factory, notebooks=results, kitchens=[kitchen_id], users=[ana, ben])


# --- The capture notebook step (US3) ----------------------------------------


def test_first_capture_in_a_kitchen_creates_its_notebook_and_second_uses_it(
    db_session: Session,
) -> None:
    ana = _user(db_session, alias="ana_cap")
    kitchen_id = _kitchen(db_session, ana, "My kitchen")
    service = _resolve_service(db_session)

    first = service.execute(ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=kitchen_id))
    second = service.execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=kitchen_id)
    )

    assert first.created is True
    assert second.created is False
    assert second.notebook_id == first.notebook_id
    row = db_session.get(NotebookModel, first.notebook_id)
    assert row.name == "Cuaderno de ana_cap (My kitchen)"
    assert row.owner_user_id == ana
    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 1


def test_capture_auto_selects_user_notebook_or_creates_one(db_session: Session) -> None:
    ana = _user(db_session, alias="ana_auto")
    ben = _user(db_session, alias="ben_auto")
    kitchen_id = _kitchen(db_session, ana, "Home")
    db_session.add(
        KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=ben, role="member")
    )
    db_session.flush()
    ana_notebook = _kitchen_notebook(db_session, kitchen_id, "ana's Home", ana)
    ben_notebook = _kitchen_notebook(db_session, kitchen_id, "ben's Home", ben)
    other_kitchen = _kitchen(db_session, ana, "Other")
    stranger = _kitchen_notebook(db_session, other_kitchen, "elsewhere", ana)
    service = _resolve_service(db_session)

    # Ana uses her own notebook automatically
    result = service.execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=kitchen_id)
    )
    assert result.notebook_id == ana_notebook
    assert result.created is False

    # Ben uses his own notebook automatically
    result = service.execute(
        ResolveCaptureNotebookCommand(actor_user_id=ben, kitchen_id=kitchen_id)
    )
    assert result.notebook_id == ben_notebook
    assert result.created is False

    # Ana can explicitly pick Ben's notebook
    with pytest.raises(NotebookNotFoundError):
        service.execute(
            ResolveCaptureNotebookCommand(
                actor_user_id=ana, kitchen_id=kitchen_id, picked_notebook_id=stranger
            )
        )

    result = service.execute(
        ResolveCaptureNotebookCommand(
            actor_user_id=ana, kitchen_id=kitchen_id, picked_notebook_id=ben_notebook
        )
    )
    assert result.notebook_id == ben_notebook
    assert result.created is False


def test_capture_by_a_non_member_creates_nothing(db_session: Session) -> None:
    ana = _user(db_session, alias="ana_guard")
    carl = _user(db_session, alias="carl_guard")
    kitchen_id = _kitchen(db_session, ana, "Home")

    with pytest.raises(KitchenNotFoundError):
        _resolve_service(db_session).execute(
            ResolveCaptureNotebookCommand(actor_user_id=carl, kitchen_id=kitchen_id)
        )
    assert _notebook_count(db_session, kitchen_id=kitchen_id) == 0


def test_archived_kitchen_refuses_capture_even_with_notebooks(db_session: Session) -> None:
    ana = _user(db_session, alias="ana_archive")
    kitchen_id = _kitchen(db_session, ana, "Home")
    _kitchen_notebook(db_session, kitchen_id, "existing", ana)
    db_session.get(KitchenModel, kitchen_id).is_archived = True
    db_session.flush()
    before = _notebook_count(db_session)

    with pytest.raises(KitchenArchivedError):
        _resolve_service(db_session).execute(
            ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=kitchen_id)
        )
    assert _notebook_count(db_session) == before


def test_personal_capture_with_no_notebook_creates_the_default(db_session: Session) -> None:
    ana = _user(db_session, alias="ana_personal")

    result = _resolve_service(db_session).execute(ResolveCaptureNotebookCommand(actor_user_id=ana))

    assert result.created is True
    assert db_session.get(NotebookModel, result.notebook_id).name == "Cuaderno de ana_personal"
    assert db_session.get(UserModel, ana).default_notebook_id == result.notebook_id


def test_capture_notebook_survives_a_failed_save(engine: Engine) -> None:
    """The step commits what it creates, so a failed save keeps the notebook (FR-009)."""
    factory = sessionmaker(bind=engine)
    alias = f"save_{uuid4().hex[:6]}"
    with factory() as setup:
        ana = _user(setup, alias=alias)
        kitchen_id = _kitchen(setup, ana, "Home")
        setup.commit()

    with factory() as session:
        result = _resolve_service(session).execute(
            ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=kitchen_id)
        )
        session.rollback()  # the recipe save that called the step fails

    try:
        with factory() as check:
            assert check.get(NotebookModel, result.notebook_id) is not None
    finally:
        _cleanup(factory, notebooks=[result.notebook_id], kitchens=[kitchen_id], users=[ana])


def test_capture_race_on_one_kitchen_makes_one_notebook_per_member(engine: Engine) -> None:
    factory = sessionmaker(bind=engine)
    with factory() as setup:
        ana = _user(setup, alias=f"ana_{uuid4().hex[:6]}")
        ben = _user(setup, alias=f"ben_{uuid4().hex[:6]}")
        kitchen_id = _kitchen(setup, ana, "My kitchen")
        setup.add(
            KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=ben, role="member")
        )
        setup.commit()

    results: list[UUID] = []
    errors: list[BaseException] = []
    actors = (ana, ana, ben, ben)
    start = threading.Barrier(len(actors), timeout=10)

    def run(actor: UUID) -> None:
        with factory() as session:
            try:
                start.wait()
                result = _resolve_service(session).execute(
                    ResolveCaptureNotebookCommand(actor_user_id=actor, kitchen_id=kitchen_id)
                )
                session.commit()
                results.append(result.notebook_id)
            except BaseException as exc:
                session.rollback()
                errors.append(exc)

    workers = [threading.Thread(target=run, args=(actor,)) for actor in actors]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
    try:
        assert not errors, errors
        assert len(results) == len(actors)
        assert len(set(results)) == 2
        with factory() as check:
            assert _notebook_count(check, kitchen_id=kitchen_id, owner_user_id=ana) == 1
            assert _notebook_count(check, kitchen_id=kitchen_id, owner_user_id=ben) == 1
    finally:
        _cleanup(factory, notebooks=results, kitchens=[kitchen_id], users=[ana, ben])


# --- Read routes (US4) ------------------------------------------------------


def test_notebook_routes_are_gets_on_the_four_contract_paths(client: TestClient) -> None:
    paths = client.app.openapi()["paths"]
    # The capture route (spec 016) is the one POST under /notebooks; it is checked below.
    notebook_paths = {
        path: set(operations)
        for path, operations in paths.items()
        if path.startswith("/notebooks") and "/captures/" not in path
    }

    assert set(notebook_paths) == {
        "/notebooks",
        "/notebooks/default",
        "/notebooks/kitchens/{kitchen_id}",
        "/notebooks/{notebook_id}",
        # The recipe lists (spec 021) are reads under the same router.
        "/notebooks/kitchens/{kitchen_id}/recipes",
        "/notebooks/{notebook_id}/recipes",
    }
    assert {method for operations in notebook_paths.values() for method in operations} == {"get"}
    capture_paths = {path: set(ops) for path, ops in paths.items() if "/captures/" in path}
    assert capture_paths == {"/notebooks/{notebook_id}/captures/text": {"post"}}


def test_read_routes_show_each_person_only_what_they_may_see(
    client: TestClient, db_session: Session
) -> None:
    ben_id = _register(client, "nb_read_ben@example.com")
    family = _personal_notebook(db_session, ben_id, "ben's Family")
    client.post("/auth/sign-out")

    ana_id = _register(client, "nb_read_ana@example.com")
    db_session.add(NotebookMembershipModel(notebook_id=family, user_id=ana_id, role="member"))
    db_session.flush()
    default = client.get("/notebooks/default").json()
    kitchen_id = client.post("/kitchens", json={"name": "Home"}).json()["id"]
    home = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]

    listed = client.get("/notebooks").json()["notebooks"]
    assert {view["id"] for view in listed} == {default["id"], str(family), home["id"]}
    assert {view["id"]: view["access"] for view in listed} == {
        default["id"]: "owner",
        str(family): "member",
        home["id"]: "kitchen_member",
    }
    assert client.get(f"/notebooks/{family}").json()["owner_alias"] == alias_from_email(
        "nb_read_ben@example.com"
    )
    assert client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"] == [home]

    client.post("/auth/sign-out")
    _register(client, "nb_read_carl@example.com")

    missing_notebook = client.get(f"/notebooks/{home['id']}")
    random_notebook = client.get(f"/notebooks/{uuid4()}")
    family_for_carl = client.get(f"/notebooks/{family}")
    assert missing_notebook.status_code == 404
    assert missing_notebook.json()["code"] == "notebook_not_found"
    assert missing_notebook.text == random_notebook.text == family_for_carl.text

    missing_kitchen = client.get(f"/notebooks/kitchens/{uuid4()}")
    carl_kitchen = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert carl_kitchen.status_code == 404
    assert carl_kitchen.json()["code"] == "kitchen_not_found"
    assert carl_kitchen.text == missing_kitchen.text


def test_leaving_a_kitchen_ends_access_to_its_notebooks(
    client: TestClient, db_session: Session
) -> None:
    ben_id = _register(client, "nb_leave_ben@example.com")
    client.post("/auth/sign-out")
    _register(client, "nb_leave_ana@example.com")
    kitchen_id = UUID(client.post("/kitchens", json={"name": "Home"}).json()["id"])
    home = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]
    ana_default = client.get("/notebooks/default").json()["id"]
    db_session.add(
        KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=ben_id, role="member")
    )
    db_session.flush()
    client.post("/auth/sign-out")

    client.post(
        "/auth/sign-in", json={"email": "nb_leave_ben@example.com", "password": "password1"}
    )
    assert client.get(f"/notebooks/{home['id']}").status_code == 200
    # Ben shares Home with Ana, but Ana's personal notebook is still not his (AC1a.2).
    assert client.get(f"/notebooks/{ana_default}").status_code == 404

    db_session.execute(
        delete(KitchenMembershipModel).where(
            KitchenMembershipModel.kitchen_id == kitchen_id,
            KitchenMembershipModel.user_id == ben_id,
        )
    )
    db_session.expire_all()

    assert client.get(f"/notebooks/{home['id']}").status_code == 404
    assert client.get(f"/notebooks/kitchens/{kitchen_id}").status_code == 404
    assert db_session.get(NotebookModel, UUID(home["id"])) is not None


def test_notebook_steps_write_only_notebook_membership_ingredient_and_default(
    client: TestClient, db_session: Session
) -> None:
    """FR-022 / SC-011: the notebook steps never touch invites, origins or kitchen memberships.

    The recipe, step, category, source and cart tables do not exist yet (S-016 onward), so
    the invite table and the origin label stand in for "other data" here.
    """
    user_id = _register(client, "nb_fr022@example.com")

    def invite_count() -> int:
        return db_session.scalar(select(func.count()).select_from(KitchenInviteTokenModel)) or 0

    def origin_count() -> int:
        return (
            db_session.scalar(
                select(func.count())
                .select_from(NotebookModel)
                .where(NotebookModel.source_notebook_id.is_not(None))
            )
            or 0
        )

    before_invites, before_origins = invite_count(), origin_count()

    client.get("/notebooks/default")
    kitchen_id = UUID(client.post("/kitchens", json={"name": "Home"}).json()["id"])
    client.get(f"/notebooks/kitchens/{kitchen_id}")
    service = _resolve_service(db_session)
    service.execute(ResolveCaptureNotebookCommand(actor_user_id=user_id, kitchen_id=kitchen_id))
    service.execute(ResolveCaptureNotebookCommand(actor_user_id=user_id))

    assert invite_count() == before_invites
    assert origin_count() == before_origins == 0
    kitchen_memberships = db_session.scalar(
        select(func.count())
        .select_from(NotebookMembershipModel)
        .join(NotebookModel, NotebookModel.id == NotebookMembershipModel.notebook_id)
        .where(NotebookModel.kitchen_id.is_not(None))
    )
    assert kitchen_memberships == 0
