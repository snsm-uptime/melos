"""The operator command against Postgres (spec 019 contracts/worker-and-commands.md)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from api.settings import load_embedding_settings
from scripts import embeddings as command
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests import embedding_db as build
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


@pytest.fixture
def settings():  # noqa: ANN201
    return replace(load_embedding_settings(), model=build.MODEL, strategy="toon")


def test_catch_up_prints_queued_and_is_safe_to_repeat(db_session: Session, settings) -> None:  # noqa: ANN001
    notebook = build.personal_notebook(db_session, build.user(db_session, "ana"))
    plain = build.recipe(db_session, notebook, "plain")
    assert build.embed(db_session, plain, strategy="plain")
    build.recipe(db_session, notebook, "missing")

    first = command.catch_up(db_session, settings, other_strategy=False)
    second = command.catch_up(db_session, settings, other_strategy=False)
    other = command.catch_up(db_session, settings, other_strategy=True)

    assert first[0].startswith("queued=") and int(first[0].split("=")[1]) >= 1
    assert second == ["queued=0"]
    assert other == ["queued=1"]
    assert build.job(db_session, plain) is not None


def test_status_prints_the_backlog_and_failures(db_session: Session) -> None:
    notebook = build.personal_notebook(db_session, build.user(db_session, "ben"))
    recipe = build.recipe(db_session, notebook, "rice")
    db_session.execute(
        text(
            "INSERT INTO embedding_job (recipe_id, last_failure, enqueued_at)"
            " VALUES (:id, 'LimitReached', timestamptz '2000-01-01')"
        ),
        {"id": recipe},
    )

    lines = command.status(db_session, now=datetime(2000, 1, 1, 0, 1, tzinfo=UTC))

    assert lines[0].startswith("waiting=") and int(lines[0].split("=")[1]) >= 1
    assert lines[1] == "oldest_wait_s=60"
    assert any(line.startswith("failures LimitReached=") for line in lines)


def test_score_report_and_cleanup(db_session: Session, settings) -> None:  # noqa: ANN001
    notebook = build.personal_notebook(db_session, build.user(db_session, "carla"))
    recipe = build.recipe(db_session, notebook, "rice")
    search_id = db_session.scalar(
        text(
            "INSERT INTO search_event (feature, scope_kind, result_count, model, strategy,"
            " min_closeness, created_at) VALUES ('test', 'notebook', 1, 'm', 'toon', 0.65,"
            " now() - interval '400 days') RETURNING id"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO search_result (search_id, recipe_id, rank, score, mark, used_at)"
            " VALUES (:s, :r, 1, 0.712, 'close', now())"
        ),
        {"s": search_id, "r": recipe},
    )

    report = command.score_report(db_session, 0.05)
    assert report[0] == "low high shown used share"
    assert any(line.startswith("0.70 0.75 ") for line in report[1:])

    deleted = command.cleanup(db_session, settings)
    assert deleted[0].startswith("deleted=") and int(deleted[0].split("=")[1]) >= 1
    assert (
        db_session.scalar(
            text("SELECT count(*) FROM search_event WHERE id = :id"), {"id": search_id}
        )
        == 0
    )
