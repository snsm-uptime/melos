"""Embedding jobs and embeddings against Postgres (spec 019 US1, US5, research R4, R5, R7).

Requires DATABASE_URL. Most tests run inside the fixture's transaction. The SKIP LOCKED test
needs two real connections, so it commits rows of its own and deletes them at the end.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.embeddings import SqlAlchemyEmbeddingJobs, SqlAlchemyRecipeEmbeddings
from adapters.persistence.models import KitchenModel, NotebookModel, RecipeEmbeddingModel
from adapters.persistence.notebooks import SqlAlchemyTransactionCommitter
from application.embedding_worker import EmbedPendingRecipes, strategy_named
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests import embedding_db as build
from tests.embedding_fakes import FakeEmbedder
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

MODEL = build.MODEL


def _jobs(db: Session) -> SqlAlchemyEmbeddingJobs:
    return SqlAlchemyEmbeddingJobs(db)


def _count(db: Session, table: str, recipe_id: UUID) -> int:
    return db.scalar(text(f"SELECT count(*) FROM {table} WHERE recipe_id = :id"), {"id": recipe_id})


@pytest.fixture
def notebook(db_session: Session) -> UUID:
    return build.personal_notebook(db_session, build.user(db_session, "ana"))


# --- enqueue ------------------------------------------------------------------------------------


def test_enqueue_is_an_upsert_that_resets_the_retry_state(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "tomato rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe, recipe])
    db_session.execute(
        text(
            "UPDATE embedding_job SET attempts = 4, last_wait_s = 135,"
            " last_failure = 'Unavailable', due_at = now() + interval '1 hour',"
            " claimed_until = now() WHERE recipe_id = :id"
        ),
        {"id": recipe},
    )

    jobs.enqueue([recipe])

    row = build.job(db_session, recipe)
    assert row.attempts == 0 and row.last_wait_s is None and row.last_failure is None
    assert row.claimed_until is None
    assert db_session.scalar(text("SELECT :due <= now()"), {"due": row.due_at})
    assert _count(db_session, "embedding_job", recipe) == 1


def test_enqueue_notebook_queues_every_recipe_of_it(db_session: Session, notebook) -> None:
    first = build.recipe(db_session, notebook, "a")
    second = build.recipe(db_session, notebook, "b")
    elsewhere = build.personal_notebook(db_session, build.user(db_session, "ben"))
    other = build.recipe(db_session, elsewhere, "c")

    _jobs(db_session).enqueue_notebook(notebook)

    assert build.job(db_session, first) and build.job(db_session, second)
    assert build.job(db_session, other) is None


def test_enqueue_missing_queues_only_recipes_without_a_current_embedding(
    db_session: Session, notebook
) -> None:
    embedded = build.recipe(db_session, notebook, "embedded")
    stale = build.recipe(db_session, notebook, "stale")
    missing = build.recipe(db_session, notebook, "missing")
    other_model = build.recipe(db_session, notebook, "other model")
    assert build.embed(db_session, embedded)
    assert build.embed(db_session, stale)
    build.bump(db_session, stale)
    assert build.embed(db_session, other_model, model="older-model")
    jobs = _jobs(db_session)

    first = jobs.enqueue_missing(MODEL)
    second = jobs.enqueue_missing(MODEL)

    assert first >= 3 and second == 0
    assert build.job(db_session, embedded) is None
    for recipe in (stale, missing, other_model):
        assert build.job(db_session, recipe) is not None


def test_enqueue_missing_makes_waiting_jobs_due_now_and_keeps_their_retry_state(
    db_session: Session, notebook
) -> None:
    recipe = build.recipe(db_session, notebook, "queued")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    db_session.execute(
        text(
            "UPDATE embedding_job SET attempts = 3, last_wait_s = 135,"
            " due_at = now() + interval '2 minutes' WHERE recipe_id = :id"
        ),
        {"id": recipe},
    )
    jobs.enqueue_missing(MODEL)

    counted = jobs.enqueue_missing(MODEL)

    row = build.job(db_session, recipe)
    assert row.attempts == 3 and row.last_wait_s == 135
    assert db_session.scalar(text("SELECT :due <= now()"), {"due": row.due_at})
    assert counted == 0


# --- claim, fail, release -----------------------------------------------------------------------


def test_claim_takes_due_jobs_once_and_a_lapsed_lease_frees_them(
    db_session: Session, notebook
) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])

    claimed = jobs.claim(1, 120)
    assert [job.recipe_id for job in claimed] == [recipe]
    assert recipe not in [job.recipe_id for job in jobs.claim(50, 120)]

    db_session.execute(
        text(
            "UPDATE embedding_job SET claimed_until = now() - interval '1 second' "
            "WHERE recipe_id = :id"
        ),
        {"id": recipe},
    )
    assert recipe in [job.recipe_id for job in jobs.claim(50, 120)]


def test_fail_sets_the_wait_and_keeps_the_job(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])
    jobs.claim(1, 120)

    jobs.fail(recipe, 90.0, "Unavailable")

    row = build.job(db_session, recipe)
    assert row.attempts == 1 and row.last_wait_s == 90.0 and row.last_failure == "Unavailable"
    assert row.claimed_until is None
    assert db_session.scalar(
        text("SELECT :due BETWEEN now() + interval '89 seconds' AND now() + interval '91 seconds'"),
        {"due": row.due_at},
    )
    assert recipe not in [job.recipe_id for job in jobs.claim(50, 120)]
    assert jobs.failure_counts().get("Unavailable", 0) >= 1


def test_a_job_re_enqueued_while_claimed_is_not_failed_or_dropped(
    db_session: Session, notebook
) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])
    jobs.claim(1, 120)
    detail_version = build.version(db_session, recipe)
    build.bump(db_session, recipe)
    jobs.enqueue([recipe])  # the edit

    jobs.fail(recipe, 60.0, "Unavailable")
    assert build.job(db_session, recipe).attempts == 0

    written = SqlAlchemyRecipeEmbeddings(db_session).write_if_current(
        recipe, detail_version, MODEL, [0.1] * build.DIM, "toon", 3
    )
    assert written is False
    assert build.job(db_session, recipe) is not None


def test_backlog_counts_and_finds_the_oldest(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])

    backlog = jobs.backlog()

    assert backlog.count >= 1
    assert backlog.oldest_enqueued_at.year == 2000


def test_two_sessions_claiming_at_once_never_get_the_same_recipe(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    notebook_id = uuid4()
    recipe_ids: list[UUID] = []
    with factory() as setup:
        setup.add(NotebookModel(id=notebook_id, name="skip locked notebook"))
        setup.flush()
        for title in ("first", "second"):
            recipe_ids.append(build.recipe(setup, notebook_id, title))
        SqlAlchemyEmbeddingJobs(setup).enqueue(recipe_ids)
        build.age_jobs(setup, recipe_ids)
        setup.commit()
    try:
        first, second = factory(), factory()
        try:
            got_first = SqlAlchemyEmbeddingJobs(first).claim(1, 120)
            got_second = SqlAlchemyEmbeddingJobs(second).claim(1, 120)
            first.commit()
            second.commit()
        finally:
            first.close()
            second.close()
        mine_first = {job.recipe_id for job in got_first}
        mine_second = {job.recipe_id for job in got_second}
        assert mine_first and mine_second
        assert mine_first.isdisjoint(mine_second)
        assert (mine_first | mine_second) <= set(recipe_ids)
    finally:
        with factory() as cleanup:
            notebook = cleanup.get(NotebookModel, notebook_id)
            if notebook is not None:
                cleanup.delete(notebook)
                cleanup.commit()


# --- write_if_current ---------------------------------------------------------------------------


def test_write_if_current_writes_an_unchanged_recipe_and_ends_its_job(
    db_session: Session, notebook
) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])
    jobs.claim(1, 120)

    assert SqlAlchemyRecipeEmbeddings(db_session).write_if_current(
        recipe, build.version(db_session, recipe), MODEL, [0.5] * build.DIM, "plain", 21, True
    )

    row = build.embedding_row(db_session, recipe)
    assert row.strategy_used == "plain" and row.input_tokens == 21 and row.input_truncated
    assert row.recipe_updated_at == build.version(db_session, recipe)
    assert row.updated_at is not None
    assert build.job(db_session, recipe) is None


def test_write_if_current_writes_nothing_after_an_edit(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    read = build.version(db_session, recipe)
    build.bump(db_session, recipe)

    assert not SqlAlchemyRecipeEmbeddings(db_session).write_if_current(
        recipe, read, MODEL, [0.5] * build.DIM, "toon", 1
    )
    assert build.embedding_row(db_session, recipe) is None


def test_write_if_current_writes_nothing_for_a_deleted_recipe(
    db_session: Session, notebook
) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    read = build.version(db_session, recipe)
    db_session.execute(text("DELETE FROM recipe WHERE id = :id"), {"id": recipe})

    assert not SqlAlchemyRecipeEmbeddings(db_session).write_if_current(
        recipe, read, MODEL, [0.5] * build.DIM, "toon", 1
    )


def test_a_second_write_replaces_the_first(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    assert build.embed(db_session, recipe)
    build.bump(db_session, recipe)
    assert build.embed(db_session, recipe, "new text")

    assert _count(db_session, "recipe_embedding", recipe) == 1
    row = build.embedding_row(db_session, recipe)
    assert row.recipe_updated_at == build.version(db_session, recipe)


# --- cascades (FR-005) --------------------------------------------------------------------------


def _with_search_data(db: Session, notebook_id: UUID) -> UUID:
    recipe = build.recipe(db, notebook_id, "rice")
    assert build.embed(db, recipe)
    _jobs(db).enqueue([recipe])
    search_id = db.scalar(
        text(
            "INSERT INTO search_event (feature, scope_kind, result_count, model, strategy,"
            " min_closeness) VALUES ('test', 'notebook', 1, :m, 'toon', 0.65) RETURNING id"
        ),
        {"m": MODEL},
    )
    db.execute(
        text(
            "INSERT INTO search_result (search_id, recipe_id, rank, score, mark)"
            " VALUES (:s, :r, 1, 0.9, 'close')"
        ),
        {"s": search_id, "r": recipe},
    )
    return recipe


def _gone(db: Session, recipe: UUID) -> bool:
    return all(
        _count(db, table, recipe) == 0
        for table in ("recipe_embedding", "embedding_job", "search_result")
    )


def test_deleting_a_recipe_removes_its_search_data(db_session: Session, notebook) -> None:
    recipe = _with_search_data(db_session, notebook)
    db_session.execute(text("DELETE FROM recipe WHERE id = :id"), {"id": recipe})
    assert _gone(db_session, recipe)


def test_deleting_a_notebook_removes_its_search_data(db_session: Session, notebook) -> None:
    recipe = _with_search_data(db_session, notebook)
    db_session.delete(db_session.get(NotebookModel, notebook))
    db_session.flush()
    assert _gone(db_session, recipe)


def test_deleting_a_kitchen_removes_its_search_data(db_session: Session) -> None:
    owner = build.user(db_session, "carla")
    kitchen_id = build.kitchen(db_session, owner)
    recipe = _with_search_data(db_session, build.kitchen_notebook(db_session, kitchen_id))
    db_session.execute(text("DELETE FROM kitchens WHERE id = :id"), {"id": kitchen_id})
    db_session.flush()
    assert db_session.get(KitchenModel, kitchen_id) is None
    assert _gone(db_session, recipe)


# --- one worker pass end to end -----------------------------------------------------------------


def test_one_worker_pass_embeds_a_queued_recipe(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "tomato rice", ("rice", "tomato"))
    jobs = _jobs(db_session)
    jobs.enqueue([recipe])
    build.age_jobs(db_session, [recipe])
    embedder = FakeEmbedder(dimension=build.DIM, model=MODEL)
    worker = EmbedPendingRecipes(
        jobs,
        SqlAlchemyRecipeEmbeddings(db_session),
        embedder,
        strategy_named("toon"),
        SqlAlchemyTransactionCommitter(db_session),
    )

    assert worker.run_once() == 1

    row = build.embedding_row(db_session, recipe)
    assert row is not None and row.input_tokens == 7 and row.strategy_used == "toon"
    assert build.job(db_session, recipe) is None
    assert "tomato" in embedder.document_calls[0][0][0]


# --- US5: strategies ----------------------------------------------------------------------------


def test_rows_name_model_strategy_tokens_and_time(db_session: Session, notebook) -> None:
    recipe = build.recipe(db_session, notebook, "rice")
    assert build.embed(db_session, recipe, strategy="plain")

    row = build.embedding_row(db_session, recipe)
    assert (row.model, row.strategy_used, row.input_tokens, row.input_truncated) == (
        MODEL,
        "plain",
        12,
        False,
    )
    assert row.updated_at is not None


def test_another_strategy_is_queued_only_when_asked(db_session: Session, notebook) -> None:
    plain = build.recipe(db_session, notebook, "plain one")
    toon = build.recipe(db_session, notebook, "toon one")
    assert build.embed(db_session, plain, strategy="plain")
    assert build.embed(db_session, toon, strategy="toon")
    jobs = _jobs(db_session)
    jobs.enqueue_missing(MODEL)
    assert build.job(db_session, plain) is None and build.job(db_session, toon) is None

    jobs.enqueue_missing(MODEL, other_strategy_of="toon")

    assert build.job(db_session, plain) is not None
    assert build.job(db_session, toon) is None


def test_catch_up_on_many_recipes_leaves_one_current_embedding_each(
    db_session: Session, notebook
) -> None:
    recipes = [build.recipe(db_session, notebook, f"recipe {n}") for n in range(25)]
    jobs = _jobs(db_session)
    jobs.enqueue_missing(MODEL)
    build.age_jobs(db_session, recipes)
    worker = EmbedPendingRecipes(
        jobs,
        SqlAlchemyRecipeEmbeddings(db_session),
        FakeEmbedder(dimension=build.DIM, model=MODEL),
        strategy_named("toon"),
        SqlAlchemyTransactionCommitter(db_session),
        batch_size=5,
    )
    for _ in range(5):
        worker.run_once()

    counts = db_session.execute(
        select(RecipeEmbeddingModel.recipe_id, func.count())
        .where(RecipeEmbeddingModel.recipe_id.in_(recipes), RecipeEmbeddingModel.model == MODEL)
        .group_by(RecipeEmbeddingModel.recipe_id)
    ).all()
    assert len(counts) == 25 and all(count == 1 for _, count in counts)
    jobs.enqueue_missing(MODEL)
    assert all(build.job(db_session, recipe) is None for recipe in recipes)
