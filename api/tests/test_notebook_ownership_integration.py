# ruff: noqa: F401, F811 - fixtures are imported from the invite suite and named as parameters.
"""Settling an owner's notebooks with Postgres (spec 058). Skips when DATABASE_URL is unset.

Each test runs the service and then deletes the user row, as account deletion (S-054) will. The
`client` fixture shares one transaction, so every membership in it gets the same `now()`: joining
times are set by hand. Concurrency and rollback tests use the `engine` fixture with their own
sessions and clean up after themselves.

In the concurrency tests one request holds its transaction open while the other is shown to be
waiting, so each order is forced instead of being left to timing.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    IngredientModel,
    NotebookInviteModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeModel,
    SourceModel,
    UserModel,
)
from adapters.persistence.notebooks import SqlAlchemyNotebookRepository
from application.notebook_invites import AcceptNotebookInviteCommand
from application.notebook_members import LeaveNotebookCommand, LeaveNotebookService
from application.notebook_ownership import (
    PassedNotebook,
    PassOwnedNotebooksCommand,
    PassOwnedNotebooksResult,
    PassOwnedNotebooksService,
)
from domain.errors import InvalidInviteTokenError, NotebookOwnerStaysError
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import alias_from_email, database_url
from tests.test_notebook_integration import _cleanup
from tests.test_notebook_invites_integration import (
    _accept,
    _accept_service,
    _committed_invite,
    _finish,
    _invite,
    _join,
    _names,
    _preview,
    _register,
    _role,
    _token,
    _use,
    ana,
    client,
    mailer,
)
from tests.test_notebook_members_integration import _locks
from tests.test_notebook_snapshots_integration import _add, _kitchen, _personal, _recipe

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _pass(db: Session, user_id: UUID) -> PassOwnedNotebooksResult:
    return PassOwnedNotebooksService(SqlAlchemyNotebookRepository(db)).execute(
        PassOwnedNotebooksCommand(user_id=user_id)
    )


def _settle(db: Session, user_id: UUID) -> PassOwnedNotebooksResult:
    """The rule, then the user row: the order S-054 must keep (contract)."""
    result = _pass(db, user_id)
    db.execute(delete(UserModel).where(UserModel.id == user_id))
    db.flush()
    db.expire_all()
    return result


def _set_joined(db: Session, notebook_id: UUID, user_id: UUID, days_ago: int) -> datetime:
    joined_at = datetime(2026, 6, 1, tzinfo=UTC) - timedelta(days=days_ago)
    db.execute(
        update(NotebookMembershipModel)
        .where(
            NotebookMembershipModel.notebook_id == notebook_id,
            NotebookMembershipModel.user_id == user_id,
        )
        .values(created_at=joined_at)
    )
    return joined_at


def _joined(db: Session, notebook_id: UUID, user_id: UUID) -> datetime | None:
    return db.scalar(
        select(NotebookMembershipModel.created_at).where(
            NotebookMembershipModel.notebook_id == notebook_id,
            NotebookMembershipModel.user_id == user_id,
        )
    )


def _owners(db: Session, notebook_id: UUID) -> list[UUID]:
    return list(
        db.scalars(
            select(NotebookMembershipModel.user_id).where(
                NotebookMembershipModel.notebook_id == notebook_id,
                NotebookMembershipModel.role == "owner",
            )
        )
    )


def _listed(client, notebook_id: UUID) -> dict:  # noqa: ANN001
    rows = client.get("/notebooks").json()["notebooks"]
    return next(row for row in rows if row["id"] == str(notebook_id))


def _source_of(db: Session, recipe_id: UUID) -> UUID:
    source_id = db.scalar(select(RecipeModel.source_id).where(RecipeModel.id == recipe_id))
    assert source_id is not None
    return source_id


# --- User Story 1: a shared notebook passes on ----------------------------------------------


def test_the_longest_standing_member_inherits_and_nothing_else_changes(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    # The first to join has the higher id, so the id order alone would pick the wrong person.
    first, second = sorted(
        (_register(client, "ben"), _register(client, "carla")), key=lambda p: p[0], reverse=True
    )
    for _id, member_cookie, email in (first, second):
        _join(client, mailer, notebook_id, cookie, member_cookie, email)
    first_joined = _set_joined(db_session, notebook_id, first[0], 9)
    second_joined = _set_joined(db_session, notebook_id, second[0], 3)
    db_session.add(IngredientModel(notebook_id=notebook_id, name="saffron"))
    db_session.flush()
    by_owner = _recipe(db_session, notebook_id, owner)
    by_member = _recipe(db_session, notebook_id, first[0])
    names = _names(db_session, notebook_id)

    result = _settle(db_session, owner)

    assert result == PassOwnedNotebooksResult(
        passed=[PassedNotebook(notebook_id=notebook_id, new_owner_id=first[0])], deleted=[]
    )
    assert _role(db_session, notebook_id, first[0]) == "owner"
    assert _role(db_session, notebook_id, second[0]) == "member"
    assert _joined(db_session, notebook_id, first[0]) == first_joined
    assert _joined(db_session, notebook_id, second[0]) == second_joined
    assert _names(db_session, notebook_id) == names
    assert db_session.get(NotebookModel, notebook_id).name == "ana's Notebook"
    assert db_session.get(RecipeModel, by_owner).author_id is None
    assert db_session.get(RecipeModel, by_member).author_id == first[0]

    _use(client, second[1])
    assert client.get(f"/recipes/{by_owner}").status_code == 200
    row = _listed(client, notebook_id)
    assert row["access"] == "member"
    assert row["owner_alias"] == alias_from_email(first[2])
    members = client.get(f"/notebooks/{notebook_id}/members").json()["members"]
    assert {member["user_id"] for member in members} == {str(first[0]), str(second[0])}

    # The new owner has what an owner has, with no step on their part (SC-006).
    _use(client, first[1])
    assert _listed(client, notebook_id)["access"] == "owner"
    assert _invite(client, notebook_id, "dara@example.test").status_code == 201
    response = client.delete(f"/notebooks/{notebook_id}/members/{second[0]}")
    assert response.status_code == 204


def test_the_heir_keeps_their_edit_lock_and_their_own_default_notebook(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    recipe_id = _recipe(db_session, notebook_id, owner)
    own = _personal(db_session, ben_id, "ben's Notebook")
    db_session.execute(
        update(UserModel).where(UserModel.id == ben_id).values(default_notebook_id=own)
    )
    assert client.post(f"/recipes/{recipe_id}/edit-lock").status_code == 200
    assert _locks(db_session, ben_id) == 1

    _settle(db_session, owner)

    assert _locks(db_session, ben_id) == 1
    assert db_session.get(UserModel, ben_id).default_notebook_id == own


def test_a_member_who_rejoined_counts_from_the_rejoining(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    carla_id, carla_cookie, carla_email = _register(client, "carla")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    _join(client, mailer, notebook_id, cookie, carla_cookie, carla_email)
    _set_joined(db_session, notebook_id, ben_id, 9)
    _set_joined(db_session, notebook_id, carla_id, 5)

    _use(client, ben_cookie)
    assert client.delete(f"/notebooks/{notebook_id}/members/me").status_code == 204
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)

    result = _settle(db_session, owner)

    assert [row.new_owner_id for row in result.passed] == [carla_id]
    assert _role(db_session, notebook_id, ben_id) == "member"


def test_members_who_joined_at_the_same_moment_give_the_same_heir_every_time(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, first = ana
    second = _personal(db_session, owner, "ana's other Notebook")
    people = [_register(client, "ben"), _register(client, "carla")]
    for notebook_id in (first, second):
        for _id, member_cookie, email in people:
            _join(client, mailer, notebook_id, cookie, member_cookie, email)
            _set_joined(db_session, notebook_id, _id, 4)

    result = _settle(db_session, owner)

    expected = min(person[0] for person in people)
    assert sorted(row.new_owner_id for row in result.passed) == [expected, expected]


def test_several_notebooks_can_go_to_different_people(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, first = ana
    second = _personal(db_session, owner, "ana's other Notebook")
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    carla_id, carla_cookie, carla_email = _register(client, "carla")
    _join(client, mailer, first, cookie, ben_cookie, ben_email)
    _join(client, mailer, second, cookie, carla_cookie, carla_email)

    _settle(db_session, owner)

    assert _owners(db_session, first) == [ben_id]
    assert _owners(db_session, second) == [carla_id]


def test_open_invites_outlive_the_owner(client, db_session: Session, mailer, ana) -> None:
    owner, cookie, notebook_id = ana
    ben_id, ben_cookie, ben_email = _register(client, "ben")
    dara_id, dara_cookie, dara_email = _register(client, "dara")
    _, _, eve_email = _register(client, "eve")
    _join(client, mailer, notebook_id, cookie, ben_cookie, ben_email)
    _use(client, cookie)
    assert _invite(client, notebook_id, dara_email).status_code == 201
    token = _token(mailer)
    sent = _invite(client, notebook_id, eve_email)
    assert sent.status_code == 201
    eve_invite = UUID(sent.json()["invite"]["id"])

    _settle(db_session, owner)

    client.cookies.clear()
    preview = _preview(client, token)
    assert preview.status_code == 200
    assert preview.json()["notebook_name"] == "ana's Notebook"
    assert preview.json()["inviter_alias"] is None

    _use(client, dara_cookie)
    assert _accept(client, token).status_code == 200
    assert _role(db_session, notebook_id, dara_id) == "member"

    _use(client, ben_cookie)
    open_invites = client.get(f"/notebooks/{notebook_id}/invites").json()["invites"]
    assert [row["id"] for row in open_invites] == [str(eve_invite)]
    response = client.post(f"/notebooks/{notebook_id}/invites/{eve_invite}/resend")
    assert response.status_code < 300, response.text
    db_session.expire_all()
    assert db_session.get(NotebookInviteModel, eve_invite).invited_by == ben_id


def test_a_failed_deletion_changes_no_notebook(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, ben = uuid4(), uuid4()
    shared, alone = uuid4(), uuid4()
    with factory() as db:
        for user_id in (owner, ben):
            db.add(
                UserModel(id=user_id, email=f"{user_id.hex[:12]}@example.test", password_hash="x")
            )
        db.add_all([NotebookModel(id=shared, name="shared"), NotebookModel(id=alone, name="alone")])
        db.flush()
        db.add_all(
            [
                NotebookMembershipModel(notebook_id=shared, user_id=owner, role="owner"),
                NotebookMembershipModel(notebook_id=shared, user_id=ben, role="member"),
                NotebookMembershipModel(notebook_id=alone, user_id=owner, role="owner"),
            ]
        )
        recipe_id = _recipe(db, alone, owner)
        db.commit()

    try:
        with factory() as db:
            result = _settle(db, owner)
            assert len(result.passed) == 1
            assert result.deleted == [alone]
            db.rollback()

        with factory() as db:
            assert db.get(UserModel, owner) is not None
            assert _owners(db, shared) == [owner]
            assert _role(db, shared, ben) == "member"
            assert _owners(db, alone) == [owner]
            assert db.get(RecipeModel, recipe_id) is not None
            assert db.get(SourceModel, _source_of(db, recipe_id)) is not None
    finally:
        with factory() as db:
            db.execute(delete(SourceModel).where(SourceModel.user_id == owner))
            db.commit()
        _cleanup(factory, notebooks=[shared, alone], kitchens=[], users=[owner, ben])


# --- Concurrency ----------------------------------------------------------------------------


def _people(factory: sessionmaker[Session], count: int) -> list[UUID]:
    ids = [uuid4() for _ in range(count)]
    with factory() as db:
        for user_id in ids:
            db.add(
                UserModel(id=user_id, email=f"{user_id.hex[:12]}@example.test", password_hash="x")
            )
        db.commit()
    return ids


def _shared_notebook(factory: sessionmaker[Session], owner: UUID, *members: UUID) -> UUID:
    notebook_id = uuid4()
    with factory() as db:
        db.add(NotebookModel(id=notebook_id, name="shared"))
        db.flush()
        db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
        for index, member in enumerate(members):
            db.add(
                NotebookMembershipModel(
                    notebook_id=notebook_id,
                    user_id=member,
                    role="member",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
                )
            )
        db.commit()
    return notebook_id


def _in_background(
    factory: sessionmaker[Session], call: Callable[[Session], object]
) -> tuple[threading.Thread, list[BaseException | None]]:
    outcome: list[BaseException | None] = []

    def run() -> None:
        with factory() as session:
            try:
                call(session)
                session.commit()
                outcome.append(None)
            except Exception as exc:  # checked in the main thread
                session.rollback()
                outcome.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    return worker, outcome


def _assert_waiting(worker: threading.Thread) -> None:
    time.sleep(0.4)
    assert worker.is_alive(), "the second request should wait for the notebook lock"


def _release(worker: threading.Thread, holder: Session) -> None:
    _assert_waiting(worker)
    holder.commit()
    worker.join(timeout=10)
    assert not worker.is_alive()


def _leave(notebook_id: UUID, user_id: UUID) -> Callable[[Session], None]:
    def call(session: Session) -> None:
        LeaveNotebookService(SqlAlchemyNotebookRepository(session)).execute(
            LeaveNotebookCommand(actor_user_id=user_id, notebook_id=notebook_id)
        )

    return call


def _accept_invite(user_id: UUID, raw: str, *, committer=None) -> Callable[[Session], object]:  # noqa: ANN001
    def call(session: Session) -> object:
        return _accept_service(
            session, committer=committer(session) if committer else None
        ).execute(
            AcceptNotebookInviteCommand(
                actor_user_id=user_id, raw_token=raw, email_verification_required=False
            )
        )

    return call


def test_an_heir_leaving_during_the_rule_is_refused_and_stays_owner(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, ben, carla = _people(factory, 3)
    notebook_id = _shared_notebook(factory, owner, ben, carla)
    try:
        with factory() as holder:
            _pass(holder, owner)
            worker, outcome = _in_background(factory, _leave(notebook_id, ben))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookOwnerStaysError)
        with factory() as db:
            assert _owners(db, notebook_id) == [ben]
            assert _role(db, notebook_id, carla) == "member"
    finally:
        _cleanup(factory, notebooks=[notebook_id], kitchens=[], users=[owner, ben, carla])


def test_a_member_who_left_first_does_not_inherit(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, ben, carla = _people(factory, 3)
    notebook_id = _shared_notebook(factory, owner, ben, carla)
    try:
        with factory() as holder:
            _leave(notebook_id, ben)(holder)
            worker, outcome = _in_background(factory, lambda session: _pass(session, owner))
            _release(worker, holder)

        assert outcome == [None]
        with factory() as db:
            assert _owners(db, notebook_id) == [carla]
            assert _role(db, notebook_id, ben) is None
    finally:
        _cleanup(factory, notebooks=[notebook_id], kitchens=[], users=[owner, ben, carla])


def test_someone_joining_during_the_rule_comes_in_as_a_member(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)
    carla = _people(factory, 1)[0]
    with factory() as db:
        db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=carla, role="member"))
        db.commit()
    try:
        with factory() as holder:
            _pass(holder, owner)
            worker, outcome = _in_background(factory, _accept_invite(person, raw))
            _release(worker, holder)

        assert outcome == [None]
        with factory() as db:
            assert _owners(db, notebook_id) == [carla]
            assert _role(db, notebook_id, person) == "member"
    finally:
        _finish(factory, notebook_id, owner, person, carla)


def test_someone_who_joined_first_inherits_a_notebook_that_would_have_been_deleted(
    engine: Engine,
) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)
    reached_commit, go_on = threading.Event(), threading.Event()

    class HoldingCommitter:
        def __init__(self, session: Session) -> None:
            self._session = session

        def commit(self) -> None:
            reached_commit.set()
            assert go_on.wait(timeout=10)
            self._session.commit()

    try:
        accept, accepted = _in_background(
            factory, _accept_invite(person, raw, committer=HoldingCommitter)
        )
        assert reached_commit.wait(timeout=10)
        rule, ruled = _in_background(factory, lambda session: _pass(session, owner))
        _assert_waiting(rule)
        go_on.set()
        accept.join(timeout=10)
        rule.join(timeout=10)

        assert accepted == [None]
        assert ruled == [None]
        with factory() as db:
            assert _owners(db, notebook_id) == [person]
    finally:
        go_on.set()
        _finish(factory, notebook_id, owner, person)


# --- User Story 2: no members ---------------------------------------------------------------


def test_a_notebook_with_no_members_goes_and_its_snapshot_stays(
    client, db_session: Session, mailer, ana
) -> None:
    owner, cookie, notebook_id = ana
    dana_id, _, _ = _register(client, "dana")
    kitchen_id = _kitchen(db_session, dana_id, members=(owner,))
    db_session.add(IngredientModel(notebook_id=notebook_id, name="saffron"))
    db_session.flush()
    alone = _recipe(db_session, notebook_id, owner)
    shared_source = _recipe(db_session, notebook_id, owner, "Bean stew")
    _use(client, cookie)
    assert _add(client, kitchen_id, notebook_id).status_code < 300
    snapshot_id = db_session.scalar(
        select(NotebookModel.id).where(NotebookModel.source_notebook_id == notebook_id)
    )
    assert snapshot_id is not None
    snapshot_sources = list(
        db_session.scalars(
            select(RecipeModel.source_id).where(RecipeModel.notebook_id == snapshot_id)
        )
    )
    assert _invite(client, notebook_id, "dara@example.test").status_code == 201
    token = _token(mailer)

    gone_source = _source_of(db_session, alone)
    kept_source = _source_of(db_session, shared_source)
    elsewhere = _recipe(db_session, _personal(db_session, dana_id, "dana's Notebook"), dana_id)
    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == elsewhere).values(source_id=kept_source)
    )

    result = _settle(db_session, owner)

    assert result == PassOwnedNotebooksResult(passed=[], deleted=[notebook_id])
    assert db_session.get(NotebookModel, notebook_id) is None
    assert db_session.get(RecipeModel, alone) is None
    assert _names(db_session, notebook_id) == []
    count = select(func.count()).select_from(NotebookInviteModel)
    assert db_session.scalar(count.where(NotebookInviteModel.notebook_id == notebook_id)) == 0

    # The captured text goes too, unless another recipe still uses it (research R5).
    assert db_session.get(SourceModel, gone_source) is None
    assert db_session.get(SourceModel, kept_source) is not None

    snapshot = db_session.get(NotebookModel, snapshot_id)
    assert snapshot is not None
    assert snapshot.source_notebook_id is None
    assert sorted(
        db_session.scalars(
            select(RecipeModel.source_id).where(RecipeModel.notebook_id == snapshot_id)
        ),
        key=str,
    ) == sorted(snapshot_sources, key=str)
    assert all(db_session.get(SourceModel, source) for source in snapshot_sources)

    client.cookies.clear()
    assert _preview(client, token).status_code == 410


def test_an_invite_accepted_while_the_notebook_is_deleted_answers_as_invalid(
    engine: Engine,
) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook_id, raw = _committed_invite(factory)
    try:
        with factory() as holder:
            result = _pass(holder, owner)
            assert result.deleted == [notebook_id]
            worker, outcome = _in_background(factory, _accept_invite(person, raw))
            _release(worker, holder)

        assert isinstance(outcome[0], InvalidInviteTokenError)
        with factory() as db:
            assert db.get(NotebookModel, notebook_id) is None
            assert _role(db, notebook_id, person) is None
    finally:
        _finish(factory, notebook_id, owner, person)


# --- User Story 3: what is not the owner's --------------------------------------------------


def test_what_the_person_does_not_own_keeps_its_owner_and_its_contents(
    client, db_session: Session, mailer
) -> None:
    ana_id, ana_cookie, ana_email = _register(client, "ana")
    dana_id, dana_cookie, _ = _register(client, "dana")
    ben_id, ben_cookie, ben_email = _register(client, "ben")

    danas = _personal(db_session, dana_id, "dana's Notebook")
    _join(client, mailer, danas, dana_cookie, ana_cookie, ana_email)
    added_by_ana = _recipe(db_session, danas, ana_id)

    kitchen_id = _kitchen(db_session, dana_id, members=(ana_id,))
    kitchen_notebook = uuid4()
    db_session.add(
        NotebookModel(
            id=kitchen_notebook,
            name="ana's (Home) Notebook",
            kitchen_id=kitchen_id,
            owner_user_id=ana_id,
        )
    )
    db_session.flush()
    in_kitchen = _recipe(db_session, kitchen_notebook, ana_id)

    own = _personal(db_session, ana_id)
    _join(client, mailer, own, ana_cookie, ben_cookie, ben_email)
    _use(client, ana_cookie)
    assert _add(client, kitchen_id, own).status_code < 300
    snapshot_id = db_session.scalar(
        select(NotebookModel.id).where(NotebookModel.source_notebook_id == own)
    )

    result = _settle(db_session, ana_id)

    assert result == PassOwnedNotebooksResult(
        passed=[PassedNotebook(notebook_id=own, new_owner_id=ben_id)], deleted=[]
    )
    assert _owners(db_session, danas) == [dana_id]
    assert _role(db_session, danas, ana_id) is None
    assert db_session.get(RecipeModel, added_by_ana).author_id is None

    stored = db_session.get(NotebookModel, kitchen_notebook)
    assert stored.owner_user_id is None
    assert db_session.get(RecipeModel, in_kitchen) is not None
    _use(client, dana_cookie)
    assert client.get(f"/notebooks/{kitchen_notebook}").status_code == 200

    assert db_session.get(NotebookModel, snapshot_id).source_notebook_id == own
