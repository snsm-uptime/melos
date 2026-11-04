# Constitution exception (principle 1, "No queue, no worker"): approved in writing by the
# project lead on 2026-11-02 (specs/019-recipe-embeddings-search/spec.md, Clarifications).
# Scope: background jobs running inside the api process, with their state in Postgres. No new
# service and no queue system.
"""The embedding worker: one daemon thread per api process (spec 019 research R3).

On start it checks that the stored column matches GEMINI_EMBED_DIM, then runs the catch-up
(FR-010) without delaying start-up, and loops: it runs passes of EmbedPendingRecipes while jobs
are due, then waits EMBED_WORKER_POLL_S or until a save, edit or snapshot wakes it. Each pass
has its own session. Once a day it deletes old search records (FR-017e).

Correctness never depends on waking: the job row is written in the request's transaction.
Logs carry counts and class names only (FR-023).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from adapters.llm.gemini_embedder import GeminiEmbedder
from adapters.persistence.embeddings import SqlAlchemyEmbeddingJobs, SqlAlchemyRecipeEmbeddings
from adapters.persistence.notebooks import SqlAlchemyTransactionCommitter
from adapters.persistence.search_records import SqlAlchemySearchRecords
from application.embedding_worker import (
    CleanUpSearchRecords,
    EmbedPendingRecipes,
    strategy_named,
)
from application.ports import Embedder
from domain.retry import RetryPolicy, next_wait
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.settings import EmbeddingSettings

logger = logging.getLogger(__name__)

# Seconds between checks when no key or model is configured (FR-014).
NOT_CONFIGURED_WAIT_S = 60.0
# A request wakes the worker before its transaction commits; this lets the commit land first.
WAKE_GRACE_S = 0.5
# The daily clean-up runs on the first pass after this local hour.
CLEANUP_HOUR = 3
# A pass that keeps finding work yields after this many batches, to check the stop flag and logs.
MAX_BATCHES_PER_WAKE = 500


def make_embedder(settings: EmbeddingSettings) -> GeminiEmbedder:
    return GeminiEmbedder(
        api_key=settings.api_key, model=settings.model, dimension=settings.dimension
    )


def column_dimension(session: Session) -> int | None:
    """The dimension of recipe_embedding.embedding as stored, or None if it cannot be read."""
    spec = session.execute(
        text(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid = to_regclass('recipe_embedding') AND attname = 'embedding'"
        )
    ).scalar_one_or_none()
    if not spec or not spec.startswith("vector(") or not spec.endswith(")"):
        return None
    try:
        return int(spec[len("vector(") : -1])
    except ValueError:
        return None


class EmbeddingWorker:
    def __init__(
        self,
        settings: EmbeddingSettings,
        session_factory: Callable[[], Session],
        embedder: Embedder,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now().astimezone(),
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._embedder = embedder
        self._clock = clock
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._policy = RetryPolicy(
            first_s=settings.retry_first_wait_s,
            growth=settings.retry_growth,
            cap_s=settings.retry_cap_s,
        )
        # Daily clean-up state, in memory: a restart runs it again, which is harmless.
        self._cleaned_on: date | None = None
        self._cleanup_retry_at: datetime | None = None
        self._cleanup_last_wait: float | None = None

    # --- lifecycle -----------------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="embedding-worker", daemon=True)
        self._thread.start()

    def wake(self) -> None:
        self._wake.set()

    def stop(self, timeout_s: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # --- the loop ------------------------------------------------------------------------------

    def _run(self) -> None:
        if not self._dimension_matches():
            return
        if not self._embedder.configured:
            logger.info("embeddings not configured; the worker waits")
            while not self._embedder.configured and not self._stop.wait(NOT_CONFIGURED_WAIT_S):
                pass
            if self._stop.is_set():
                return
        self.catch_up()
        while not self._stop.is_set():
            self.run_cleanup_if_due()
            self.drain()
            woken = self._wake.wait(self._settings.worker_poll_s)
            self._wake.clear()
            if woken and not self._stop.is_set():
                self._stop.wait(WAKE_GRACE_S)

    def _dimension_matches(self) -> bool:
        try:
            with self._session_factory() as session:
                stored = column_dimension(session)
        except Exception as exc:  # the database may still be starting
            logger.error("embedding worker not started: class=%s", type(exc).__name__)
            return False
        if stored != self._settings.dimension:
            logger.error(
                "embedding worker not started: GEMINI_EMBED_DIM=%d but the column holds %s",
                self._settings.dimension,
                stored,
            )
            return False
        return True

    def catch_up(self) -> int:
        """Queue every recipe without a current embedding (FR-010). Safe to repeat."""
        try:
            with self._session_factory() as session:
                queued = SqlAlchemyEmbeddingJobs(session).enqueue_missing(self._embedder.model)
                session.commit()
        except Exception as exc:
            logger.error("embedding catch-up failed: class=%s", type(exc).__name__)
            return 0
        logger.info("embedding catch-up queued=%d", queued)
        return queued

    def drain(self) -> int:
        """Run passes while jobs are due; returns how many jobs were handled."""
        handled = 0
        for _ in range(MAX_BATCHES_PER_WAKE):
            if self._stop.is_set():
                break
            try:
                with self._session_factory() as session:
                    count = self._pass(session).run_once()
            except Exception as exc:
                logger.error("embedding pass failed: class=%s", type(exc).__name__)
                break
            if count == 0:
                break
            handled += count
        self._log_backlog()
        return handled

    def _pass(self, session: Session) -> EmbedPendingRecipes:
        return EmbedPendingRecipes(
            SqlAlchemyEmbeddingJobs(session),
            SqlAlchemyRecipeEmbeddings(session),
            self._embedder,
            strategy_named(self._settings.strategy),
            SqlAlchemyTransactionCommitter(session),
            batch_size=self._settings.batch_size,
            timeout_s=self._settings.text_timeout_s,
            policy=self._policy,
        )

    def _log_backlog(self) -> None:
        try:
            with self._session_factory() as session:
                backlog = SqlAlchemyEmbeddingJobs(session).backlog()
        except Exception as exc:
            logger.error("embedding backlog unreadable: class=%s", type(exc).__name__)
            return
        if backlog.count:
            oldest = backlog.oldest_enqueued_at or datetime.now(UTC)
            waited = max(0, int((datetime.now(UTC) - oldest).total_seconds()))
            logger.info("embedding backlog count=%d oldest_s=%d", backlog.count, waited)

    # --- daily clean-up (FR-017e) --------------------------------------------------------------

    def run_cleanup_if_due(self) -> bool:
        now = self._clock()
        if self._cleanup_retry_at is not None:
            if now < self._cleanup_retry_at:
                return False
        elif self._cleaned_on is not None and (
            now.date() <= self._cleaned_on or now.hour < CLEANUP_HOUR
        ):
            return False
        try:
            with self._session_factory() as session:
                CleanUpSearchRecords(
                    SqlAlchemySearchRecords(session),
                    SqlAlchemyTransactionCommitter(session),
                    retention_days=self._settings.record_retention_days,
                ).run(now)
        except Exception as exc:
            # The shared retry rule, with its defaults (FR-009a).
            self._cleanup_last_wait = next_wait(self._cleanup_last_wait)
            self._cleanup_retry_at = now + timedelta(seconds=self._cleanup_last_wait)
            logger.error(
                "search record clean-up failed: class=%s retry_s=%d",
                type(exc).__name__,
                self._cleanup_last_wait,
            )
            return False
        self._cleaned_on = now.date()
        self._cleanup_retry_at = None
        self._cleanup_last_wait = None
        return True


def start_embedding_worker(
    app: FastAPI, settings: EmbeddingSettings, session_factory: Callable[[], Session]
) -> EmbeddingWorker:
    embedder = getattr(app.state, "embedder", None) or make_embedder(settings)
    app.state.embedder = embedder
    worker = EmbeddingWorker(settings, session_factory, embedder)
    worker.start()
    app.state.embedding_worker = worker
    return worker


def wake_embedding_worker(app: FastAPI) -> None:
    """Shorten the worker's wait after a save, edit or snapshot. Does nothing when it is off."""
    worker = getattr(app.state, "embedding_worker", None)
    if worker is not None:
        worker.wake()
