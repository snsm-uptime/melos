"""`scripts.recipe_languages` against Postgres with a fake detector (spec 043 T040).

Requires DATABASE_URL. Skips when unset. The command commits, so rows are committed and removed.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import NotebookModel, RecipeIngredientModel, RecipeModel
from scripts.recipe_languages import detect, status
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


@dataclass
class FakeLanguageDetector:
    """Answers by the recipe's title, the first line of the text it is sent."""

    answers: dict[str, str | None]
    texts: list[str] = field(default_factory=list)

    def detect(self, text: str) -> str | None:
        self.texts.append(text)
        return self.answers.get(text.split("\n", 1)[0])


@pytest.fixture
def recipes(engine: Engine) -> Iterator[tuple[sessionmaker[Session], dict[str, UUID]]]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    notebook_id = uuid4()
    ids = {"Sopa de ajo": uuid4(), "Garlic soup": uuid4(), "Mixed": uuid4()}
    with factory() as setup:
        setup.add(NotebookModel(id=notebook_id, name="languages notebook"))
        setup.flush()
        for title, recipe_id in ids.items():
            # All stored with the fallback 'es'.
            setup.add(
                RecipeModel(
                    id=recipe_id,
                    notebook_id=notebook_id,
                    title=title,
                    base_servings=2,
                    language="es",
                )
            )
        setup.flush()
        setup.add(
            RecipeIngredientModel(
                recipe_id=ids["Garlic soup"], position=0, name="garlic", quantity=2, unit="unit"
            )
        )
        setup.commit()
    yield factory, ids
    with factory() as cleanup:
        cleanup.execute(delete(NotebookModel).where(NotebookModel.id == notebook_id))
        cleanup.commit()


def _rows(factory: sessionmaker[Session], ids: dict[str, UUID]) -> dict[str, tuple]:
    with factory() as db:
        rows = db.execute(
            select(
                RecipeModel.title,
                RecipeModel.language,
                RecipeModel.proposed_language,
                RecipeModel.language_detected_at.is_not(None),
            ).where(RecipeModel.id.in_(list(ids.values())))
        ).all()
    return {title: (language, proposed, read) for title, language, proposed, read in rows}


def test_a_differing_answer_is_stored_as_a_proposal_only(recipes) -> None:
    factory, ids = recipes
    detector = FakeLanguageDetector({"Sopa de ajo": "es", "Garlic soup": "en", "Mixed": None})

    with factory() as session:
        lines = detect(session, detector, only=list(ids.values()))

    assert lines == ["read=3", "proposed=1", "unsure=1"]
    assert _rows(factory, ids) == {
        "Sopa de ajo": ("es", None, True),  # agrees: nothing to propose
        "Garlic soup": ("es", "en", True),  # the language itself never changes
        "Mixed": ("es", None, True),  # unsure: read, nothing stored
    }
    garlic = next(text for text in detector.texts if text.startswith("Garlic soup"))
    assert "garlic" in garlic


def test_a_second_run_reads_nothing_and_changes_nothing(recipes) -> None:
    factory, ids = recipes
    detector = FakeLanguageDetector({"Garlic soup": "en"})
    with factory() as session:
        detect(session, detector, only=list(ids.values()))
    before = _rows(factory, ids)

    with factory() as session:
        again = detect(
            session, FakeLanguageDetector({"Garlic soup": "es"}), only=list(ids.values())
        )

    assert again == ["read=0", "proposed=0", "unsure=0"]
    assert _rows(factory, ids) == before


def test_a_limit_reads_that_many_and_status_counts(recipes) -> None:
    factory, ids = recipes
    with factory() as session:
        assert detect(session, FakeLanguageDetector({}), 2, only=list(ids.values()))[0] == "read=2"
    with factory() as session:
        lines = status(session)
    assert lines[0].startswith("read=") and lines[1].startswith("waiting=")
