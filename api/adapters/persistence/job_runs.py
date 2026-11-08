"""SQLAlchemy JobRunLog: one `job_run` row per run, and the discovery watermark (spec 073, R5)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from adapters.persistence.models import JobRunModel


class SqlAlchemyJobRunLog:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def start(self, started_at: datetime) -> UUID:
        with self._session_factory.begin() as session:
            run = JobRunModel(started_at=started_at, status="running")
            session.add(run)
            session.flush()
            return run.id

    def skip(self, at: datetime) -> None:
        with self._session_factory.begin() as session:
            session.add(
                JobRunModel(started_at=at, finished_at=at, status="skipped", error="lock_busy")
            )

    def finish(
        self,
        run_id: UUID,
        *,
        status: Literal["succeeded", "failed"],
        finished_at: datetime,
        found: int,
        translated: int,
        rejected: int,
        failed: int,
        error: str | None,
    ) -> None:
        with self._session_factory.begin() as session:
            session.execute(
                update(JobRunModel)
                .where(JobRunModel.id == run_id)
                .values(
                    status=status,
                    finished_at=finished_at,
                    found=found,
                    translated=translated,
                    rejected=rejected,
                    failed=failed,
                    error=error,
                )
            )

    def last_succeeded_start(self) -> datetime | None:
        stmt = select(func.max(JobRunModel.started_at)).where(JobRunModel.status == "succeeded")
        with self._session_factory() as session:
            return session.execute(stmt).scalar_one()
