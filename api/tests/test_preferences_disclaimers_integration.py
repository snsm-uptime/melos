"""The "disclaimers" option over HTTP with Postgres (spec 041, contracts/disclaimers-preference).

Requires DATABASE_URL. Skips when unset.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.integration_db import claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

PASSWORD = "password1"


def _register(client: TestClient, email: str) -> None:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    claim_alias(client, email)


def test_get_me_returns_a_boolean_disclaimers_default_true(client: TestClient) -> None:
    _register(client, "disc_get@example.com")
    body = client.get("/auth/me").json()
    assert body["disclaimers"] is True


def test_patch_turns_it_off_and_a_later_get_agrees_after_sign_in(client: TestClient) -> None:
    email = "disc_persist@example.com"
    _register(client, email)
    patched = client.patch("/auth/me", json={"disclaimers": False})
    assert patched.status_code == 200, patched.text
    assert patched.json()["disclaimers"] is False
    assert client.get("/auth/me").json()["disclaimers"] is False

    client.post("/auth/sign-out")
    response = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    assert client.get("/auth/me").json()["disclaimers"] is False


@pytest.mark.parametrize("value", ["no", 1])
def test_a_non_boolean_is_refused(client: TestClient, value) -> None:  # noqa: ANN001
    _register(client, f"disc_bad_{abs(hash(str(value)))}@example.com")
    response = client.patch("/auth/me", json={"disclaimers": value})
    assert response.status_code == 422


def test_sending_only_a_language_leaves_disclaimers_unchanged(client: TestClient) -> None:
    _register(client, "disc_lang@example.com")
    client.patch("/auth/me", json={"disclaimers": False})
    response = client.patch("/auth/me", json={"language": "es"})
    assert response.status_code == 200, response.text
    assert response.json()["disclaimers"] is False
