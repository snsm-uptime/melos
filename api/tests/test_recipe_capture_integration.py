"""Recipe capture over HTTP with Postgres (spec 016 FR-022, FR-029, FR-033, SC-003, SC-005, SC-008).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset. The assistant is
replaced by FakeRecipeExtractor through the dependency override, so no test needs the network.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.llm.vocabulary import load_vocabulary
from adapters.persistence.models import IngredientModel, NotebookModel
from api.deps import get_recipe_extraction
from application.recipe_extraction import (
    ONE_RECIPE_REASON,
    AIProviderError,
    Draft,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    RecipeExtraction,
    Unavailable,
)
from domain.recipe_draft import DraftRecipe, IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
TEXT = "2 large onions, chopped. Simmer them."


def _register(client: TestClient, email: str) -> UUID:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"])


def _switch_to(client: TestClient, email: str) -> None:
    client.post("/auth/sign-out")
    response = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def _good_draft(main: tuple[str, ...] = ()) -> DraftRecipe:
    return DraftRecipe(
        title="Onion soup",
        base_servings=4,
        servings_estimated=False,
        main_ingredients=main,
        cuisines=(),
        ingredient_lines=(
            IngredientLine("salt", True, note="a pinch"),
            IngredientLine("onion", False, 2.0, "unit", "large", None, "chopped"),
        ),
        steps=("Simmer the onion.",),
    )


@pytest.fixture
def script(client: TestClient) -> FakeRecipeExtractor:
    """Every capture in the test gets this result from the fake assistant."""
    fake = FakeRecipeExtractor(script=Draft(recipe=_good_draft()))
    use_case = RecipeExtraction(fake, load_vocabulary())
    client.app.dependency_overrides[get_recipe_extraction] = lambda: use_case
    yield fake
    client.app.dependency_overrides.pop(get_recipe_extraction, None)


def _set_result(fake: FakeRecipeExtractor, result) -> None:
    fake.script = result


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


def _row_counts(db_session: Session) -> tuple[int, int]:
    ingredients = db_session.scalar(select(func.count()).select_from(IngredientModel))
    notebooks = db_session.scalar(select(func.count()).select_from(NotebookModel))
    return ingredients, notebooks


def _capture(client: TestClient, notebook_id: str, text: str = TEXT):
    return client.post(f"/notebooks/{notebook_id}/captures/text", json={"text": text})


def test_draft_for_the_personal_notebook_and_no_rows_written(
    client: TestClient, db_session: Session, script: FakeRecipeExtractor
) -> None:
    _register(client, "ana_capture@example.com")
    notebook_id = _personal_notebook(client)
    before = _row_counts(db_session)

    response = _capture(client, notebook_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "draft"
    assert body["notebook"]["kind"] == "personal"
    assert body["draft"]["title"] == "Onion soup"
    assert body["draft"]["ingredient_lines"][0]["vague"] is True
    assert body["draft"]["ingredient_lines"][1]["preparation"] == "chopped"
    assert _row_counts(db_session) == before


def test_draft_for_a_kitchen_notebook_opened_first_by_the_member(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "ben_capture@example.com")
    kitchen_id, notebook_id = _kitchen_notebook(client)

    response = _capture(client, notebook_id)

    assert response.status_code == 200, response.text
    assert response.json()["notebook"]["kind"] == "kitchen"
    assert response.json()["notebook"]["kitchen_id"] == kitchen_id


def test_non_member_and_missing_notebook_get_the_same_not_found(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "owner_capture@example.com")
    _, notebook_id = _kitchen_notebook(client)
    _register(client, "other_capture@example.com")

    other_members = _capture(client, notebook_id)
    missing = _capture(client, "00000000-0000-4000-8000-000000000000")

    assert other_members.status_code == 404
    assert other_members.json() == missing.json()
    assert other_members.json()["code"] == "notebook_not_found"
    assert script.calls == []


def test_another_members_personal_notebook_is_not_found(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "first_capture@example.com")
    first_notebook = _personal_notebook(client)
    _register(client, "second_capture@example.com")

    response = _capture(client, first_notebook)

    assert response.status_code == 404
    assert response.json()["code"] == "notebook_not_found"
    assert script.calls == []


def test_archived_kitchen_is_refused_for_a_member_before_any_assistant_call(
    client: TestClient, db_session: Session, script: FakeRecipeExtractor
) -> None:
    _register(client, "archive_capture@example.com")
    kitchen_id, notebook_id = _kitchen_notebook(client)
    assert client.post(f"/kitchens/{kitchen_id}/archive").status_code == 200

    response = _capture(client, notebook_id)

    assert response.status_code == 409
    assert response.json()["code"] == "kitchen_archived"
    assert script.calls == []


@pytest.mark.parametrize(
    ("result", "status", "code"),
    [
        (NotARecipe(reason="That is a weather question."), 422, "not_a_recipe"),
        (NotARecipe(reason=ONE_RECIPE_REASON), 422, "one_recipe_at_a_time"),
        (InvalidOutput(), 422, "ai_invalid_output"),
        (Unavailable(), 503, "ai_unavailable"),
        (AIProviderError(), 503, "ai_misconfigured"),
    ],
)
def test_refusals_and_failures_map_to_their_code(
    client: TestClient,
    db_session: Session,
    script: FakeRecipeExtractor,
    result,
    status: int,
    code: str,
) -> None:
    _register(client, f"fail_{code}@example.com")
    notebook_id = _personal_notebook(client)
    _set_result(script, result)
    before = _row_counts(db_session)

    response = _capture(client, notebook_id)

    assert response.status_code == status, response.text
    assert response.json()["code"] == code
    assert _row_counts(db_session) == before


def test_not_a_recipe_reason_is_kept_and_limited_to_120_characters(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "reason_capture@example.com")
    notebook_id = _personal_notebook(client)
    _set_result(script, NotARecipe(reason="x" * 200))

    response = _capture(client, notebook_id)

    assert response.status_code == 422
    assert len(response.json()["detail"]) == 120


def test_limit_reached_sets_retry_after_when_hinted(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "limit_capture@example.com")
    notebook_id = _personal_notebook(client)
    _set_result(script, LimitReached(retry_after_seconds=30))

    response = _capture(client, notebook_id)

    assert response.status_code == 429
    assert response.json()["code"] == "ai_limit_reached"
    assert response.headers["Retry-After"] == "30"


def test_empty_and_too_long_text_are_refused_with_no_assistant_call(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "limits_capture@example.com")
    notebook_id = _personal_notebook(client)

    empty = _capture(client, notebook_id, text="   ")
    too_long = _capture(client, notebook_id, text="x" * 5001)

    assert empty.status_code == 422 and empty.json()["code"] == "text_empty"
    assert too_long.status_code == 422 and too_long.json()["code"] == "text_too_long"
    assert too_long.json()["detail"] == "That text is too long. Paste up to 5000 characters."
    assert script.calls == []


def test_chip_labels_follow_the_account_language(
    client: TestClient, script: FakeRecipeExtractor
) -> None:
    _register(client, "lang_capture@example.com")
    assert client.patch("/auth/me", json={"language": "es"}).status_code == 200
    notebook_id = _personal_notebook(client)
    _set_result(script, Draft(recipe=_good_draft(main=("poultry",))))

    response = _capture(client, notebook_id)

    assert response.status_code == 200, response.text
    assert response.json()["language"] == "es"
    assert response.json()["draft"]["main_ingredients"] == [{"id": "poultry", "label": "Aves"}]


def test_vocabulary_lists_the_controlled_values(client: TestClient) -> None:
    _register(client, "vocab_capture@example.com")

    response = client.get("/recipe-vocabulary")

    assert response.status_code == 200
    body = response.json()
    assert body["max_text_chars"] == 5000
    assert body["max_main_ingredients"] == 2 and body["max_cuisines"] == 2
    assert "international" in [c["id"] for c in body["cuisines"]]
    assert {"id": "poultry", "label": {"en": "Poultry", "es": "Aves"}} in body["main_ingredients"]
