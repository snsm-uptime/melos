"""The per-person vocabulary and the typed unit check, over HTTP (spec 055 contracts/units-api)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from adapters.persistence.models import UnitModel
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"
TEN = ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"]


def _register(client: TestClient, email: str) -> None:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)


def _keep(client: TestClient, *words: str) -> None:
    notebook_id = client.get("/notebooks/default").json()["id"]
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": "Beans",
            "base_servings": 4,
            "ingredient_lines": [
                {"name": f"thing {word}", "quantity": 1, "unit": word} for word in words
            ],
            "steps": ["Open."],
            "keep_units": list(words),
        },
    )
    assert response.status_code == 201, response.text


def _check(client: TestClient, word: str):
    return client.post("/recipe-vocabulary/unit-check", json={"word": word})


def test_vocabulary_is_the_ten_then_the_person_s_units_sorted(client: TestClient) -> None:
    _register(client, "vocab_order@example.com")
    assert client.get("/recipe-vocabulary").json()["units"] == TEN
    _keep(client, "sobre", "lata")
    assert client.get("/recipe-vocabulary").json()["units"] == [*TEN, "lata", "sobre"]


def test_vocabulary_is_per_person(client: TestClient) -> None:
    _register(client, "vocab_one@example.com")
    _keep(client, "lata")
    client.post("/auth/sign-out")
    _register(client, "vocab_two@example.com")
    assert client.get("/recipe-vocabulary").json()["units"] == TEN


@pytest.mark.parametrize(
    ("word", "answer"),
    [
        ("tazas", {"outcome": "known", "unit": "cup"}),
        ("Latas", {"outcome": "known", "unit": "lata"}),
        ("latta", {"outcome": "known", "unit": "lata"}),
        ("Sobres", {"outcome": "new", "unit": "sobre"}),
        ("", {"outcome": "not_a_unit", "unit": None}),
        ("123", {"outcome": "not_a_unit", "unit": None}),
        ("!!", {"outcome": "not_a_unit", "unit": None}),
        ("x" * 33, {"outcome": "not_a_unit", "unit": None}),
        ("cdaas", {"outcome": "not_a_unit", "unit": None}),
        ("grande", {"outcome": "not_a_unit", "unit": None}),
    ],
)
def test_unit_check_answers(client: TestClient, word: str, answer: dict) -> None:
    _register(client, "check_words@example.com")
    _keep(client, "lata")
    response = _check(client, word)
    assert response.status_code == 200, response.text
    assert response.json() == answer


def test_unit_check_stores_nothing(client: TestClient, db_session: Session) -> None:
    _register(client, "check_store@example.com")
    _check(client, "zumbido")
    assert db_session.scalar(select(UnitModel).where(UnitModel.name == "zumbido")) is None


def test_unit_check_refuses_a_word_over_200_characters(client: TestClient) -> None:
    _register(client, "check_long@example.com")
    assert _check(client, "x" * 201).status_code == 422


def test_unit_check_needs_a_signed_in_person(client: TestClient) -> None:
    assert _check(client, "lata").status_code == 401
