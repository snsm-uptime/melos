"""The worker thread's steps against Postgres (spec 019 research R3, FR-009b, FR-010, FR-017e).

Sessions share the test's connection with savepoints, so the worker's commits stay inside the
test transaction. The thread itself is only started for the not-configured case.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

import pytest
from api import worker as worker_module
from api.settings import load_embedding_settings
from api.worker import EmbeddingWorker
from application.recipe_extraction import Unavailable
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests import embedding_db as build
from tests.embedding_fakes import FakeEmbedder
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


@pytest.fixture
def shared(engine: Engine) -> Iterator[tuple[Session, sessionmaker]]:
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = factory()
    try:
        yield session, factory
    finally:
        session.close()
        transaction.rollback()
        connection.close()


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _worker(factory, *, dimension: int = 768, clock=None, embedder=None) -> EmbeddingWorker:  # noqa: ANN001
    settings = replace(load_embedding_settings(), model=build.MODEL, dimension=dimension)
    return EmbeddingWorker(
        settings,
        factory,
        embedder or FakeEmbedder(dimension=dimension, model=build.MODEL),
        **({"clock": clock} if clock else {}),
    )


@pytest.fixture(autouse=True)
def _logger_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module.logger, "disabled", False)


def test_the_dimension_check_reads_the_column(shared) -> None:  # noqa: ANN001
    _, factory = shared
    assert _worker(factory)._dimension_matches()
    assert not _worker(factory, dimension=3072)._dimension_matches()


def test_catch_up_then_drain_embeds_waiting_recipes(shared, caplog) -> None:  # noqa: ANN001
    session, factory = shared
    notebook = build.personal_notebook(session, build.user(session, "ana"))
    recipes: list[UUID] = [build.recipe(session, notebook, f"dish {n}") for n in range(3)]
    session.commit()
    worker = _worker(factory)
    caplog.set_level(logging.INFO)

    assert worker.catch_up() >= 3
    build.age_jobs(session, recipes)
    session.commit()
    worker.drain()

    for recipe in recipes:
        assert build.embedding_row(session, recipe) is not None
        assert build.job(session, recipe) is None
    assert "embedding catch-up queued=" in caplog.text
    assert "dish" not in caplog.text


def test_the_backlog_is_logged_with_counts_only(shared, caplog) -> None:  # noqa: ANN001
    session, factory = shared
    notebook = build.personal_notebook(session, build.user(session, "ben"))
    recipe = build.recipe(session, notebook, "secret dish")
    session.commit()
    failing = FakeEmbedder(dimension=768, model=build.MODEL, failure=Unavailable())
    worker = _worker(factory, embedder=failing)
    worker.catch_up()
    build.age_jobs(session, [recipe])
    session.commit()
    caplog.set_level(logging.INFO)

    worker.drain()

    assert "embedding backlog count=" in caplog.text and "oldest_s=" in caplog.text
    assert "secret dish" not in caplog.text
    assert build.job(session, recipe).last_failure == "Unavailable"


def test_the_daily_clean_up_runs_at_start_then_after_3_am(shared) -> None:  # noqa: ANN001
    session, factory = shared
    session.execute(
        text(
            "INSERT INTO search_event (feature, scope_kind, result_count, model, strategy,"
            " min_closeness, created_at) VALUES ('test', 'notebook', 0, 'm', 'toon', 0.65,"
            " now() - interval '200 days')"
        )
    )
    session.commit()
    clock = Clock(datetime(2026, 11, 3, 1, 0).astimezone())
    worker = _worker(factory, clock=clock)

    assert worker.run_cleanup_if_due() is True
    old = session.scalar(
        text("SELECT count(*) FROM search_event WHERE created_at < now() - interval '180 days'")
    )
    assert old == 0
    assert worker.run_cleanup_if_due() is False
    clock.now += timedelta(hours=1)  # 02:00 the same day
    assert worker.run_cleanup_if_due() is False
    clock.now += timedelta(days=1)  # 02:00 the next day
    assert worker.run_cleanup_if_due() is False
    clock.now += timedelta(hours=1, minutes=1)  # 03:01
    assert worker.run_cleanup_if_due() is True


def test_a_failed_clean_up_retries_by_the_shared_rule(shared, monkeypatch) -> None:  # noqa: ANN001
    _, factory = shared
    clock = Clock(datetime(2026, 11, 3, 4, 0).astimezone())
    worker = _worker(factory, clock=clock)

    def broken(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("database gone")

    monkeypatch.setattr(worker_module.CleanUpSearchRecords, "run", broken)
    assert worker.run_cleanup_if_due() is False
    clock.now += timedelta(seconds=59)
    assert worker.run_cleanup_if_due() is False
    clock.now += timedelta(seconds=2)
    assert worker.run_cleanup_if_due() is False  # failed again; next wait is 90 s
    assert worker._cleanup_last_wait == 90.0
    monkeypatch.undo()
    clock.now += timedelta(seconds=91)
    assert worker.run_cleanup_if_due() is True


def test_an_unconfigured_worker_waits_quietly_and_stops(shared, caplog) -> None:  # noqa: ANN001
    _, factory = shared
    embedder = FakeEmbedder(dimension=768, model=build.MODEL)
    embedder.configured = False
    worker = _worker(factory, embedder=embedder)
    caplog.set_level(logging.INFO)

    worker.start()
    worker.stop(timeout_s=5.0)

    assert not worker.alive
    assert caplog.text.count("embeddings not configured") == 1
    assert "ERROR" not in caplog.text
    assert embedder.calls == 0
