"""One pass of the embedding worker, against fakes (spec 019 US1, US3)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from application import embedding_worker
from application.embedding_worker import EmbedPendingRecipes, strategy_named
from application.ports import RecipeDetail, RecipeLineDetail
from application.recipe_extraction import AIProviderError, LimitReached, Unavailable
from domain.retry import RetryPolicy
from tests.embedding_fakes import FakeEmbedder, FakeEmbeddingJobs, FakeRecipeEmbeddings

SECRET_TITLE = "SECRET-TITLE-TEXT"


class _Committer:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _detail(title: str = "tomato rice", notebook_id: UUID | None = None) -> RecipeDetail:
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    return RecipeDetail(
        id=uuid4(),
        notebook_id=notebook_id or uuid4(),
        title=title,
        base_servings=4,
        servings_estimated=False,
        author_alias="ana",
        lines=(RecipeLineDetail("rice", False, 1.0, "cup", None, None, None),),
        steps=("Cook.",),
        source_type="text",
        source_url=None,
        created_at=now,
        updated_at=now,
    )


class World:
    def __init__(self, embedder: FakeEmbedder | None = None, **kwargs) -> None:  # noqa: ANN003
        self.embeddings = FakeRecipeEmbeddings()
        self.jobs = FakeEmbeddingJobs(self.embeddings)
        self.embeddings.jobs = self.jobs
        self.embedder = embedder or FakeEmbedder()
        self.committer = _Committer()
        self.worker = EmbedPendingRecipes(
            self.jobs,
            self.embeddings,
            self.embedder,
            strategy_named("toon"),
            self.committer,
            **kwargs,
        )

    def add(self, title: str = "tomato rice") -> RecipeDetail:
        detail = self.embeddings.add(_detail(title))
        self.jobs.enqueue([detail.id])
        return detail

    def later(self, seconds: float) -> None:
        self.jobs.now += timedelta(seconds=seconds)


@pytest.fixture(autouse=True)
def _logger_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_worker.logger, "disabled", False)


def test_one_pass_claims_renders_embeds_and_writes() -> None:
    world = World()
    recipe = world.add()

    assert world.worker.run_once() == 1

    row = world.embeddings.rows[(recipe.id, "fake-embed")]
    assert row.version == recipe.updated_at
    assert row.strategy == "toon"
    assert row.tokens == 7
    assert world.jobs.jobs == {}
    texts, titles = world.embedder.document_calls[0]
    assert titles == ("tomato rice",)
    assert texts[0].startswith("title: tomato rice")
    assert world.committer.commits >= 3


def test_nothing_due_does_nothing() -> None:
    world = World()

    assert world.worker.run_once() == 0
    assert world.embedder.calls == 0


def test_a_recipe_changed_between_read_and_write_is_due_again_now() -> None:
    world = World()
    recipe = world.add()
    world.embeddings.before_write = lambda: world.embeddings.edit(recipe.id, title="new title")

    world.worker.run_once()

    assert (recipe.id, "fake-embed") not in world.embeddings.rows
    job = world.jobs.jobs[recipe.id]
    assert job.due_at <= world.jobs.now and job.claimed_until is None and job.attempts == 0

    world.worker.run_once()
    assert world.embeddings.rows[(recipe.id, "fake-embed")].version == (
        world.embeddings.details[recipe.id].updated_at
    )


def test_a_deleted_recipe_is_dropped() -> None:
    world = World()
    recipe = world.add()
    world.embeddings.delete(recipe.id)
    world.jobs.enqueue([recipe.id])  # a stale job the cascade has not removed in the fake
    world.embeddings.details.pop(recipe.id, None)

    assert world.worker.run_once() == 1
    assert world.embedder.calls == 0


def test_a_missing_token_count_is_counted_once() -> None:
    world = World(FakeEmbedder(token_count=None, count_tokens_result=21))
    recipe = world.add()

    world.worker.run_once()

    assert len(world.embedder.count_calls) == 1
    assert world.embeddings.rows[(recipe.id, "fake-embed")].tokens == 21


def test_a_failing_token_count_stores_none() -> None:
    world = World(FakeEmbedder(token_count=None, count_tokens_result=None))
    recipe = world.add()

    world.worker.run_once()

    assert world.embeddings.rows[(recipe.id, "fake-embed")].tokens is None
    assert recipe.id not in world.jobs.jobs


def test_not_configured_does_nothing() -> None:
    embedder = FakeEmbedder()
    embedder.configured = False
    world = World(embedder)
    recipe = world.add()

    assert world.worker.run_once() == 0
    assert world.embedder.calls == 0
    assert world.jobs.jobs[recipe.id].attempts == 0


def test_plain_strategy_is_recorded() -> None:
    world = World()
    world.worker = EmbedPendingRecipes(
        world.jobs, world.embeddings, world.embedder, strategy_named("plain"), world.committer
    )
    recipe = world.add()

    world.worker.run_once()

    assert world.embeddings.rows[(recipe.id, "fake-embed")].strategy == "plain"
    assert world.embedder.document_calls[0][0][0].startswith("tomato rice\nServes 4.")


# --- US3: the growing retry rule ---------------------------------------------------------------


def test_repeated_failures_follow_the_rule_up_to_the_cap() -> None:
    world = World(FakeEmbedder(failure=Unavailable()))
    recipe = world.add()
    waits = []
    for _ in range(14):
        assert world.worker.run_once() == 1
        job = world.jobs.jobs[recipe.id]
        waits.append(job.last_wait_s)
        assert job.due_at == world.jobs.now + timedelta(seconds=job.last_wait_s)
        world.later(job.last_wait_s)

    assert waits[:4] == [60.0, 90.0, 135.0, 202.5]
    assert waits[-1] == 7200.0 and max(waits) == 7200.0
    assert world.jobs.jobs[recipe.id].attempts == 14
    assert world.jobs.jobs[recipe.id].last_failure == "Unavailable"


def test_a_job_is_not_retried_before_its_wait() -> None:
    world = World(FakeEmbedder(failure=Unavailable()))
    world.add()
    world.worker.run_once()
    world.later(59)

    assert world.worker.run_once() == 0


def test_a_longer_service_wait_is_honoured() -> None:
    world = World(FakeEmbedder(failure=LimitReached(retry_after_seconds=300)))
    recipe = world.add()

    world.worker.run_once()

    assert world.jobs.jobs[recipe.id].last_wait_s == 300.0
    assert world.jobs.jobs[recipe.id].last_failure == "LimitReached"


def test_a_custom_policy_is_used() -> None:
    world = World(
        FakeEmbedder(failure=Unavailable()), policy=RetryPolicy(first_s=5, growth=2, cap_s=8)
    )
    recipe = world.add()
    world.worker.run_once()
    world.later(5)
    world.worker.run_once()

    assert world.jobs.jobs[recipe.id].last_wait_s == 8


def test_success_after_failures_resets_the_next_enqueue() -> None:
    embedder = FakeEmbedder(failure=Unavailable())
    world = World(embedder)
    recipe = world.add()
    world.worker.run_once()
    world.later(60)
    world.worker.run_once()
    world.later(90)
    embedder.failure = None

    world.worker.run_once()
    assert recipe.id not in world.jobs.jobs

    world.embeddings.edit(recipe.id, title="edited")
    world.jobs.enqueue([recipe.id])
    embedder.failure = AIProviderError()
    world.worker.run_once()
    assert world.jobs.jobs[recipe.id].attempts == 1
    assert world.jobs.jobs[recipe.id].last_wait_s == 60.0


def test_only_class_names_are_stored_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    world = World(FakeEmbedder(failure=Unavailable()))
    recipe = world.add(SECRET_TITLE)

    world.worker.run_once()
    world.embedder.failure = None
    world.later(60)
    world.worker.run_once()

    assert world.embeddings.rows[(recipe.id, "fake-embed")]
    assert "class=Unavailable" in caplog.text
    assert SECRET_TITLE not in caplog.text
    assert "rice" not in caplog.text
