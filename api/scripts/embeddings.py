"""Operator commands for recipe embeddings and search records (spec 019).

Run inside the api container:

    docker compose exec api uv run python -m scripts.embeddings <subcommand>

| Subcommand | Does |
|---|---|
| catch-up [--reembed-other-strategy] | queue recipes without a current embedding (FR-011, FR-013) |
| status | backlog count, longest wait, failures by class (FR-009b) |
| score-report [--width 0.05] | used share per score band (FR-017d) |
| cleanup | delete search records past the retention now (FR-017e) |

Each prints plain lines, exits 0, or 1 on a database error. Every subcommand is safe to repeat;
the worker does the embedding calls.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from adapters.persistence.db import get_session_factory
from adapters.persistence.embeddings import SqlAlchemyEmbeddingJobs
from adapters.persistence.notebooks import SqlAlchemyTransactionCommitter
from adapters.persistence.search_records import SqlAlchemySearchRecords
from api.settings import EmbeddingSettings, load_embedding_settings
from application.embedding_worker import CleanUpSearchRecords
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def catch_up(session: Session, settings: EmbeddingSettings, *, other_strategy: bool) -> list[str]:
    queued = SqlAlchemyEmbeddingJobs(session).enqueue_missing(
        settings.model, other_strategy_of=settings.strategy if other_strategy else None
    )
    session.commit()
    return [f"queued={queued}"]


def status(session: Session, now: datetime | None = None) -> list[str]:
    jobs = SqlAlchemyEmbeddingJobs(session)
    backlog = jobs.backlog()
    now = now or datetime.now(UTC)
    oldest = (
        max(0, int((now - backlog.oldest_enqueued_at).total_seconds()))
        if backlog.oldest_enqueued_at is not None
        else 0
    )
    lines = [f"waiting={backlog.count}", f"oldest_wait_s={oldest}"]
    lines.extend(f"failures {name}={count}" for name, count in jobs.failure_counts().items())
    return lines


def score_report(session: Session, width: float) -> list[str]:
    lines = ["low high shown used share"]
    for band in SqlAlchemySearchRecords(session).score_bands(width):
        share = band.used / band.shown if band.shown else 0.0
        lines.append(f"{band.low:.2f} {band.high:.2f} {band.shown} {band.used} {share:.2f}")
    return lines


def cleanup(session: Session, settings: EmbeddingSettings) -> list[str]:
    deleted = CleanUpSearchRecords(
        SqlAlchemySearchRecords(session),
        SqlAlchemyTransactionCommitter(session),
        retention_days=settings.record_retention_days,
    ).run(datetime.now(UTC))
    return [f"deleted={deleted}"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.embeddings")
    sub = parser.add_subparsers(dest="command", required=True)
    catch = sub.add_parser("catch-up", help="queue recipes without a current embedding")
    catch.add_argument(
        "--reembed-other-strategy",
        action="store_true",
        help="also queue recipes embedded with a strategy other than the configured one",
    )
    sub.add_parser("status", help="backlog and failures")
    report = sub.add_parser("score-report", help="used share per score band")
    report.add_argument("--width", type=float, default=0.05)
    sub.add_parser("cleanup", help="delete search records past the retention")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = load_embedding_settings()
    try:
        with get_session_factory()() as session:
            if args.command == "catch-up":
                lines = catch_up(session, settings, other_strategy=args.reembed_other_strategy)
            elif args.command == "status":
                lines = status(session)
            elif args.command == "score-report":
                if args.width <= 0:
                    print("--width must be > 0", file=sys.stderr)
                    return 2
                lines = score_report(session, args.width)
            else:
                lines = cleanup(session, settings)
    except SQLAlchemyError as exc:
        print(f"database error: {type(exc).__name__}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
