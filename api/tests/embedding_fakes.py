"""In-memory fakes for the embedding and search ports (spec 019). No network, no database."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from application.ports import (
    Backlog,
    Band,
    ClaimedJob,
    Embedded,
    EmbedFailure,
    EmbedResult,
    RawHit,
    RecipeDetail,
    RecordedHit,
    SearchEventRecord,
)
from domain.recipe_search import SearchFilters

DIM = 8


def fake_vector(text: str, dim: int = DIM) -> tuple[float, ...]:
    """A deterministic unit vector from a hash of the text."""
    digest = hashlib.sha256(text.encode()).digest()
    values = [(digest[i % len(digest)] - 127.5) / 127.5 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in values))
    return tuple(v / norm for v in values)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class FakeEmbedder:
    def __init__(
        self,
        *,
        model: str = "fake-embed",
        dimension: int = DIM,
        failure: EmbedFailure | None = None,
        token_count: int | None = 7,
        count_tokens_result: int | None = 11,
    ) -> None:
        self._model = model
        self._dimension = dimension
        self.failure = failure
        self.token_count = token_count
        self.count_tokens_result = count_tokens_result
        self.document_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.query_calls: list[str] = []
        self.count_calls: list[str] = []
        # Set to a vector to make every query embed to it.
        self.query_vector: tuple[float, ...] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    configured: bool = True

    @property
    def calls(self) -> int:
        return len(self.document_calls) + len(self.query_calls)

    def embed_documents(
        self, texts: Sequence[str], titles: Sequence[str], timeout_s: float
    ) -> EmbedResult:
        self.document_calls.append((tuple(texts), tuple(titles)))
        if self.failure is not None:
            return self.failure
        return Embedded(
            vectors=tuple(fake_vector(text, self._dimension) for text in texts),
            token_counts=tuple(self.token_count for _ in texts),
            truncated=tuple(False for _ in texts),
        )

    def embed_query(self, text: str, timeout_s: float) -> EmbedResult:
        self.query_calls.append(text)
        if self.failure is not None:
            return self.failure
        vector = self.query_vector or fake_vector(text, self._dimension)
        return Embedded(vectors=(vector,), token_counts=(None,), truncated=(False,))

    def count_tokens(self, text: str, timeout_s: float) -> int | None:
        self.count_calls.append(text)
        return self.count_tokens_result


@dataclass
class _Job:
    recipe_id: UUID
    due_at: datetime
    attempts: int = 0
    last_wait_s: float | None = None
    claimed_until: datetime | None = None
    last_failure: str | None = None
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeEmbeddingJobs:
    """Jobs in a dict. `now` can be moved forward to make waiting jobs due."""

    def __init__(self, recipes: FakeRecipeEmbeddings | None = None) -> None:
        self.jobs: dict[UUID, _Job] = {}
        self.now = datetime.now(UTC)
        self.recipes = recipes
        self.enqueued: list[UUID] = []
        self.enqueued_notebooks: list[UUID] = []

    def enqueue(self, recipe_ids: Sequence[UUID]) -> None:
        for recipe_id in recipe_ids:
            self.enqueued.append(recipe_id)
            current = self.jobs.get(recipe_id)
            enqueued_at = current.enqueued_at if current else self.now
            self.jobs[recipe_id] = _Job(recipe_id, due_at=self.now, enqueued_at=enqueued_at)

    def enqueue_notebook(self, notebook_id: UUID) -> None:
        self.enqueued_notebooks.append(notebook_id)
        if self.recipes is not None:
            self.enqueue(
                [r.id for r in self.recipes.details.values() if r.notebook_id == notebook_id]
            )

    def enqueue_missing(self, model: str, *, other_strategy_of: str | None = None) -> int:
        if self.recipes is None:
            return 0
        queued = 0
        for recipe in self.recipes.details.values():
            row = self.recipes.rows.get((recipe.id, model))
            current = row is not None and row.version == recipe.updated_at
            if current and other_strategy_of is not None:
                current = row.strategy == other_strategy_of  # type: ignore[union-attr]
            if current:
                continue
            waiting = self.jobs.get(recipe.id)
            if waiting is None:
                self.jobs[recipe.id] = _Job(recipe.id, due_at=self.now, enqueued_at=self.now)
                queued += 1
            elif waiting.due_at > self.now:
                waiting.due_at = self.now
        return queued

    def claim(self, batch: int, lease_s: float) -> list[ClaimedJob]:
        due = sorted(
            (
                job
                for job in self.jobs.values()
                if job.due_at <= self.now
                and (job.claimed_until is None or job.claimed_until < self.now)
            ),
            key=lambda job: job.due_at,
        )[:batch]
        for job in due:
            job.claimed_until = self.now + timedelta(seconds=lease_s)
        return [ClaimedJob(job.recipe_id, job.attempts, job.last_wait_s) for job in due]

    def fail(self, recipe_id: UUID, wait_s: float, failure: str) -> None:
        job = self.jobs.get(recipe_id)
        if job is None or job.claimed_until is None:
            return
        job.attempts += 1
        job.last_wait_s = wait_s
        job.last_failure = failure
        job.claimed_until = None
        job.due_at = self.now + timedelta(seconds=wait_s)

    def release_changed(self, recipe_id: UUID) -> None:
        job = self.jobs.get(recipe_id)
        if job is not None:
            job.claimed_until = None
            job.due_at = self.now

    def complete(self, recipe_id: UUID) -> None:
        job = self.jobs.get(recipe_id)
        if job is not None and job.claimed_until is not None:
            del self.jobs[recipe_id]

    def backlog(self) -> Backlog:
        if not self.jobs:
            return Backlog(count=0, oldest_enqueued_at=None)
        return Backlog(
            count=len(self.jobs),
            oldest_enqueued_at=min(job.enqueued_at for job in self.jobs.values()),
        )

    def failure_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for job in self.jobs.values():
            if job.last_failure:
                counts[job.last_failure] = counts.get(job.last_failure, 0) + 1
        return counts


@dataclass
class _Row:
    vector: tuple[float, ...]
    version: datetime
    strategy: str
    tokens: int | None
    truncated: bool


class FakeRecipeEmbeddings:
    """Recipe details and their embeddings, keyed by (recipe id, model)."""

    def __init__(self) -> None:
        self.details: dict[UUID, RecipeDetail] = {}
        self.rows: dict[tuple[UUID, str], _Row] = {}
        self.ingredients: dict[UUID, set[str]] = {}
        self.authors: dict[UUID, UUID | None] = {}
        self.jobs: FakeEmbeddingJobs | None = None
        # Called between content_for and write_if_current, to simulate a concurrent edit.
        self.before_write = None

    def add(self, detail: RecipeDetail, *, author_id: UUID | None = None) -> RecipeDetail:
        self.details[detail.id] = detail
        self.ingredients[detail.id] = {line.name for line in detail.lines}
        self.authors[detail.id] = author_id
        return detail

    def edit(self, recipe_id: UUID, **changes) -> RecipeDetail:  # noqa: ANN003
        detail = self.details[recipe_id]
        edited = replace(detail, updated_at=detail.updated_at + timedelta(seconds=1), **changes)
        self.details[recipe_id] = edited
        return edited

    def delete(self, recipe_id: UUID) -> None:
        self.details.pop(recipe_id, None)
        for key in [key for key in self.rows if key[0] == recipe_id]:
            del self.rows[key]
        if self.jobs is not None:
            self.jobs.jobs.pop(recipe_id, None)

    def content_for(self, recipe_ids: Sequence[UUID]) -> list[RecipeDetail]:
        found = [self.details[rid] for rid in recipe_ids if rid in self.details]
        if self.before_write is not None:
            hook, self.before_write = self.before_write, None
            hook()
        return found

    def write_if_current(
        self,
        recipe_id: UUID,
        read_version: datetime,
        model: str,
        vector: Sequence[float],
        strategy: str,
        tokens: int | None,
        truncated: bool = False,
    ) -> bool:
        detail = self.details.get(recipe_id)
        if detail is None or detail.updated_at != read_version:
            return False
        self.rows[(recipe_id, model)] = _Row(
            tuple(vector), read_version, strategy, tokens, truncated
        )
        if self.jobs is not None:
            self.jobs.complete(recipe_id)
        return True

    def search(
        self,
        notebook_ids: Sequence[UUID],
        filters: SearchFilters,
        model: str,
        query_vector: Sequence[float],
        limit: int,
    ) -> list[RawHit]:
        hits: list[RawHit] = []
        for detail in self.details.values():
            row = self.rows.get((detail.id, model))
            if row is None or row.version != detail.updated_at:
                continue
            if detail.notebook_id not in notebook_ids or detail.id in filters.exclude_recipe_ids:
                continue
            if filters.author_id is not None and self.authors.get(detail.id) != filters.author_id:
                continue
            if not set(filters.ingredient_names) <= self.ingredients.get(detail.id, set()):
                continue
            hits.append(
                RawHit(
                    detail.id, detail.notebook_id, detail.title, cosine(row.vector, query_vector)
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]


class FakeSearchRecords:
    def __init__(self) -> None:
        self.events: dict[UUID, tuple[SearchEventRecord, tuple[RecordedHit, ...]]] = {}
        self.used: dict[tuple[UUID, UUID], datetime] = {}

    def record(self, event: SearchEventRecord, hits: Sequence[RecordedHit]) -> UUID:
        search_id = uuid4()
        self.events[search_id] = (event, tuple(hits))
        return search_id

    def mark_used(self, search_id: UUID, recipe_id: UUID) -> bool:
        stored = self.events.get(search_id)
        if stored is None or recipe_id not in {hit.recipe_id for hit in stored[1]}:
            return False
        self.used.setdefault((search_id, recipe_id), datetime.now(UTC))
        return True

    def delete_older_than(self, cutoff: datetime) -> int:
        return 0

    def score_bands(self, width: float) -> list[Band]:
        return []
