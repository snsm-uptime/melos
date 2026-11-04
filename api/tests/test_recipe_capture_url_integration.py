"""Link capture over HTTP with Postgres (spec 026 T032, T056; SC-001, SC-005, SC-009).

Requires DATABASE_URL (Compose test overlay or CI Postgres 16). Skips when unset. The page
fetcher is FakePageFetcher loaded with the invented fixture pages and the assistant is
FakeRecipeExtractor, both through dependency overrides: no test opens a website or the model.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.persistence.models import (
    IngredientModel,
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
)
from adapters.web.fake_page_fetcher import FakePageFetcher
from api.deps import get_page_fetcher, get_recipe_extraction
from application.ports import FetchedImage, FetchedPage, PageFetchFailed
from application.recipe_extraction import (
    AIProviderError,
    Draft,
    DraftPart,
    ExtractionMode,
    InvalidOutput,
    LimitReached,
    NoRecipeContent,
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

PAGES = Path(__file__).parent / "fixtures" / "pages"
PASSWORD = "password1"
BASE = "https://example.test/recipes/"
JPEG = (PAGES / "photo.jpg").read_bytes()


def _page(name: str) -> FetchedPage:
    html = (PAGES / f"{name}.html").read_text(encoding="utf-8")
    return FetchedPage(final_url=f"{BASE}{name}", html=html, byte_count=len(html.encode()))


FIXTURES = (
    "jsonld_recipe",
    "jsonld_no_ingredients",
    "jsonld_two_recipes",
    "plain_recipe",
    "long_blog",
    "no_recipe",
    "script_only",
    "injection",
    "spanish_recipe",
)


def _draft() -> DraftRecipe:
    return DraftRecipe(
        title="Model title",
        base_servings=4,
        servings_estimated=False,
        ingredient_lines=(
            IngredientLine("lentil", False, 1.0, "cup"),
            IngredientLine("onion", False, 2.0, "unit", "large", None, "chopped"),
        ),
        steps=("Model step.",),
    )


@pytest.fixture
def fetcher(client: TestClient) -> FakePageFetcher:
    fake = FakePageFetcher(
        pages={f"{BASE}{name}": _page(name) for name in FIXTURES},
        images={"https://example.test/images/lentil-soup.jpg": FetchedImage("image/jpeg", JPEG)},
    )
    client.app.dependency_overrides[get_page_fetcher] = lambda: fake
    yield fake
    client.app.dependency_overrides.pop(get_page_fetcher, None)


@pytest.fixture
def assistant(client: TestClient) -> FakeRecipeExtractor:
    fake = FakeRecipeExtractor(script=Draft(recipe=_draft()))
    use_case = RecipeExtraction(fake)
    client.app.dependency_overrides[get_recipe_extraction] = lambda: use_case
    yield fake
    client.app.dependency_overrides.pop(get_recipe_extraction, None)


def _register(client: TestClient, email: str) -> UUID:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"])


def _switch_to(client: TestClient, email: str) -> None:
    client.post("/auth/sign-out")
    response = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def _notebook(client: TestClient) -> str:
    response = client.get("/notebooks/default")
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _capture(client: TestClient, notebook_id: str, url: str):
    return client.post(f"/notebooks/{notebook_id}/captures/url", json={"url": url})


def _counts(db_session: Session) -> tuple[int, ...]:
    return tuple(
        db_session.scalar(select(func.count()).select_from(model))
        for model in (RecipeModel, SourceModel, RecipeIngredientModel, StepModel, IngredientModel)
    )


def test_a_schema_org_page_gives_a_draft_with_its_title_steps_and_photo(
    client: TestClient,
    db_session: Session,
    fetcher: FakePageFetcher,
    assistant: FakeRecipeExtractor,
) -> None:
    _register(client, "ana_link@example.com")
    notebook_id = _notebook(client)
    before = _counts(db_session)

    response = _capture(client, notebook_id, f"{BASE}jsonld_recipe")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "draft"
    assert body["draft"]["title"] == "Golden Lentil Soup"
    assert body["draft"]["steps"] == [
        "Rinse the lentils.",
        "Fry the onions in the oil until soft.",
        "Add the lentils and 1 litre of water & simmer for 20 minutes.",
        "Season with salt and serve.",
    ]
    assert body["draft"]["base_servings"] == 4
    assert body["draft"]["servings_estimated"] is False
    assert body["page"]["source_url"] == f"{BASE}jsonld_recipe"
    assert body["page"]["preview_image"].startswith("data:image/jpeg;base64,")
    assert body["page"]["cut"] is False
    assert len(assistant.calls) == 1
    assert _counts(db_session) == before  # SC-005: nothing is stored before Save


def test_a_plain_page_gives_a_draft_from_its_markdown(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "ben_link@example.com")

    response = _capture(client, _notebook(client), f"{BASE}plain_recipe")

    assert response.status_code == 200, response.text
    assert response.json()["page"]["preview_image"] is None
    (call,) = assistant.calls
    assert "- 2 ripe bananas" in call.text
    assert "COMMENTER TEXT" not in call.text


def test_a_long_page_is_read_in_parts_and_merged_without_repeats(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "cy_link@example.com")
    onion = IngredientLine("onion", False, 1.0, "unit", preparation="chopped")
    bean = IngredientLine("bean", False, 500.0, "gram")
    assistant.script = [
        DraftPart("Farmhouse White Bean Stew", 6, (bean, onion), ()),
        NoRecipeContent(),
        NoRecipeContent(),
        DraftPart("Farmhouse White Bean Stew", 6, (bean, onion), ("Soak the beans.", "Simmer.")),
    ]

    response = _capture(client, _notebook(client), f"{BASE}long_blog")

    assert response.status_code == 200, response.text
    parts = [call for call in assistant.calls if call.mode is ExtractionMode.PAGE_PART]
    assert len(parts) >= 3
    assert {call.part[1] for call in parts} == {len(parts)}
    draft = response.json()["draft"]
    assert [line["name"] for line in draft["ingredient_lines"]] == ["bean", "onion"]
    assert draft["steps"] == ["Soak the beans.", "Simmer."]
    assert draft["title"] == "Farmhouse White Bean Stew"


def test_a_non_member_gets_not_found_and_nothing_is_fetched(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "owner_link@example.com")
    notebook_id = _notebook(client)
    _register(client, "other_link@example.com")
    _switch_to(client, "other_link@example.com")

    response = _capture(client, notebook_id, f"{BASE}jsonld_recipe")

    assert response.status_code == 404
    assert response.json()["code"] == "notebook_not_found"
    assert fetcher.calls == []
    assert assistant.calls == []


def test_an_archived_kitchen_gets_conflict_and_nothing_is_fetched(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "arch_link@example.com")
    kitchen = client.post("/kitchens", json={"name": "Old Kitchen"})
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]
    notebook_id = client.get(f"/notebooks/kitchens/{kitchen_id}").json()["notebooks"][0]["id"]
    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code in (200, 204), archived.text

    response = _capture(client, notebook_id, f"{BASE}jsonld_recipe")

    assert response.status_code == 409
    assert response.json()["code"] == "kitchen_archived"
    assert fetcher.calls == []


# --- refusals (T056; FR-021, FR-021a, FR-022, FR-024) ---


@pytest.mark.parametrize(
    "kind",
    ["blocked", "dns", "timeout", "connect", "redirect", "status", "not_html", "too_large"],
)
def test_every_fetch_failure_has_one_body_with_no_kind(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor, kind: str
) -> None:
    _register(client, f"fail_{kind}@example.com")
    url = f"https://example.test/fails/{kind}"
    fetcher.pages[url] = PageFetchFailed(kind)

    response = _capture(client, _notebook(client), url)

    assert response.status_code == 422
    assert response.json() == {"detail": "", "code": "page_fetch_failed"}
    assert assistant.calls == []


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("   ", "link_empty"),
        ("javascript:alert(1)", "link_invalid"),
        ("https://user:pw@example.test/", "page_fetch_failed"),
        ("https://example.test:8080/", "page_fetch_failed"),
    ],
)
def test_link_refusals(
    client: TestClient,
    fetcher: FakePageFetcher,
    assistant: FakeRecipeExtractor,
    url: str,
    code: str,
) -> None:
    _register(client, f"link_{code}_{len(url)}@example.com")

    response = _capture(client, _notebook(client), url)

    assert response.status_code == 422
    assert response.json()["code"] == code
    assert fetcher.calls == []


def test_a_link_over_the_limit_names_the_limit(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "long_link@example.com")

    response = _capture(client, _notebook(client), "https://example.test/" + "a" * 2100)

    assert response.status_code == 422
    assert response.json() == {"detail": "", "code": "link_too_long", "max": 2048}


@pytest.mark.parametrize("name", ["no_recipe", "script_only"])
def test_pages_without_a_recipe(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor, name: str
) -> None:
    from application.recipe_extraction import NotARecipe, NotRecipeReason

    _register(client, f"none_{name}@example.com")
    assistant.script = NotARecipe(reason=NotRecipeReason.STORY_OR_ARTICLE)

    response = _capture(client, _notebook(client), f"{BASE}{name}")

    assert response.status_code == 422
    assert response.json()["code"] == "page_no_recipe"


def test_two_schema_org_recipes_ask_for_one_at_a_time(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "two_link@example.com")

    response = _capture(client, _notebook(client), f"{BASE}jsonld_two_recipes")

    assert response.status_code == 422
    assert response.json()["code"] == "one_recipe_at_a_time"
    assert assistant.calls == []


@pytest.mark.parametrize(
    ("result", "status", "code"),
    [
        (LimitReached(retry_after_seconds=30), 429, "ai_limit_reached"),
        (Unavailable(), 503, "ai_unavailable"),
        (AIProviderError(), 503, "ai_misconfigured"),
        (InvalidOutput(), 422, "ai_invalid_output"),
    ],
)
def test_assistant_failures_keep_their_codes(
    client: TestClient,
    fetcher: FakePageFetcher,
    assistant: FakeRecipeExtractor,
    result,
    status: int,
    code: str,
) -> None:
    _register(client, f"ai_{code}@example.com")
    assistant.script = result

    response = _capture(client, _notebook(client), f"{BASE}plain_recipe")

    assert response.status_code == status
    assert response.json()["code"] == code
    if isinstance(result, LimitReached):
        assert response.headers["retry-after"] == "30"


def test_a_merged_draft_with_no_steps_still_opens_for_the_form_to_complete(
    client: TestClient, fetcher: FakePageFetcher, assistant: FakeRecipeExtractor
) -> None:
    _register(client, "nosteps_link@example.com")
    assistant.script = DraftPart("Stew", None, (IngredientLine("bean", False, None, None),), ())

    response = _capture(client, _notebook(client), f"{BASE}long_blog")

    assert response.status_code == 200, response.text
    draft = response.json()["draft"]
    assert draft["title"] == "Stew"
    assert draft["steps"] == []
    assert draft["ingredient_lines"][0]["quantity"] is None
    assert draft["ingredient_lines"][0]["match"] == {"kind": "new", "entry": None}
    assert draft["servings_estimated"] is True
