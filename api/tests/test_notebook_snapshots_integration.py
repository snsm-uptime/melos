"""Notebook snapshots over HTTP with Postgres (spec 035). Skips when DATABASE_URL is unset.

The `client` fixture shares the test's session. Tests for concurrency and for the rollback of a
failed add use the `engine` fixture with their own sessions and clean up after themselves.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    CartItemModel,
    IngredientModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeEditLockModel,
    RecipeIngredientModel,
    RecipeModel,
    SessionModel,
    SourceModel,
    StepModel,
    UserModel,
)
from adapters.persistence.notebooks import SqlAlchemyNotebookRepository
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import SqlAlchemyKitchenRepository
from application.notebooks import AddNotebookSnapshotCommand, AddNotebookSnapshotService
from domain.recipe import EditedRecipe
from domain.recipe_draft import IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import claim_alias, database_url
from tests.test_notebook_integration import _cleanup, _race

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)

COOKIE = "melos_session"


def _register(client: TestClient, name: str) -> tuple[UUID, str]:
    email = f"{name}_{uuid4().hex[:6]}@example.com"
    client.cookies.clear()
    response = client.post("/auth/register", json={"email": email, "password": "password1"})
    assert response.status_code == 201, response.text
    claim_alias(client, email)
    return UUID(client.get("/auth/me").json()["user_id"]), client.cookies[COOKIE]


def _use(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE, token)


def _kitchen(db: Session, owner: UUID, *, members: tuple[UUID, ...] = ()) -> UUID:
    kitchen_id = uuid4()
    db.add(KitchenModel(id=kitchen_id, name="Home", owner_id=owner))
    db.flush()
    db.add(KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=owner, role="owner"))
    for member in members:
        db.add(
            KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=member, role="member")
        )
    db.flush()
    return kitchen_id


def _personal(
    db: Session, owner: UUID, name: str = "ana's Notebook", *, names: tuple[str, ...] = ()
) -> UUID:
    notebook_id = uuid4()
    db.add(NotebookModel(id=notebook_id, name=name))
    db.flush()
    db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
    for catalog_name in names:
        db.add(IngredientModel(notebook_id=notebook_id, name=catalog_name))
    db.flush()
    return notebook_id


def _recipe(
    db: Session,
    notebook_id: UUID,
    author: UUID | None,
    title: str = "Tomato rice",
    *,
    created_at: datetime | None = None,
    url: str | None = "https://example.com/rice",
    line_count: int = 3,
) -> UUID:
    """A recipe with a measured line, a sized line and a vague line, in that order."""
    source_id = uuid4()
    db.add(
        SourceModel(
            id=source_id,
            user_id=author,
            type="url" if url else "text",
            url=url,
            raw_text="Invented recipe text.",
        )
    )
    db.flush()
    recipe_id = uuid4()
    db.add(
        RecipeModel(
            id=recipe_id,
            notebook_id=notebook_id,
            author_id=author,
            source_id=source_id,
            title=title,
            base_servings=4,
            servings_estimated=True,
            save_key=uuid4(),
            cart_add_count=7,
            **({"created_at": created_at} if created_at else {}),
        )
    )
    db.flush()
    db.add_all(
        [
            RecipeIngredientModel(
                recipe_id=recipe_id,
                position=0,
                name="rice",
                quantity=Decimal("1.5"),
                unit="cup",
                preparation="rinsed",
            ),
            RecipeIngredientModel(
                recipe_id=recipe_id, position=1, name="onion", quantity=2, unit="unit", size="large"
            ),
            RecipeIngredientModel(
                recipe_id=recipe_id, position=2, name="salt", vague_note="a pinch"
            ),
        ][:line_count]
    )
    db.add_all(
        [
            StepModel(recipe_id=recipe_id, position=0, text="Rinse."),
            StepModel(recipe_id=recipe_id, position=1, text="Cook."),
        ]
    )
    db.flush()
    return recipe_id


def _add(
    client: TestClient,
    kitchen_id: UUID,
    source_id: UUID,
    *,
    key: UUID | None = None,
    confirm: bool = False,
):
    return client.post(
        f"/notebooks/kitchens/{kitchen_id}/snapshots",
        json={
            "source_notebook_id": str(source_id),
            "snapshot_key": str(key or uuid4()),
            "confirm_repeat": confirm,
        },
    )


def _added(client: TestClient, kitchen_id: UUID, source_id: UUID, **kwargs) -> UUID:
    response = _add(client, kitchen_id, source_id, **kwargs)
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _in_kitchen(db: Session, kitchen_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(NotebookModel)
            .where(NotebookModel.kitchen_id == kitchen_id)
        )
        or 0
    )


def _recipes_of(db: Session, notebook_id: UUID) -> list[RecipeModel]:
    return list(
        db.scalars(
            select(RecipeModel)
            .where(RecipeModel.notebook_id == notebook_id)
            .order_by(RecipeModel.created_at, RecipeModel.title)
            .execution_options(populate_existing=True)
        ).all()
    )


def _content(db: Session, recipe_id: UUID) -> dict[str, object]:
    """Every copied field of a recipe, to compare an original with its copy."""
    recipe = db.scalars(
        select(RecipeModel)
        .where(RecipeModel.id == recipe_id)
        .execution_options(populate_existing=True)
    ).one()
    source = db.get(SourceModel, recipe.source_id) if recipe.source_id else None
    lines = db.execute(
        select(
            RecipeIngredientModel.position,
            RecipeIngredientModel.name,
            RecipeIngredientModel.quantity,
            RecipeIngredientModel.unit,
            RecipeIngredientModel.size,
            RecipeIngredientModel.preparation,
            RecipeIngredientModel.vague_note,
        )
        .where(RecipeIngredientModel.recipe_id == recipe_id)
        .order_by(RecipeIngredientModel.position)
    ).all()
    steps = db.execute(
        select(StepModel.position, StepModel.text)
        .where(StepModel.recipe_id == recipe_id)
        .order_by(StepModel.position)
    ).all()
    return {
        "title": recipe.title,
        "author_id": recipe.author_id,
        "base_servings": recipe.base_servings,
        "servings_estimated": recipe.servings_estimated,
        "created_at": recipe.created_at,
        "lines": [tuple(line) for line in lines],
        "steps": [tuple(step) for step in steps],
        "source": source and (source.user_id, source.type, source.url, source.raw_text),
    }


def _catalog(db: Session, notebook_id: UUID) -> list[str]:
    return SqlAlchemyIngredientCatalog(db).names_for_notebook(notebook_id)


def _service(session: Session, recipes: SqlAlchemyRecipeRepository) -> AddNotebookSnapshotService:
    return AddNotebookSnapshotService(
        SqlAlchemyKitchenRepository(session),
        SqlAlchemyNotebookRepository(session),
        SqlAlchemyIngredientCatalog(session),
        recipes,
    )


@pytest.fixture
def ana(client: TestClient) -> tuple[UUID, str]:
    return _register(client, "ana")


# --- US1: what is copied (FR-009 to FR-012, SC-003) ------------------------------------------


def test_every_field_matches_the_original(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    linked = _recipe(db_session, source, ana_id, "Linked")
    pasted = _recipe(db_session, source, ana_id, "Pasted", url=None)

    _use(client, token)
    snapshot = _added(client, kitchen, source)

    copies = {row.title: row.id for row in _recipes_of(db_session, snapshot)}
    assert set(copies) == {"Linked", "Pasted"}
    assert _content(db_session, copies["Linked"]) == _content(db_session, linked)
    assert _content(db_session, copies["Pasted"]) == _content(db_session, pasted)


def test_the_answer_is_the_new_notebook(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id, "Cuaderno de ana")
    _recipe(db_session, source, ana_id)
    _use(client, token)

    body = _add(client, kitchen, source).json()

    assert body["name"] == "Cuaderno de ana"
    assert body["kind"] == "kitchen"
    assert body["kitchen_id"] == str(kitchen)
    assert body["recipe_count"] == 1
    assert body["origin_notebook_name"] == "Cuaderno de ana"
    assert body["is_snapshot"] is True
    assert body["is_own_capture_notebook"] is False
    assert "snapshot_key" not in body
    assert "source_notebook_id" not in body


def test_the_whole_catalog_is_copied_and_no_recipe_name_changes(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    # "onion" is a recipe name left out of the catalog, which must stay as it is.
    source = _personal(db_session, ana_id, names=("rice", "saffron"))
    _recipe(db_session, source, ana_id)
    _use(client, token)

    snapshot = _added(client, kitchen, source)

    assert _catalog(db_session, snapshot) == ["rice", "saffron"]
    copied = _recipes_of(db_session, snapshot)[0].id
    names = db_session.scalars(
        select(RecipeIngredientModel.name)
        .where(RecipeIngredientModel.recipe_id == copied)
        .order_by(RecipeIngredientModel.position)
    ).all()
    assert names == ["rice", "onion", "salt"]


def test_a_deleted_author_stays_unknown(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, None)
    _use(client, token)

    snapshot = _added(client, kitchen, source)

    assert _recipes_of(db_session, snapshot)[0].author_id is None


def test_a_copy_starts_clean_and_outside_every_cart(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    original = _recipe(db_session, source, ana_id)
    _use(client, token)

    snapshot = _added(client, kitchen, source)

    copy = _recipes_of(db_session, snapshot)[0]
    assert copy.cart_add_count == 0
    assert copy.save_key is None
    assert db_session.get(RecipeModel, original).cart_add_count == 7
    assert db_session.scalar(select(func.count()).select_from(CartItemModel)) == 0
    assert copy.source_id != db_session.get(RecipeModel, original).source_id


def test_the_order_of_the_kitchen_list_is_kept(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for index, title in enumerate(["First", "Second", "Third"]):
        _recipe(db_session, source, ana_id, title, created_at=start + timedelta(days=index))
    _use(client, token)

    snapshot = _added(client, kitchen, source)

    assert [row.title for row in _recipes_of(db_session, snapshot)] == ["First", "Second", "Third"]
    listed = client.get(f"/notebooks/kitchens/{kitchen}/recipes").json()["items"]
    titles = [item["title"] for item in listed]
    assert titles == ["Third", "Second", "First"]


def test_an_empty_notebook_can_be_added(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id, names=("rice",))
    _use(client, token)

    response = _add(client, kitchen, source)

    assert response.status_code == 201
    assert response.json()["recipe_count"] == 0
    assert _catalog(db_session, UUID(response.json()["id"])) == ["rice"]
    listed = client.get(f"/notebooks/kitchens/{kitchen}").json()["notebooks"]
    assert response.json()["id"] in [row["id"] for row in listed]


def test_another_member_can_read_and_cart_a_copy(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, ana_token = ana
    ben_id, ben_token = _register(client, "ben")
    kitchen = _kitchen(db_session, ana_id, members=(ben_id,))
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, ana_id)
    _use(client, ana_token)
    snapshot = _added(client, kitchen, source)
    copy_id = _recipes_of(db_session, snapshot)[0].id

    _use(client, ben_token)
    assert client.get(f"/notebooks/{snapshot}").status_code == 200
    detail = client.get(f"/recipes/{copy_id}").json()
    assert detail["author_alias"].startswith("ana")
    assert detail["source"]["url"] == "https://example.com/rice"
    listed = client.get(f"/notebooks/kitchens/{kitchen}/recipes").json()["items"]
    assert [item["id"] for item in listed] == [str(copy_id)]
    carted = client.post(f"/kitchens/{kitchen}/cart/draft/items", json={"recipe_id": str(copy_id)})
    assert carted.status_code == 200, carted.text


def test_an_edit_lock_on_the_original_is_left_alone(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    original = _recipe(db_session, source, ana_id)
    session_id = db_session.scalar(select(SessionModel.id).where(SessionModel.user_id == ana_id))
    now = datetime.now(UTC)
    db_session.add(
        RecipeEditLockModel(
            recipe_id=original,
            session_id=session_id,
            user_id=ana_id,
            notebook_id=source,
            last_active_at=now,
        )
    )
    db_session.flush()
    _use(client, token)

    snapshot = _added(client, kitchen, source)

    assert db_session.get(RecipeEditLockModel, original) is not None
    copy = _recipes_of(db_session, snapshot)[0]
    assert db_session.get(RecipeEditLockModel, copy.id) is None


# --- US1: who may add (FR-002, FR-004, FR-005, SC-006) ---------------------------------------


def test_a_non_member_gets_not_found(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, _ = ana
    ben_id, ben_token = _register(client, "ben")
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ben_id)
    _use(client, ben_token)

    response = _add(client, kitchen, source)

    assert response.status_code == 404
    assert response.json()["code"] == "kitchen_not_found"
    assert _in_kitchen(db_session, kitchen) == 0


def test_an_archived_kitchen_refuses(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    db_session.get(KitchenModel, kitchen).is_archived = True
    db_session.flush()
    source = _personal(db_session, ana_id)
    _use(client, token)

    response = _add(client, kitchen, source)

    assert response.status_code == 403
    assert response.json()["code"] == "kitchen_archived"
    assert _in_kitchen(db_session, kitchen) == 0


@pytest.mark.parametrize("case", ["someone_else", "member_only", "kitchen_notebook"])
def test_only_a_notebook_the_caller_owns_is_accepted(
    client: TestClient, db_session: Session, ana: tuple[UUID, str], case: str
) -> None:
    ana_id, token = ana
    ben_id, _ = _register(client, "ben")
    kitchen = _kitchen(db_session, ana_id, members=(ben_id,))
    if case == "kitchen_notebook":
        other = _kitchen(db_session, ana_id)
        source = uuid4()
        db_session.add(NotebookModel(id=source, name="Kitchen one", kitchen_id=other))
        db_session.flush()
    else:
        source = _personal(db_session, ben_id, "ben's Notebook")
    if case == "member_only":
        db_session.add(NotebookMembershipModel(notebook_id=source, user_id=ana_id, role="member"))
        db_session.flush()
    _use(client, token)

    response = _add(client, kitchen, source)

    assert response.status_code == 404
    assert response.json()["code"] == "notebook_not_found"
    assert _in_kitchen(db_session, kitchen) == 0


def test_an_invalid_body_is_422(client: TestClient, db_session: Session, ana) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    _use(client, token)

    response = client.post(f"/notebooks/kitchens/{kitchen}/snapshots", json={"snapshot_key": "x"})

    assert response.status_code == 422


def test_it_needs_a_session(client: TestClient) -> None:
    client.cookies.clear()

    assert _add(client, uuid4(), uuid4()).status_code == 401


# --- US1: repeats (FR-008, FR-008a) ----------------------------------------------------------


def test_the_same_key_returns_the_same_snapshot(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, ana_id)
    key = uuid4()
    _use(client, token)
    first = _add(client, kitchen, source, key=key)

    second = _add(client, kitchen, source, key=key)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert _in_kitchen(db_session, kitchen) == 1
    assert len(_recipes_of(db_session, UUID(first.json()["id"]))) == 1


def test_a_repeat_warns_then_makes_a_new_snapshot_of_the_notebook_as_it_is(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, ana_id, "Old")
    _use(client, token)
    first = _added(client, kitchen, source)
    _recipe(db_session, source, ana_id, "New")
    key = uuid4()

    warned = _add(client, kitchen, source, key=key)
    assert warned.status_code == 409
    assert warned.json()["code"] == "snapshot_exists"
    assert _in_kitchen(db_session, kitchen) == 1

    second = _add(client, kitchen, source, key=key, confirm=True)
    assert second.status_code == 201
    assert _in_kitchen(db_session, kitchen) == 2
    assert [row.title for row in _recipes_of(db_session, first)] == ["Old"]
    assert {r.title for r in _recipes_of(db_session, UUID(second.json()["id"]))} == {"Old", "New"}


def test_no_warning_once_the_earlier_snapshot_is_deleted(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _use(client, token)
    first = _added(client, kitchen, source)
    db_session.execute(delete(NotebookModel).where(NotebookModel.id == first))

    assert _add(client, kitchen, source).status_code == 201


def test_a_key_may_be_reused_in_another_kitchen(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    source = _personal(db_session, ana_id)
    key = uuid4()
    _use(client, token)

    first = _add(client, _kitchen(db_session, ana_id), source, key=key)
    second = _add(client, _kitchen(db_session, ana_id), source, key=key)

    assert (first.status_code, second.status_code) == (201, 201)


def test_the_same_key_at_the_same_moment_makes_one_snapshot(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as setup:
        ana_id = uuid4()
        setup.add(
            UserModel(
                id=ana_id,
                email=f"{ana_id.hex[:12]}@example.com",
                alias=f"a{ana_id.hex[:12]}",
                password_hash="not-a-real-hash",
            )
        )
        setup.flush()
        kitchen = _kitchen(setup, ana_id)
        source = _personal(setup, ana_id)
        _recipe(setup, source, ana_id)
        setup.commit()
    key = uuid4()

    def call(session: Session) -> UUID:
        added = _service(session, SqlAlchemyRecipeRepository(session)).execute(
            AddNotebookSnapshotCommand(
                actor_user_id=ana_id,
                kitchen_id=kitchen,
                source_notebook_id=source,
                snapshot_key=key,
            )
        )
        return added.notebook.id

    results, errors = _race(factory, call, threads=4)

    try:
        assert errors == []
        assert len(set(results)) == 1
        with factory() as check:
            assert _in_kitchen(check, kitchen) == 1
            assert len(_recipes_of(check, results[0])) == 1
    finally:
        _cleanup(factory, notebooks=[source], kitchens=[kitchen], users=[ana_id])


# --- US1: all or nothing (FR-006, SC-005) ----------------------------------------------------


@pytest.mark.parametrize("fail_at", ["catalog", "recipes", "after_recipes"])
def test_a_failure_at_any_point_leaves_nothing(engine: Engine, fail_at: str) -> None:
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as setup:
        ana_id = uuid4()
        setup.add(
            UserModel(
                id=ana_id,
                email=f"{ana_id.hex[:12]}@example.com",
                alias=f"a{ana_id.hex[:12]}",
                password_hash="not-a-real-hash",
            )
        )
        setup.flush()
        kitchen = _kitchen(setup, ana_id)
        source = _personal(setup, ana_id, names=("rice",))
        _recipe(setup, source, ana_id)
        setup.commit()

    class Failing(SqlAlchemyRecipeRepository):
        def copy_all(self, source_id: UUID, target_id: UUID) -> int:
            if fail_at == "after_recipes":
                super().copy_all(source_id, target_id)
            raise RuntimeError("forced")

    class FailingCatalog(SqlAlchemyIngredientCatalog):
        def copy_names(self, source_id: UUID, target_id: UUID) -> None:
            super().copy_names(source_id, target_id)
            raise RuntimeError("forced")

    try:
        counts_before = None
        with factory() as session:
            counts_before = _table_counts(session)
            service = AddNotebookSnapshotService(
                SqlAlchemyKitchenRepository(session),
                SqlAlchemyNotebookRepository(session),
                (FailingCatalog if fail_at == "catalog" else SqlAlchemyIngredientCatalog)(session),
                Failing(session),
            )
            with pytest.raises(RuntimeError):
                service.execute(
                    AddNotebookSnapshotCommand(
                        actor_user_id=ana_id,
                        kitchen_id=kitchen,
                        source_notebook_id=source,
                        snapshot_key=uuid4(),
                    )
                )
            # What get_db does with an exception.
            session.rollback()
        with factory() as check:
            assert _in_kitchen(check, kitchen) == 0
            assert _table_counts(check) == counts_before
    finally:
        _cleanup(factory, notebooks=[source], kitchens=[kitchen], users=[ana_id])


def _table_counts(session: Session) -> list[int]:
    models = (NotebookModel, IngredientModel, SourceModel, RecipeModel, StepModel)
    models += (RecipeIngredientModel,)
    return [session.scalar(select(func.count()).select_from(model)) or 0 for model in models]


# --- US1: captures keep going where they did (FR-017) ----------------------------------------


def _capture_notebook(client: TestClient, kitchen: UUID):
    return client.post(f"/notebooks/kitchens/{kitchen}/capture-notebook")


def test_an_adder_with_only_a_snapshot_gets_their_own_notebook(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    ben_id, _ = _register(client, "ben")
    kitchen = _kitchen(db_session, ben_id, members=(ana_id,))
    source = _personal(db_session, ana_id)
    _use(client, token)
    snapshot = _added(client, kitchen, source)

    response = _capture_notebook(client, kitchen)

    assert response.status_code == 200
    body = response.json()
    assert UUID(body["id"]) != snapshot
    assert body["is_own_capture_notebook"] is True
    assert body["is_snapshot"] is False
    assert body["name"] != "ana's Notebook"
    assert _capture_notebook(client, kitchen).json()["id"] == body["id"]


def test_a_member_with_their_own_notebook_keeps_it_as_the_default(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _use(client, token)
    own = _capture_notebook(client, kitchen).json()["id"]

    _added(client, kitchen, source)

    assert _capture_notebook(client, kitchen).json()["id"] == own
    listed = client.get(f"/notebooks/kitchens/{kitchen}").json()["notebooks"]
    assert [row["id"] for row in listed if row["is_own_capture_notebook"]] == [own]


def test_a_snapshot_stays_out_of_captures_after_its_label_is_cleared(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    ben_id, _ = _register(client, "ben")
    kitchen = _kitchen(db_session, ben_id, members=(ana_id,))
    source = _personal(db_session, ana_id)
    _use(client, token)
    snapshot = _added(client, kitchen, source)
    db_session.execute(delete(NotebookModel).where(NotebookModel.id == source))
    db_session.expire_all()

    response = _capture_notebook(client, kitchen)

    assert UUID(response.json()["id"]) != snapshot
    assert client.get(f"/notebooks/{snapshot}").json()["is_snapshot"] is True


def test_the_capture_route_refuses_a_non_member_and_an_archived_kitchen(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    ben_id, _ = _register(client, "ben")
    foreign = _kitchen(db_session, ben_id)
    archived = _kitchen(db_session, ana_id)
    db_session.get(KitchenModel, archived).is_archived = True
    db_session.flush()
    _use(client, token)

    assert _capture_notebook(client, foreign).status_code == 404
    response = _capture_notebook(client, archived)
    assert response.status_code == 403
    assert response.json()["code"] == "kitchen_archived"


# --- US1: speed (SC-002) ---------------------------------------------------------------------


def test_a_notebook_of_100_recipes_is_added_in_under_5_seconds(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    for index in range(100):
        _recipe(db_session, source, ana_id, f"Recipe {index}")
    _use(client, token)

    started = time.perf_counter()
    snapshot = _added(client, kitchen, source)
    elapsed = time.perf_counter() - started

    assert len(_recipes_of(db_session, snapshot)) == 100
    assert elapsed < 5


# --- US2: the two notebooks stay independent (FR-015, FR-016, FR-018, SC-004) ----------------


def _edited(title: str) -> EditedRecipe:
    return EditedRecipe(
        title=title,
        base_servings=2,
        servings_estimated=False,
        lines=(IngredientLine(name="lentil", vague=False, quantity=1, unit="cup"),),
        steps=("Simmer.",),
    )


def _edit(db: Session, recipe_id: UUID, title: str) -> None:
    version = db.get(RecipeModel, recipe_id).updated_at
    SqlAlchemyRecipeRepository(db).replace(recipe_id, version, _edited(title))


def test_an_edit_on_either_side_does_not_reach_the_other(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    first = _recipe(db_session, source, ana_id, "One")
    second = _recipe(db_session, source, ana_id, "Two")
    _use(client, token)
    snapshot = _added(client, kitchen, source)
    copies = {row.title: row.id for row in _recipes_of(db_session, snapshot)}
    copy_of_first, copy_of_second = copies["One"], copies["Two"]
    before_first_copy = _content(db_session, copy_of_first)
    before_second = _content(db_session, second)

    _edit(db_session, first, "One edited")
    _edit(db_session, copy_of_second, "Two edited")

    assert _content(db_session, copy_of_first) == before_first_copy
    assert _content(db_session, second) == before_second


def test_a_delete_on_either_side_keeps_the_other_and_its_source_link(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    first = _recipe(db_session, source, ana_id, "One")
    second = _recipe(db_session, source, ana_id, "Two")
    _use(client, token)
    snapshot = _added(client, kitchen, source)
    copies = {row.title: row.id for row in _recipes_of(db_session, snapshot)}

    repository = SqlAlchemyRecipeRepository(db_session)
    repository.delete(first)
    repository.delete(copies["Two"])

    assert client.get(f"/recipes/{copies['One']}").json()["source"]["url"] == (
        "https://example.com/rice"
    )
    assert client.get(f"/recipes/{second}").json()["source"]["url"] == "https://example.com/rice"
    assert [row.title for row in _recipes_of(db_session, source)] == ["Two"]
    assert [row.title for row in _recipes_of(db_session, snapshot)] == ["One"]


def test_new_recipes_and_names_stay_on_their_side(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id, names=("rice",))
    _use(client, token)
    snapshot = _added(client, kitchen, source)

    _recipe(db_session, source, ana_id, "Only in the original")
    _recipe(db_session, snapshot, ana_id, "Only in the snapshot")
    catalog = SqlAlchemyIngredientCatalog(db_session)
    catalog.add_names(source, ["basil"])
    catalog.add_names(snapshot, ["cumin"])

    assert [row.title for row in _recipes_of(db_session, source)] == ["Only in the original"]
    assert [row.title for row in _recipes_of(db_session, snapshot)] == ["Only in the snapshot"]
    assert _catalog(db_session, source) == ["basil", "rice"]
    assert _catalog(db_session, snapshot) == ["cumin", "rice"]


def test_a_rename_of_the_original_leaves_the_snapshots_name(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _use(client, token)
    snapshot = _added(client, kitchen, source)

    db_session.get(NotebookModel, source).name = "Renamed"
    db_session.flush()

    assert client.get(f"/notebooks/{snapshot}").json()["name"] == "ana's Notebook"


def test_the_adder_leaving_ends_their_access_and_nothing_else(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, ana_token = ana
    ben_id, ben_token = _register(client, "ben")
    kitchen = _kitchen(db_session, ben_id, members=(ana_id,))
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, ana_id)
    _use(client, ana_token)
    snapshot = _added(client, kitchen, source)

    # No route lets a member leave yet (spec.md Assumptions).
    db_session.execute(
        delete(KitchenMembershipModel).where(
            KitchenMembershipModel.kitchen_id == kitchen,
            KitchenMembershipModel.user_id == ana_id,
        )
    )
    db_session.expire_all()

    assert client.get(f"/notebooks/{snapshot}").status_code == 404
    assert client.get(f"/notebooks/{source}").status_code == 200
    _use(client, ben_token)
    assert client.get(f"/notebooks/{snapshot}").json()["recipe_count"] == 1


def test_a_deleted_kitchen_takes_the_snapshot_and_not_the_original(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id)
    _recipe(db_session, source, ana_id)
    _use(client, token)
    snapshot = _added(client, kitchen, source)

    db_session.execute(delete(KitchenModel).where(KitchenModel.id == kitchen))
    db_session.expire_all()

    assert db_session.get(NotebookModel, snapshot) is None
    assert len(_recipes_of(db_session, source)) == 1


def test_neither_side_gains_access_to_the_other(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, ana_token = ana
    ben_id, ben_token = _register(client, "ben")
    carol_id, carol_token = _register(client, "carol")
    kitchen = _kitchen(db_session, ana_id, members=(ben_id,))
    source = _personal(db_session, ana_id)
    db_session.add(NotebookMembershipModel(notebook_id=source, user_id=carol_id, role="member"))
    original = _recipe(db_session, source, ana_id)
    db_session.flush()
    _use(client, ana_token)
    before = client.get(f"/notebooks/{source}").json()
    snapshot = _added(client, kitchen, source)

    # The original shows nothing about the snapshot.
    assert client.get(f"/notebooks/{source}").json() == before

    # A kitchen member can't open the original.
    _use(client, ben_token)
    assert client.get(f"/notebooks/{source}").status_code == 404
    assert client.get(f"/notebooks/{source}/recipes").status_code == 404
    assert client.get(f"/recipes/{original}").status_code == 404

    # A member of the original can't open the kitchen or the snapshot.
    _use(client, carol_token)
    assert client.get(f"/notebooks/kitchens/{kitchen}").status_code == 404
    assert client.get(f"/notebooks/{snapshot}").status_code == 404


# --- US3: the origin label (FR-019 to FR-022) ------------------------------------------------


def test_the_label_reads_the_originals_current_name(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, ana_token = ana
    ben_id, ben_token = _register(client, "ben")
    kitchen = _kitchen(db_session, ana_id, members=(ben_id,))
    source = _personal(db_session, ana_id)
    _use(client, ana_token)
    snapshot = _added(client, kitchen, source)

    db_session.get(NotebookModel, source).name = "Renamed"
    db_session.flush()

    _use(client, ben_token)
    body = client.get(f"/notebooks/{snapshot}").json()
    assert body["origin_notebook_name"] == "Renamed"
    assert str(source) not in str(body)


def test_deleting_the_original_clears_the_label_and_the_warning_and_keeps_the_rest(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    source = _personal(db_session, ana_id, names=("rice",))
    _recipe(db_session, source, ana_id)
    _use(client, token)
    snapshot = _added(client, kitchen, source)

    db_session.execute(delete(NotebookModel).where(NotebookModel.id == source))
    db_session.expire_all()

    body = client.get(f"/notebooks/{snapshot}").json()
    assert body["origin_notebook_name"] is None
    assert body["is_snapshot"] is True
    assert body["recipe_count"] == 1
    assert _catalog(db_session, snapshot) == ["rice"]
    # The same name in a new notebook isn't the deleted original, so nothing warns.
    assert not SqlAlchemyNotebookRepository(db_session).has_snapshot_of(kitchen, source)


def test_a_plain_kitchen_notebook_has_no_label(
    client: TestClient, db_session: Session, ana: tuple[UUID, str]
) -> None:
    ana_id, token = ana
    kitchen = _kitchen(db_session, ana_id)
    _use(client, token)

    body = _capture_notebook(client, kitchen).json()

    assert body["origin_notebook_name"] is None
    assert body["is_snapshot"] is False


# --- Creating a personal notebook (S-059, creation only) ---------------------


def test_a_new_notebook_is_empty_owned_by_the_caller_and_starts_from_their_names(
    client: TestClient, db_session: Session
) -> None:
    user_id, _ = _register(client, "ana")
    _personal(db_session, user_id, "Mine", names=("onion",))
    response = client.post("/notebooks", json={"name": "  Postres  "})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Postres"
    assert body["kind"] == "personal"
    assert body["access"] == "owner"
    assert body["is_default"] is False
    assert body["recipe_count"] == 0
    notebook_id = UUID(body["id"])
    assert client.get(f"/notebooks/{notebook_id}").status_code == 200
    assert client.get(f"/notebooks/{notebook_id}/recipes").json()["items"] == []
    names = db_session.scalars(
        select(IngredientModel.name).where(IngredientModel.notebook_id == notebook_id)
    ).all()
    assert list(names) == ["onion"]


def test_a_new_notebook_does_not_replace_the_default(client: TestClient) -> None:
    _register(client, "ana")
    default_id = client.get("/notebooks/default").json()["id"]
    client.post("/notebooks", json={"name": "Postres"})
    assert client.get("/notebooks/default").json()["id"] == default_id


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_a_new_notebook_needs_a_name(client: TestClient, name: str) -> None:
    _register(client, "ana")
    before = len(client.get("/notebooks").json()["notebooks"])
    response = client.post("/notebooks", json={"name": name})
    assert (response.status_code, response.json()["code"]) == (422, "invalid_notebook_name")
    assert len(client.get("/notebooks").json()["notebooks"]) == before


def test_creating_a_notebook_needs_an_alias(client: TestClient) -> None:
    client.cookies.clear()
    email = f"noalias_{uuid4().hex[:6]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "password1"})
    response = client.post("/notebooks", json={"name": "Postres"})
    assert (response.status_code, response.json()["code"]) == (403, "alias_required")
