"""The kitchen shopping list over HTTP with Postgres (spec 023).

Requires DATABASE_URL (Compose db or CI Postgres 16) with migrations at head. Skips when unset.
Recipes are saved through POST /recipes and carts through the cart edit routes (spec 022), so the
whole path from stored ingredient lines to the response is exercised.
"""

from __future__ import annotations

import time
from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import (
    CartEditLockModel,
    CartItemModel,
    CartModel,
    IngredientModel,
    RecipeIngredientModel,
    RecipeModel,
)
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_carts_integration import People, _home

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _cart(kitchen_id: str, path: str = "") -> str:
    return f"/kitchens/{kitchen_id}/cart{path}"


def _list(kitchen_id: str) -> str:
    return f"/kitchens/{kitchen_id}/shopping-list"


def measured(name: str, quantity: float, unit: str, size: str | None = None) -> dict:
    line: dict = {"name": name, "quantity": quantity, "unit": unit}
    if size:
        line["size"] = size
    return line


def vague(name: str, note: str) -> dict:
    return {"name": name, "vague": True, "note": note}


def recipe(
    client: TestClient, notebook_id: str, title: str, lines: list[dict], base: int = 4
) -> str:
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": title,
            "base_servings": base,
            "ingredient_lines": lines,
            "steps": ["Cook."],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def save_cart(
    client: TestClient,
    kitchen_id: str,
    recipe_ids: list[str],
    people: int | None = None,
    meals: int = 1,
) -> None:
    assert client.post(_cart(kitchen_id, "/edit")).status_code == 200
    put = client.put(
        _cart(kitchen_id, "/draft"),
        json={"people": people, "items": [{"recipe_id": r, "meals": meals} for r in recipe_ids]},
    )
    assert put.status_code == 200, put.text
    assert client.post(_cart(kitchen_id, "/save")).status_code == 200


def shown(body: dict) -> list[tuple[str, str | None, tuple[tuple[str, str], ...]]]:
    return [
        (ln["name"], ln["size"], tuple((a["quantity"], a["unit"]) for a in ln["amounts"]))
        for ln in body["lines"]
    ]


def bread_and_pancakes(
    client: TestClient, db_session: Session
) -> tuple[People, str, str, str, str]:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    bread = recipe(ana, notebook_id, "Bread", [measured("flour", 3, "tbsp")])
    pancakes = recipe(
        ana, notebook_id, "Pancakes", [measured("flour", 1, "cup"), measured("egg", 2, "unit")]
    )
    return people, kitchen_id, notebook_id, bread, pancakes


# --- US1 ------------------------------------------------------------------------------------


def test_combined_scaled_list_has_the_contract_shape(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [bread, pancakes], people=4)  # base 4 → factor 1

    response = ana.get(_list(kitchen_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"is_empty", "lines", "your_call"}
    assert body["is_empty"] is False and body["your_call"] == []
    assert shown(body) == [
        ("egg", None, (("2", "unit"),)),
        ("flour", None, (("1", "cup"), ("3", "tbsp"))),
    ]
    flour = body["lines"][1]
    assert set(flour) == {"name", "kind", "size", "amounts", "recipes"}
    assert flour["kind"] == "volume"
    assert body["lines"][0]["kind"] == "count"
    assert set(flour["recipes"][0]) == {"recipe_id", "title"}


def test_amounts_follow_people_and_meals(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [pancakes], people=3)  # factor 3/4: 1.5 eggs → 2
    assert shown(ana.get(_list(kitchen_id)).json()) == [
        ("egg", None, (("2", "unit"),)),
        ("flour", None, (("0.75", "cup"),)),
    ]
    save_cart(ana, kitchen_id, [pancakes], people=3, meals=2)  # factor 3/2: 3 eggs, 1.5 cup
    assert shown(ana.get(_list(kitchen_id)).json()) == [
        ("egg", None, (("3", "unit"),)),
        ("flour", None, (("1.5", "cup"),)),
    ]


def test_rice_in_two_kinds_and_onions_by_size(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = recipe(
        ana, notebook_id, "A", [measured("rice", 200, "g"), measured("onion", 1, "unit", "large")]
    )
    b = recipe(
        ana, notebook_id, "B", [measured("rice", 1, "cup"), measured("onion", 1, "unit", "large")]
    )
    c = recipe(ana, notebook_id, "C", [measured("onion", 1, "unit", "small")])
    save_cart(ana, kitchen_id, [a, b, c], people=4)

    body = ana.get(_list(kitchen_id)).json()

    assert shown(body) == [
        ("onion", "large", (("2", "unit"),)),
        ("onion", "small", (("1", "unit"),)),
        ("rice", None, (("200", "g"),)),
        ("rice", None, (("1", "cup"),)),
    ]
    assert [ln["kind"] for ln in body["lines"]][2:] == ["mass", "volume"]


def test_preparation_is_ignored(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = recipe(ana, notebook_id, "A", [{**measured("onion", 1, "unit"), "preparation": "chopped"}])
    b = recipe(ana, notebook_id, "B", [{**measured("onion", 1, "unit"), "preparation": "sliced"}])
    save_cart(ana, kitchen_id, [a, b], people=4)
    assert shown(ana.get(_list(kitchen_id)).json()) == [("onion", None, (("2", "unit"),))]


def test_non_member_and_unknown_kitchen_get_the_same_404(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    people.register("cat")
    outsider = people.as_("cat").get(_list(kitchen_id))
    unknown = people.as_("cat").get(_list(str(uuid4())))
    assert outsider.status_code == 404 and unknown.status_code == 404
    assert outsider.json() == unknown.json()
    assert outsider.json()["code"] == "kitchen_not_found"


def test_an_empty_cart_is_empty(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _ = _home(client, db_session)
    body = people.as_("ana").get(_list(kitchen_id)).json()
    assert body == {"is_empty": True, "lines": [], "your_call": []}


def test_archived_kitchen_can_still_be_read(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _, bread, _ = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [bread], people=4)
    assert ana.post(f"/kitchens/{kitchen_id}/archive").status_code == 200
    response = people.as_("ben").get(_list(kitchen_id))
    assert response.status_code == 200
    assert shown(response.json()) == [("flour", None, (("3", "tbsp"),))]


def test_reading_the_list_changes_nothing(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, _, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [bread, pancakes], people=4)

    def snapshot() -> tuple:
        db_session.expire_all()
        return (
            db_session.execute(
                select(
                    CartItemModel.recipe_id, CartItemModel.meals, CartItemModel.added_at
                ).order_by(CartItemModel.recipe_id)
            ).all(),
            db_session.execute(
                select(RecipeModel.id, RecipeModel.cart_add_count).order_by(RecipeModel.id)
            ).all(),
            db_session.scalar(select(func.count()).select_from(IngredientModel)),
            db_session.scalar(select(func.count()).select_from(RecipeIngredientModel)),
            db_session.scalar(select(func.count()).select_from(CartEditLockModel)),
            db_session.scalar(select(CartModel.updated_at)),
        )

    before = snapshot()
    for name in ("ana", "ben"):
        assert people.as_(name).get(_list(kitchen_id)).status_code == 200
    assert snapshot() == before


def test_a_cart_of_100_recipes_with_20_lines_reads_fast_in_few_statements(
    client: TestClient, db_session: Session, engine: Engine
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    ids = [uuid4() for _ in range(100)]
    db_session.add_all(
        RecipeModel(id=rid, notebook_id=UUID(notebook_id), title=f"R{n}", base_servings=4)
        for n, rid in enumerate(ids)
    )
    cart_id = uuid4()
    db_session.add(CartModel(id=cart_id, kitchen_id=UUID(kitchen_id)))
    db_session.flush()
    db_session.add_all(CartItemModel(cart_id=cart_id, recipe_id=rid, meals=1) for rid in ids)
    units = ("g", "cup", "tbsp", "unit")
    db_session.add_all(
        RecipeIngredientModel(
            recipe_id=rid,
            position=position,
            name=f"item{position % 12}",
            quantity=1 + position,
            unit=units[position % 4],
        )
        for rid in ids
        for position in range(20)
    )
    db_session.flush()

    statements: list[str] = []

    def count(conn, cursor, statement, *args) -> None:  # noqa: ANN001
        if "cart" in statement or "recipe" in statement:
            statements.append(statement)

    connection = db_session.connection()
    event.listen(connection, "before_cursor_execute", count)
    try:
        started = time.perf_counter()
        response = ana.get(_list(kitchen_id))
        elapsed = time.perf_counter() - started
    finally:
        event.remove(connection, "before_cursor_execute", count)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lines"] and all(ln["recipes"] for ln in body["lines"])
    # cart + items, recipe facts, live lock reads, one query for every ingredient line.
    assert len(statements) <= 10, statements
    assert elapsed < 1.0, elapsed


# --- US2 ------------------------------------------------------------------------------------


def test_chips_list_the_recipes_of_a_line_in_cart_order(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [bread, pancakes], people=4)

    body = ana.get(_list(kitchen_id)).json()

    by_name = {ln["name"]: ln for ln in body["lines"]}
    assert by_name["flour"]["recipes"] == [
        {"recipe_id": bread, "title": "Bread"},
        {"recipe_id": pancakes, "title": "Pancakes"},
    ]
    assert by_name["egg"]["recipes"] == [{"recipe_id": pancakes, "title": "Pancakes"}]


def test_two_recipes_with_the_same_title_are_two_chips(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    first = recipe(ana, notebook_id, "Soup", [measured("salt", 1, "tsp")])
    second = recipe(ana, notebook_id, "Soup", [measured("salt", 1, "tsp")])
    save_cart(ana, kitchen_id, [first, second], people=4)

    chips = ana.get(_list(kitchen_id)).json()["lines"][0]["recipes"]

    assert [c["title"] for c in chips] == ["Soup", "Soup"]
    assert {c["recipe_id"] for c in chips} == {first, second}


# --- US3 ------------------------------------------------------------------------------------


def test_vague_lines_go_to_your_call_once_per_ingredient(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = recipe(ana, notebook_id, "A", [vague("salt", "a pinch"), vague("butter", "to taste")])
    b = recipe(ana, notebook_id, "B", [vague("salt", "to taste"), measured("butter", 100, "g")])
    save_cart(ana, kitchen_id, [a, b], people=4)

    body = ana.get(_list(kitchen_id)).json()

    assert shown(body) == [("butter", None, (("100", "g"),))]
    assert body["lines"][0]["recipes"] == [{"recipe_id": b, "title": "B"}]
    assert [(e["name"], e["notes"]) for e in body["your_call"]] == [
        ("butter", ["to taste"]),
        ("salt", ["a pinch", "to taste"]),
    ]
    salt = body["your_call"][1]
    assert set(salt) == {"name", "notes", "recipes"}
    assert [r["title"] for r in salt["recipes"]] == ["A", "B"]
    butter = body["your_call"][0]
    assert [r["title"] for r in butter["recipes"]] == ["A"]


def test_vague_lines_are_not_scaled_by_people(client: TestClient, db_session: Session) -> None:
    people, kitchen_id, notebook_id = _home(client, db_session)
    ana = people.as_("ana")
    a = recipe(ana, notebook_id, "A", [vague("pepper", "a pinch")])
    save_cart(ana, kitchen_id, [a], people=40, meals=9)
    body = ana.get(_list(kitchen_id)).json()
    assert body["lines"] == []
    assert body["your_call"][0]["notes"] == ["a pinch"]


# --- US4 ------------------------------------------------------------------------------------


def _draft(client: TestClient, kitchen_id: str, recipe_ids: list[str], people: int | None) -> None:
    put = client.put(
        _cart(kitchen_id, "/draft"),
        json={"people": people, "items": [{"recipe_id": r, "meals": 1} for r in recipe_ids]},
    )
    assert put.status_code == 200, put.text


def test_the_editor_sees_the_draft_and_another_member_the_saved_cart(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, _, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [pancakes], people=4)
    assert ana.post(_cart(kitchen_id, "/edit")).status_code == 200
    _draft(ana, kitchen_id, [pancakes], people=8)

    mine = shown(people.as_("ana").get(_list(kitchen_id)).json())
    theirs = shown(people.as_("ben").get(_list(kitchen_id)).json())

    assert mine == [("egg", None, (("4", "unit"),)), ("flour", None, (("2", "cup"),))]
    assert theirs == [("egg", None, (("2", "unit"),)), ("flour", None, (("1", "cup"),))]


def test_discard_returns_the_editor_to_the_saved_list_and_save_shows_to_everyone(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, _, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [pancakes], people=4)

    ana.post(_cart(kitchen_id, "/edit"))
    _draft(ana, kitchen_id, [pancakes], people=8)
    assert ana.delete(_cart(kitchen_id, "/edit")).status_code == 204
    assert shown(ana.get(_list(kitchen_id)).json())[0] == ("egg", None, (("2", "unit"),))

    ana.post(_cart(kitchen_id, "/edit"))
    _draft(ana, kitchen_id, [pancakes], people=8)
    assert ana.post(_cart(kitchen_id, "/save")).status_code == 200
    for name in ("ana", "ben"):
        body = people.as_(name).get(_list(kitchen_id)).json()
        assert shown(body) == [("egg", None, (("4", "unit"),)), ("flour", None, (("2", "cup"),))]


def test_changing_people_changes_every_amount_and_counts_round_up_again(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, _, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    expected = {
        2: (("1", "unit"), ("0.5", "cup")),
        3: (("2", "unit"), ("0.75", "cup")),  # 1.5 eggs → 2
        4: (("2", "unit"), ("1", "cup")),
        8: (("4", "unit"), ("2", "cup")),
    }
    for count, (egg, flour) in expected.items():
        save_cart(ana, kitchen_id, [pancakes], people=count)
        assert shown(ana.get(_list(kitchen_id)).json()) == [
            ("egg", None, (egg,)),
            ("flour", None, (flour,)),
        ], count


def test_an_edited_recipe_shows_its_new_ingredients_on_the_next_read(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, _, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [pancakes], people=4)
    assert shown(ana.get(_list(kitchen_id)).json())[1] == ("flour", None, (("1", "cup"),))

    db_session.execute(
        update(RecipeIngredientModel)
        .where(RecipeIngredientModel.recipe_id == UUID(pancakes))
        .where(RecipeIngredientModel.name == "flour")
        .values(quantity=3)
    )
    db_session.flush()

    assert shown(ana.get(_list(kitchen_id)).json())[1] == ("flour", None, (("3", "cup"),))


def test_a_recipe_deleted_from_the_cart_never_reaches_the_list(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, bread, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    save_cart(ana, kitchen_id, [bread, pancakes], people=4)
    assert ana.delete(f"/recipes/{pancakes}").status_code in (200, 204)
    assert shown(ana.get(_list(kitchen_id)).json()) == [("flour", None, (("3", "tbsp"),))]


def test_reading_the_list_never_keeps_the_editors_lock_alive(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen_id, _, _, pancakes = bread_and_pancakes(client, db_session)
    ana = people.as_("ana")
    ana.post(_cart(kitchen_id, "/edit"))
    _draft(ana, kitchen_id, [pancakes], people=4)

    def last_active() -> object:
        db_session.expire_all()
        return db_session.scalar(select(CartEditLockModel.last_active_at))

    before = last_active()
    for name in ("ana", "ben", "ana"):
        assert people.as_(name).get(_list(kitchen_id)).status_code == 200
    assert last_active() == before
    # The editor still holds the lock, so the other member is still refused.
    refused = people.as_("ben").post(_cart(kitchen_id, "/edit"))
    assert refused.status_code == 409 and refused.json()["code"] == "cart_locked"
