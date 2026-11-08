"""Scheduled job: find new standard ingredients, validate and translate each once (spec 073).

One run: take the lock (or record a skipped run), read the watermark, discover new names in recipe
lines since it, then ask the translator once per standard ingredient that has no AI check yet.
A run that fails in discovery does not move the watermark. A failed translation call leaves its
ingredient unchecked, so the next run retries it (FR-006). A quota error stops the run early.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from domain.ingredient_discovery import discover
from domain.ingredient_translation import (
    IngredientTranslationRequest,
    TranslationQuotaExceeded,
    TranslationUnavailable,
    TranslationUnparseable,
    target_language,
)

from application.ports import IngredientTranslator, JobRunLog, RunLock, StandardCatalog

Emit = Callable[..., None]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class RunSummary:
    status: Literal["succeeded", "failed", "skipped"]
    found: int = 0
    translated: int = 0
    rejected: int = 0
    failed: int = 0


@dataclass(slots=True)
class _Counts:
    found: int = 0
    translated: int = 0
    rejected: int = 0
    failed: int = 0


class TranslateIngredients:
    def __init__(
        self,
        *,
        catalog: StandardCatalog,
        runs: JobRunLog,
        lock: RunLock,
        translator: IngredientTranslator,
        model: str,
        batch_size: int,
        clock: Clock,
        emit: Emit,
    ) -> None:
        self._catalog = catalog
        self._runs = runs
        self._lock = lock
        self._translator = translator
        self._model = model
        self._batch_size = batch_size
        self._clock = clock
        self._emit = emit

    def run(self) -> RunSummary:
        with self._lock.try_acquire() as acquired:
            if not acquired:
                self._runs.skip(self._clock())
                self._emit("run.skipped", reason="lock_busy")
                return RunSummary(status="skipped")
            return self._run_locked()

    def _run_locked(self) -> RunSummary:
        started_at = self._clock()
        run_id = self._runs.start(started_at)
        self._emit("run.start", run_id=str(run_id), started_at=started_at.isoformat())

        counts = _Counts()
        status: Literal["succeeded", "failed"] = "succeeded"
        error: str | None = None
        try:
            watermark = self._runs.last_succeeded_start()
            scan = self._catalog.recipe_scan_since(watermark)
            counts.found = self._catalog.add_discovered(discover(scan.lines))
            self._emit(
                "discovery.done",
                run_id=str(run_id),
                recipes_scanned=scan.recipes_scanned,
                found=counts.found,
            )
            self._translate(run_id, counts)
        except Exception as exc:
            # Only the class name leaves the process: no message, no recipe text (run-log.md).
            status = "failed"
            error = type(exc).__name__

        finished_at = self._clock()
        self._runs.finish(
            run_id,
            status=status,
            finished_at=finished_at,
            found=counts.found,
            translated=counts.translated,
            rejected=counts.rejected,
            failed=counts.failed,
            error=error,
        )
        self._emit(
            "run.end",
            run_id=str(run_id),
            status=status,
            found=counts.found,
            translated=counts.translated,
            rejected=counts.rejected,
            failed=counts.failed,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
        )
        return RunSummary(
            status=status,
            found=counts.found,
            translated=counts.translated,
            rejected=counts.rejected,
            failed=counts.failed,
        )

    def _translate(self, run_id: Any, counts: _Counts) -> None:
        for item in self._catalog.pending_translations(self._batch_size):
            target = target_language(item.language)
            if self._catalog.has_name_in_language(item.id, target):
                # The name is already there (FR-005a): no call, and it counts as checked.
                self._catalog.mark_checked(item.id, self._clock())
                continue

            request = IngredientTranslationRequest(
                name=item.name, source_language=item.language, target_language=target
            )
            try:
                result = self._translator.translate(request)
            except TranslationQuotaExceeded:
                counts.failed += 1
                self._emit(
                    "translate.failed",
                    run_id=str(run_id),
                    standard_ingredient_id=str(item.id),
                    error_kind="quota",
                )
                break
            except TranslationUnavailable:
                counts.failed += 1
                self._emit(
                    "translate.failed",
                    run_id=str(run_id),
                    standard_ingredient_id=str(item.id),
                    error_kind="unavailable",
                )
                continue
            except TranslationUnparseable:
                counts.failed += 1
                self._emit(
                    "translate.failed",
                    run_id=str(run_id),
                    standard_ingredient_id=str(item.id),
                    error_kind="unparseable",
                )
                continue

            now = self._clock()
            if result.valid and result.translation is not None:
                self._catalog.save_translation(
                    item.id, result.translation, target, self._model, now
                )
                counts.translated += 1
                outcome = "translated"
            else:
                self._catalog.mark_checked(item.id, now)
                counts.rejected += 1
                outcome = "rejected"
            self._emit(
                "translate.item",
                run_id=str(run_id),
                standard_ingredient_id=str(item.id),
                outcome=outcome,
            )
