"""Translation job against Postgres (spec 073, T018 and T025). Requires DATABASE_URL.

The job's adapters commit on their own sessions, so these tests commit too. Every ingredient name
carries a unique suffix, and every row a test creates is deleted afterwards, so the shared test
database is left as it was.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.job_lock import JobLock
from adapters.persistence.job_runs import SqlAlchemyJobRunLog
from adapters.persistence.models import (
    JobRunModel,
    RecipeModel,
    StandardIngredientModel,
    StandardIngredientNameModel,
)
from adapters.persistence.standard_ingredients import SqlAlchemyStandardCatalog
from application.translate_ingredients import TranslateIngredients
from domain.ingredient_translation import IngredientTranslationResult, TranslationUnavailable
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import Session, sessionmaker
from tests.catalog_translation_fakes import FakeIngredientTranslator
from tests.embedding_db import personal_notebook, recipe, user
from tests.integration_db import database_url
from tests.translate_job_fakes import EmitLog

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


@pytest.fixture(scope="module")
def engine():  # noqa: ANN201
    from alembic import command
    from alembic.config import Config

    url = database_url()
    assert url is not None
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    eng = create_engine(url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture
def factory(engine) -> Iterator[sessionmaker[Session]]:  # noqa: ANN001
    session_factory = sessionmaker(bind=engine, autoflush=False)
    yield session_factory
    # Every name these tests invent starts with "zz-", so the cleanup touches nothing else.
    with session_factory.begin() as db:
        db.execute(
            delete(StandardIngredientModel).where(
                StandardIngredientModel.normalized_name.like("zz-%")
            )
        )
        db.execute(delete(RecipeModel).where(RecipeModel.title.like("Recipe zz-%")))
        db.execute(delete(JobRunModel))


def _suffix() -> str:
    return uuid4().hex[:10]


def _job(
    factory: sessionmaker[Session],
    engine,  # noqa: ANN001
    translator: FakeIngredientTranslator,
    batch_size: int = 50,
) -> TranslateIngredients:
    return TranslateIngredients(
        catalog=SqlAlchemyStandardCatalog(factory),
        runs=SqlAlchemyJobRunLog(factory),
        lock=JobLock(engine),
        translator=translator,
        model="fake-translate",
        batch_size=batch_size,
        clock=lambda: datetime.now(UTC),
        emit=EmitLog(),
    )


def _seed_recipe(
    factory: sessionmaker[Session],
    created_recipes: list[UUID],
    ingredients: list[str],
    language: str,
    updated_at: datetime | None = None,
) -> UUID:
    with factory.begin() as db:
        author = user(db, f"author{_suffix()}")
        notebook = personal_notebook(db, author)
        recipe_id = recipe(db, notebook, f"Recipe zz-{_suffix()}", ingredients, author_id=author)
        db.execute(update(RecipeModel).where(RecipeModel.id == recipe_id).values(language=language))
        if updated_at is not None:
            db.execute(
                update(RecipeModel).where(RecipeModel.id == recipe_id).values(updated_at=updated_at)
            )
    created_recipes.append(recipe_id)
    return recipe_id


def _run_rows(factory: sessionmaker[Session]) -> list[JobRunModel]:
    with factory() as db:
        return list(db.execute(select(JobRunModel).order_by(JobRunModel.started_at)).scalars())


def test_first_run_discovers_a_new_ingredient_and_a_repeat_creates_none(
    factory: sessionmaker[Session], engine
) -> None:
    created: list[UUID] = []
    name = f"zz-onion-{_suffix()}"
    _seed_recipe(factory, created, [name], "en")
    translator = FakeIngredientTranslator()
    first = _job(factory, engine, translator).run()
    second = _job(factory, engine, translator).run()
    assert first.status == "succeeded"
    assert second.status == "succeeded"
    with factory() as db:
        rows = db.execute(
            select(StandardIngredientModel).where(
                StandardIngredientModel.normalized_name == name.lower()
            )
        ).scalars()
        assert len(list(rows)) == 1


def test_a_failed_run_does_not_move_the_watermark(factory: sessionmaker[Session], engine) -> None:
    created: list[UUID] = []
    _seed_recipe(factory, created, [f"zz-fail-{_suffix()}"], "en")

    class BrokenCatalog(SqlAlchemyStandardCatalog):
        def add_discovered(self, candidates):  # type: ignore[override]
            raise RuntimeError("database write failed")

    job = TranslateIngredients(
        catalog=BrokenCatalog(factory),
        runs=SqlAlchemyJobRunLog(factory),
        lock=JobLock(engine),
        translator=FakeIngredientTranslator(),
        model="fake-translate",
        batch_size=50,
        clock=lambda: datetime.now(UTC),
        emit=EmitLog(),
    )
    assert job.run().status == "failed"
    assert SqlAlchemyJobRunLog(factory).last_succeeded_start() is None


def test_a_recipe_edited_during_a_run_is_picked_up_by_the_next_run(
    factory: sessionmaker[Session], engine
) -> None:
    created: list[UUID] = []
    _job(factory, engine, FakeIngredientTranslator()).run()
    first_run = _run_rows(factory)[-1]
    late = first_run.started_at + timedelta(seconds=5)
    name = f"zz-late-{_suffix()}"
    _seed_recipe(factory, created, [name], "en", updated_at=late)
    summary = _job(factory, engine, FakeIngredientTranslator()).run()
    assert summary.found >= 1
    with factory() as db:
        found = db.execute(
            select(StandardIngredientModel.id).where(
                StandardIngredientModel.normalized_name == name.lower()
            )
        ).first()
    assert found is not None


def test_one_ingredient_in_two_notebooks_makes_one_call(
    factory: sessionmaker[Session], engine
) -> None:
    created: list[UUID] = []
    name = f"zz-shared-{_suffix()}"
    _seed_recipe(factory, created, [name], "en")
    _seed_recipe(factory, created, [name.upper()], "en")
    translator = FakeIngredientTranslator(
        results={name: IngredientTranslationResult(True, "compartido")}
    )
    _job(factory, engine, translator).run()
    _job(factory, engine, translator).run()
    assert sum(1 for c in translator.calls if c.name == name) == 1


def test_batch_size_caps_the_calls_per_run(factory: sessionmaker[Session], engine) -> None:
    created: list[UUID] = []
    names = [f"zz-batch-{_suffix()}-{i}" for i in range(3)]
    _seed_recipe(factory, created, names, "en")
    translator = FakeIngredientTranslator()
    _job(factory, engine, translator, batch_size=2).run()
    assert len(translator.calls) == 2


def test_one_failing_item_does_not_stop_the_others(factory: sessionmaker[Session], engine) -> None:
    created: list[UUID] = []
    bad, good = f"zz-bad-{_suffix()}", f"zz-good-{_suffix()}"
    _seed_recipe(factory, created, [bad, good], "en")
    translator = FakeIngredientTranslator(
        results={good: IngredientTranslationResult(True, "bueno")},
        failures={bad: TranslationUnavailable},
    )
    summary = _job(factory, engine, translator).run()
    assert summary.failed >= 1
    assert summary.translated >= 1
    with factory() as db:
        good_row = db.execute(
            select(StandardIngredientModel).where(
                StandardIngredientModel.normalized_name == good.lower()
            )
        ).scalar_one()
        bad_row = db.execute(
            select(StandardIngredientModel).where(
                StandardIngredientModel.normalized_name == bad.lower()
            )
        ).scalar_one()
        assert good_row.ai_checked_at is not None
        assert bad_row.ai_checked_at is None


def test_the_ai_name_and_its_check_marker_are_saved_together(
    factory: sessionmaker[Session], engine
) -> None:
    created: list[UUID] = []
    name = f"zz-pair-{_suffix()}"
    _seed_recipe(factory, created, [name], "en")
    translator = FakeIngredientTranslator(results={name: IngredientTranslationResult(True, "par")})
    _job(factory, engine, translator).run()
    with factory() as db:
        ai = db.execute(
            select(StandardIngredientNameModel)
            .join(
                StandardIngredientModel,
                StandardIngredientModel.id == StandardIngredientNameModel.standard_ingredient_id,
            )
            .where(
                StandardIngredientModel.normalized_name == name.lower(),
                StandardIngredientNameModel.source == "ai",
            )
        ).scalar_one()
        assert (ai.name, ai.language, ai.model) == ("par", "es", "fake-translate")


def test_plural_and_singular_in_two_notebooks_make_one_standard_ingredient(
    factory: sessionmaker[Session], engine
) -> None:
    created: list[UUID] = []
    tag = _suffix()
    _seed_recipe(factory, created, [f"zz-{tag}-tomatoes"], "en")
    _seed_recipe(factory, created, [f"zz-{tag}-tomato"], "en")
    summary = _job(factory, engine, FakeIngredientTranslator()).run()
    assert summary.status == "succeeded"
    with factory() as db:
        rows = db.execute(
            select(StandardIngredientModel).where(
                StandardIngredientModel.normalized_name == f"zz-{tag}-tomato"
            )
        ).scalars()
        assert len(list(rows)) == 1
