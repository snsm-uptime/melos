"""Save a picture recipe over HTTP with Postgres (spec 041 T058, T059, FR-019 to FR-027).

Requires DATABASE_URL. Skips when unset. Nothing here calls the assistant.
"""

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from adapters.persistence.models import RecipeModel, SourceModel
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_recipe_save_integration import _body, _personal_notebook, _register

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

WEBP_URI = "data:image/webp;base64," + base64.b64encode(b"RIFF\x00\x00\x00\x00WEBP").decode()


def _photo_body(notebook_id: str, **overrides) -> dict:
    body = _body(notebook_id, source_text="", source_kind="photo", preview_image=WEBP_URI)
    body.update(overrides)
    return body


def test_a_photo_draft_stores_a_photo_source_with_no_url_and_no_text(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "photo_save@example.com")
    response = client.post("/recipes", json=_photo_body(_personal_notebook(client)))
    assert response.status_code in (200, 201), response.text
    recipe_id = response.json()["recipe"]["id"]
    source = db_session.scalars(
        select(SourceModel)
        .join(RecipeModel, RecipeModel.source_id == SourceModel.id)
        .where(RecipeModel.id == recipe_id)
    ).one()
    assert source.type == "photo"
    assert source.url is None
    assert source.raw_text is None
    recipe = db_session.get(RecipeModel, recipe_id)
    assert recipe is not None and recipe.preview_image_base64 == WEBP_URI


def test_a_photo_without_a_preview_stores_none(client: TestClient, db_session: Session) -> None:
    _register(client, "photo_nopreview@example.com")
    body = _photo_body(_personal_notebook(client), preview_image=None)
    response = client.post("/recipes", json=body)
    assert response.status_code in (200, 201), response.text
    recipe = db_session.get(RecipeModel, response.json()["recipe"]["id"])
    assert recipe is not None and recipe.preview_image_base64 is None


def test_the_detail_of_a_photo_recipe_has_a_null_source_and_the_preview(
    client: TestClient,
) -> None:
    _register(client, "photo_detail@example.com")
    recipe_id = client.post("/recipes", json=_photo_body(_personal_notebook(client))).json()[
        "recipe"
    ]["id"]
    detail = client.get(f"/recipes/{recipe_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["source"] is None
    assert body["preview_image"] == WEBP_URI


def test_a_photo_with_typed_text_is_refused(client: TestClient) -> None:
    _register(client, "photo_text@example.com")
    body = _photo_body(_personal_notebook(client), source_text="pasted")
    assert client.post("/recipes", json=body).status_code == 422


def test_a_non_webp_photo_preview_is_refused(client: TestClient) -> None:
    _register(client, "photo_jpeg@example.com")
    jpeg = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0").decode()
    body = _photo_body(_personal_notebook(client), preview_image=jpeg)
    assert client.post("/recipes", json=body).status_code == 422


def test_a_non_member_cannot_read_the_preview_of_a_photo_recipe(client: TestClient) -> None:
    _register(client, "photo_owner@example.com")
    recipe_id = client.post("/recipes", json=_photo_body(_personal_notebook(client))).json()[
        "recipe"
    ]["id"]
    client.post("/auth/sign-out")
    _register(client, f"photo_stranger_{uuid4().hex[:6]}@example.com")
    assert client.get(f"/recipes/{recipe_id}").status_code == 404


def test_deleting_a_photo_recipe_deletes_its_source(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "photo_delete@example.com")
    recipe_id = client.post("/recipes", json=_photo_body(_personal_notebook(client))).json()[
        "recipe"
    ]["id"]
    source_id = db_session.get(RecipeModel, recipe_id).source_id
    assert client.delete(f"/recipes/{recipe_id}").status_code in (200, 204)
    db_session.expire_all()
    assert db_session.get(SourceModel, source_id) is None
