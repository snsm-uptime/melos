"""Catalog management over HTTP with Postgres (spec 043).

Skips when DATABASE_URL is unset. Accounts, kitchens, notebooks and recipes are invented. Recipes
are saved through POST /recipes, so a saved line goes through the same name resolution as a
capture.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    IngredientModel,
    IngredientPlaceModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    UserModel,
)
from adapters.persistence.notebooks import SqlAlchemyNotebookRepository
from adapters.persistence.places import SqlAlchemyPlaceRepository
from api.deps import get_pair_suggester, get_recipe_extraction
from application.catalog_manage import MergeCommand, MergeService
from application.recipe_extraction import Draft, RecipeExtraction
from domain.recipe_draft import DraftRecipe, IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.catalog_manage_fakes import FakePairSuggester
from tests.integration_db import database_url
from tests.test_carts_integration import _home
from tests.test_notebook_integration import _race
from tests.test_shopping_list_integration import measured, save_cart

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _save(
    client: TestClient, notebook_id: str, title: str, language: str, lines: list[dict]
) -> str:
    response = client.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": notebook_id,
            "title": title,
            "base_servings": 4,
            "ingredient_lines": lines,
            "steps": ["Cook."],
            "language": language,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["recipe"]["id"]


def _default(client: TestClient) -> str:
    response = client.get("/notebooks/default")
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _set_language(db: Session, user_id: UUID, language: str) -> None:
    db.execute(update(UserModel).where(UserModel.id == user_id).values(language=language))
    db.flush()


def _lines(db: Session, recipe_id: str) -> list[str]:
    return list(
        db.scalars(
            select(RecipeIngredientModel.name)
            .where(RecipeIngredientModel.recipe_id == UUID(recipe_id))
            .order_by(RecipeIngredientModel.position)
        )
    )


def _orphan_lines(db: Session, notebook_ids: list[str]) -> list[str]:
    """SC-005: lines whose name is not a kept name of their notebook's catalog."""
    ids = [UUID(n) for n in notebook_ids]
    kept = select(IngredientModel.name).where(
        IngredientModel.notebook_id == RecipeModel.notebook_id
    )
    return list(
        db.scalars(
            select(RecipeIngredientModel.name)
            .join(RecipeModel, RecipeModel.id == RecipeIngredientModel.recipe_id)
            .where(RecipeModel.notebook_id.in_(ids), RecipeIngredientModel.name.not_in(kept))
        )
    )


@pytest.fixture
def home(client: TestClient, db_session: Session):
    """Ana owns a kitchen Ben belongs to; each kitchen and personal book has both onions."""
    people, kitchen_id, kitchen_notebook = _home(client, db_session)
    ana = people.as_("ana")
    personal = _default(ana)
    recipes = {
        "sopa": _save(ana, kitchen_notebook, "Sopa", "es", [measured("cebolla", 1, "unit")]),
        "soup": _save(ana, kitchen_notebook, "Soup", "en", [measured("onion", 2, "unit")]),
        "tortilla": _save(ana, personal, "Tortilla", "es", [measured("cebolla", 1, "unit")]),
        "curry": _save(ana, personal, "Curry", "en", [measured("onion", 1, "unit")]),
    }
    return {
        "people": people,
        "kitchen": kitchen_id,
        "kitchen_notebook": kitchen_notebook,
        "personal": personal,
        "recipes": recipes,
    }


def _merge_onions(client: TestClient, home) -> dict:
    preview = client.post(
        "/catalog/merge-preview",
        json={"from_notebook_id": home["kitchen_notebook"], "merged": "cebolla", "kept": "onion"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    merged = client.post(
        "/catalog/merge",
        json={
            "merged": body["merged"],
            "kept": body["kept"],
            "merged_language": "es",
            "kept_language": "en",
            "notebook_ids": [n["notebook_id"] for n in body["notebooks"]],
        },
    )
    assert merged.status_code == 200, merged.text
    return {"preview": body, "result": merged.json()}


# --- User Story 1: merge (T026) -----------------------------------------------------------------


def test_a_merge_reaches_the_kitchen_and_the_personal_notebook(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    done = _merge_onions(ana, home)

    preview = done["preview"]
    assert (preview["merged_language"], preview["kept_language"]) == ("es", "en")
    counts = {n["notebook_id"]: n["recipe_count"] for n in preview["notebooks"]}
    assert counts == {home["kitchen_notebook"]: 1, home["personal"]: 1}
    assert done["result"]["skipped"] == []
    assert {m["notebook_id"] for m in done["result"]["merged"]} == set(counts)

    recipes = home["recipes"]
    for key in ("sopa", "soup", "tortilla", "curry"):
        assert _lines(db_session, recipes[key]) == ["onion"]
    sopa = ana.get(f"/recipes/{recipes['sopa']}").json()
    assert sopa["language"] == "es"
    assert sopa["ingredient_lines"][0]["name"] == "onion"
    assert sopa["ingredient_lines"][0]["shown_name"] == "cebolla"
    soup = ana.get(f"/recipes/{recipes['soup']}").json()
    assert soup["ingredient_lines"][0]["shown_name"] == "onion"

    catalog = ana.get(f"/notebooks/{home['kitchen_notebook']}/catalog").json()
    onion = next(i for i in catalog["ingredients"] if i["name"] == "onion")
    assert onion["language"] == "en"
    assert onion["variants"] == [{"name": "cebolla", "language": "es"}]
    assert onion["recipe_count"] == 2
    assert "cebolla" not in [i["name"] for i in catalog["ingredients"]]
    assert _orphan_lines(db_session, [home["kitchen_notebook"], home["personal"]]) == []


def test_after_a_merge_a_saved_cebolla_line_takes_the_kept_name(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    _merge_onions(ana, home)
    recipe_id = _save(
        ana, home["kitchen_notebook"], "Guiso", "es", [measured("Cebolla", 1, "unit")]
    )
    assert _lines(db_session, recipe_id) == ["onion"]
    names = SqlAlchemyIngredientCatalog(db_session).names_for_notebook(
        UUID(home["kitchen_notebook"])
    )
    assert "cebolla" not in names


def test_a_capture_with_cebollas_lists_a_change_and_adds_no_name(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    _merge_onions(ana, home)
    draft = DraftRecipe(
        title="Sopa de cebolla",
        base_servings=4,
        servings_estimated=False,
        ingredient_lines=(
            IngredientLine(
                "cebolla", False, 2.0, "unit", text_name="cebollas", catalog_match="cebolla"
            ),
        ),
        steps=("Cocinar.",),
        language="es",
    )
    use_case = RecipeExtraction(FakeRecipeExtractor(script=Draft(recipe=draft)))
    client.app.dependency_overrides[get_recipe_extraction] = lambda: use_case
    try:
        response = ana.post(
            f"/notebooks/{home['kitchen_notebook']}/captures/text", json={"text": "Sopa..."}
        )
    finally:
        client.app.dependency_overrides.pop(get_recipe_extraction, None)
    assert response.status_code == 200, response.text
    body = response.json()["draft"]
    assert body["language"] == "es"
    assert body["changes"] == [{"line": 0, "from": "cebollas", "to": "cebolla"}]
    assert body["ingredient_lines"][0]["match"] == {"kind": "matched", "entry": "cebolla"}


def test_the_shopping_list_has_one_line_in_each_viewer_s_language(
    client: TestClient, db_session: Session, home
) -> None:
    people = home["people"]
    ana = people.as_("ana")
    _merge_onions(ana, home)
    _set_language(db_session, people.ids["ana"], "en")
    _set_language(db_session, people.ids["ben"], "es")
    recipes = home["recipes"]
    save_cart(ana, home["kitchen"], [recipes["sopa"], recipes["soup"]], servings=4)

    english = people.as_("ana").get(f"/kitchens/{home['kitchen']}/shopping-list").json()
    spanish = people.as_("ben").get(f"/kitchens/{home['kitchen']}/shopping-list").json()

    assert [(ln["name"], ln["kept_name"]) for ln in english["lines"]] == [("onion", "onion")]
    assert [(ln["name"], ln["kept_name"]) for ln in spanish["lines"]] == [("cebolla", "onion")]
    assert english["lines"][0]["amounts"] == [{"quantity": "3", "unit": "unit"}]


def test_a_place_set_on_onion_applies_to_the_spanish_view(
    client: TestClient, db_session: Session, home
) -> None:
    people = home["people"]
    ana = people.as_("ana")
    _merge_onions(ana, home)
    _set_language(db_session, people.ids["ben"], "es")
    db_session.add(
        IngredientPlaceModel(user_id=people.ids["ben"], name="onion", default_key="farmers_market")
    )
    db_session.flush()
    save_cart(ana, home["kitchen"], [home["recipes"]["sopa"]], servings=4)
    line = people.as_("ben").get(f"/kitchens/{home['kitchen']}/shopping-list").json()["lines"][0]
    assert line["name"] == "cebolla"
    assert line["place"]["key"] == "farmers_market"


def test_a_place_on_the_merged_name_moves_to_the_kept_name(
    client: TestClient, db_session: Session, home
) -> None:
    people = home["people"]
    db_session.add(
        IngredientPlaceModel(user_id=people.ids["ana"], name="cebolla", default_key="butcher")
    )
    db_session.flush()
    _merge_onions(people.as_("ana"), home)
    choices = SqlAlchemyPlaceRepository(db_session).choices(people.ids["ana"])
    assert choices["onion"].key == "butcher"


def test_no_access_is_404_and_read_only_is_403(
    client: TestClient, db_session: Session, home
) -> None:
    people = home["people"]
    people.register("cy")
    cy = people.as_("cy")
    assert cy.get(f"/notebooks/{home['kitchen_notebook']}/catalog").status_code == 404
    preview = cy.post(
        "/catalog/merge-preview",
        json={"from_notebook_id": home["kitchen_notebook"], "merged": "cebolla", "kept": "onion"},
    )
    assert preview.status_code == 404

    db_session.execute(
        update(KitchenModel)
        .where(KitchenModel.id == UUID(home["kitchen"]))
        .values(is_archived=True)
    )
    db_session.flush()
    ben = people.as_("ben")
    catalog = ben.get(f"/notebooks/{home['kitchen_notebook']}/catalog")
    assert catalog.status_code == 200 and catalog.json()["can_write"] is False
    rename = ben.patch(
        f"/notebooks/{home['kitchen_notebook']}/catalog/onion", json={"new_name": "onions"}
    )
    assert rename.status_code == 403
    assert rename.json()["code"] == "catalog_read_only"


def test_a_second_merge_of_the_same_names_reports_a_skip(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    _merge_onions(ana, home)
    again = ana.post(
        "/catalog/merge",
        json={
            "merged": "cebolla",
            "kept": "onion",
            "notebook_ids": [home["kitchen_notebook"]],
        },
    )
    assert again.json() == {
        "merged": [],
        "skipped": [{"notebook_id": home["kitchen_notebook"], "reason": "name_changed"}],
    }


def test_two_merges_at_once_leave_one_merge_and_one_skip(engine: Engine) -> None:
    """FR-015: under the row locks the second merge finds the name gone and skips."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, notebook_id, recipe_id = uuid4(), uuid4(), uuid4()
    with factory() as setup:
        setup.add(UserModel(id=owner, email=f"race_{owner}@example.com", password_hash="x"))
        setup.flush()
        setup.add(NotebookModel(id=notebook_id, name="race notebook"))
        setup.flush()
        setup.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
        setup.add_all(
            [
                IngredientModel(notebook_id=notebook_id, name="onion"),
                IngredientModel(notebook_id=notebook_id, name="cebolla"),
            ]
        )
        setup.add(
            RecipeModel(
                id=recipe_id, notebook_id=notebook_id, title="Sopa", base_servings=2, language="es"
            )
        )
        setup.flush()
        setup.add(
            RecipeIngredientModel(
                recipe_id=recipe_id, position=0, name="cebolla", quantity=1, unit="unit"
            )
        )
        setup.commit()

    outcomes: list[tuple] = []

    def merge(session: Session) -> UUID:
        service = MergeService(
            SqlAlchemyNotebookRepository(session),
            SqlAlchemyIngredientCatalog(session),
            SqlAlchemyPlaceRepository(session),
        )
        result = service.execute(
            MergeCommand(owner, "cebolla", "onion", "es", "en", (notebook_id,))
        )
        outcomes.append((result.merged, result.skipped))
        return notebook_id

    try:
        _, errors = _race(factory, merge)
        assert errors == []
        merged = [o for o in outcomes if o[0]]
        skipped = [o for o in outcomes if o[1]]
        assert len(merged) == 1 and len(skipped) == 1
        assert skipped[0][1] == ((notebook_id, "name_changed"),)
        with factory() as check:
            assert _lines(check, str(recipe_id)) == ["onion"]
    finally:
        with factory() as cleanup:
            cleanup.execute(delete(NotebookModel).where(NotebookModel.id == notebook_id))
            cleanup.execute(delete(UserModel).where(UserModel.id == owner))
            cleanup.commit()


# --- User Story 2: rename (T036) ----------------------------------------------------------------


def test_a_rename_rewrites_lines_and_refuses_an_existing_or_blank_name(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    notebook = home["kitchen_notebook"]
    recipe_id = _save(ana, notebook, "Salsa", "en", [measured("tomatoe", 2, "unit")])
    _save(ana, notebook, "Salad", "en", [measured("tomato", 1, "unit")])

    taken = ana.patch(f"/notebooks/{notebook}/catalog/tomatoe", json={"new_name": "tomatoes"})
    assert taken.status_code == 409
    assert taken.json()["code"] == "name_exists" and taken.json()["existing"] == "tomato"
    blank = ana.patch(f"/notebooks/{notebook}/catalog/tomatoe", json={"new_name": "  "})
    assert blank.status_code == 422 and blank.json()["code"] == "name_blank"

    renamed = ana.patch(
        f"/notebooks/{notebook}/catalog/tomatoe", json={"new_name": "  Plum  Tomato "}
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "plum tomato"
    assert renamed.json()["recipes_changed"] == 1
    assert _lines(db_session, recipe_id) == ["plum tomato"]

    gone = ana.patch(f"/notebooks/{notebook}/catalog/tomatoe", json={"new_name": "roma"})
    assert gone.status_code == 409 and gone.json()["code"] == "name_changed"


def test_setting_a_language_without_renaming(client: TestClient, home) -> None:
    ana = home["people"].as_("ana")
    notebook = home["kitchen_notebook"]
    response = ana.patch(
        f"/notebooks/{notebook}/catalog/onion", json={"new_name": "onion", "language": "en"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["language"] == "en" and response.json()["recipes_changed"] == 0


# --- User Story 3: delete (T043) ----------------------------------------------------------------


def test_an_unused_name_is_deleted_and_a_used_one_refused_with_its_count(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    notebook = home["kitchen_notebook"]
    db_session.add(IngredientModel(notebook_id=UUID(notebook), name="saffron"))
    db_session.flush()

    assert ana.delete(f"/notebooks/{notebook}/catalog/saffron").status_code == 204
    used = ana.delete(f"/notebooks/{notebook}/catalog/onion")
    assert used.status_code == 409
    assert used.json()["code"] == "name_in_use" and used.json()["recipe_count"] == 1
    gone = ana.delete(f"/notebooks/{notebook}/catalog/saffron")
    assert gone.status_code == 409 and gone.json()["code"] == "name_changed"


# --- User Story 4: split (T053) -----------------------------------------------------------------


def test_a_split_keeps_every_shown_word_and_splits_the_list_again(
    client: TestClient, db_session: Session, home
) -> None:
    people = home["people"]
    ana = people.as_("ana")
    _merge_onions(ana, home)
    notebook = home["kitchen_notebook"]
    recipes = home["recipes"]

    split = ana.post(f"/notebooks/{notebook}/catalog/onion/split", json={"other_name": "cebolla"})

    assert split.status_code == 200, split.text
    assert split.json()["recipes_changed"] == 1
    assert (
        ana.get(f"/recipes/{recipes['sopa']}").json()["ingredient_lines"][0]["shown_name"]
        == "cebolla"
    )
    assert (
        ana.get(f"/recipes/{recipes['soup']}").json()["ingredient_lines"][0]["shown_name"]
        == "onion"
    )
    save_cart(ana, home["kitchen"], [recipes["sopa"], recipes["soup"]], servings=4)
    lines = ana.get(f"/kitchens/{home['kitchen']}/shopping-list").json()["lines"]
    assert sorted(ln["kept_name"] for ln in lines) == ["cebolla", "onion"]
    # A later "cebolla" line matches the split-out name, not "onion".
    recipe_id = _save(ana, notebook, "Caldo", "es", [measured("cebolla", 1, "unit")])
    assert _lines(db_session, recipe_id) == ["cebolla"]


# --- User Story 5: pairs (T048) -----------------------------------------------------------------


def test_pairs_drop_invented_names_remember_dismissals_and_report_the_model(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    notebook = home["kitchen_notebook"]
    db_session.add_all(
        [
            IngredientModel(notebook_id=UUID(notebook), name="garlic"),
            IngredientModel(notebook_id=UUID(notebook), name="ajo"),
        ]
    )
    db_session.flush()
    fake = FakePairSuggester([("garlic", "ajo"), ("onion", "cebolla"), ("salt", "sal")])
    client.app.dependency_overrides[get_pair_suggester] = lambda: fake
    try:
        first = ana.post(f"/notebooks/{notebook}/catalog/pair-suggestions")
        assert first.status_code == 200, first.text
        assert first.json()["pairs"] == [
            {"en": "garlic", "es": "ajo"},
            {"en": "onion", "es": "cebolla"},
        ]
        dismissed = ana.post(
            f"/notebooks/{notebook}/catalog/pair-dismissals", json={"en": "garlic", "es": "ajo"}
        )
        assert dismissed.status_code == 204
        again = ana.post(f"/notebooks/{notebook}/catalog/pair-suggestions").json()
        assert again["pairs"] == [{"en": "onion", "es": "cebolla"}]

        fake.unavailable = True
        down = ana.post(f"/notebooks/{notebook}/catalog/pair-suggestions")
        assert down.status_code == 503 and down.json()["code"] == "ai_unavailable"

        db_session.execute(
            update(KitchenModel)
            .where(KitchenModel.id == UUID(home["kitchen"]))
            .values(is_archived=True)
        )
        db_session.flush()
        fake.unavailable = False
        assert ana.post(f"/notebooks/{notebook}/catalog/pair-suggestions").status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_pair_suggester, None)


# --- recipe language (T013, T041) ---------------------------------------------------------------


def test_a_detected_language_is_applied_or_dismissed(
    client: TestClient, db_session: Session, home
) -> None:
    ana = home["people"].as_("ana")
    recipe_id = home["recipes"]["soup"]
    _merge_onions(ana, home)
    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == UUID(recipe_id)).values(proposed_language="es")
    )
    db_session.flush()
    assert ana.get(f"/recipes/{recipe_id}").json()["proposed_language"] == "es"

    applied = ana.patch(f"/recipes/{recipe_id}/language", json={"language": "es"})
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert (body["language"], body["proposed_language"]) == ("es", None)
    assert body["ingredient_lines"][0]["shown_name"] == "cebolla"

    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == UUID(recipe_id)).values(proposed_language="en")
    )
    db_session.flush()
    dismissed = ana.patch(f"/recipes/{recipe_id}/language", json={"language": None}).json()
    assert (dismissed["language"], dismissed["proposed_language"]) == ("es", None)


# --- copy into a kitchen (T061) -----------------------------------------------------------------


def test_a_copy_into_the_kitchen_keeps_a_merge_merged(
    client: TestClient, db_session: Session, home
) -> None:
    """FR-008: a copy matches against the target's other names, so "cebolla" stays merged."""
    ana = home["people"].as_("ana")
    merged = ana.post(
        "/catalog/merge",
        json={
            "merged": "cebolla",
            "kept": "onion",
            "merged_language": "es",
            "kept_language": "en",
            "notebook_ids": [home["kitchen_notebook"]],
        },
    )
    assert merged.status_code == 200, merged.text
    # The personal notebook was not merged: its tortilla still says "cebolla".
    copied = ana.post(
        f"/notebooks/kitchens/{home['kitchen']}/recipe-copies",
        json={"source_recipe_id": home["recipes"]["tortilla"], "on_repeat": "add"},
    )
    assert copied.status_code in (200, 201), copied.text
    body = copied.json()
    assert _lines(db_session, body["recipe_id"]) == ["onion"]
    names = SqlAlchemyIngredientCatalog(db_session).names_for_notebook(UUID(body["notebook_id"]))
    assert "cebolla" not in names


def test_the_places_view_shows_other_names_under_their_ingredient(
    client: TestClient, db_session: Session, home
) -> None:
    """Plan R8 (T064): after the merge, "cebolla" shows under "onion", not as its own row."""
    ana = home["people"].as_("ana")
    _merge_onions(ana, home)
    items = {i["name"]: i for i in ana.get("/me/ingredient-places").json()["items"]}
    assert items["onion"]["other_names"] == ["cebolla"]
    assert "cebolla" not in items
