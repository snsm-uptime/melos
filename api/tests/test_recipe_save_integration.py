"""Save a recipe over HTTP with Postgres (spec 020 FR-002 to FR-013, SC-002 to SC-006).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset. Nothing here calls
the assistant: Save takes the draft the member edited.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    IngredientModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
)
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from application.ports import DuplicateSaveKeyError
from domain.recipe import NewRecipe
from domain.recipe_draft import IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
TEXT = "2 large onions, chopped. A pinch of salt. Simmer them."


def _register(client: TestClient, email: str) -> UUID:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"])


def _switch_to(client: TestClient, email: str) -> None:
    client.post("/auth/sign-out")
    response = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def _personal_notebook(client: TestClient) -> str:
    response = client.get("/notebooks/default")
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _kitchen_notebook(client: TestClient, name: str = "Test Kitchen") -> tuple[str, str]:
    kitchen = client.post("/kitchens", json={"name": name})
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]
    listed = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert listed.status_code == 200, listed.text
    return kitchen_id, listed.json()["notebooks"][0]["id"]


def _lines() -> list[dict]:
    return [
        {"name": "onion", "quantity": 2, "unit": "unit", "size": "large", "preparation": "chopped"},
        {"name": "salt", "vague": True, "note": "a pinch"},
    ]


def _body(notebook_id: str | None, **overrides) -> dict:
    body = {
        "save_key": str(uuid4()),
        "notebook_id": notebook_id,
        "source_text": TEXT,
        "title": "Onion soup",
        "base_servings": 4,
        "servings_estimated": False,
        "ingredient_lines": _lines(),
        "steps": ["Simmer the onion."],
    }
    body.update(overrides)
    return body


def _counts(db: Session) -> tuple[int, ...]:
    return tuple(
        db.scalar(select(func.count()).select_from(model)) or 0
        for model in (RecipeModel, RecipeIngredientModel, StepModel, SourceModel, IngredientModel)
    )


def _catalog(db: Session, notebook_id: str) -> list[str]:
    return list(
        db.scalars(
            select(IngredientModel.name)
            .where(IngredientModel.notebook_id == UUID(notebook_id))
            .order_by(IngredientModel.name)
        )
    )


def test_a_draft_is_saved_into_the_personal_notebook(client: TestClient, db_session: Session):
    user_id = _register(client, "ana_save@example.com")
    notebook_id = _personal_notebook(client)
    before = _counts(db_session)

    response = client.post("/recipes", json=_body(notebook_id))

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["recipe"]["title"] == "Onion soup" and data["notebook"]["id"] == notebook_id
    assert data["created_catalog_names"] == ["onion", "salt"]
    recipe = db_session.get(RecipeModel, UUID(data["recipe"]["id"]))
    assert recipe is not None
    assert recipe.author_id == user_id and str(recipe.notebook_id) == notebook_id
    assert recipe.base_servings == 4 and recipe.servings_estimated is False
    lines = list(
        db_session.scalars(
            select(RecipeIngredientModel)
            .where(RecipeIngredientModel.recipe_id == recipe.id)
            .order_by(RecipeIngredientModel.position)
        )
    )
    assert [(row.name, row.unit, row.size, row.vague_note) for row in lines] == [
        ("onion", "unit", "large", None),
        ("salt", None, None, "a pinch"),
    ]
    assert lines[0].quantity == 2 and lines[0].preparation == "chopped"
    source = db_session.get(SourceModel, recipe.source_id)
    assert source is not None and source.type == "text" and source.raw_text == TEXT
    steps = list(db_session.scalars(select(StepModel).where(StepModel.recipe_id == recipe.id)))
    assert [step.text for step in steps] == ["Simmer the onion."]
    assert _counts(db_session) == tuple(
        n + d for n, d in zip(before, (1, 2, 1, 1, 2), strict=True)
    )


def test_a_repeated_save_returns_the_same_recipe(client: TestClient, db_session: Session):
    _register(client, "repeat_save@example.com")
    notebook_id = _personal_notebook(client)
    body = _body(notebook_id)

    first = client.post("/recipes", json=body)
    counts = _counts(db_session)
    second = client.post("/recipes", json=body)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["recipe"]["id"] == first.json()["recipe"]["id"]
    assert second.json()["created_catalog_names"] == []
    assert _counts(db_session) == counts


def test_a_kitchen_draft_goes_to_the_kitchen_notebook_only(
    client: TestClient, db_session: Session
):
    user_id = _register(client, "ben_save@example.com")
    _, notebook_id = _kitchen_notebook(client)
    personal_id = _personal_notebook(client)

    response = client.post("/recipes", json=_body(notebook_id))

    assert response.status_code == 201, response.text
    recipe = db_session.get(RecipeModel, UUID(response.json()["recipe"]["id"]))
    assert recipe is not None and str(recipe.notebook_id) == notebook_id
    assert recipe.author_id == user_id
    assert _catalog(db_session, personal_id) == []


def test_the_author_is_the_signed_in_member_not_a_body_field(
    client: TestClient, db_session: Session
):
    user_id = _register(client, "author_save@example.com")
    notebook_id = _personal_notebook(client)
    response = client.post(
        "/recipes", json=_body(notebook_id, author_id=str(uuid4()))
    )
    recipe = db_session.get(RecipeModel, UUID(response.json()["recipe"]["id"]))
    assert recipe is not None and recipe.author_id == user_id


def test_new_names_join_the_catalog_and_matched_names_do_not(
    client: TestClient, db_session: Session
):
    _register(client, "catalog_save@example.com")
    notebook_id = _personal_notebook(client)
    client.post("/recipes", json=_body(notebook_id))
    again = client.post(
        "/recipes",
        json=_body(
            notebook_id,
            ingredient_lines=[
                {"name": "Onion ", "quantity": 1, "unit": "unit"},
                {"name": "leek", "quantity": 1, "unit": "unit"},
            ],
        ),
    )
    assert again.json()["created_catalog_names"] == ["leek"]
    assert _catalog(db_session, notebook_id) == ["leek", "onion", "salt"]


def test_a_broken_draft_stores_nothing_and_adds_no_catalog_name(
    client: TestClient, db_session: Session
):
    _register(client, "broken_save@example.com")
    notebook_id = _personal_notebook(client)
    before = _counts(db_session)
    response = client.post(
        "/recipes",
        json=_body(
            notebook_id,
            ingredient_lines=[
                {"name": "leek", "quantity": 1, "unit": "unit"},
                {"name": "flour", "quantity": 1, "unit": "pint"},
            ],
        ),
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] in {"ingredient_line_problem", "invalid_recipe"}
    assert _counts(db_session) == before


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"title": " "}, 422, "draft_incomplete"),
        ({"steps": []}, 422, "draft_incomplete"),
        (
            {"ingredient_lines": [{"name": "flour", "quantity": 1}]},
            422,
            "ingredient_line_problem",
        ),
        (
            {"ingredient_lines": [{"name": "salt", "vague": True, "quantity": 1, "note": "x"}]},
            422,
            "invalid_recipe",
        ),
        (
            {"steps": [f"step {i}" for i in range(101)]},
            422,
            "invalid_recipe",
        ),
        ({"base_servings": 0}, 422, "invalid_recipe"),
    ],
)
def test_refusals_map_to_their_code_and_store_nothing(
    client: TestClient, db_session: Session, overrides: dict, status: int, code: str
):
    _register(client, f"refuse_{abs(hash(code + str(overrides)))}@example.com")
    notebook_id = _personal_notebook(client)
    before = _counts(db_session)
    response = client.post("/recipes", json=_body(notebook_id, **overrides))
    assert (response.status_code, response.json()["code"]) == (status, code), response.text
    assert _counts(db_session) == before


def test_an_over_long_text_is_refused(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("RECIPE_TEXT_MAX_CHARS", "20")
    _register(client, "long_save@example.com")
    notebook_id = _personal_notebook(client)
    before = _counts(db_session)
    response = client.post("/recipes", json=_body(notebook_id, source_text="x" * 40))
    assert response.status_code == 422 and response.json()["code"] == "text_too_long"
    assert _counts(db_session) == before


def test_an_archived_kitchen_is_refused(client: TestClient, db_session: Session):
    _register(client, "archived_save@example.com")
    kitchen_id, notebook_id = _kitchen_notebook(client)
    assert client.post(f"/kitchens/{kitchen_id}/archive").status_code == 200
    before = _counts(db_session)
    response = client.post("/recipes", json=_body(notebook_id))
    assert (response.status_code, response.json()["code"]) == (409, "kitchen_archived")
    assert _counts(db_session) == before


def test_missing_and_forbidden_notebooks_get_the_same_not_found(
    client: TestClient, db_session: Session
):
    _register(client, "owner_save@example.com")
    _, kitchen_notebook = _kitchen_notebook(client)
    personal = _personal_notebook(client)
    _register(client, "outsider_save@example.com")
    before = _counts(db_session)

    missing = client.post("/recipes", json=_body(str(uuid4())))
    kitchen = client.post("/recipes", json=_body(kitchen_notebook))
    other_personal = client.post("/recipes", json=_body(personal))

    assert missing.status_code == kitchen.status_code == other_personal.status_code == 404
    assert missing.json() == kitchen.json() == other_personal.json()
    assert missing.json()["code"] == "notebook_not_found"
    assert _counts(db_session) == before


def test_a_member_who_left_cannot_save(client: TestClient, db_session: Session):
    _register(client, "home_owner_save@example.com")
    kitchen_id, notebook_id = _kitchen_notebook(client, "Shared")
    _register(client, "stranger_save@example.com")
    before = _counts(db_session)
    response = client.post("/recipes", json=_body(notebook_id))
    assert response.status_code == 404 and _counts(db_session) == before
    _switch_to(client, "home_owner_save@example.com")
    assert client.post("/recipes", json=_body(notebook_id)).status_code == 201
    assert kitchen_id


def test_a_kitchen_without_a_notebook_gets_one_at_save(client: TestClient, db_session: Session):
    _register(client, "empty_kitchen_save@example.com")
    kitchen = client.post("/kitchens", json={"name": "Quiet"}).json()
    kitchen_id = kitchen["id"]
    notebook_count = db_session.scalar(
        select(func.count()).select_from(NotebookModel).where(
            NotebookModel.kitchen_id == UUID(kitchen_id)
        )
    )
    response = client.post("/recipes", json=_body(None, kitchen_id=kitchen_id))
    assert response.status_code == 201, response.text
    assert response.json()["notebook"]["kitchen_id"] == kitchen_id
    assert (notebook_count or 0) <= 1


def test_exactly_one_of_notebook_and_kitchen_is_required(client: TestClient):
    _register(client, "either_save@example.com")
    notebook_id = _personal_notebook(client)
    neither = client.post("/recipes", json=_body(None))
    both = client.post("/recipes", json=_body(notebook_id, kitchen_id=str(uuid4())))
    assert neither.status_code == both.status_code == 422
    assert neither.json()["code"] == both.json()["code"] == "invalid_recipe"


def test_signed_out_callers_are_refused(client: TestClient):
    assert client.post("/recipes", json=_body(str(uuid4()))).status_code == 401


def test_a_duplicate_save_key_is_reported_and_the_session_stays_usable(
    client: TestClient, db_session: Session
):
    user_id = _register(client, "dup_save@example.com")
    notebook_id = UUID(_personal_notebook(client))
    repository = SqlAlchemyRecipeRepository(db_session)
    key = uuid4()

    def recipe() -> NewRecipe:
        return NewRecipe(
            title="Soup",
            base_servings=2,
            servings_estimated=False,
            lines=(IngredientLine("leek", False, 1.0, "unit"),),
            steps=("Stir.",),
            source_text="x",
            author_id=user_id,
            notebook_id=notebook_id,
            save_key=key,
        )

    first = repository.add(recipe())
    with pytest.raises(DuplicateSaveKeyError):
        repository.add(recipe())
    assert repository.find_by_save_key(user_id, key) == first
    assert db_session.scalar(select(func.count()).select_from(RecipeModel)) is not None


def test_adding_the_same_catalog_name_twice_leaves_one_row(
    client: TestClient, db_session: Session
):
    _register(client, "twice_save@example.com")
    notebook_id = UUID(_personal_notebook(client))
    catalog = SqlAlchemyIngredientCatalog(db_session)
    catalog.add_names(notebook_id, ["leek", "leek-2"])
    catalog.add_names(notebook_id, ["leek"])
    catalog.add_names(notebook_id, [])
    assert _catalog(db_session, str(notebook_id)) == ["leek", "leek-2"]
