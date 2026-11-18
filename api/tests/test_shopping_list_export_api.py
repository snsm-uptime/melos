"""The shopping list export over HTTP (spec 024, contracts/shopping-list-export-api.md).

Requires DATABASE_URL with migrations at head. Skips when unset.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_shopping_list_integration import (
    _list,
    bread_and_pancakes,
    save_cart,
)

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _export(client: TestClient, kitchen_id: str, list_id: str, fmt: str | None = "markdown"):  # noqa: ANN202
    query = "" if fmt is None else f"?format={fmt}"
    return client.get(f"/kitchens/{kitchen_id}/shopping-lists/{list_id}/export{query}")


def _saved(ana: TestClient, kitchen_id: str, bread: str, pancakes: str) -> str:
    save_cart(ana, kitchen_id, [bread, pancakes], servings=4)
    return ana.get(_list(kitchen_id)).json()["list_id"]


def test_a_bad_or_missing_format_is_400(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    list_id = _saved(ana, kitchen_id, bread, pancakes)
    for fmt in ("docx", None):
        response = _export(ana, kitchen_id, list_id, fmt)
        assert response.status_code == 400
        assert response.json() == {"detail": "format must be markdown or pdf"}


def test_markdown_is_the_renderer_output_for_the_saved_list(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    list_id = _saved(ana, kitchen_id, bread, pancakes)

    response = _export(ana, kitchen_id, list_id, "markdown")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    today = datetime.now(UTC).date().isoformat()
    # No language is saved for this member, so the default Spanish headings apply (spec 063).
    assert response.text == (
        f"## Lista de compras ({today})\n"
        "\n"
        "- egg — 2 (Pancakes)\n"
        "- flour — 1 cup + 3 tbsp (Bread, Pancakes)\n"
    )


def test_pdf_is_an_attachment_named_with_the_day(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    list_id = _saved(ana, kitchen_id, bread, pancakes)

    response = _export(ana, kitchen_id, list_id, "pdf")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    today = datetime.now(UTC).date().isoformat()
    assert response.headers["content-disposition"] == (
        f'attachment; filename="shopping-list-{today}.pdf"'
    )
    assert response.content.startswith(b"%PDF-1.4")


def test_a_closed_list_exports_with_its_closing_date(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    list_id = _saved(ana, kitchen_id, bread, pancakes)
    closed = ana.post(_list(kitchen_id) + "/done", json={"list_id": list_id})
    assert closed.status_code == 200, closed.text
    closing = closed.json()["closing_date"]

    response = _export(ana, kitchen_id, list_id, "pdf")

    assert response.status_code == 200, response.text
    assert response.headers["content-disposition"] == (
        f'attachment; filename="shopping-list-{closing}.pdf"'
    )


def test_a_non_member_and_an_unknown_id_get_the_same_404(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    list_id = _saved(people.as_("ana"), kitchen_id, bread, pancakes)
    people.register("cat")
    cat = people.as_("cat")

    outsider = _export(cat, kitchen_id, list_id, "markdown")
    unknown = _export(cat, kitchen_id, str(uuid4()), "markdown")

    assert outsider.status_code == 404 and unknown.status_code == 404
    assert outsider.json() == unknown.json() == {"detail": "Not found"}


def test_a_pdf_failure_is_500_and_the_markdown_copy_still_works(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    people, kitchen_id, _nb, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    list_id = _saved(ana, kitchen_id, bread, pancakes)

    def broken(_document: object) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr("api.routes.shopping_list.render_pdf", broken)

    failed = _export(ana, kitchen_id, list_id, "pdf")
    copied = _export(ana, kitchen_id, list_id, "markdown")

    assert failed.status_code == 500
    assert failed.json() == {"detail": "PDF could not be created"}
    assert copied.status_code == 200
