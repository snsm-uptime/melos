"""The unit table through its repository, on Postgres (spec 055 R2, R3, SC-003)."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator

import pytest
from adapters.persistence.units import SqlAlchemyUnitRepository
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

WORDS = ("zlata", "zbote")


def _user(session: Session) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.execute(
        text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'x')"),
        {"id": user_id, "email": f"units-{user_id}@example.com"},
    )
    return user_id


def _row(session: Session, name: str):
    return session.execute(
        text("SELECT user_references, reference_count, is_default FROM unit WHERE name = :n"),
        {"n": name},
    ).one_or_none()


@pytest.fixture
def clean_words(engine: Engine) -> Iterator[None]:
    yield
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM unit WHERE name = ANY(:w)"), {"w": list(WORDS)})


def test_two_people_keep_one_word_on_one_row(db_session: Session) -> None:
    units = SqlAlchemyUnitRepository(db_session)
    first, second = _user(db_session), _user(db_session)
    units.add_user(["lata"], first)
    units.add_user(["lata"], second)
    row = _row(db_session, "lata")
    assert set(row.user_references) == {first, second}
    assert row.reference_count == 2
    assert row.is_default is False


def test_the_same_person_twice_counts_once(db_session: Session) -> None:
    units = SqlAlchemyUnitRepository(db_session)
    person = _user(db_session)
    units.add_user(["lata"], person)
    units.add_user(["lata"], person)
    assert _row(db_session, "lata").reference_count == 1


def test_a_person_s_extras_show_nothing_of_another_account(db_session: Session) -> None:
    units = SqlAlchemyUnitRepository(db_session)
    first, second = _user(db_session), _user(db_session)
    units.add_user(["lata"], first)
    units.add_user(["bote"], second)
    assert units.extras_for(first) == ["lata"]
    assert units.extras_for(second) == ["bote"]


def test_extras_leave_out_the_ten_and_include_a_later_default(db_session: Session) -> None:
    units = SqlAlchemyUnitRepository(db_session)
    person = _user(db_session)
    assert units.extras_for(person) == []
    db_session.execute(text("INSERT INTO unit (name, is_default) VALUES ('sobre', true)"))
    assert units.extras_for(person) == ["sobre"]


def test_concurrent_saves_of_the_same_two_words_do_not_deadlock(
    engine: Engine, clean_words: None
) -> None:
    factory = sessionmaker(bind=engine)
    people = [uuid.uuid4() for _ in range(8)]
    start = threading.Barrier(len(people))
    failures: list[BaseException] = []

    def keep(index: int) -> None:
        # Half the callers list the words the other way round: the repository sorts them.
        names = list(WORDS) if index % 2 else list(reversed(WORDS))
        with factory() as session:
            try:
                start.wait(timeout=10)
                SqlAlchemyUnitRepository(session).add_user(names, people[index])
                session.commit()
            except BaseException as exc:  # noqa: BLE001 - reported by the assertion below
                failures.append(exc)

    threads = [threading.Thread(target=keep, args=(i,)) for i in range(len(people))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert failures == []
    with factory() as session:
        for word in WORDS:
            assert _row(session, word).reference_count == len(people)
