"""A person's places over HTTP with Postgres (spec 070 US2, US3, contracts/places.md).

Requires DATABASE_URL with migrations at head. Skips when unset.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from adapters.persistence.models import KitchenMembershipModel
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session
from tests.integration_db import database_url
from tests.test_carts_integration import People, _home
from tests.test_shopping_list_integration import _list, measured, recipe, save_cart

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

FARMERS = {"kind": "default", "key": "farmers_market"}


def _custom(place_id: str) -> dict:
    return {"kind": "custom", "id": place_id}


def _places(client: TestClient) -> dict[str, dict]:
    response = client.get("/me/ingredient-places")
    assert response.status_code == 200, response.text
    return {item["name"]: item["place"] for item in response.json()["items"]}


def _set(client: TestClient, name: str, place: dict):  # noqa: ANN202
    return client.put("/me/ingredient-places", json={"name": name, "place": place})


def test_place_crud_and_refusals(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _nb = _home(client, db_session)
    ana = people.as_("ana")
    assert ana.get("/me/places").json() == {
        "defaults": [
            "supermarket",
            "farmers_market",
            "butcher",
            "fish_market",
            "bakery",
            "pharmacy",
            "other",
        ],
        "custom": [],
    }
    added = ana.post("/me/places", json={"name": " Asian  market "})
    assert added.status_code == 201, added.text
    place = added.json()
    assert place["name"] == "Asian market"

    for name, status, code in [
        ("", 422, "place_name_invalid"),
        ("x" * 41, 422, "place_name_invalid"),
        ("asian MARKET", 409, "place_name_taken"),
        ("Supermercado", 409, "place_name_taken"),
    ]:
        refused = ana.post("/me/places", json={"name": name})
        assert (refused.status_code, refused.json()["code"]) == (status, code), name

    renamed = ana.patch(f"/me/places/{place['id']}", json={"name": "Japanese market"})
    assert renamed.json()["name"] == "Japanese market"

    ben = people.as_("ben")
    assert ben.patch(f"/me/places/{place['id']}", json={"name": "Mine"}).status_code == 404
    assert ben.delete(f"/me/places/{place['id']}").status_code == 404
    stolen = _set(ben, "tomato", _custom(place["id"]))
    assert (stolen.status_code, stolen.json()["code"]) == (422, "invalid_place")
    blank = _set(ben, "  ", FARMERS)
    assert (blank.status_code, blank.json()["code"]) == (422, "ingredient_name_invalid")


def test_catalog_page_and_delete_falls_back(client: TestClient, db_session: Session) -> None:
    people, _kitchen, nb = _home(client, db_session)
    ana = people.as_("ana")
    recipe(ana, nb, "Salad", [measured("tomato", 2, "unit"), measured("miso", 1, "tbsp")])
    personal = ana.get("/notebooks/default").json()["id"]
    recipe(ana, personal, "Toast", [measured("bread", 1, "unit")])

    places = _places(ana)
    assert {"tomato", "miso", "bread"} <= set(places)
    assert places["tomato"] == {"kind": "default", "key": "supermarket", "id": None, "name": None}
    # Ana's personal notebook is not Ben's to see.
    assert "bread" not in _places(people.as_("ben"))

    ana = people.as_("ana")
    asian = ana.post("/me/places", json={"name": "Asian market"}).json()
    assert _set(ana, "Tomato", FARMERS).json()["name"] == "tomato"
    assert _set(ana, "miso", _custom(asian["id"])).status_code == 200
    places = _places(ana)
    assert places["tomato"]["key"] == "farmers_market"
    assert places["miso"]["name"] == "Asian market"

    assert ana.delete(f"/me/places/{asian['id']}").status_code == 204
    assert _places(ana)["miso"]["key"] == "supermarket"


def test_copy_from_a_member_is_a_snapshot(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb = _home(client, db_session)
    ana = people.as_("ana")
    asian = ana.post("/me/places", json={"name": "Asian market"}).json()
    _set(ana, "miso", _custom(asian["id"]))

    ben = people.as_("ben")
    sources = ben.get("/me/place-sources").json()["items"]
    assert [s["user_id"] for s in sources] == [str(people.ids["ana"])]
    copied = ben.post("/me/places/copy", json={"source_user_id": str(people.ids["ana"])})
    assert copied.status_code == 200, copied.text
    assert [p["name"] for p in copied.json()["custom"]] == ["Asian market"]
    assert _places(ben)["miso"]["name"] == "Asian market"

    people.as_("ana").patch(f"/me/places/{asian['id']}", json={"name": "Japanese market"})
    assert _places(people.as_("ben"))["miso"]["name"] == "Asian market"

    # Once Ben leaves the only kitchen they share, Ana is no longer a source; his copy stays.
    db_session.execute(
        delete(KitchenMembershipModel).where(
            KitchenMembershipModel.kitchen_id == UUID(kitchen),
            KitchenMembershipModel.user_id == people.ids["ben"],
        )
    )
    db_session.flush()
    ben = people.as_("ben")
    assert ben.get("/me/place-sources").json()["items"] == []
    refused = ben.post("/me/places/copy", json={"source_user_id": str(people.ids["ana"])})
    assert refused.status_code == 404
    assert _places(ben)["miso"]["name"] == "Asian market"


def test_a_stranger_is_not_a_source(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _nb = _home(client, db_session)
    others = People(client)
    others.register("cleo")
    cleo = others.as_("cleo")
    refused = cleo.post("/me/places/copy", json={"source_user_id": str(people.ids["ana"])})
    assert refused.status_code == 404


# --- US3: places on the list, for the viewer -------------------------------------------------


def test_each_member_sees_their_own_places(client: TestClient, db_session: Session) -> None:
    people, kitchen, nb = _home(client, db_session)
    ana = people.as_("ana")
    salad = recipe(ana, nb, "Salad", [measured("tomato", 2, "unit"), measured("rice", 1, "cup")])
    save_cart(ana, kitchen, [salad])
    _set(ana, "tomato", FARMERS)
    asian = ana.post("/me/places", json={"name": "Asian market"}).json()
    _set(ana, "rice", _custom(asian["id"]))

    mine = {ln["name"]: ln["place"] for ln in ana.get(_list(kitchen)).json()["lines"]}
    assert mine["tomato"]["key"] == "farmers_market"
    assert mine["rice"] == {
        "kind": "custom",
        "key": None,
        "id": asian["id"],
        "name": "Asian market",
    }
    assert ana.get(_list(kitchen)).json()["custom_places"] == [asian]

    ben = people.as_("ben")
    body = ben.get(_list(kitchen)).json()
    assert {ln["place"]["key"] for ln in body["lines"]} == {"supermarket"}
    assert body["custom_places"] == []


def test_a_hand_item_with_a_place(client: TestClient, db_session: Session) -> None:
    people, kitchen, _nb = _home(client, db_session)
    ana = people.as_("ana")
    added = ana.post(
        _list(kitchen) + "/items",
        json={"name": "Dish soap", "place": {"kind": "default", "key": "pharmacy"}},
    )
    assert added.status_code == 201, added.text
    soap = added.json()["hand_items"][0]
    assert soap["place"]["key"] == "pharmacy"
    assert _places(ana)["dish soap"]["key"] == "pharmacy"

    bad = ana.post(
        _list(kitchen) + "/items", json={"name": "glue", "place": {"kind": "default", "key": "x"}}
    )
    assert (bad.status_code, bad.json()["code"]) == (422, "invalid_place")
    names = [i["name"] for i in ana.get(_list(kitchen)).json()["hand_items"]]
    assert names == ["dish soap"]


def test_a_closed_list_uses_the_viewers_current_places(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, nb = _home(client, db_session)
    ana = people.as_("ana")
    salad = recipe(ana, nb, "Salad", [measured("tomato", 2, "unit")])
    save_cart(ana, kitchen, [salad])
    list_id = ana.get(_list(kitchen)).json()["list_id"]
    assert ana.post(_list(kitchen) + "/done", json={"list_id": list_id}).status_code == 200
    _set(ana, "tomato", FARMERS)
    read = ana.get(f"/kitchens/{kitchen}/shopping-lists/{list_id}").json()
    assert read["lines"][0]["place"]["key"] == "farmers_market"


def test_ingredient_page_lists_recipes_and_last_use(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, notebook = _home(client, db_session)
    ana = people.as_("ana")
    soup = recipe(
        ana, notebook, "Soup", [measured("tomato", 2, "unit"), measured("Tomato", 1, "unit")]
    )
    recipe(ana, notebook, "Salad", [measured("tomato", 1, "unit")])
    items = {i["name"]: i for i in ana.get("/me/ingredient-places").json()["items"]}
    # A recipe that lists the name twice counts once (order is covered by the unit test).
    assert sorted(r["title"] for r in items["tomato"]["recipes"]) == ["Salad", "Soup"]
    assert soup in {r["id"] for r in items["tomato"]["recipes"]}
    assert items["tomato"]["last_used_at"] is not None


def test_copy_keeps_the_persons_own_places_and_choices(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _nb = _home(client, db_session)
    ana = people.as_("ana")
    asian = ana.post("/me/places", json={"name": "Asian market"}).json()
    ana_deli = ana.post("/me/places", json={"name": "deli"}).json()
    _set(ana, "miso", _custom(asian["id"]))
    _set(ana, "ham", _custom(ana_deli["id"]))
    _set(ana, "tomato", FARMERS)

    ben = people.as_("ben")
    deli = ben.post("/me/places", json={"name": "Deli"}).json()
    _set(ben, "tomato", _custom(deli["id"]))
    copied = ben.post("/me/places/copy", json={"source_user_id": str(people.ids["ana"])})
    assert copied.status_code == 200, copied.text
    assert sorted(p["name"] for p in copied.json()["custom"]) == ["Asian market", "Deli"]
    places = _places(ben)
    assert places["tomato"]["id"] == deli["id"]  # his own choice stays
    assert places["ham"]["id"] == deli["id"]  # her "deli" is his "Deli"
    assert places["miso"]["name"] == "Asian market"
