"""Ingredient matching over HTTP with Postgres (spec 018 US1, US2, US3, FR-005, FR-006).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset. The assistant is the
fake from test_recipe_capture_integration, so no test needs the network.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.llm.vocabulary import load_vocabulary
from adapters.persistence.models import IngredientModel
from api.deps import get_recipe_extraction
from application.recipe_extraction import Draft, RecipeExtraction
from domain.recipe_draft import DraftRecipe, IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_recipe_capture_integration import _capture, _personal_notebook, _register

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _matching_draft() -> DraftRecipe:
    return DraftRecipe(
        title="Onion soup",
        base_servings=2,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(
            IngredientLine(
                "onion",
                False,
                2.0,
                "unit",
                "large",
                None,
                None,
                text_name="onions",
                catalog_match="onion",
            ),
            IngredientLine(
                "flour",
                False,
                200.0,
                "g",
                None,
                None,
                None,
                text_name="flour",
                catalog_match="flour",
            ),
        ),
        steps=("Fry the onions.",),
    )


@pytest.fixture
def script(client: TestClient) -> FakeRecipeExtractor:
    """The fake assistant returns the matching draft unless a test sets another script."""
    fake = FakeRecipeExtractor(script=Draft(recipe=_matching_draft()))
    use_case = RecipeExtraction(fake, load_vocabulary())
    client.app.dependency_overrides[get_recipe_extraction] = lambda: use_case
    yield fake
    client.app.dependency_overrides.pop(get_recipe_extraction, None)


def _seed_catalog(db_session: Session, notebook_id: str, names: list[str]) -> None:
    for name in names:
        db_session.add(IngredientModel(notebook_id=UUID(notebook_id), name=name))
    db_session.flush()


def test_draft_matches_the_catalog_and_lists_the_change(
    client: TestClient, db_session: Session, script: FakeRecipeExtractor
) -> None:
    _register(client, "matcher_one@example.com")
    notebook_id = _personal_notebook(client)
    _seed_catalog(db_session, notebook_id, ["flour", "onion"])
    script.script = Draft(recipe=_matching_draft())

    response = _capture(client, notebook_id, "Onion soup\n2 large onions\n200 g flour")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["catalog"] == ["flour", "onion"]
    draft = body["draft"]
    onion, flour = draft["ingredient_lines"]
    assert onion["name"] == "onion"
    assert onion["text_name"] == "onions"
    assert onion["match"] == {"kind": "matched", "entry": "onion"}
    assert flour["match"] == {"kind": "matched", "entry": "flour"}
    assert draft["changes"] == [{"line": 0, "from": "onions", "to": "onion"}]


def test_draft_with_an_empty_catalog_is_all_new_with_no_changes(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "matcher_two@example.com")
    notebook_id = _personal_notebook(client)
    script.script = Draft(recipe=_matching_draft())

    response = _capture(client, notebook_id, "Onion soup\n2 large onions\n200 g flour")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["catalog"] == []
    assert [line["match"]["kind"] for line in body["draft"]["ingredient_lines"]] == ["new", "new"]
    assert body["draft"]["changes"] == []


def test_capture_writes_nothing_to_the_catalog(
    client: TestClient, db_session: Session, script: FakeRecipeExtractor
) -> None:
    _register(client, "matcher_three@example.com")
    notebook_id = _personal_notebook(client)
    _seed_catalog(db_session, notebook_id, ["onion"])
    before = db_session.scalars(select(IngredientModel.name)).all()
    script.script = Draft(recipe=_matching_draft())

    _capture(client, notebook_id, "Onion soup\n2 large onions\n200 g flour")

    after = db_session.scalars(select(IngredientModel.name)).all()
    assert sorted(after) == sorted(before)
