"""In-memory ports for the translation job's application tests (spec 073). No database."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from application.ports import PendingStandardIngredient, RecipeScan
from domain.ingredient_discovery import Candidate, RecipeLineName

Language = Literal["en", "es"]
T0 = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


class Clock:
    """Each call moves time forward one minute, so timestamps are ordered and deterministic."""

    def __init__(self) -> None:
        self._now = T0

    def __call__(self) -> datetime:
        self._now += timedelta(minutes=1)
        return self._now


@dataclass
class _Ingredient:
    id: UUID
    language: Language
    created_at: datetime
    names: dict[Language, tuple[str, str]] = field(default_factory=dict)  # lang -> (name, source)
    ai_checked_at: datetime | None = None
    model: str | None = None


@dataclass
class FakeCatalog:
    """Standard table in memory. `lines` are recipe lines; `recipe_count` the recipes they span."""

    lines: list[RecipeLineName] = field(default_factory=list)
    recipe_count: int = 0
    ingredients: dict[str, _Ingredient] = field(default_factory=dict)  # by discovery key
    _order: int = 0

    def recipe_scan_since(self, since: datetime | None) -> RecipeScan:
        return RecipeScan(lines=list(self.lines), recipes_scanned=self.recipe_count)

    def add_discovered(self, candidates: Sequence[Candidate]) -> int:
        created = 0
        for candidate in candidates:
            if candidate.key in self.ingredients:
                continue
            self._order += 1
            ingredient = _Ingredient(
                id=uuid4(),
                language=candidate.language,
                created_at=T0 + timedelta(seconds=self._order),
            )
            ingredient.names[candidate.language] = (candidate.name, "discovery")
            self.ingredients[candidate.key] = ingredient
            created += 1
        return created

    def pending_translations(self, limit: int) -> list[PendingStandardIngredient]:
        pending = sorted(
            (i for i in self.ingredients.values() if i.ai_checked_at is None),
            key=lambda i: i.created_at,
        )
        return [
            PendingStandardIngredient(id=i.id, name=i.names[i.language][0], language=i.language)
            for i in pending[:limit]
        ]

    def has_name_in_language(self, ingredient_id: UUID, language: Language) -> bool:
        return any(i.id == ingredient_id and language in i.names for i in self.ingredients.values())

    def save_translation(
        self, ingredient_id: UUID, name: str, language: Language, model: str, checked_at: datetime
    ) -> None:
        ingredient = self._by_id(ingredient_id)
        ingredient.names[language] = (name, "ai")
        ingredient.model = model
        ingredient.ai_checked_at = checked_at

    def mark_checked(self, ingredient_id: UUID, checked_at: datetime) -> None:
        self._by_id(ingredient_id).ai_checked_at = checked_at

    def _by_id(self, ingredient_id: UUID) -> _Ingredient:
        return next(i for i in self.ingredients.values() if i.id == ingredient_id)

    def names_for(self, key: str) -> dict[Language, tuple[str, str]]:
        return self.ingredients[key].names


@dataclass
class FakeRunLog:
    runs: list[dict[str, object]] = field(default_factory=list)
    watermark: datetime | None = None

    def start(self, started_at: datetime) -> UUID:
        run_id = uuid4()
        self.runs.append({"id": run_id, "status": "running", "started_at": started_at})
        return run_id

    def skip(self, at: datetime) -> None:
        self.runs.append({"status": "skipped", "started_at": at})

    def finish(self, run_id: UUID, **fields: object) -> None:
        run = next(r for r in self.runs if r.get("id") == run_id)
        run.update(fields)
        if fields.get("status") == "succeeded":
            self.watermark = run["started_at"]  # type: ignore[assignment]

    def last_succeeded_start(self) -> datetime | None:
        return self.watermark


@dataclass
class FakeLock:
    busy: bool = False

    @contextmanager
    def try_acquire(self) -> Iterator[bool]:
        yield not self.busy


@dataclass
class EmitLog:
    events: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def __call__(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]
