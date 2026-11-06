"""Share a recipe with a co-member over HTTP with Postgres (spec 071).

Skips when DATABASE_URL is unset. Accounts, kitchens, notebooks and recipes are invented.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from adapters.persistence.co_members import SqlAlchemyCoMemberDirectory
from adapters.persistence.models import (
    NotebookMembershipModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    UserModel,
)
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_notebook_snapshots_integration import (
    _content,
    _kitchen,
    _personal,
    _recipe,
    _register,
    _use,
)

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _candidates(client: TestClient):
    return client.get("/recipes/share-candidates")


def _share(client: TestClient, recipe_id: UUID, recipient: UUID):
    return client.post(f"/recipes/{recipe_id}/share", json={"recipient_user_id": str(recipient)})


def _set_default(db: Session, user_id: UUID, notebook_id: UUID) -> None:
    db.execute(
        update(UserModel).where(UserModel.id == user_id).values(default_notebook_id=notebook_id)
    )
    db.flush()


@pytest.fixture
def setup(client: TestClient, db_session: Session):
    ana_id, ana_token = _register(client, "ana")
    bea_id, bea_token = _register(client, "bea")
    cy_id, _ = _register(client, "cy")  # a stranger: shares nothing with Ana
    kitchen_id = _kitchen(db_session, ana_id, members=(bea_id,))
    ana_personal = _personal(db_session, ana_id)
    recipe_id = _recipe(db_session, ana_personal, ana_id, "Lentil soup")
    bea_default = _personal(db_session, bea_id, "bea's Notebook", names=("tomato",))
    _set_default(db_session, bea_id, bea_default)
    _use(client, ana_token)
    return {
        "ana": (ana_id, ana_token),
        "bea": (bea_id, bea_token),
        "cy": cy_id,
        "kitchen": kitchen_id,
        "recipe": recipe_id,
        "bea_default": bea_default,
    }


def test_candidates_list_kitchen_peer_and_skip_stranger(client: TestClient, setup) -> None:
    response = _candidates(client)
    assert response.status_code == 200, response.text
    ids = [c["user_id"] for c in response.json()["candidates"]]
    assert str(setup["bea"][0]) in ids
    assert str(setup["cy"]) not in ids
    assert str(setup["ana"][0]) not in ids


def test_candidates_include_notebook_only_peer_once(
    client: TestClient, db_session: Session, setup
) -> None:
    cy_id = setup["cy"]
    shared = _personal(db_session, setup["ana"][0], "shared with cy")
    db_session.add(NotebookMembershipModel(notebook_id=shared, user_id=cy_id, role="member"))
    # Bea is in the kitchen and also in this notebook: she must appear once.
    db_session.add(
        NotebookMembershipModel(notebook_id=shared, user_id=setup["bea"][0], role="member")
    )
    db_session.flush()
    _use(client, setup["ana"][1])
    ids = [c["user_id"] for c in _candidates(client).json()["candidates"]]
    assert str(cy_id) in ids
    assert ids.count(str(setup["bea"][0])) == 1


def test_candidates_empty_when_nobody_shared(client: TestClient, db_session: Session) -> None:
    solo_id, solo_token = _register(client, "solo")
    _personal(db_session, solo_id, "solo's Notebook")
    _use(client, solo_token)
    assert _candidates(client).json() == {"candidates": []}


def test_share_copies_into_recipient_default_notebook(
    client: TestClient, db_session: Session, setup
) -> None:
    bea_id = setup["bea"][0]
    before = _content(db_session, setup["recipe"])

    response = _share(client, setup["recipe"], bea_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"recipe_id", "recipient_alias", "notebook_id"}
    assert body["notebook_id"] == str(setup["bea_default"])
    copy = db_session.scalars(
        select(RecipeModel)
        .where(RecipeModel.id == UUID(body["recipe_id"]))
        .execution_options(populate_existing=True)
    ).one()
    assert copy.notebook_id == setup["bea_default"]
    assert copy.author_id == bea_id
    assert copy.copied_from_recipe_id is None
    assert _content(db_session, setup["recipe"]) == before


def test_share_normalizes_names_to_recipient_catalog(
    client: TestClient, db_session: Session, setup
) -> None:
    db_session.execute(
        update(RecipeIngredientModel)
        .where(RecipeIngredientModel.recipe_id == setup["recipe"])
        .where(RecipeIngredientModel.position == 0)
        .values(name="tomatoes")
    )
    db_session.flush()

    body = _share(client, setup["recipe"], setup["bea"][0]).json()

    names = db_session.scalars(
        select(RecipeIngredientModel.name).where(
            RecipeIngredientModel.recipe_id == UUID(body["recipe_id"])
        )
    ).all()
    assert "tomato" in names
    assert "tomatoes" not in names
    source_names = db_session.scalars(
        select(RecipeIngredientModel.name).where(RecipeIngredientModel.recipe_id == setup["recipe"])
    ).all()
    assert "tomatoes" in source_names


def test_share_to_stranger_is_404_without_alias(client: TestClient, setup) -> None:
    response = _share(client, setup["recipe"], setup["cy"])
    assert response.status_code == 404
    assert response.json()["code"] == "recipient_not_found"
    assert "cy" not in response.text.lower()


def test_share_unknown_recipient_matches_stranger_response(client: TestClient, setup) -> None:
    stranger = _share(client, setup["recipe"], setup["cy"])
    missing = _share(client, setup["recipe"], UUID("00000000-0000-0000-0000-00000000dead"))
    assert missing.status_code == stranger.status_code == 404
    assert missing.json()["code"] == stranger.json()["code"]


def test_share_unreadable_recipe_is_404(client: TestClient, db_session: Session, setup) -> None:
    # Cy's own recipe is not readable by Ana.
    cy_id = setup["cy"]
    cy_notebook = _personal(db_session, cy_id, "cy's Notebook")
    cy_recipe = _recipe(db_session, cy_notebook, cy_id, "Cy's secret")
    response = _share(client, cy_recipe, setup["bea"][0])
    assert response.status_code == 404
    assert response.json()["code"] == "recipe_not_found"


def test_share_to_self_is_409(client: TestClient, setup) -> None:
    response = _share(client, setup["recipe"], setup["ana"][0])
    assert response.status_code == 409
    assert response.json()["code"] == "share_self"


def test_share_requires_session(client: TestClient, setup) -> None:
    client.cookies.clear()
    assert _share(client, setup["recipe"], setup["bea"][0]).status_code == 401
    assert _candidates(client).status_code == 401


def test_recipient_sees_copy_and_can_edit_without_touching_source(
    client: TestClient, db_session: Session, setup
) -> None:
    before = _content(db_session, setup["recipe"])
    copy_id = UUID(_share(client, setup["recipe"], setup["bea"][0]).json()["recipe_id"])

    _use(client, setup["bea"][1])
    listed = client.get(f"/notebooks/{setup['bea_default']}/recipes")
    assert listed.status_code == 200, listed.text
    assert str(copy_id) in listed.text

    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == copy_id).values(title="Bea's version")
    )
    db_session.flush()
    assert _content(db_session, setup["recipe"]) == before
    assert db_session.get(RecipeModel, setup["recipe"]).title == "Lentil soup"
    assert db_session.get(RecipeModel, copy_id).title == "Bea's version"
    assert db_session.get(NotebookModel, setup["bea_default"]) is not None


def test_co_member_directory_excludes_caller(db_session: Session, setup) -> None:
    directory = SqlAlchemyCoMemberDirectory(db_session)
    ids = {c.user_id for c in directory.list_co_members(setup["ana"][0])}
    assert setup["bea"][0] in ids
    assert setup["ana"][0] not in ids
    assert directory.is_co_member(setup["ana"][0], setup["bea"][0])
    assert not directory.is_co_member(setup["ana"][0], setup["cy"])
    assert not directory.is_co_member(setup["ana"][0], setup["ana"][0])


def test_recipient_deletes_copy_and_source_stays(
    client: TestClient, db_session: Session, setup
) -> None:
    copy_id = UUID(_share(client, setup["recipe"], setup["bea"][0]).json()["recipe_id"])

    _use(client, setup["bea"][1])
    response = client.delete(f"/recipes/{copy_id}")
    assert response.status_code in (200, 204), response.text
    db_session.expire_all()
    assert db_session.get(RecipeModel, copy_id) is None
    assert db_session.get(RecipeModel, setup["recipe"]) is not None
