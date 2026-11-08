"""Picture capture over HTTP with Postgres (spec 041 T027, T067, T060; SC-005).

Requires DATABASE_URL (Compose test overlay or CI Postgres 16). Skips when unset. The picture
pipeline is the real one (Pillow on a generated JPEG); the assistant is FakeRecipeExtractor
through a dependency override, so no test calls the model.
"""

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.persistence.models import (
    IngredientModel,
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
)
from api.deps import get_recipe_extraction
from application.recipe_extraction import (
    AIProviderError,
    DraftPart,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    RecipeExtraction,
    Unavailable,
)
from domain.recipe_draft import IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url
from tests.picture_bytes import pil_image_bytes, png_bytes

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
TIERS = {"tier_1", "tier_2", "tier_3"}


def _jpeg_b64() -> str:
    return base64.b64encode(pil_image_bytes("JPEG", size=(240, 180))).decode("ascii")


def _complete() -> DraftPart:
    return DraftPart(
        title="Tomato soup",
        base_servings=4,
        ingredient_lines=(IngredientLine(name="tomato", vague=False, quantity=3.0, unit="unit"),),
        steps=("Blend.",),
    )


@pytest.fixture
def assistant(client: TestClient) -> FakeRecipeExtractor:
    fake = FakeRecipeExtractor(script=_complete())
    use_case = RecipeExtraction(fake)
    client.app.dependency_overrides[get_recipe_extraction] = lambda: use_case
    yield fake
    client.app.dependency_overrides.pop(get_recipe_extraction, None)


def _register(client: TestClient, email: str) -> None:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)


def _notebook(client: TestClient) -> str:
    response = client.get("/notebooks/default")
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _picture(client: TestClient, notebook_id: str, **body):
    return client.post(f"/notebooks/{notebook_id}/captures/picture", json=body)


def _recipe_count(db_session: Session) -> tuple[int, ...]:
    return tuple(
        db_session.scalar(select(func.count()).select_from(model))
        for model in (RecipeModel, SourceModel, RecipeIngredientModel, StepModel, IngredientModel)
    )


def test_a_jpeg_gives_a_draft_with_the_processed_picture_and_no_page_key(
    client: TestClient, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "ana_picture@example.com")
    response = _picture(client, _notebook(client), image_base64=_jpeg_b64())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "draft"
    assert "page" not in body
    assert body["draft"]["title"] == "Tomato soup"
    picture = body["picture"]
    assert picture["tier"] == "tier_3"
    assert picture["sharpness"] is None
    assert picture["original_dimensions"] == [240, 180]
    assert picture["preview_image"].startswith("data:image/webp;base64,")
    assert picture["steps_taken"]


def test_handwritten_absent_means_tier_3_with_no_sharpness(
    client: TestClient, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "ben_picture@example.com")
    body = _picture(client, _notebook(client), image_base64=_jpeg_b64()).json()
    assert body["picture"]["tier"] == "tier_3"
    assert body["picture"]["sharpness"] is None


def test_printed_gives_a_measured_sharpness_and_a_tier(
    client: TestClient, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "cy_picture@example.com")
    body = _picture(client, _notebook(client), image_base64=_jpeg_b64(), handwritten=False).json()
    assert isinstance(body["picture"]["sharpness"], float)
    assert body["picture"]["tier"] in TIERS


def test_a_partial_result_opens_with_blanks_and_estimated_servings(
    client: TestClient, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "dan_picture@example.com")
    assistant.script = DraftPart(
        title=None, base_servings=None, ingredient_lines=(), steps=("Stir.",)
    )
    response = _picture(client, _notebook(client), image_base64=_jpeg_b64())
    assert response.status_code == 200, response.text
    draft = response.json()["draft"]
    assert draft["title"] == ""
    assert draft["steps"] == ["Stir."]
    assert draft["servings_estimated"] is True


def test_a_member_of_another_kitchen_gets_notebook_not_found(
    client: TestClient, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "eva_picture@example.com")
    response = _picture(client, str(uuid4()), image_base64=_jpeg_b64())
    assert response.status_code == 404
    assert response.json()["code"] == "notebook_not_found"


@pytest.mark.parametrize(
    ("image", "code"),
    [
        ("", "picture_empty"),
        (base64.b64encode(b"%PDF-1.7\n" + b"\x00" * 64).decode(), "picture_unsupported"),
        (base64.b64encode(png_bytes(iend=False)).decode(), "picture_unsupported"),
        ("A" * 13_333_337, "picture_too_large"),
    ],
    ids=["empty", "pdf", "damaged-png", "too-long"],
)
def test_a_refused_picture_gets_its_code_and_no_assistant_call(
    client: TestClient, assistant: FakeRecipeExtractor, image: str, code: str
) -> None:
    _register(client, f"fay_{code}@example.com")
    response = _picture(client, _notebook(client), image_base64=image)
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert assistant.picture_calls == []


@pytest.mark.parametrize(
    ("outcome", "status", "code", "detail"),
    [
        (NotARecipe(NotRecipeReason.NOT_FOOD), 422, "not_a_recipe", "not_food"),
        (NotARecipe(NotRecipeReason.STORY_OR_ARTICLE), 422, "not_a_recipe", "story_or_article"),
        (NotARecipe(NotRecipeReason.MULTIPLE_RECIPES), 422, "one_recipe_at_a_time", ""),
        (InvalidOutput(), 422, "ai_invalid_output", ""),
        (Unavailable(), 503, "ai_unavailable", None),
        (LimitReached(30), 429, "ai_limit_reached", None),
        (AIProviderError(), 503, "ai_misconfigured", None),
    ],
    ids=["not_food", "story", "multiple", "invalid", "unavailable", "limit", "provider"],
)
def test_assistant_outcomes_map_to_their_codes(
    client: TestClient,
    assistant: FakeRecipeExtractor,
    outcome: object,
    status: int,
    code: str,
    detail: str | None,
) -> None:
    _register(client, f"gil_{code}_{status}@example.com")
    assistant.script = outcome  # type: ignore[assignment]
    response = _picture(client, _notebook(client), image_base64=_jpeg_b64())
    assert response.status_code == status
    body = response.json()
    assert body["code"] == code
    if detail is not None:
        assert body["detail"] == detail
    if isinstance(outcome, LimitReached):
        assert response.headers["Retry-After"] == "30"


def test_a_capture_writes_nothing_and_the_draft_holds_no_original(
    client: TestClient, assistant: FakeRecipeExtractor, db_session: Session
) -> None:
    _register(client, "hal_picture@example.com")
    before = _recipe_count(db_session)
    image = _jpeg_b64()
    response = _picture(client, _notebook(client), image_base64=image)
    assert response.status_code == 200
    assert _recipe_count(db_session) == before
    assert image not in response.text
