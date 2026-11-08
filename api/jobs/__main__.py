"""Entry point for the scheduled jobs service: `python -m jobs` (spec 073).

Loop: write the heartbeat, run the translation job once, sleep JOBS_INTERVAL_SECONDS. With
JOBS_RUN_ONCE=1 it runs once and exits 0 after a succeeded or skipped run, 1 after a failed one.
A missing model name or API key stops it at startup with a message (FR-015, FR-014). A database
that is not ready yet is retried with a fixed delay, and the process does not exit (FR-011).
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime

from adapters.llm.gemini_translator import GeminiIngredientTranslator
from adapters.persistence.db import get_engine, get_session_factory
from adapters.persistence.job_lock import JobLock
from adapters.persistence.job_runs import SqlAlchemyJobRunLog
from adapters.persistence.standard_ingredients import SqlAlchemyStandardCatalog
from api.settings import GeminiSettings, JobsSettings, load_gemini_settings, load_jobs_settings
from application.translate_ingredients import RunSummary, TranslateIngredients
from sqlalchemy import text

from jobs import heartbeat
from jobs.run_log import emit

DB_RETRY_SECONDS = 10


class ConfigError(RuntimeError):
    """A required setting is missing. Raised before anything runs."""


def _wait_for_database() -> None:
    engine = get_engine()
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:
            emit("db.wait", attempt=attempt, retry_in_s=DB_RETRY_SECONDS, error=type(exc).__name__)
            time.sleep(DB_RETRY_SECONDS)


def _build_job(
    jobs_settings: JobsSettings, gemini_settings: GeminiSettings
) -> TranslateIngredients:
    session_factory = get_session_factory()
    translator = GeminiIngredientTranslator(
        api_key=gemini_settings.api_key,
        model=jobs_settings.translate_model,
        timeout_s=gemini_settings.text_timeout_s,
    )
    return TranslateIngredients(
        catalog=SqlAlchemyStandardCatalog(session_factory),
        runs=SqlAlchemyJobRunLog(session_factory),
        lock=JobLock(get_engine()),
        translator=translator,
        model=jobs_settings.translate_model,
        batch_size=jobs_settings.translate_batch_size,
        clock=lambda: datetime.now(UTC),
        emit=emit,
    )


def _check_config(jobs_settings: JobsSettings, gemini_settings: GeminiSettings) -> None:
    if not jobs_settings.translate_model:
        raise ConfigError("GEMINI_TRANSLATE_MODEL is required: set the model name in .env")
    if not gemini_settings.api_key:
        raise ConfigError("GEMINI_API_KEY is required: set it in .env")


def _exit_code(summary: RunSummary) -> int:
    return 1 if summary.status == "failed" else 0


def main() -> int:
    jobs_settings = load_jobs_settings()
    gemini_settings = load_gemini_settings()
    try:
        _check_config(jobs_settings, gemini_settings)
    except ConfigError as exc:
        print(f"jobs: {exc}", file=sys.stderr)
        return 2

    _wait_for_database()
    job = _build_job(jobs_settings, gemini_settings)

    while True:
        heartbeat.write(jobs_settings.heartbeat_path)
        summary = job.run()
        if jobs_settings.run_once:
            return _exit_code(summary)
        time.sleep(jobs_settings.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
