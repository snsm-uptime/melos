"""Recipe lists over HTTP with Postgres (spec 021 FR-001 to FR-012, SC-001 to SC-006).

Requires DATABASE_URL (Compose db or CI Postgres 16) with migrations at head. Skips when
unset. Recipes are saved through POST /recipes, then given distinct creation times, since
every row written in one test transaction shares the same now().
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import (
    IngredientModel,
    NotebookModel,
    RecipeModel,
    UserModel,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
START = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


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


def _kitchen(client: TestClient, name: str = "Home") -> tuple[str, str]:
    kitchen = client.post("/kitchens", json={"name": name})
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]
    listed = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert listed.status_code == 200, listed.text
    return kitchen_id, listed.json()["notebooks"][0]["id"]


def _save(
    client: TestClient,
    db: Session,
    notebook_id: str,
    title: str,
    ingredients: tuple[str, ...] = ("salt",),
    minutes: int = 0,
) -> UUID:
    body = {
        "save_key": str(uuid4()),
        "notebook_id": notebook_id,
        "source_text": "pasted text",
        "title": title,
        "base_servings": 2,
        "servings_estimated": False,
        "ingredient_lines": [{"name": name, "vague": True, "note": "some"} for name in ingredients],
        "steps": ["Cook it."],
    }
    response = client.post("/recipes", json=body)
    assert response.status_code == 201, response.text
    recipe_id = UUID(response.json()["recipe"]["id"])
    db.execute(
        update(RecipeModel)
        .where(RecipeModel.id == recipe_id)
        .values(created_at=START + timedelta(minutes=minutes))
    )
    db.flush()
    return recipe_id


def _counts(db: Session) -> tuple[int, ...]:
    return tuple(
        db.scalar(select(func.count()).select_from(model)) or 0
        for model in (NotebookModel, RecipeModel, IngredientModel)
    )


def _titles(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


# --- US1: a notebook's list ---


def test_personal_list_is_newest_first_with_author_and_count(
    client: TestClient, db_session: Session
):
    _register(client, "ana_list@example.com")
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "Old soup", ("lentil", "onion"), minutes=1)
    _save(client, db_session, notebook, "New soup", ("lentil",), minutes=2)

    response = client.get(f"/notebooks/{notebook}/recipes")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["New soup", "Old soup"]
    first, second = body["items"]
    assert first["author_alias"] == "ana_list" and first["ingredient_count"] == 1
    assert second["ingredient_count"] == 2 and second["notebook_id"] == notebook
    assert (body["page"], body["page_size"], body["total"], body["total_pages"]) == (1, 12, 2, 1)


def test_a_notebook_member_sees_the_owners_recipes(client: TestClient, db_session: Session):
    _register(client, "own_list@example.com")
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "Shared soup")
    ana_id = UUID(client.get("/auth/me").json()["user_id"])
    _register(client, "mem_list@example.com")
    member_id = UUID(client.get("/auth/me").json()["user_id"])
    from adapters.persistence.models import NotebookMembershipModel

    db_session.add(
        NotebookMembershipModel(notebook_id=UUID(notebook), user_id=member_id, role="member")
    )
    db_session.flush()
    assert ana_id != member_id

    assert _titles(client.get(f"/notebooks/{notebook}/recipes")) == ["Shared soup"]


def test_a_stranger_gets_the_same_404_as_an_unknown_notebook(
    client: TestClient, db_session: Session
):
    _register(client, "own2_list@example.com")
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "Private soup")
    _register(client, "str2_list@example.com")

    stranger = client.get(f"/notebooks/{notebook}/recipes")
    unknown = client.get(f"/notebooks/{uuid4()}/recipes")

    assert stranger.status_code == unknown.status_code == 404
    assert stranger.json() == unknown.json()
    assert stranger.json()["code"] == "notebook_not_found"


def test_empty_notebook_lists_nothing_without_error(client: TestClient):
    _register(client, "empty_list@example.com")
    notebook = _personal_notebook(client)

    body = client.get(f"/notebooks/{notebook}/recipes").json()

    assert (body["items"], body["total"], body["page"], body["total_pages"]) == ([], 0, 1, 1)


def test_a_deleted_author_reads_as_null(client: TestClient, db_session: Session):
    user_id = _register(client, "gone_list@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, db_session, notebook, "Orphan soup")
    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == recipe_id).values(author_id=None)
    )
    db_session.flush()
    assert db_session.get(UserModel, user_id) is not None

    item = client.get(f"/notebooks/{notebook}/recipes").json()["items"][0]

    assert item["author_alias"] is None


def test_paging_by_twelve_and_a_page_past_the_end(client: TestClient, db_session: Session):
    _register(client, "page_list@example.com")
    notebook = _personal_notebook(client)
    for index in range(13):
        _save(client, db_session, notebook, f"Recipe {index:02d}", minutes=index)

    first = client.get(f"/notebooks/{notebook}/recipes").json()
    second = client.get(f"/notebooks/{notebook}/recipes?page=2").json()
    beyond = client.get(f"/notebooks/{notebook}/recipes?page=9").json()

    assert (len(first["items"]), first["total_pages"]) == (12, 2)
    assert [item["title"] for item in second["items"]] == ["Recipe 00"]
    assert beyond["page"] == 2 and [i["title"] for i in beyond["items"]] == ["Recipe 00"]


def test_page_zero_and_long_filter_are_422(client: TestClient):
    _register(client, "bad_list@example.com")
    notebook = _personal_notebook(client)

    page = client.get(f"/notebooks/{notebook}/recipes?page=0")
    long = client.get(f"/notebooks/{notebook}/recipes", params={"q": "a" * 101})

    assert page.status_code == 422 and page.json()["code"] == "invalid_page"
    assert long.status_code == 422 and long.json()["code"] == "invalid_query"


def test_opening_lists_writes_nothing(client: TestClient, db_session: Session):
    _register(client, "ro_list@example.com")
    notebook = _personal_notebook(client)
    kitchen_id, _ = _kitchen(client)
    _save(client, db_session, notebook, "Soup")
    before = _counts(db_session)

    client.get(f"/notebooks/{notebook}/recipes")
    client.get(f"/notebooks/kitchens/{kitchen_id}/recipes")

    assert _counts(db_session) == before


# --- US2: a kitchen's list ---


def test_kitchen_list_merges_members_recipes_and_skips_personal_ones(
    client: TestClient, db_session: Session
):
    _register(client, "ann_k@example.com")
    kitchen_id, kitchen_notebook = _kitchen(client)
    personal = _personal_notebook(client)
    _save(client, db_session, kitchen_notebook, "Ann soup", minutes=1)
    _save(client, db_session, personal, "Ann private", minutes=5)
    ben_id = _register(client, "ben_k@example.com")
    from adapters.persistence.models import KitchenMembershipModel

    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=UUID(kitchen_id), user_id=ben_id, role="member"
        )
    )
    db_session.flush()
    _save(client, db_session, kitchen_notebook, "Ben stew", minutes=2)

    response = client.get(f"/notebooks/kitchens/{kitchen_id}/recipes")

    assert _titles(response) == ["Ben stew", "Ann soup"]
    items = response.json()["items"]
    assert [item["author_alias"] for item in items] == ["ben_k", "ann_k"]
    assert {item["notebook_id"] for item in items} == {kitchen_notebook}
    assert items[0]["notebook_name"]


def test_kitchen_non_member_and_unknown_kitchen_get_identical_404s(
    client: TestClient, db_session: Session
):
    _register(client, "own_k2@example.com")
    kitchen_id, notebook = _kitchen(client)
    _save(client, db_session, notebook, "Soup")
    _register(client, "out_k2@example.com")

    outsider = client.get(f"/notebooks/kitchens/{kitchen_id}/recipes")
    unknown = client.get(f"/notebooks/kitchens/{uuid4()}/recipes")

    assert outsider.status_code == unknown.status_code == 404
    assert outsider.json() == unknown.json()
    assert outsider.json()["code"] == "kitchen_not_found"


def test_kitchen_without_a_notebook_is_empty_and_creates_nothing(
    client: TestClient, db_session: Session
):
    _register(client, "none_k@example.com")
    kitchen = client.post("/kitchens", json={"name": "Bare"})
    kitchen_id = kitchen.json()["id"]
    before = _counts(db_session)

    body = client.get(f"/notebooks/kitchens/{kitchen_id}/recipes").json()

    assert (body["items"], body["total"], body["page"]) == ([], 0, 1)
    assert _counts(db_session) == before


def test_archived_kitchen_still_lists(client: TestClient, db_session: Session):
    _register(client, "arch_k@example.com")
    kitchen_id, notebook = _kitchen(client)
    _save(client, db_session, notebook, "Kept soup")
    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code in (200, 204), archived.text

    assert _titles(client.get(f"/notebooks/kitchens/{kitchen_id}/recipes")) == ["Kept soup"]


# --- US3: the text filter ---


def _filter_notebook(client: TestClient, db_session: Session, email: str) -> str:
    _register(client, email)
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "Lentil soup", ("lentil", "onion"), minutes=1)
    _save(client, db_session, notebook, "Pancakes", ("flour", "milk"), minutes=2)
    _save(client, db_session, notebook, "Crema de calabaza", ("calabaza",), minutes=3)
    return notebook


def test_filter_by_title_ingredient_case_and_accent(client: TestClient, db_session: Session):
    notebook = _filter_notebook(client, db_session, "flt_list@example.com")

    def titles(q: str) -> list[str]:
        return _titles(client.get(f"/notebooks/{notebook}/recipes", params={"q": q}))

    assert titles("soup") == ["Lentil soup"]
    assert titles("milk") == ["Pancakes"]
    assert titles("PANCAKE") == ["Pancakes"]
    assert titles("calabazá") == ["Crema de calabaza"]
    assert titles("  onion  ") == ["Lentil soup"]
    assert len(titles("   ")) == 3
    assert titles("zzz") == []


def test_no_match_reports_zero_total(client: TestClient, db_session: Session):
    notebook = _filter_notebook(client, db_session, "none_list@example.com")

    body = client.get(f"/notebooks/{notebook}/recipes", params={"q": "zzz"}).json()

    assert (body["items"], body["total"], body["page"], body["total_pages"]) == ([], 0, 1, 1)


def test_wildcards_match_literally(client: TestClient, db_session: Session):
    _register(client, "wild_list@example.com")
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "100% juice", minutes=1)
    _save(client, db_session, notebook, "Plain soup", minutes=2)
    _save(client, db_session, notebook, "a_b stew", minutes=3)

    def titles(q: str) -> list[str]:
        return _titles(client.get(f"/notebooks/{notebook}/recipes", params={"q": q}))

    assert titles("%") == ["100% juice"]
    assert titles("_") == ["a_b stew"]
    assert titles("\\") == []


def test_filter_covers_all_pages_and_keeps_order(client: TestClient, db_session: Session):
    _register(client, "allp_list@example.com")
    notebook = _personal_notebook(client)
    for index in range(14):
        _save(client, db_session, notebook, f"Soup {index:02d}", minutes=index)
    _save(client, db_session, notebook, "Tart", minutes=50)

    body = client.get(f"/notebooks/{notebook}/recipes", params={"q": "soup", "page": 2}).json()

    assert (body["total"], body["total_pages"], body["page"]) == (14, 2, 2)
    assert [item["title"] for item in body["items"]] == ["Soup 01", "Soup 00"]


def test_kitchen_filter_searches_every_notebook(client: TestClient, db_session: Session):
    _register(client, "kf_list@example.com")
    kitchen_id, first = _kitchen(client)
    second_notebook = NotebookModel(name="Second", kitchen_id=UUID(kitchen_id))
    db_session.add(second_notebook)
    db_session.flush()
    _save(client, db_session, first, "Lentil soup", minutes=1)
    _save(client, db_session, str(second_notebook.id), "Onion tart", ("onion",), minutes=2)

    response = client.get(f"/notebooks/kitchens/{kitchen_id}/recipes", params={"q": "onion"})

    assert _titles(response) == ["Onion tart"]


def test_switching_user_keeps_lists_private(client: TestClient, db_session: Session):
    _register(client, "sw1_list@example.com")
    notebook = _personal_notebook(client)
    _save(client, db_session, notebook, "Mine")
    _register(client, "sw2_list@example.com")
    _switch_to(client, "sw1_list@example.com")

    assert _titles(client.get(f"/notebooks/{notebook}/recipes")) == ["Mine"]
