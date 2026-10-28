"""Recipe detail, edit and delete over HTTP with Postgres (spec 027).

Requires DATABASE_URL (Compose db or CI Postgres 16) with migrations at head. Skips when unset.
Recipes are saved through POST /recipes. The suite runs inside one transaction per test, so the
version moves because `replace` stamps `clock_timestamp()`. The one true-concurrency test
(SC-007) uses committed rows of its own on two connections and cleans them up.
"""

from __future__ import annotations

import threading
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import (
    IngredientModel,
    KitchenMembershipModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
)
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from domain.errors import RecipeChangedError
from domain.recipe import EditedRecipe
from domain.recipe_draft import IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"


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


def _kitchen(client: TestClient) -> tuple[str, str]:
    kitchen = client.post("/kitchens", json={"name": "Home"})
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]
    listed = client.get(f"/notebooks/kitchens/{kitchen_id}")
    assert listed.status_code == 200, listed.text
    return kitchen_id, listed.json()["notebooks"][0]["id"]


def _join_kitchen(db: Session, kitchen_id: str, user_id: UUID) -> None:
    db.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=UUID(kitchen_id), user_id=user_id, role="member"
        )
    )
    db.flush()


def _lines() -> list[dict]:
    return [
        {"name": "rice", "quantity": 1, "unit": "cup"},
        {"name": "onion", "quantity": 2, "unit": "unit", "size": "large", "preparation": "chopped"},
        {"name": "salt", "vague": True, "note": "to taste"},
    ]


def _save(client: TestClient, notebook_id: str, title: str = "Tomato rice", **over) -> str:
    body = {
        "save_key": str(uuid4()),
        "notebook_id": notebook_id,
        "source_text": "pasted private text",
        "title": title,
        "base_servings": 4,
        "servings_estimated": False,
        "ingredient_lines": _lines(),
        "steps": ["Fry the garlic.", "Add the rice.", "Simmer."],
    }
    body.update(over)
    response = client.post("/recipes", json=body)
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def _edit_body(recipe: dict, **over) -> dict:
    body = {
        "version": recipe["version"],
        "title": recipe["title"],
        "base_servings": recipe["base_servings"],
        "servings_estimated": recipe["servings_estimated"],
        "ingredient_lines": recipe["ingredient_lines"],
        "steps": recipe["steps"],
    }
    body.update(over)
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


# --- US1: read ------------------------------------------------------------------------------


def test_the_author_reads_a_recipe_as_saved(client: TestClient, db_session: Session):
    _register(client, "ana_read@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, notebook)
    before = _counts(db_session)

    response = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Tomato rice" and data["base_servings"] == 4
    assert data["author_alias"] == "ana_read" and data["can_write"] is True
    assert data["notebook"]["id"] == notebook and data["notebook"]["kind"] == "personal"
    assert [line["name"] for line in data["ingredient_lines"]] == ["rice", "onion", "salt"]
    assert data["ingredient_lines"][1]["size"] == "large"
    assert data["ingredient_lines"][1]["preparation"] == "chopped"
    assert data["ingredient_lines"][2]["vague"] is True
    assert data["ingredient_lines"][2]["note"] == "to taste"
    assert data["steps"] == ["Fry the garlic.", "Add the rice.", "Simmer."]
    assert data["source"] is None
    assert "pasted private text" not in response.text
    assert datetime.fromisoformat(data["version"])
    assert _counts(db_session) == before


def test_members_read_and_the_archived_kitchen_is_read_only(
    client: TestClient, db_session: Session
):
    _register(client, "ana_acc@example.com")
    personal = _personal_notebook(client)
    kitchen_id, kitchen_notebook = _kitchen(client)
    own = _save(client, personal)
    shared = _save(client, kitchen_notebook, "Home soup")
    ben_id = _register(client, "ben_acc@example.com")
    db_session.add(
        NotebookMembershipModel(notebook_id=UUID(personal), user_id=ben_id, role="member")
    )
    _join_kitchen(db_session, kitchen_id, ben_id)

    assert client.get(f"/recipes/{own}").json()["can_write"] is True
    assert client.get(f"/recipes/{shared}").json()["can_write"] is True

    _switch_to(client, "ana_acc@example.com")
    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code in (200, 204), archived.text
    _switch_to(client, "ben_acc@example.com")
    read = client.get(f"/recipes/{shared}")
    assert read.status_code == 200 and read.json()["can_write"] is False


def test_a_non_reader_and_an_unknown_id_get_identical_404s(client: TestClient, db_session: Session):
    _register(client, "ana_404@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    _register(client, "stranger_404@example.com")

    private = client.get(f"/recipes/{recipe_id}")
    unknown = client.get(f"/recipes/{uuid4()}")

    assert private.status_code == unknown.status_code == 404
    assert private.json() == unknown.json()
    assert private.json()["code"] == "recipe_not_found"


def test_a_recipe_of_100_lines_and_100_steps_opens(client: TestClient, db_session: Session):
    _register(client, "ana_big@example.com")
    lines = [{"name": f"item{n}", "quantity": 1, "unit": "g"} for n in range(100)]
    steps = [f"Step {n}." for n in range(100)]
    recipe_id = _save(client, _personal_notebook(client), ingredient_lines=lines, steps=steps)

    data = client.get(f"/recipes/{recipe_id}").json()

    assert len(data["ingredient_lines"]) == 100 and data["steps"] == steps


# --- US2: edit ------------------------------------------------------------------------------


def test_edit_changes_content_and_keeps_the_rest(client: TestClient, db_session: Session):
    user_id = _register(client, "ana_edit@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, notebook)
    original = client.get(f"/recipes/{recipe_id}").json()
    row = db_session.get(RecipeModel, UUID(recipe_id))
    assert row is not None
    source_id, created_at = row.source_id, row.created_at

    lines = [dict(line) for line in original["ingredient_lines"]]
    lines[0]["quantity"] = 2
    response = client.put(
        f"/recipes/{recipe_id}",
        json=_edit_body(
            original, title="Better rice", ingredient_lines=lines, steps=["First.", "Second."]
        ),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Better rice" and data["steps"] == ["First.", "Second."]
    assert data["ingredient_lines"][0]["quantity"] == 2
    assert data["version"] != original["version"]
    assert data["created_catalog_names"] == []
    db_session.expire_all()
    row = db_session.get(RecipeModel, UUID(recipe_id))
    assert row is not None
    assert row.author_id == user_id and str(row.notebook_id) == notebook
    assert row.source_id == source_id and row.created_at == created_at
    assert row.updated_at > created_at
    positions = list(
        db_session.scalars(
            select(RecipeIngredientModel.position)
            .where(RecipeIngredientModel.recipe_id == row.id)
            .order_by(RecipeIngredientModel.position)
        )
    )
    assert positions == [0, 1, 2]
    step_positions = list(
        db_session.scalars(
            select(StepModel.position)
            .where(StepModel.recipe_id == row.id)
            .order_by(StepModel.position)
        )
    )
    assert step_positions == [0, 1]


def test_lines_can_be_added_removed_and_reordered(client: TestClient, db_session: Session):
    _register(client, "ana_order@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    recipe = client.get(f"/recipes/{recipe_id}").json()
    lines = recipe["ingredient_lines"]
    new = [lines[2], {"name": "garlic", "quantity": 2, "unit": "unit"}, lines[0]]

    response = client.put(
        f"/recipes/{recipe_id}",
        json=_edit_body(recipe, ingredient_lines=new, steps=["Last.", "First."]),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert [line["name"] for line in data["ingredient_lines"]] == ["salt", "garlic", "rice"]
    assert data["steps"] == ["Last.", "First."]
    assert data["ingredient_lines"][0]["vague"] is True


def test_a_kitchen_member_and_a_notebook_member_edit_what_others_saved(
    client: TestClient, db_session: Session
):
    _register(client, "ana_who@example.com")
    personal = _personal_notebook(client)
    kitchen_id, kitchen_notebook = _kitchen(client)
    mine = _save(client, personal)
    shared = _save(client, kitchen_notebook, "Home soup")
    ben_id = _register(client, "ben_who@example.com")
    db_session.add(
        NotebookMembershipModel(notebook_id=UUID(personal), user_id=ben_id, role="member")
    )
    _join_kitchen(db_session, kitchen_id, ben_id)

    for recipe_id in (mine, shared):
        recipe = client.get(f"/recipes/{recipe_id}").json()
        response = client.put(
            f"/recipes/{recipe_id}", json=_edit_body(recipe, title="Edited by Ben")
        )
        assert response.status_code == 200, response.text
        assert response.json()["author_alias"] == "ana_who"
    _switch_to(client, "ana_who@example.com")
    assert client.get(f"/recipes/{mine}").json()["title"] == "Edited by Ben"


@pytest.mark.parametrize(
    ("override", "status", "code"),
    [
        ({"title": "  "}, 422, "draft_incomplete"),
        ({"steps": []}, 422, "draft_incomplete"),
        ({"ingredient_lines": []}, 422, "draft_incomplete"),
        ({"ingredient_lines": [{"name": "rice", "quantity": 1}]}, 422, "ingredient_line_problem"),
        ({"ingredient_lines": [{"name": "rice", "unit": "cup"}]}, 422, "ingredient_line_problem"),
        ({"base_servings": 0}, 422, "invalid_recipe"),
        (
            {"ingredient_lines": [{"name": "salt", "vague": True, "quantity": 2, "unit": "g"}]},
            422,
            "invalid_recipe",
        ),
        (
            {
                "ingredient_lines": [
                    {"name": f"i{n}", "quantity": 1, "unit": "g"} for n in range(101)
                ]
            },
            422,
            "invalid_recipe",
        ),
    ],
)
def test_an_edit_that_breaks_a_rule_changes_nothing(
    client: TestClient, db_session: Session, override: dict, status: int, code: str
):
    _register(client, "ana_rule@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    recipe = client.get(f"/recipes/{recipe_id}").json()
    before = _counts(db_session)

    response = client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe, **override))

    assert response.status_code == status, response.text
    assert response.json()["code"] == code
    assert _counts(db_session) == before
    assert client.get(f"/recipes/{recipe_id}").json() == recipe


def test_an_edit_names_the_missing_parts_and_lines(client: TestClient, db_session: Session):
    _register(client, "ana_msg@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    recipe = client.get(f"/recipes/{recipe_id}").json()

    missing = client.put(
        f"/recipes/{recipe_id}", json=_edit_body(recipe, title="", ingredient_lines=[])
    )
    assert set(missing.json()["missing"]) == {"title", "ingredients"}

    bad_line = client.put(
        f"/recipes/{recipe_id}",
        json=_edit_body(recipe, ingredient_lines=[{"name": "rice", "quantity": 1}]),
    )
    assert bad_line.json()["line_problems"] == [{"name": "rice", "kind": "unit_missing"}]


def test_a_read_only_member_cannot_change_or_delete(client: TestClient, db_session: Session):
    _register(client, "ana_ro@example.com")
    kitchen_id, notebook = _kitchen(client)
    recipe_id = _save(client, notebook)
    recipe = client.get(f"/recipes/{recipe_id}").json()
    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code in (200, 204), archived.text
    before = _counts(db_session)

    put = client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe, title="Nope"))
    delete = client.delete(f"/recipes/{recipe_id}")
    match = client.post(f"/recipes/{recipe_id}/name-matches", json={"names": ["onions"]})

    for response in (put, delete, match):
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "recipe_read_only"
    assert _counts(db_session) == before
    assert client.get(f"/recipes/{recipe_id}").json()["title"] == "Tomato rice"


def test_a_non_reader_cannot_change_delete_or_match(client: TestClient, db_session: Session):
    _register(client, "ana_nr@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    recipe = client.get(f"/recipes/{recipe_id}").json()
    _register(client, "stranger_nr@example.com")
    before = _counts(db_session)

    put = client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe, title="Nope"))
    delete = client.delete(f"/recipes/{recipe_id}")
    match = client.post(f"/recipes/{recipe_id}/name-matches", json={"names": ["onions"]})

    for response in (put, delete, match):
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "recipe_not_found"
    assert _counts(db_session) == before


def test_a_stale_edit_is_refused_and_the_first_save_stays(client: TestClient, db_session: Session):
    _register(client, "ana_stale@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    opened = client.get(f"/recipes/{recipe_id}").json()

    first = client.put(f"/recipes/{recipe_id}", json=_edit_body(opened, title="First"))
    second = client.put(f"/recipes/{recipe_id}", json=_edit_body(opened, title="Second"))

    assert first.status_code == 200, first.text
    assert second.status_code == 409 and second.json()["code"] == "recipe_changed"
    assert client.get(f"/recipes/{recipe_id}").json()["title"] == "First"
    again = client.put(f"/recipes/{recipe_id}", json=_edit_body(first.json(), title="Second"))
    assert again.status_code == 200 and again.json()["title"] == "Second"


def test_new_names_join_the_catalog_and_none_is_removed(client: TestClient, db_session: Session):
    _register(client, "ana_cat@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, notebook)
    recipe = client.get(f"/recipes/{recipe_id}").json()
    assert _catalog(db_session, notebook) == ["onion", "rice", "salt"]

    response = client.put(
        f"/recipes/{recipe_id}",
        json=_edit_body(
            recipe,
            ingredient_lines=[
                {"name": " Onion ", "quantity": 1, "unit": "unit"},
                {"name": "garlic", "quantity": 2, "unit": "unit"},
            ],
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["created_catalog_names"] == ["garlic"]
    assert [line["name"] for line in response.json()["ingredient_lines"]] == ["onion", "garlic"]
    assert _catalog(db_session, notebook) == ["garlic", "onion", "rice", "salt"]


def test_name_matches_propose_the_catalog_entry(client: TestClient, db_session: Session):
    _register(client, "ana_match@example.com")
    recipe_id = _save(client, _personal_notebook(client))

    response = client.post(
        f"/recipes/{recipe_id}/name-matches", json={"names": ["onions", "Onion", "garlic"]}
    )

    assert response.status_code == 200, response.text
    assert response.json()["matches"] == [
        {"name": "onions", "entry": "onion"},
        {"name": "Onion", "entry": "onion"},
        {"name": "garlic", "entry": None},
    ]
    assert client.post(f"/recipes/{recipe_id}/name-matches", json={"names": []}).status_code == 422


def _copy(db: Session, source_recipe_id: str, owner_id: UUID) -> UUID:
    """An independent copy of a recipe in a notebook of its own (flow G, inserted directly)."""
    notebook = NotebookModel(id=uuid4(), name="copy notebook")
    db.add(notebook)
    db.flush()
    original = db.get(RecipeModel, UUID(source_recipe_id))
    assert original is not None
    copy = RecipeModel(
        notebook_id=notebook.id,
        author_id=owner_id,
        title=original.title,
        base_servings=original.base_servings,
        servings_estimated=False,
    )
    db.add(copy)
    db.flush()
    db.add(
        RecipeIngredientModel(recipe_id=copy.id, position=0, name="rice", quantity=1, unit="cup")
    )
    db.add(StepModel(recipe_id=copy.id, position=0, text="Copy step."))
    db.flush()
    return copy.id


def _snapshot(db: Session, recipe_id: UUID) -> tuple:
    db.expire_all()
    row = db.get(RecipeModel, recipe_id)
    assert row is not None
    lines = db.execute(
        select(RecipeIngredientModel.name, RecipeIngredientModel.quantity)
        .where(RecipeIngredientModel.recipe_id == recipe_id)
        .order_by(RecipeIngredientModel.position)
    ).all()
    steps = db.scalars(select(StepModel.text).where(StepModel.recipe_id == recipe_id)).all()
    return (row.title, row.updated_at, tuple(map(tuple, lines)), tuple(steps))


def test_editing_the_original_leaves_its_copy_alone(client: TestClient, db_session: Session):
    user_id = _register(client, "ana_copy@example.com")
    recipe_id = _save(client, _personal_notebook(client))
    copy_id = _copy(db_session, recipe_id, user_id)
    before = _snapshot(db_session, copy_id)
    recipe = client.get(f"/recipes/{recipe_id}").json()

    response = client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe, title="Changed"))

    assert response.status_code == 200, response.text
    assert _snapshot(db_session, copy_id) == before


# --- US3: delete ----------------------------------------------------------------------------


def test_delete_removes_the_recipe_but_not_its_copy_or_the_catalog(
    client: TestClient, db_session: Session
):
    user_id = _register(client, "ana_del@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, notebook)
    sibling = _save(client, notebook, "Soup")
    copy_id = _copy(db_session, recipe_id, user_id)
    catalog = _catalog(db_session, notebook)
    sibling_before, copy_before = (
        _snapshot(db_session, UUID(sibling)),
        _snapshot(db_session, copy_id),
    )
    row = db_session.get(RecipeModel, UUID(recipe_id))
    assert row is not None
    source_id = row.source_id

    response = client.delete(f"/recipes/{recipe_id}")

    assert response.status_code == 204 and response.content == b""
    db_session.expire_all()
    rid = UUID(recipe_id)
    assert db_session.get(RecipeModel, rid) is None
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RecipeIngredientModel)
            .where(RecipeIngredientModel.recipe_id == rid)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(StepModel).where(StepModel.recipe_id == rid)
        )
        == 0
    )
    assert source_id is not None and db_session.get(SourceModel, source_id) is None
    assert _catalog(db_session, notebook) == catalog
    assert _snapshot(db_session, UUID(sibling)) == sibling_before
    assert _snapshot(db_session, copy_id) == copy_before
    listed = client.get(f"/notebooks/{notebook}/recipes").json()
    assert [item["title"] for item in listed["items"]] == ["Soup"]


def test_a_deleted_recipe_is_gone_for_every_route_and_a_second_delete_is_a_404(
    client: TestClient, db_session: Session
):
    _register(client, "ana_gone@example.com")
    notebook = _personal_notebook(client)
    recipe_id = _save(client, notebook)
    recipe = client.get(f"/recipes/{recipe_id}").json()
    assert client.delete(f"/recipes/{recipe_id}").status_code == 204

    responses = [
        client.get(f"/recipes/{recipe_id}"),
        client.put(f"/recipes/{recipe_id}", json=_edit_body(recipe)),
        client.post(f"/recipes/{recipe_id}/name-matches", json={"names": ["x"]}),
        client.delete(f"/recipes/{recipe_id}"),
    ]
    bodies = {response.text for response in responses}
    assert {response.status_code for response in responses} == {404} and len(bodies) == 1
    assert responses[0].json()["code"] == "recipe_not_found"
    listed = client.get(f"/notebooks/{notebook}/recipes")
    assert (
        listed.status_code == 200 and listed.json()["items"] == [] and listed.json()["total"] == 0
    )


def test_a_kitchen_recipe_leaves_the_kitchen_list(client: TestClient, db_session: Session):
    _register(client, "ana_kl@example.com")
    kitchen_id, notebook = _kitchen(client)
    keep, drop = _save(client, notebook, "Keep"), _save(client, notebook, "Drop")
    assert client.delete(f"/recipes/{drop}").status_code == 204

    items = client.get(f"/notebooks/kitchens/{kitchen_id}/recipes").json()["items"]

    assert [item["id"] for item in items] == [keep]


# --- US4: nothing left pointing at a deleted recipe -----------------------------------------


def test_only_the_lines_and_steps_point_at_recipe_ids(engine: Engine):
    """A new table with a key to recipe.id must cascade, or be cleaned in DeleteRecipeService.

    Spec 027 FR-016: when this fails, S-022 (cart), S-019 (embeddings) or S-030 (citations) added
    a reference. Add its cleanup to DeleteRecipeService, then update this list.
    """
    inspector = inspect(engine)
    referencing: dict[str, str | None] = {}
    for table in inspector.get_table_names():
        for key in inspector.get_foreign_keys(table):
            if key["referred_table"] == "recipe":
                referencing[table] = (key.get("options") or {}).get("ondelete")
    assert referencing == {"recipe_ingredient": "CASCADE", "step": "CASCADE"}


# --- SC-007: two sessions saving at once ----------------------------------------------------


def test_the_second_of_two_concurrent_saves_waits_and_is_told(engine: Engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    notebook_id, recipe_id = uuid4(), uuid4()
    with factory() as setup:
        setup.add(NotebookModel(id=notebook_id, name="concurrency notebook"))
        setup.flush()
        setup.add(
            RecipeModel(id=recipe_id, notebook_id=notebook_id, title="Start", base_servings=2)
        )
        setup.flush()
        setup.add(StepModel(recipe_id=recipe_id, position=0, text="Cook."))
        setup.add(
            RecipeIngredientModel(
                recipe_id=recipe_id, position=0, name="rice", quantity=1, unit="cup"
            )
        )
        setup.commit()

    def edited(title: str) -> EditedRecipe:
        line = IngredientLine(name="rice", vague=False, quantity=1.0, unit="cup")
        return EditedRecipe(
            title=title,
            base_servings=2,
            servings_estimated=False,
            lines=(line,),
            steps=("Cook.",),
        )

    outcome: dict[str, object] = {}
    try:
        first = factory()
        version = SqlAlchemyRecipeRepository(first).get_detail(recipe_id).updated_at  # type: ignore[union-attr]
        SqlAlchemyRecipeRepository(first).replace(recipe_id, version, edited("First"))

        def second_save() -> None:
            with factory() as second:
                try:
                    SqlAlchemyRecipeRepository(second).replace(recipe_id, version, edited("Second"))
                    second.commit()
                    outcome["result"] = "saved"
                except RecipeChangedError:
                    second.rollback()
                    outcome["result"] = "changed"

        worker = threading.Thread(target=second_save)
        worker.start()
        worker.join(timeout=1.0)
        assert worker.is_alive(), "the second save should wait for the first one's lock"
        first.commit()
        first.close()
        worker.join(timeout=10.0)
        assert not worker.is_alive()
        assert outcome["result"] == "changed"
        with factory() as check:
            stored = SqlAlchemyRecipeRepository(check).get_detail(recipe_id)
            assert stored is not None and stored.title == "First"
    finally:
        with factory() as cleanup:
            notebook = cleanup.get(NotebookModel, notebook_id)
            if notebook is not None:
                cleanup.delete(notebook)
                cleanup.commit()
