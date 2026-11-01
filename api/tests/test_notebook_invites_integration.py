"""Notebook invites over HTTP with Postgres (spec 057). Skips when DATABASE_URL is unset.

The `client` fixture shares the test's session. Tests for concurrency and for rollback use the
`engine` fixture with their own sessions and clean up after themselves.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    IngredientModel,
    NotebookInviteModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeModel,
    UserModel,
)
from adapters.persistence.notebook_invites import SqlAlchemyNotebookInviteRepository
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
)
from adapters.persistence.repositories import SqlAlchemyAuthUserRepository
from application.notebook_invites import AcceptNotebookInviteCommand, AcceptNotebookInviteService
from application.ports import EmailMessage
from domain.errors import SmtpConfigurationError, SmtpSendError
from domain.kitchen_invite import hash_invite_token
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import claim_alias, database_url, make_client
from tests.test_notebook_integration import _cleanup, _race
from tests.test_notebook_snapshots_integration import _kitchen, _personal, _recipe
from tests.test_recipe_manage_integration import _edit_body, _put
from tests.test_recipe_save_integration import _body

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

COOKIE = "melos_session"


class CapturingMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.fail: Exception | None = None

    def send(self, message: EmailMessage) -> None:
        if self.fail is not None:
            raise self.fail
        self.sent.append(message)


@pytest.fixture
def mailer() -> CapturingMailer:
    return CapturingMailer()


@pytest.fixture
def client(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, mailer: CapturingMailer
) -> Iterator[TestClient]:
    from api.routes import notebooks as notebooks_routes

    monkeypatch.setattr(notebooks_routes, "SmtpEmailSender", lambda _settings: mailer)
    yield from make_client(db_session, monkeypatch, smtp=True)


def _register(client: TestClient, name: str, *, alias: bool = True) -> tuple[UUID, str, str]:
    email = f"{name}_{uuid4().hex[:6]}@example.test"
    client.cookies.clear()
    response = client.post("/auth/register", json={"email": email, "password": "password1"})
    assert response.status_code == 201, response.text
    if alias:
        claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"]), client.cookies[COOKIE], email


def _use(client: TestClient, cookie: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE, cookie)


def _token(mailer: CapturingMailer, index: int = -1) -> str:
    return mailer.sent[index].body_text.split("?token=")[1].split()[0]


def _invite(client: TestClient, notebook_id: UUID, email: str):  # noqa: ANN202
    return client.post(f"/notebooks/{notebook_id}/invites", json={"email": email})


def _accept(client: TestClient, token: str):  # noqa: ANN202
    return client.post("/invites/notebook/accept", json={"token": token})


def _preview(client: TestClient, token: str):  # noqa: ANN202
    return client.get("/invites/notebook/preview", params={"token": token})


def _role(db: Session, notebook_id: UUID, user_id: UUID) -> str | None:
    return db.scalar(
        select(NotebookMembershipModel.role).where(
            NotebookMembershipModel.notebook_id == notebook_id,
            NotebookMembershipModel.user_id == user_id,
        )
    )


def _names(db: Session, notebook_id: UUID) -> list[str]:
    return sorted(
        db.scalars(select(IngredientModel.name).where(IngredientModel.notebook_id == notebook_id))
    )


def _join(
    client: TestClient,
    mailer: CapturingMailer,
    notebook_id: UUID,
    owner_cookie: str,
    cookie: str,
    email: str,
) -> None:
    _use(client, owner_cookie)
    assert _invite(client, notebook_id, email).status_code == 201
    _use(client, cookie)
    assert _accept(client, _token(mailer)).status_code == 200


@pytest.fixture
def ana(client: TestClient, db_session: Session) -> tuple[UUID, str, UUID]:
    """The owner: id, cookie and a personal notebook."""
    user_id, cookie, _ = _register(client, "ana")
    return user_id, cookie, _personal(db_session, user_id)


# --- Sending -------------------------------------------------------------------------------


def test_send_answers_per_the_contract(
    client: TestClient, db_session: Session, mailer: CapturingMailer, ana
) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    response = _invite(client, notebook_id, "Ben@Example.Test")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"status", "invite"}
    assert body["status"] == "sent"
    assert set(body["invite"]) == {"id", "email", "expires_at", "expired"}
    assert body["invite"]["email"] == "ben@example.test"

    row = db_session.scalar(select(NotebookInviteModel))
    assert row.token_hash == hash_invite_token(_token(mailer))
    assert "/invites/notebook?token=" in mailer.sent[0].body_text


def test_send_refusals(client: TestClient, db_session: Session, mailer, ana) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _, eve_cookie, _ = _register(client, "eve")
    db_session.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=ben_id, role="member"))
    kitchen_notebook = uuid4()
    kitchen = _kitchen(db_session, owner)
    db_session.add(NotebookModel(id=kitchen_notebook, name="Home", kitchen_id=kitchen))
    db_session.flush()

    _use(client, ben_cookie)
    member = _invite(client, notebook_id, "x@example.test")
    assert (member.status_code, member.json()["code"]) == (403, "notebook_owner_only")

    _use(client, eve_cookie)
    stranger = _invite(client, notebook_id, "x@example.test")
    assert (stranger.status_code, stranger.json()["code"]) == (404, "notebook_not_found")

    _use(client, cookie)
    bad = _invite(client, notebook_id, "nope")
    assert (bad.status_code, bad.json()["code"]) == (422, "invalid_invite_email")
    in_already = _invite(client, notebook_id, ben_email)
    assert (in_already.status_code, in_already.json()["code"]) == (409, "already_in_notebook")
    kitchen_refused = _invite(client, kitchen_notebook, "x@example.test")
    assert (kitchen_refused.status_code, kitchen_refused.json()["code"]) == (
        403,
        "notebook_not_shareable",
    )
    assert mailer.sent == []


def test_routes_need_an_alias(client: TestClient, ana) -> None:
    _, _, notebook_id = ana
    _register(client, "noalias", alias=False)
    response = client.get(f"/notebooks/{notebook_id}/members")
    assert (response.status_code, response.json()["code"]) == (403, "alias_required")
    accept = _accept(client, "anything")
    assert (accept.status_code, accept.json()["code"]) == (403, "alias_required")


@pytest.mark.parametrize(
    ("failure", "code"),
    [(SmtpSendError(), "smtp_send_error"), (SmtpConfigurationError("no"), "smtp_config_error")],
)
def test_failed_email_stores_nothing(
    client: TestClient, db_session: Session, mailer, ana, failure: Exception, code: str
) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    mailer.fail = failure
    response = _invite(client, notebook_id, "ben@example.test")
    assert (response.status_code, response.json()["code"]) == (503, code)
    assert db_session.scalar(select(func.count()).select_from(NotebookInviteModel)) == 0


def test_failed_repeat_leaves_the_earlier_invite_working(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    assert _invite(client, notebook_id, ben_email).status_code == 201
    token = _token(mailer)
    mailer.fail = SmtpSendError()
    assert _invite(client, notebook_id, ben_email).status_code == 503
    mailer.fail = None
    _use(client, ben_cookie)
    assert _accept(client, token).status_code == 200
    assert _role(db_session, notebook_id, ben_id) == "member"


def test_response_is_the_same_with_and_without_an_account(client: TestClient, mailer, ana) -> None:
    _, cookie, notebook_id = ana
    _, _, known_email = _register(client, "known")
    _use(client, cookie)
    known = _invite(client, notebook_id, known_email).json()
    unknown = _invite(client, notebook_id, "nobody@example.test").json()
    assert set(known) == set(unknown) and set(known["invite"]) == set(unknown["invite"])
    known_preview = _preview(client, _token(mailer, 0)).json()
    unknown_preview = _preview(client, _token(mailer, 1)).json()
    assert (
        set(known_preview)
        == set(unknown_preview)
        == {
            "notebook_name",
            "inviter_alias",
            "email_hint",
        }
    )


# --- Preview and accept --------------------------------------------------------------------


def test_preview_needs_no_session_and_changes_nothing(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    _invite(client, notebook_id, "ben@example.test")
    client.cookies.clear()
    response = _preview(client, _token(mailer))
    assert response.status_code == 200
    body = response.json()
    assert body["notebook_name"] == "ana's Notebook"
    assert body["inviter_alias"].startswith("ana")
    assert body["email_hint"] == "b***n@example.test"
    assert db_session.scalar(select(NotebookInviteModel)).used_at is None


def test_accept_joins_as_a_member_and_lists_the_notebook(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    _invite(client, notebook_id, ben_email.upper())
    _use(client, ben_cookie)
    response = _accept(client, _token(mailer))
    assert response.status_code == 200
    assert response.json() == {"notebook_id": str(notebook_id)}
    assert _role(db_session, notebook_id, ben_id) == "member"

    listed = next(
        row for row in client.get("/notebooks").json()["notebooks"] if row["id"] == str(notebook_id)
    )
    assert listed["access"] == "member"
    assert listed["owner_alias"].startswith("ana")
    assert listed["is_default"] is False


def test_accept_needs_a_session(client: TestClient) -> None:
    client.cookies.clear()
    assert _accept(client, "anything").status_code == 401


def test_every_dead_link_answers_the_same(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    """Unknown, blank, used, expired, cancelled and replaced (SC-006)."""
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    carla_id, carla_cookie, carla_email = _register(client, "carla")
    _use(client, cookie)

    _invite(client, notebook_id, "replaced@example.test")
    replaced = _token(mailer)
    _invite(client, notebook_id, "replaced@example.test")

    _invite(client, notebook_id, "cancelled@example.test")
    cancelled = _token(mailer)
    invite_id = _invite_row(db_session, "cancelled@example.test").id
    assert client.delete(f"/notebooks/{notebook_id}/invites/{invite_id}").status_code == 204

    _invite(client, notebook_id, "expired@example.test")
    expired = _token(mailer)
    _invite_row(db_session, "expired@example.test").expires_at = datetime.now(UTC) - timedelta(
        seconds=1
    )
    db_session.flush()

    _invite(client, notebook_id, ben_email)
    used = _token(mailer)
    _use(client, ben_cookie)
    assert _accept(client, used).status_code == 200
    _use(client, carla_cookie)

    bodies = []
    for token in ("unknown", "   ", replaced, cancelled, expired, used):
        for call in (_preview, _accept):
            response = call(client, token)
            assert response.status_code == 410, (token, response.text)
            bodies.append(response.json())
    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["code"] == "invalid_invite_token"
    assert "notebook" in bodies[0]["detail"]
    assert "kitchen" not in bodies[0]["detail"]
    assert _role(db_session, notebook_id, carla_id) is None


def _invite_row(db: Session, email: str) -> NotebookInviteModel:
    return db.scalars(
        select(NotebookInviteModel)
        .where(NotebookInviteModel.email == email, NotebookInviteModel.used_at.is_(None))
        .execution_options(populate_existing=True)
    ).one()


def test_mismatch_stays_usable_for_the_invited_person(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    carla_id, carla_cookie, _ = _register(client, "carla")
    _use(client, cookie)
    _invite(client, notebook_id, ben_email)
    token = _token(mailer)
    _use(client, carla_cookie)
    response = _accept(client, token)
    assert (response.status_code, response.json()["code"]) == (403, "invite_email_mismatch")
    assert _role(db_session, notebook_id, carla_id) is None
    _use(client, ben_cookie)
    assert _accept(client, token).status_code == 200


def test_reopening_a_used_link_is_a_quiet_success(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    second = _accept(client, _token(mailer))
    assert second.status_code == 200
    assert second.json() == {"notebook_id": str(notebook_id)}


def test_a_new_invite_after_joining_is_refused_then_a_stale_link_is_quiet(
    client: TestClient, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    _invite(client, notebook_id, ben_email)
    _use(client, ben_cookie)
    _accept(client, _token(mailer))
    _use(client, cookie)
    assert _invite(client, notebook_id, ben_email).status_code == 409


# --- What a member can do (AC1a.1, FR-020) -------------------------------------------------


def test_member_reads_adds_edits_and_deletes_and_the_owner_sees_it(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    recipe_id = _recipe(db_session, notebook_id, owner)
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)

    read = client.get(f"/recipes/{recipe_id}")
    assert read.status_code == 200 and read.json()["can_write"] is True
    edited = _put(client, str(recipe_id), _edit_body(read.json(), title="Edited by Ben"))
    assert edited.status_code == 200, edited.text
    client.delete(f"/recipes/{recipe_id}/edit-lock")

    added = client.post("/recipes", json=_body(str(notebook_id)))
    assert added.status_code == 201, added.text
    added_id = added.json()["recipe"]["id"]

    _use(client, cookie)
    assert client.get(f"/recipes/{recipe_id}").json()["title"] == "Edited by Ben"
    assert client.get(f"/recipes/{added_id}").json()["author_alias"].startswith("ben")

    _use(client, ben_cookie)
    assert client.delete(f"/recipes/{added_id}").status_code in (200, 204)


def test_member_cannot_snapshot_the_notebook_into_a_kitchen(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    kitchen = _kitchen(db_session, ben_id)
    response = client.post(
        f"/notebooks/kitchens/{kitchen}/snapshots",
        json={"source_notebook_id": str(notebook_id), "snapshot_key": str(uuid4())},
    )
    assert (response.status_code, response.json()["code"]) == (404, "notebook_not_found")


def test_default_notebook_stays_the_owners(client: TestClient, db_session: Session, mailer) -> None:
    owner, cookie, _ = _register(client, "ana")
    default_id = UUID(client.get("/notebooks/default").json()["id"])
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, default_id, cookie, ben_cookie, ben_email)
    assert client.get(f"/notebooks/{default_id}").json()["is_default"] is False
    assert client.get("/notebooks/default").json()["id"] != str(default_id)
    _use(client, cookie)
    assert client.get("/notebooks/default").json()["id"] == str(default_id)


# --- The merge (User Story 2) --------------------------------------------------------------


def test_merge_keeps_the_notebooks_names_and_adds_the_rest(
    client: TestClient, db_session: Session, mailer
) -> None:
    owner, cookie, _ = _register(client, "ana")
    notebook_id = _personal(db_session, owner, names=("onion",))
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    other = _personal(db_session, ben_id, "Ben's", names=("onions", "saffron", "tomato"))
    second = _personal(db_session, ben_id, "Ben's 2", names=("tomatoes",))
    recipe_id = _recipe(db_session, notebook_id, owner)
    title_before = db_session.get(RecipeModel, recipe_id).title
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)

    assert _names(db_session, notebook_id) == ["onion", "saffron", "tomato"]
    assert _names(db_session, other) == ["onions", "saffron", "tomato"]
    assert _names(db_session, second) == ["tomatoes"]
    assert db_session.get(RecipeModel, recipe_id).title == title_before


def test_merge_of_a_person_with_no_notebook_changes_nothing(
    client: TestClient, db_session: Session, mailer
) -> None:
    owner, cookie, _ = _register(client, "ana")
    notebook_id = _personal(db_session, owner, names=("onion",))
    _, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    assert _names(db_session, notebook_id) == ["onion"]


def test_kitchen_notebook_names_are_not_merged(
    client: TestClient, db_session: Session, mailer
) -> None:
    owner, cookie, _ = _register(client, "ana")
    notebook_id = _personal(db_session, owner)
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    kitchen = _kitchen(db_session, ben_id)
    kitchen_notebook = uuid4()
    db_session.add(NotebookModel(id=kitchen_notebook, name="Home", kitchen_id=kitchen))
    db_session.flush()
    db_session.add(IngredientModel(notebook_id=kitchen_notebook, name="rice"))
    db_session.flush()
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    assert _names(db_session, notebook_id) == []


def _committed_invite(
    factory: sessionmaker[Session],
) -> tuple[UUID, UUID, UUID, str]:
    """A committed owner, invited person with names, notebook and live invite."""
    owner, person, notebook_id = uuid4(), uuid4(), uuid4()
    own_notebook = uuid4()
    raw = uuid4().hex
    with factory() as db:
        db.add(UserModel(id=owner, email=f"{owner.hex[:12]}@example.test", password_hash="x"))
        db.add(UserModel(id=person, email=f"{person.hex[:12]}@example.test", password_hash="x"))
        db.add(NotebookModel(id=notebook_id, name="ana's Notebook"))
        db.add(NotebookModel(id=own_notebook, name="ben's Notebook"))
        db.flush()
        db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
        db.add(NotebookMembershipModel(notebook_id=own_notebook, user_id=person, role="owner"))
        db.add(IngredientModel(notebook_id=own_notebook, name="saffron"))
        db.add(
            NotebookInviteModel(
                id=uuid4(),
                notebook_id=notebook_id,
                email=f"{person.hex[:12]}@example.test",
                token_hash=hash_invite_token(raw),
                invited_by=owner,
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        db.commit()
    return owner, person, notebook_id, raw


def _accept_service(
    session: Session, *, catalog=None, notebooks=None, committer=None
) -> AcceptNotebookInviteService:
    return AcceptNotebookInviteService(
        SqlAlchemyNotebookInviteRepository(session),
        notebooks or SqlAlchemyNotebookRepository(session),
        SqlAlchemyAuthUserRepository(session),
        SqlAlchemyEmailVerificationRepository(session),
        catalog or SqlAlchemyIngredientCatalog(session),
        committer or SqlAlchemyTransactionCommitter(session),
    )


def test_simultaneous_accepts_make_one_membership_and_one_merge(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)
    merges: list[tuple[str, ...]] = []

    class CountingCatalog(SqlAlchemyIngredientCatalog):
        def add_names(self, target, names) -> None:  # noqa: ANN001
            merges.append(tuple(names))
            super().add_names(target, names)

    def call(session: Session) -> UUID:
        return (
            _accept_service(session, catalog=CountingCatalog(session))
            .execute(
                AcceptNotebookInviteCommand(
                    actor_user_id=person, raw_token=raw, email_verification_required=False
                )
            )
            .notebook_id
        )

    try:
        results, errors = _race(factory, call, threads=4)
        assert errors == []
        assert results == [notebook_id] * 4
        assert merges == [("saffron",)]
        with factory() as db:
            count = db.scalar(
                select(func.count())
                .select_from(NotebookMembershipModel)
                .where(
                    NotebookMembershipModel.notebook_id == notebook_id,
                    NotebookMembershipModel.user_id == person,
                )
            )
            assert count == 1
            assert _names(db, notebook_id) == ["saffron"]
    finally:
        _finish(factory, notebook_id, owner, person)


def _finish(factory: sessionmaker[Session], notebook_id: UUID, *users: UUID) -> None:
    with factory() as db:
        own = list(
            db.scalars(
                select(NotebookMembershipModel.notebook_id).where(
                    NotebookMembershipModel.user_id.in_(users)
                )
            )
        )
    _cleanup(factory, notebooks=[notebook_id, *own], kitchens=[], users=list(users))


@pytest.mark.parametrize(
    "step", ["names_for_person", "names_for_notebook", "add_names", "add_member", "commit"]
)
def test_a_failure_at_any_step_leaves_nothing_and_the_invite_usable(
    engine: Engine, step: str
) -> None:
    """SC-007: as get_db does, an exception rolls the whole request back."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)

    class Boom(RuntimeError):
        pass

    def failing(target: object, name: str) -> object:
        class Failing(type(target)):  # type: ignore[misc]
            pass

        def boom(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            if name == "add_names":
                getattr(target, name)(*args, **kwargs)  # the insert happens, then it fails
            raise Boom

        setattr(Failing, name, boom)
        return Failing(target._session)

    command = AcceptNotebookInviteCommand(
        actor_user_id=person, raw_token=raw, email_verification_required=False
    )
    try:
        with factory() as session:
            catalog = SqlAlchemyIngredientCatalog(session)
            notebooks = SqlAlchemyNotebookRepository(session)
            committer = SqlAlchemyTransactionCommitter(session)
            if step in ("names_for_person", "names_for_notebook", "add_names"):
                catalog = failing(catalog, step)
            elif step == "add_member":
                notebooks = failing(notebooks, step)
            else:
                committer = failing(committer, step)
            service = _accept_service(
                session, catalog=catalog, notebooks=notebooks, committer=committer
            )
            with pytest.raises(Boom):
                service.execute(command)
            session.rollback()

        with factory() as db:
            assert _role(db, notebook_id, person) is None
            assert _names(db, notebook_id) == []
            invite = db.scalar(
                select(NotebookInviteModel).where(NotebookInviteModel.notebook_id == notebook_id)
            )
            assert invite.used_at is None

        with factory() as session:
            _accept_service(session).execute(command)
            session.commit()
        with factory() as db:
            assert _role(db, notebook_id, person) == "member"
            assert _names(db, notebook_id) == ["saffron"]
    finally:
        _finish(factory, notebook_id, owner, person)


def test_500_by_500_names_join_in_under_two_seconds(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)
    try:
        with factory() as db:
            own = db.scalar(
                select(NotebookMembershipModel.notebook_id).where(
                    NotebookMembershipModel.user_id == person
                )
            )
            SqlAlchemyIngredientCatalog(db).add_names(own, [f"mine{i}x" for i in range(499)])
            SqlAlchemyIngredientCatalog(db).add_names(
                notebook_id, [f"theirs{i}y" for i in range(500)]
            )
            db.commit()
        with factory() as session:
            started = time.perf_counter()
            _accept_service(session).execute(
                AcceptNotebookInviteCommand(
                    actor_user_id=person, raw_token=raw, email_verification_required=False
                )
            )
            assert time.perf_counter() - started < 2
        with factory() as db:
            assert len(_names(db, notebook_id)) == 1000
    finally:
        _finish(factory, notebook_id, owner, person)


# --- A new person (User Story 4) -----------------------------------------------------------


def test_preview_is_the_same_before_any_account_exists(client: TestClient, mailer, ana) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    _invite(client, notebook_id, "newperson@example.test")
    client.cookies.clear()
    assert set(_preview(client, _token(mailer)).json()) == {
        "notebook_name",
        "inviter_alias",
        "email_hint",
    }


def test_new_account_with_the_invited_email_joins_and_adds_no_names(
    client: TestClient, db_session: Session, mailer
) -> None:
    owner, cookie, _ = _register(client, "ana")
    notebook_id = _personal(db_session, owner, names=("onion",))
    _invite(client, notebook_id, "newperson@example.test")
    token = _token(mailer)

    client.cookies.clear()
    created = client.post(
        "/auth/register", json={"email": "newperson@example.test", "password": "password1"}
    )
    assert created.status_code == 201
    no_alias = _accept(client, token)
    assert (no_alias.status_code, no_alias.json()["code"]) == (403, "alias_required")
    claim_alias(client, "newperson@example.test")
    assert _accept(client, token).status_code == 200
    user_id = UUID(client.get("/auth/me").json()["user_id"])
    assert _role(db_session, notebook_id, user_id) == "member"
    assert _names(db_session, notebook_id) == ["onion"]


def test_new_account_with_a_different_email_is_a_mismatch(client: TestClient, mailer, ana) -> None:
    _, cookie, notebook_id = ana
    _use(client, cookie)
    _invite(client, notebook_id, "newperson@example.test")
    _register(client, "someoneelse")
    response = _accept(client, _token(mailer))
    assert (response.status_code, response.json()["code"]) == (403, "invite_email_mismatch")


def test_verification_gate_keeps_the_invite_until_verified(
    client: TestClient, db_session: Session, mailer, ana, monkeypatch
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    _invite(client, notebook_id, ben_email)
    monkeypatch.setenv("EMAIL_VERIFICATION_REQUIRED", "true")
    client.app.state.auth_settings = None  # type: ignore[attr-defined]
    _use(client, ben_cookie)

    token = _token(mailer)
    response = _accept(client, token)
    assert (response.status_code, response.json()["code"]) == (403, "email_not_verified")
    assert _role(db_session, notebook_id, ben_id) is None
    assert _invite_row(db_session, ben_email).used_at is None

    db_session.get(UserModel, ben_id).email_verified_at = datetime.now(UTC)
    db_session.flush()
    assert _accept(client, token).status_code == 200


def test_signing_up_with_a_notebook_token_does_not_join(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    """The auth route takes kitchen tokens only, so joining happens at the link (FR-012)."""
    _, cookie, notebook_id = ana
    _use(client, cookie)
    _invite(client, notebook_id, "viaregister@example.test")
    token = _token(mailer)
    client.cookies.clear()
    client.post(
        "/auth/register",
        json={
            "email": "viaregister@example.test",
            "password": "password1",
            "invite_token": token,
        },
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.notebook_id == notebook_id)
        )
        == 1
    )
    assert _invite_row(db_session, "viaregister@example.test").used_at is None


# --- The owner's list, resend and cancel (User Story 5) ------------------------------------


def test_list_is_for_the_owner_and_marks_expired(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    assert client.get(f"/notebooks/{notebook_id}/invites").status_code == 403

    _use(client, cookie)
    _invite(client, notebook_id, "old@example.test")
    _invite_row(db_session, "old@example.test").expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.flush()
    _invite(client, notebook_id, "new@example.test")
    rows = client.get(f"/notebooks/{notebook_id}/invites").json()["invites"]
    assert [(row["email"], row["expired"]) for row in rows] == [
        ("new@example.test", False),
        ("old@example.test", True),
    ]


def test_resend_ends_the_earlier_link_and_starts_seven_days(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    invite = _invite(client, notebook_id, ben_email).json()["invite"]
    first = _token(mailer)
    _invite_row(db_session, ben_email).expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.flush()

    response = client.post(f"/notebooks/{notebook_id}/invites/{invite['id']}/resend")
    assert response.status_code == 200
    assert response.json()["invite"]["id"] == invite["id"]
    assert response.json()["invite"]["expired"] is False
    newest = _token(mailer)
    assert newest != first

    _use(client, ben_cookie)
    assert _accept(client, first).status_code == 410
    assert _accept(client, newest).status_code == 200


def test_failed_resend_keeps_the_previous_link(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    _, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _use(client, cookie)
    invite_id = _invite(client, notebook_id, ben_email).json()["invite"]["id"]
    token = _token(mailer)
    mailer.fail = SmtpSendError()
    assert client.post(f"/notebooks/{notebook_id}/invites/{invite_id}/resend").status_code == 503
    mailer.fail = None
    _use(client, ben_cookie)
    assert _accept(client, token).status_code == 200


def test_non_owners_are_refused_on_every_sharing_route(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _, eve_cookie, _ = _register(client, "eve")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    _use(client, cookie)
    invite_id = _invite(client, notebook_id, "x@example.test").json()["invite"]["id"]
    sent = len(mailer.sent)

    calls = [
        ("GET", f"/notebooks/{notebook_id}/invites"),
        ("POST", f"/notebooks/{notebook_id}/invites/{invite_id}/resend"),
        ("DELETE", f"/notebooks/{notebook_id}/invites/{invite_id}"),
        ("DELETE", f"/notebooks/{notebook_id}/members/{owner}"),
    ]
    for session_cookie, status, code in (
        (ben_cookie, 403, "notebook_owner_only"),
        (eve_cookie, 404, "notebook_not_found"),
    ):
        _use(client, session_cookie)
        for method, path in calls:
            response = client.request(method, path)
            assert (response.status_code, response.json()["code"]) == (status, code), path
    assert len(mailer.sent) == sent
    assert _invite_row(db_session, "x@example.test") is not None


def test_an_invite_outlives_its_sender_and_ends_with_the_notebook(
    client: TestClient, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    _, _, ben_email = _register(client, "ben")
    _use(client, cookie)
    _invite(client, notebook_id, ben_email)
    token = _token(mailer)

    db_session.execute(delete(UserModel).where(UserModel.id == owner))
    db_session.expire_all()
    assert _invite_row(db_session, ben_email).invited_by is None
    assert _preview(client, token).json()["inviter_alias"] is None

    db_session.delete(db_session.get(NotebookModel, notebook_id))
    db_session.flush()
    db_session.expire_all()
    assert _preview(client, token).status_code == 410
