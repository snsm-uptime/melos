"""Copy a personal recipe into a kitchen over HTTP with Postgres (spec 069).

Skips when DATABASE_URL is unset. Accounts, kitchens and recipes are invented.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import (
    EmbeddingJobModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeEditLockModel,
    RecipeModel,
)
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_notebook_snapshots_integration import (
    _catalog,
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


def _post(client: TestClient, kitchen_id: UUID, recipe_id: UUID, on_repeat: str = "ask"):
    return client.post(
        f"/notebooks/kitchens/{kitchen_id}/recipe-copies",
        json={"source_recipe_id": str(recipe_id), "on_repeat": on_repeat},
    )


def _row(db: Session, recipe_id: UUID) -> RecipeModel:
    return db.scalars(
        select(RecipeModel)
        .where(RecipeModel.id == recipe_id)
        .execution_options(populate_existing=True)
    ).one()


@pytest.fixture
def setup(client: TestClient, db_session: Session):
    ana_id, ana_token = _register(client, "ana")
    bea_id, bea_token = _register(client, "bea")
    kitchen_id = _kitchen(db_session, ana_id, members=(bea_id,))
    personal = _personal(db_session, ana_id)
    recipe_id = _recipe(db_session, personal, ana_id, "Lentil soup")
    db_session.execute(
        update(RecipeModel)
        .where(RecipeModel.id == recipe_id)
        .values(preview_image_base64="data:image/png;base64,AAAA")
    )
    db_session.flush()
    _use(client, ana_token)
    return {
        "ana": (ana_id, ana_token),
        "bea": (bea_id, bea_token),
        "kitchen": kitchen_id,
        "personal": personal,
        "recipe": recipe_id,
    }


def test_new_copy_in_own_kitchen_notebook(client: TestClient, db_session: Session, setup) -> None:
    ana_id, _ = setup["ana"]
    before = _content(db_session, setup["recipe"])

    response = _post(client, setup["kitchen"], setup["recipe"])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["overwritten"] is False
    copy_id = UUID(body["recipe_id"])
    notebook = db_session.get(NotebookModel, UUID(body["notebook_id"]))
    assert notebook is not None
    assert notebook.kitchen_id == setup["kitchen"]
    assert notebook.owner_user_id == ana_id
    assert body["notebook_name"] == notebook.name

    copy = _content(db_session, copy_id)
    for field in ("title", "base_servings", "servings_estimated", "lines", "steps", "source"):
        assert copy[field] == before[field], field
    assert copy["author_id"] == ana_id
    row = _row(db_session, copy_id)
    assert row.preview_image_base64 == "data:image/png;base64,AAAA"
    assert row.copied_from_recipe_id == setup["recipe"]
    assert row.source_id != _row(db_session, setup["recipe"]).source_id
    assert {"rice", "onion", "salt"} <= set(_catalog(db_session, notebook.id))
    assert db_session.scalar(
        select(EmbeddingJobModel.recipe_id).where(EmbeddingJobModel.recipe_id == copy_id)
    )
    # The original is unchanged.
    assert _content(db_session, setup["recipe"]) == before

    # Never exposed in a read.
    detail = client.get(f"/recipes/{copy_id}")
    assert detail.status_code == 200, detail.text
    assert "copied_from_recipe_id" not in detail.text


def test_repeat_asks_then_adds_or_overwrites(
    client: TestClient, db_session: Session, setup
) -> None:
    first = _post(client, setup["kitchen"], setup["recipe"]).json()

    repeat = _post(client, setup["kitchen"], setup["recipe"])
    assert repeat.status_code == 409
    assert repeat.json()["code"] == "recipe_already_in_kitchen"
    assert repeat.json()["existing_recipe_id"] == first["recipe_id"]
    assert repeat.json()["notebook_name"] == first["notebook_name"]

    second = _post(client, setup["kitchen"], setup["recipe"], "add")
    assert second.status_code == 201
    assert second.json()["recipe_id"] != first["recipe_id"]

    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == setup["recipe"]).values(title="Red lentil soup")
    )
    db_session.flush()
    # Bea, a member of the personal notebook, overwrites: the latest copy keeps its id and
    # notebook, and Bea becomes its author.
    bea_id, bea_token = setup["bea"]
    db_session.add(
        NotebookMembershipModel(notebook_id=setup["personal"], user_id=bea_id, role="member")
    )
    db_session.flush()
    _use(client, bea_token)
    over = _post(client, setup["kitchen"], setup["recipe"], "overwrite")
    assert over.status_code == 200, over.text
    assert over.json()["overwritten"] is True
    assert over.json()["recipe_id"] == second.json()["recipe_id"]
    assert over.json()["notebook_id"] == second.json()["notebook_id"]
    row = _row(db_session, UUID(second.json()["recipe_id"]))
    assert row.title == "Red lentil soup"
    assert row.author_id == bea_id
    assert _row(db_session, UUID(first["recipe_id"])).title == "Lentil soup"
    assert _row(db_session, setup["recipe"]).title == "Red lentil soup"


def test_overwrite_refused_while_copy_is_edited(
    client: TestClient, db_session: Session, setup
) -> None:
    _ana_id, ana_token = setup["ana"]
    first = _post(client, setup["kitchen"], setup["recipe"]).json()
    _bea_id, bea_token = setup["bea"]
    _use(client, bea_token)
    lock = client.post(f"/recipes/{first['recipe_id']}/edit-lock")
    assert lock.status_code == 200, lock.text
    _use(client, ana_token)

    response = _post(client, setup["kitchen"], setup["recipe"], "overwrite")

    assert response.status_code == 409
    assert response.json()["code"] == "recipe_locked"
    assert db_session.scalar(
        select(RecipeEditLockModel.recipe_id).where(
            RecipeEditLockModel.recipe_id == UUID(first["recipe_id"])
        )
    )


def test_copy_and_original_are_independent(client: TestClient, db_session: Session, setup) -> None:
    copy_id = UUID(_post(client, setup["kitchen"], setup["recipe"]).json()["recipe_id"])
    copy_before = _content(db_session, copy_id)

    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == setup["recipe"]).values(title="Changed")
    )
    db_session.flush()
    assert _content(db_session, copy_id) == copy_before

    assert client.delete(f"/recipes/{copy_id}").status_code in (200, 204)
    assert _row(db_session, setup["recipe"]).title == "Changed"


def test_deleting_source_clears_link_and_readd_is_new(
    client: TestClient, db_session: Session, setup
) -> None:
    copy_id = UUID(_post(client, setup["kitchen"], setup["recipe"]).json()["recipe_id"])
    db_session.delete(_row(db_session, setup["recipe"]))
    db_session.flush()
    assert _row(db_session, copy_id).copied_from_recipe_id is None

    gone = _post(client, setup["kitchen"], setup["recipe"])
    assert gone.status_code == 404
    assert gone.json()["code"] == "recipe_not_found"

    # A new personal recipe added after its earlier copy was deleted gets no warning.
    again = _recipe(db_session, setup["personal"], setup["ana"][0], "Pea soup")
    first = UUID(_post(client, setup["kitchen"], again).json()["recipe_id"])
    db_session.delete(_row(db_session, first))
    db_session.flush()
    assert _post(client, setup["kitchen"], again).status_code == 201


def test_outsider_and_unreadable_source_get_404(
    client: TestClient, db_session: Session, setup
) -> None:
    _bea_id, bea_token = setup["bea"]
    _use(client, bea_token)
    # Bea is in the kitchen but cannot read Ana's personal notebook (SC-004).
    response = _post(client, setup["kitchen"], setup["recipe"])
    assert response.status_code == 404
    assert response.json()["code"] == "recipe_not_found"

    _carl_id, carl_token = _register(client, "carl")
    _use(client, carl_token)
    response = _post(client, setup["kitchen"], setup["recipe"])
    assert response.status_code == 404
    assert response.json()["code"] == "kitchen_not_found"

    # A kitchen recipe is not a personal source.
    _use(client, setup["ana"][1])
    copy_id = UUID(_post(client, setup["kitchen"], setup["recipe"]).json()["recipe_id"])
    assert _post(client, setup["kitchen"], copy_id).status_code == 404
    assert _post(client, setup["kitchen"], uuid4()).status_code == 404


def test_archived_kitchen_and_bad_body(client: TestClient, db_session: Session, setup) -> None:
    assert _post(client, setup["kitchen"], setup["recipe"], "replace").status_code == 422
    db_session.execute(
        update(KitchenModel).where(KitchenModel.id == setup["kitchen"]).values(is_archived=True)
    )
    db_session.flush()
    response = _post(client, setup["kitchen"], setup["recipe"])
    assert response.json()["code"] == "kitchen_archived"
    assert response.status_code in (403, 409)
