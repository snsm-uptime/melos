"""SqlRefusedSiteLog on Postgres (spec 067 T016; R3, R4, R6).

Requires DATABASE_URL (Compose test overlay or CI Postgres 16). Skips when unset.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from uuid import uuid4

import pytest
from adapters.persistence.refused_sites import (
    SqlRefusedSiteLog,
    derive_key,
    member_key,
    registrable_domain,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

KEY = derive_key("test-session-secret-not-for-prod")


def _row(db: Session, domain: str):
    return (
        db.execute(
            text(
                "SELECT total_refusals, distinct_members, first_seen_at, last_seen_at, "
                "last_status, last_message FROM refused_site WHERE domain = :d"
            ),
            {"d": domain},
        )
        .mappings()
        .one_or_none()
    )


def test_first_and_repeated_refusals(db_session: Session) -> None:
    log = SqlRefusedSiteLog(db_session, key=KEY)
    alice, bob = uuid4(), uuid4()

    log.record("example.com", alice, 402, "first")
    first = _row(db_session, "example.com")
    assert first is not None
    assert (first["total_refusals"], first["distinct_members"]) == (1, 1)
    assert first["first_seen_at"] == first["last_seen_at"]
    assert (first["last_status"], first["last_message"]) == (402, "first")

    log.record("www.example.com", alice, 403, "second")
    again = _row(db_session, "example.com")
    assert (again["total_refusals"], again["distinct_members"]) == (2, 1)
    assert (again["last_status"], again["last_message"]) == (403, "second")
    assert again["first_seen_at"] == first["first_seen_at"]

    log.record("m.example.com", bob, 451, "")
    third = _row(db_session, "example.com")
    assert (third["total_refusals"], third["distinct_members"]) == (3, 2)
    assert db_session.scalar(text("SELECT count(*) FROM refused_site")) == 1


@pytest.mark.parametrize(
    ("host", "domain"),
    [
        ("www.example.com", "example.com"),
        ("news.bbc.co.uk", "bbc.co.uk"),
        ("WWW.Allrecipes.COM.", "allrecipes.com"),
        ("localhost", "localhost"),
    ],
)
def test_registrable_domain(host: str, domain: str) -> None:
    assert registrable_domain(host) == domain


def test_a_long_message_is_cut(db_session: Session) -> None:
    SqlRefusedSiteLog(db_session, key=KEY).record("long.test", uuid4(), 402, "x" * 5000)

    assert len(_row(db_session, "long.test")["last_message"]) == 1000


def test_member_rows_hold_no_user_id(db_session: Session) -> None:
    user = uuid4()
    log = SqlRefusedSiteLog(db_session, key=KEY)
    log.record("one.test", user, 403, "")
    log.record("two.test", user, 403, "")

    keys = [
        bytes(k)
        for (k,) in db_session.execute(
            text("SELECT member_key FROM refused_site_member ORDER BY domain")
        )
    ]
    assert len(keys) == 2 and all(len(k) == 32 for k in keys)
    assert keys[0] != keys[1]
    assert keys == [member_key(KEY, "one.test", user), member_key(KEY, "two.test", user)]
    assert user.bytes not in keys[0] and str(user).encode() not in keys[0]


def test_a_failed_write_leaves_the_session_usable(db_session: Session) -> None:
    log = SqlRefusedSiteLog(db_session, key=KEY)

    with pytest.raises(IntegrityError):
        log.record("bad.test", uuid4(), 404, "")  # breaks the status CHECK

    assert db_session.scalar(text("SELECT 1")) == 1
    log.record("good.test", uuid4(), 402, "")
    assert _row(db_session, "good.test") is not None


@pytest.fixture
def committed(engine: Engine) -> Iterator[sessionmaker]:
    factory = sessionmaker(bind=engine)
    yield factory
    with factory() as cleanup:
        cleanup.execute(text("DELETE FROM refused_site WHERE domain = 'race.test'"))
        cleanup.commit()


def test_two_first_refusals_at_once_make_one_row(committed: sessionmaker) -> None:
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def one() -> None:
        try:
            with committed() as session:
                barrier.wait()
                SqlRefusedSiteLog(session, key=KEY).record("race.test", uuid4(), 402, "")
                session.commit()
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=one) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    with committed() as session:
        row = _row(session, "race.test")
    assert (row["total_refusals"], row["distinct_members"]) == (2, 2)
