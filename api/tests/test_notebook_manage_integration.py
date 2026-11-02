"""Renaming, deleting and adding notebooks with Postgres (spec 059). Skips without DATABASE_URL.

The `client` fixture shares one transaction. Concurrency and rollback tests use the `engine`
fixture with their own sessions and clean up after themselves. In those, one request holds its
transaction open while the other is shown to be waiting, so each order is forced.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    CartItemModel,
    IngredientModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookInviteModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeEditLockModel,
    RecipeIngredientModel,
    RecipeModel,
    ShoppingListItemModel,
    SourceModel,
    StepModel,
    UserModel,
)
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
)
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import SqlAlchemyKitchenRepository
from application.notebooks import (
    AddNotebookSnapshotCommand,
    AddNotebookSnapshotService,
    CreateKitchenNotebookCommand,
    CreateKitchenNotebookService,
    DeleteNotebookCommand,
    DeleteNotebookService,
    RenameNotebookCommand,
    RenameNotebookService,
)
from domain.errors import (
    InvalidInviteTokenError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
)
from domain.recipe import NewRecipe
from domain.recipe_draft import IngredientLine
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.integration_db import database_url
from tests.test_carts_integration import People, _home, _save
from tests.test_notebook_integration import _cleanup
from tests.test_notebook_invites_integration import _committed_invite, _finish
from tests.test_notebook_ownership_integration import (
    _accept_invite,
    _assert_waiting,
    _in_background,
    _release,
)
from tests.test_notebook_snapshots_integration import _added
from tests.test_shopping_list_integration import _cart, _list, measured, recipe, save_cart

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _id(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _book(client: TestClient, name: str = "Soups") -> str:
    response = client.post("/notebooks", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _share(db: Session, notebook_id: str, user_id: UUID) -> None:
    db.add(NotebookMembershipModel(notebook_id=_id(notebook_id), user_id=user_id, role="member"))
    db.flush()


def _archive(db: Session, kitchen_id: str) -> None:
    db.execute(
        update(KitchenModel).where(KitchenModel.id == _id(kitchen_id)).values(is_archived=True)
    )
    db.flush()
    db.expire_all()


def _rename(client: TestClient, notebook_id: str, name: str):  # noqa: ANN202
    return client.patch(f"/notebooks/{notebook_id}", json={"name": name})


def _new(client: TestClient, kitchen_id: str, name: str):  # noqa: ANN202
    return client.post(f"/notebooks/kitchens/{kitchen_id}", json={"name": name})


def _name(db: Session, notebook_id: str) -> str | None:
    db.expire_all()
    return db.scalar(select(NotebookModel.name).where(NotebookModel.id == _id(notebook_id)))


def _count(db: Session, model: type, *where: object) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _carl(people: People) -> None:
    people.register("carl")


def _titled(lines: list[dict]) -> list[tuple[str, list[str]]]:
    return [(line["name"], [r["title"] for r in line["recipes"]]) for line in lines]


def _refused(response, status: int, code: str) -> None:  # noqa: ANN001
    assert (response.status_code, response.json()["code"]) == (status, code), response.text


# --- User Story 1: rename ----------------------------------------------------------------------


def test_the_owner_renames_and_every_member_reads_the_new_name(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    saved = _save(ana, book)
    default_before = ana.get("/notebooks/default").json()["id"]
    _share(db_session, book, people.ids["ben"])

    response = _rename(people.as_("ana"), book, "  Winter soups ")

    assert response.status_code == 200, response.text
    assert (response.json()["name"], response.json()["access"]) == ("Winter soups", "owner")
    rows = people.as_("ben").get("/notebooks").json()["notebooks"]
    assert [row["name"] for row in rows if row["id"] == book] == ["Winter soups"]
    ana = people.as_("ana")
    assert ana.get(f"/recipes/{saved}").status_code == 200
    assert ana.get(f"/notebooks/{book}").json()["recipe_count"] == 1
    assert ana.get("/notebooks/default").json()["id"] == default_before


def test_the_default_stays_the_default_after_a_rename(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    default = ana.get("/notebooks/default").json()["id"]

    assert _rename(ana, default, "Everyday").json()["is_default"] is True
    assert ana.get("/notebooks/default").json()["id"] == default


def test_a_notebook_member_is_refused(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    book = _book(people.as_("ana"))
    _share(db_session, book, people.ids["ben"])

    _refused(_rename(people.as_("ben"), book, "Mine"), 403, "notebook_owner_only")

    assert _name(db_session, book) == "Soups"


def test_a_kitchen_member_renames_any_of_its_notebooks_snapshots_included(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    snapshot = _added(ana, _id(kitchen), _id(book))

    ben = people.as_("ben")
    assert _rename(ben, notebook, "Weeknight").status_code == 200
    renamed = _rename(ben, str(snapshot), "Copied soups")

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["is_snapshot"] is True
    assert renamed.json()["origin_notebook_name"] == "Soups"
    assert people.as_("ana").get(f"/notebooks/{notebook}").json()["name"] == "Weeknight"


def test_an_archived_kitchen_refuses_and_changes_nothing(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, notebook = _home(client, db_session)
    before = _name(db_session, notebook)
    _archive(db_session, kitchen)

    _refused(_rename(people.as_("ana"), notebook, "Weeknight"), 403, "kitchen_archived")
    _refused(people.as_("ana").delete(f"/notebooks/{notebook}"), 403, "kitchen_archived")

    assert _name(db_session, notebook) == before


def test_an_outsider_gets_not_found_even_with_a_bad_name(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, notebook = _home(client, db_session)
    book = _book(people.as_("ana"))
    _carl(people)

    carl = people.as_("carl")
    _refused(_rename(carl, book, "Mine"), 404, "notebook_not_found")
    _refused(_rename(carl, notebook, "Mine"), 404, "notebook_not_found")
    _refused(_rename(carl, book, ""), 404, "notebook_not_found")
    _refused(_rename(carl, str(uuid4()), "Mine"), 404, "notebook_not_found")

    assert _name(db_session, book) == "Soups"


@pytest.mark.parametrize("name", ["", "    ", "x" * 201])
def test_a_bad_name_answers_422(client: TestClient, db_session: Session, name: str) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    book = _book(people.as_("ana"))

    _refused(_rename(people.as_("ana"), book, name), 422, "invalid_notebook_name")

    assert _name(db_session, book) == "Soups"


def test_the_unchanged_name_of_an_old_long_notebook_saves(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    book = _book(people.as_("ana"))
    long_name = "n" * 240
    db_session.execute(
        update(NotebookModel).where(NotebookModel.id == _id(book)).values(name=long_name)
    )
    db_session.flush()
    db_session.expire_all()

    response = _rename(people.as_("ana"), book, long_name)

    assert (response.status_code, response.json()["name"]) == (200, long_name)


def test_the_snapshot_label_follows_the_original_and_its_own_name_does_not(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    snapshot = _added(ana, _id(kitchen), _id(book))

    assert _rename(ana, book, "Winter soups").status_code == 200

    body = people.as_("ben").get(f"/notebooks/{snapshot}").json()
    assert (body["name"], body["origin_notebook_name"]) == ("Soups", "Winter soups")


def test_routes_need_an_alias(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    book = _book(people.as_("ana"))
    client.cookies.clear()
    email = f"noalias_{uuid4().hex[:6]}@example.com"
    assert (
        client.post("/auth/register", json={"email": email, "password": "password1"}).status_code
        == 201
    )

    for response in (_rename(client, book, "Mine"), client.delete(f"/notebooks/{book}")):
        assert response.json()["code"] == "alias_required"


# --- User Story 2: delete ----------------------------------------------------------------------


def test_each_role_on_delete(client: TestClient, db_session: Session) -> None:
    people, kitchen, notebook = _home(client, db_session)
    book = _book(people.as_("ana"))
    _share(db_session, book, people.ids["ben"])
    _carl(people)

    _refused(people.as_("ben").delete(f"/notebooks/{book}"), 403, "notebook_owner_only")
    _refused(people.as_("carl").delete(f"/notebooks/{book}"), 404, "notebook_not_found")
    _refused(people.as_("carl").delete(f"/notebooks/{notebook}"), 404, "notebook_not_found")
    assert _name(db_session, book) == "Soups"

    assert people.as_("ana").delete(f"/notebooks/{book}").status_code == 204
    _refused(people.as_("ana").delete(f"/notebooks/{book}"), 404, "notebook_not_found")
    _refused(people.as_("ben").get(f"/notebooks/{book}"), 404, "notebook_not_found")

    assert people.as_("ben").delete(f"/notebooks/{notebook}").status_code == 204
    assert _name(db_session, notebook) is None
    assert _count(db_session, KitchenModel, KitchenModel.id == _id(kitchen)) == 1


def test_a_deletion_leaves_nothing_of_the_notebook(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    saved = _id(_save(ana, book))
    db_session.add(
        NotebookInviteModel(
            id=uuid4(),
            notebook_id=_id(book),
            email="dara@example.test",
            token_hash=uuid4().hex,
            invited_by=people.ids["ana"],
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    db_session.flush()
    _share(db_session, book, people.ids["ben"])
    source_id = db_session.scalar(select(RecipeModel.source_id).where(RecipeModel.id == saved))
    # Someone else is editing: the lock does not block the deletion, and it ends with it.
    assert people.as_("ben").post(f"/recipes/{saved}/edit-lock").status_code == 200

    assert people.as_("ana").delete(f"/notebooks/{book}").status_code == 204

    notebook_id = _id(book)
    assert _count(db_session, RecipeModel, RecipeModel.notebook_id == notebook_id) == 0
    assert _count(db_session, RecipeIngredientModel, RecipeIngredientModel.recipe_id == saved) == 0
    assert _count(db_session, StepModel, StepModel.recipe_id == saved) == 0
    assert _count(db_session, IngredientModel, IngredientModel.notebook_id == notebook_id) == 0
    assert (
        _count(
            db_session,
            NotebookMembershipModel,
            NotebookMembershipModel.notebook_id == notebook_id,
        )
        == 0
    )
    assert (
        _count(db_session, NotebookInviteModel, NotebookInviteModel.notebook_id == notebook_id) == 0
    )
    assert _count(db_session, RecipeEditLockModel, RecipeEditLockModel.recipe_id == saved) == 0
    assert _count(db_session, SourceModel, SourceModel.id == source_id) == 0


def test_a_source_another_recipe_uses_stays(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book, other = _book(ana), _book(ana, "Stews")
    gone = _id(_save(ana, book))
    kept = _id(_save(ana, other))
    source_id = db_session.scalar(select(RecipeModel.source_id).where(RecipeModel.id == gone))
    db_session.execute(
        update(RecipeModel).where(RecipeModel.id == kept).values(source_id=source_id)
    )
    db_session.flush()

    assert ana.delete(f"/notebooks/{book}").status_code == 204

    assert _count(db_session, SourceModel, SourceModel.id == source_id) == 1


def test_a_snapshot_outlives_its_original_with_its_label_cleared(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    _save(ana, book)
    snapshot = _added(ana, _id(kitchen), _id(book))

    assert ana.delete(f"/notebooks/{book}").status_code == 204

    body = people.as_("ben").get(f"/notebooks/{snapshot}").json()
    assert (body["name"], body["origin_notebook_name"]) == ("Soups", None)
    assert body["recipe_count"] == 1


def test_deleting_a_snapshot_leaves_the_original_and_allows_adding_it_again(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    _save(ana, book)
    snapshot = _added(ana, _id(kitchen), _id(book))

    assert people.as_("ben").delete(f"/notebooks/{snapshot}").status_code == 204

    ana = people.as_("ana")
    assert ana.get(f"/notebooks/{book}").json()["recipe_count"] == 1
    assert _added(ana, _id(kitchen), _id(book)) != snapshot


def test_a_deleted_default_comes_back_new_and_empty(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    default = ana.get("/notebooks/default").json()["id"]
    _save(ana, default)

    assert ana.delete(f"/notebooks/{default}").status_code == 204

    fresh = ana.get("/notebooks/default").json()
    assert fresh["id"] != default
    assert (fresh["is_default"], fresh["recipe_count"]) == (True, 0)


def test_the_last_kitchen_notebook_comes_back_for_the_next_who_opens(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, notebook = _home(client, db_session)
    _save(people.as_("ana"), notebook)

    assert people.as_("ana").delete(f"/notebooks/{notebook}").status_code == 204

    rows = people.as_("ben").get(f"/notebooks/kitchens/{kitchen}").json()["notebooks"]
    assert len(rows) == 1
    assert rows[0]["id"] != notebook
    assert rows[0]["recipe_count"] == 0
    assert rows[0]["owner_alias"] is not None


def test_the_cart_and_lists_after_a_deletion(client: TestClient, db_session: Session) -> None:
    people, kitchen, notebook = _home(client, db_session)
    ana = people.as_("ana")
    other = _new(ana, kitchen, "Holidays").json()["id"]
    gone = recipe(ana, notebook, "Bread", [measured("flour", 3, "tbsp")])
    kept = recipe(ana, other, "Pancakes", [measured("egg", 2, "unit")])
    save_cart(ana, kitchen, [gone, kept])
    assert ana.post(_list(kitchen) + "/items", json={"name": "Soap"}).status_code == 201
    lines_before = _count(db_session, ShoppingListItemModel)
    list_before = ana.get(_list(kitchen)).json()

    ben = people.as_("ben")
    assert ben.delete(f"/notebooks/{notebook}").status_code == 204

    assert _count(db_session, CartItemModel, CartItemModel.recipe_id == _id(gone)) == 0
    assert _count(db_session, CartItemModel, CartItemModel.recipe_id == _id(kept)) == 1
    assert _count(db_session, ShoppingListItemModel) == lines_before
    lines_after = ben.get(_list(kitchen)).json()["lines"]
    assert _titled(lines_after) == _titled(list_before["lines"])
    flour = next(line for line in lines_after if line["name"] == "flour")
    assert flour["recipes"][0]["exists"] is False
    listed = ben.get(f"/notebooks/kitchens/{kitchen}/recipes").json()["items"]
    assert [row["id"] for row in listed] == [kept]

    save_cart(ben, kitchen, [kept])
    refreshed = ben.get(_list(kitchen)).json()
    assert [line["name"] for line in refreshed["lines"]] == ["egg"]
    assert [item["name"] for item in refreshed["hand_items"]] == ["soap"]


def test_a_draft_reports_a_recipe_gone_with_its_notebook(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, notebook = _home(client, db_session)
    ana = people.as_("ana")
    other = _new(ana, kitchen, "Holidays").json()["id"]
    gone = recipe(ana, notebook, "Bread", [measured("flour", 3, "tbsp")])
    kept = recipe(ana, other, "Pancakes", [measured("egg", 2, "unit")])
    assert ana.post(_cart(kitchen, "/edit")).status_code == 200
    put = ana.put(
        _cart(kitchen, "/draft"),
        json={"items": [{"recipe_id": r, "servings": 2} for r in (gone, kept)]},
    )
    assert put.status_code == 200, put.text

    assert people.as_("ben").delete(f"/notebooks/{notebook}").status_code == 204

    body = people.as_("ana").post(_cart(kitchen, "/save")).json()
    assert body["dropped_recipe_ids"] == [gone]


def test_a_persons_units_stay(client: TestClient, db_session: Session) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    response = ana.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": book,
            "title": "Beans",
            "base_servings": 4,
            "ingredient_lines": [{"name": "bean", "quantity": 1, "unit": "lata"}],
            "steps": ["Cook."],
            "keep_units": ["lata"],
        },
    )
    assert response.status_code == 201, response.text
    units = ana.get("/recipe-vocabulary").json()

    assert ana.delete(f"/notebooks/{book}").status_code == 204

    assert ana.get("/recipe-vocabulary").json() == units


def test_the_next_capture_uses_the_next_oldest_own_notebook(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ben = people.as_("ben")
    first = _new(ben, kitchen, "First").json()["id"]
    second = _new(ben, kitchen, "Second").json()["id"]
    # One test transaction gives both the same now(), so the order is set by hand.
    db_session.execute(
        update(NotebookModel)
        .where(NotebookModel.id == _id(first))
        .values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    )
    db_session.flush()
    capture = f"/notebooks/kitchens/{kitchen}/capture-notebook"
    assert ben.post(capture).json()["id"] == first

    assert ben.delete(f"/notebooks/{first}").status_code == 204
    assert ben.post(capture).json()["id"] == second

    assert ben.delete(f"/notebooks/{second}").status_code == 204
    made = ben.post(capture).json()
    assert made["id"] not in (first, second)
    assert made["is_own_capture_notebook"] is True


def test_a_snapshot_never_becomes_the_capture_notebook(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ben = people.as_("ben")
    own = _new(ben, kitchen, "Own").json()["id"]
    snapshot = _added(ben, _id(kitchen), _id(_book(ben)))

    assert ben.delete(f"/notebooks/{own}").status_code == 204

    assert ben.post(f"/notebooks/kitchens/{kitchen}/capture-notebook").json()["id"] != str(snapshot)


# --- User Story 3: add an empty kitchen notebook ------------------------------------------------


def test_a_member_adds_a_notebook_every_member_sees(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ben = people.as_("ben")
    salty = _book(ben, "Ben's")
    recipe(ben, salty, "Salted", [measured("salt", 1, "tsp")])

    response = _new(ben, kitchen, "  Holidays ")

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["name"], body["kind"], body["kitchen_id"]) == ("Holidays", "kitchen", kitchen)
    assert (body["recipe_count"], body["access"]) == (0, "kitchen_member")
    listed = people.as_("ana").get(f"/notebooks/kitchens/{kitchen}").json()["notebooks"]
    assert body["id"] in [row["id"] for row in listed]
    db_session.expire_all()
    stored = db_session.get(NotebookModel, _id(body["id"]))
    assert stored is not None
    assert stored.owner_user_id == people.ids["ben"]
    names = db_session.scalars(
        select(IngredientModel.name).where(IngredientModel.notebook_id == stored.id)
    ).all()
    assert list(names) == ["salt"]


def test_add_refusals(client: TestClient, db_session: Session) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    _carl(people)
    before = _count(db_session, NotebookModel, NotebookModel.kitchen_id == _id(kitchen))

    _refused(_new(people.as_("carl"), kitchen, "Holidays"), 404, "kitchen_not_found")
    _refused(_new(people.as_("carl"), kitchen, ""), 404, "kitchen_not_found")
    _refused(_new(people.as_("ana"), str(uuid4()), "Holidays"), 404, "kitchen_not_found")
    _refused(_new(people.as_("ana"), kitchen, "   "), 422, "invalid_notebook_name")
    _refused(_new(people.as_("ana"), kitchen, "x" * 201), 422, "invalid_notebook_name")
    _archive(db_session, kitchen)
    _refused(_new(people.as_("ana"), kitchen, "Holidays"), 403, "kitchen_archived")

    assert _count(db_session, NotebookModel, NotebookModel.kitchen_id == _id(kitchen)) == before


def test_a_new_notebook_is_the_capture_notebook_only_without_an_older_one(
    client: TestClient, db_session: Session
) -> None:
    people, kitchen, _notebook = _home(client, db_session)
    ben = people.as_("ben")
    capture = f"/notebooks/kitchens/{kitchen}/capture-notebook"

    first = _new(ben, kitchen, "Holidays").json()
    assert first["is_own_capture_notebook"] is True
    assert ben.post(capture).json()["id"] == first["id"]

    db_session.execute(
        update(NotebookModel)
        .where(NotebookModel.id == _id(first["id"]))
        .values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    )
    db_session.flush()
    later = _new(ben, kitchen, "Weeknight").json()
    assert later["is_own_capture_notebook"] is False
    assert ben.post(capture).json()["id"] == first["id"]


# --- lock_kitchen on a missing row (T045) ------------------------------------------------------


def test_lock_kitchen_on_a_missing_row_is_not_found(db_session: Session) -> None:
    with pytest.raises(KitchenNotFoundError):
        SqlAlchemyNotebookRepository(db_session).lock_kitchen(uuid4())


# --- Two real sessions (T022, T034) ------------------------------------------------------------


def _user(factory: sessionmaker[Session]) -> UUID:
    user_id = uuid4()
    with factory() as db:
        db.add(
            UserModel(
                id=user_id, email=f"{user_id.hex[:12]}@example.test", password_hash="x", alias="ana"
            )
        )
        db.commit()
    return user_id


def _kitchen_row(factory: sessionmaker[Session], owner: UUID) -> UUID:
    kitchen_id = uuid4()
    with factory() as db:
        db.add(KitchenModel(id=kitchen_id, name="Home", owner_id=owner))
        db.flush()
        db.add(
            KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=owner, role="owner")
        )
        db.commit()
    return kitchen_id


def _personal_row(factory: sessionmaker[Session], owner: UUID, name: str = "Soups") -> UUID:
    notebook_id = uuid4()
    with factory() as db:
        db.add(NotebookModel(id=notebook_id, name=name))
        db.flush()
        db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
        db.commit()
    return notebook_id


def _kitchen_notebook_row(factory: sessionmaker[Session], kitchen_id: UUID, owner: UUID) -> UUID:
    notebook_id = uuid4()
    with factory() as db:
        db.add(
            NotebookModel(
                id=notebook_id, name="Home book", kitchen_id=kitchen_id, owner_user_id=owner
            )
        )
        db.commit()
    return notebook_id


class _SessionCommits:
    """The request's own commit, left to the test's holder or worker."""

    def commit(self) -> None:
        return None


def _rename_call(actor: UUID, notebook_id: UUID, name: str) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return RenameNotebookService(
            SqlAlchemyNotebookRepository(session), SqlAlchemyTransactionCommitter(session)
        ).execute(RenameNotebookCommand(actor_user_id=actor, notebook_id=notebook_id, name=name))

    return call


def _delete_call(actor: UUID, notebook_id: UUID) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return DeleteNotebookService(
            SqlAlchemyNotebookRepository(session), SqlAlchemyTransactionCommitter(session)
        ).execute(DeleteNotebookCommand(actor_user_id=actor, notebook_id=notebook_id))

    return call


def _holding_delete(session: Session, actor: UUID, notebook_id: UUID) -> None:
    DeleteNotebookService(SqlAlchemyNotebookRepository(session), _SessionCommits()).execute(
        DeleteNotebookCommand(actor_user_id=actor, notebook_id=notebook_id)
    )


def _holding_rename(session: Session, actor: UUID, notebook_id: UUID, name: str) -> None:
    RenameNotebookService(SqlAlchemyNotebookRepository(session), _SessionCommits()).execute(
        RenameNotebookCommand(actor_user_id=actor, notebook_id=notebook_id, name=name)
    )


def _archive_call(kitchen_id: UUID) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return SqlAlchemyKitchenRepository(session).archive_kitchen(kitchen_id)

    return call


def _add_call(actor: UUID, kitchen_id: UUID) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return CreateKitchenNotebookService(
            SqlAlchemyKitchenRepository(session),
            SqlAlchemyNotebookRepository(session),
            SqlAlchemyIngredientCatalog(session),
            SqlAlchemyTransactionCommitter(session),
        ).execute(
            CreateKitchenNotebookCommand(actor_user_id=actor, kitchen_id=kitchen_id, name="New")
        )

    return call


def _snapshot_call(actor: UUID, kitchen_id: UUID, source: UUID) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return AddNotebookSnapshotService(
            SqlAlchemyKitchenRepository(session),
            SqlAlchemyNotebookRepository(session),
            SqlAlchemyIngredientCatalog(session),
            SqlAlchemyRecipeRepository(session),
        ).execute(
            AddNotebookSnapshotCommand(
                actor_user_id=actor,
                kitchen_id=kitchen_id,
                source_notebook_id=source,
                snapshot_key=uuid4(),
            )
        )

    return call


def _save_call(actor: UUID, notebook_id: UUID) -> Callable[[Session], object]:
    def call(session: Session) -> object:
        return SqlAlchemyRecipeRepository(session).add(_new_recipe(actor, notebook_id))

    return call


def _new_recipe(actor: UUID, notebook_id: UUID) -> NewRecipe:
    return NewRecipe(
        title="Tomato rice",
        base_servings=4,
        servings_estimated=False,
        lines=(IngredientLine(name="rice", vague=False, quantity=1, unit="cup"),),
        steps=("Cook.",),
        source_text="Invented recipe text.",
        author_id=actor,
        notebook_id=notebook_id,
        save_key=uuid4(),
    )


def test_two_deletes_the_second_is_told_it_is_gone(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _holding_delete(holder, owner, notebook)
            worker, outcome = _in_background(factory, _delete_call(owner, notebook))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookNotFoundError)
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_a_rename_waiting_behind_a_delete_is_told_it_is_gone(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _holding_delete(holder, owner, notebook)
            worker, outcome = _in_background(factory, _rename_call(owner, notebook, "New"))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookNotFoundError)
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_a_delete_waiting_behind_a_rename_still_wins(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _holding_rename(holder, owner, notebook, "New")
            worker, outcome = _in_background(factory, _delete_call(owner, notebook))
            _release(worker, holder)

        assert outcome == [None]
        with factory() as db:
            assert db.get(NotebookModel, notebook) is None
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_the_last_rename_wins_even_back_to_the_name_it_first_read(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _holding_rename(holder, owner, notebook, "New")

            def back_to_soups(session: Session) -> object:
                # The first read happens here and sees "Soups", since the holder has not committed.
                return _rename_call(owner, notebook, "Soups")(session)

            worker, outcome = _in_background(factory, back_to_soups)
            _release(worker, holder)

        assert outcome == [None]
        with factory() as db:
            assert db.get(NotebookModel, notebook).name == "Soups"
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_a_snapshot_finishes_before_a_delete_of_its_original(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _snapshot_call(owner, kitchen, notebook)(holder)
            worker, outcome = _in_background(factory, _delete_call(owner, notebook))
            _release(worker, holder)

        assert outcome == [None]
        with factory() as db:
            copies = db.scalars(
                select(NotebookModel).where(NotebookModel.kitchen_id == kitchen)
            ).all()
            assert [(row.name, row.source_notebook_id) for row in copies] == [("Soups", None)]
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[kitchen], users=[owner])


def test_a_snapshot_waiting_behind_a_delete_finds_the_original_gone(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _holding_delete(holder, owner, notebook)
            worker, outcome = _in_background(factory, _snapshot_call(owner, kitchen, notebook))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookNotFoundError)
        with factory() as db:
            count = db.scalar(
                select(func.count())
                .select_from(NotebookModel)
                .where(NotebookModel.kitchen_id == kitchen)
            )
            assert count == 0
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[kitchen], users=[owner])


def test_an_invite_accepted_behind_a_delete_is_an_invalid_link(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner, person, notebook, raw = _committed_invite(factory)
    try:
        with factory() as holder:
            _holding_delete(holder, owner, notebook)
            worker, outcome = _in_background(factory, _accept_invite(person, raw))
            _release(worker, holder)

        assert isinstance(outcome[0], InvalidInviteTokenError)
    finally:
        _finish(factory, notebook, owner, person)


def test_a_save_behind_a_delete_is_told_the_notebook_is_gone(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        sources_before = _sources(factory, owner)
        with factory() as holder:
            _holding_delete(holder, owner, notebook)
            worker, outcome = _in_background(factory, _save_call(owner, notebook))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookNotFoundError)
        assert _sources(factory, owner) == sources_before
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_a_delete_behind_a_save_leaves_no_orphaned_source(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    try:
        with factory() as holder:
            _save_call(owner, notebook)(holder)
            # The notebook lock does not conflict with the save's FOR KEY SHARE; the full lock does.
            worker, outcome = _in_background(factory, _delete_call(owner, notebook))
            _release(worker, holder)

        assert outcome == [None]
        assert _sources(factory, owner) == 0
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def _sources(factory: sessionmaker[Session], user_id: UUID) -> int:
    with factory() as db:
        return (
            db.scalar(
                select(func.count()).select_from(SourceModel).where(SourceModel.user_id == user_id)
            )
            or 0
        )


def test_a_kitchen_deleted_during_a_rename_reads_as_the_notebook_gone(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    notebook = _kitchen_notebook_row(factory, kitchen, owner)
    try:
        with factory() as holder:
            holder.execute(delete(KitchenModel).where(KitchenModel.id == kitchen))
            worker, outcome = _in_background(factory, _rename_call(owner, notebook, "New"))
            _release(worker, holder)

        assert isinstance(outcome[0], NotebookNotFoundError)
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[kitchen], users=[owner])


@pytest.mark.parametrize("action", ["rename", "delete"])
def test_an_archive_first_refuses_a_waiting_rename_or_delete(engine: Engine, action: str) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    notebook = _kitchen_notebook_row(factory, kitchen, owner)
    call = (
        _rename_call(owner, notebook, "New")
        if action == "rename"
        else _delete_call(owner, notebook)
    )
    try:
        with factory() as holder:
            _archive_call(kitchen)(holder)
            worker, outcome = _in_background(factory, call)
            _release(worker, holder)

        assert isinstance(outcome[0], KitchenArchivedError)
        with factory() as db:
            assert db.get(NotebookModel, notebook).name == "Home book"
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[kitchen], users=[owner])


def test_an_archive_waits_for_a_rename_already_under_way(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    notebook = _kitchen_notebook_row(factory, kitchen, owner)
    try:
        with factory() as holder:
            _holding_rename(holder, owner, notebook, "New")
            worker, outcome = _in_background(factory, _archive_call(kitchen))
            _release(worker, holder)

        assert outcome == [None]
    finally:
        _cleanup(factory, notebooks=[notebook], kitchens=[kitchen], users=[owner])


def test_an_archive_first_stops_a_waiting_add(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    try:
        with factory() as holder:
            _archive_call(kitchen)(holder)
            worker, outcome = _in_background(factory, _add_call(owner, kitchen))
            _release(worker, holder)

        assert isinstance(outcome[0], KitchenArchivedError)
        with factory() as db:
            count = db.scalar(
                select(func.count())
                .select_from(NotebookModel)
                .where(NotebookModel.kitchen_id == kitchen)
            )
            assert count == 0
    finally:
        _cleanup(factory, notebooks=[], kitchens=[kitchen], users=[owner])


def test_an_add_first_makes_a_waiting_archive_wait(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    kitchen = _kitchen_row(factory, owner)
    try:
        with factory() as holder:
            CreateKitchenNotebookService(
                SqlAlchemyKitchenRepository(holder),
                SqlAlchemyNotebookRepository(holder),
                SqlAlchemyIngredientCatalog(holder),
                _SessionCommits(),
            ).execute(
                CreateKitchenNotebookCommand(actor_user_id=owner, kitchen_id=kitchen, name="New")
            )
            worker, outcome = _in_background(factory, _archive_call(kitchen))
            _assert_waiting(worker)
            holder.commit()
            worker.join(timeout=10)

        assert outcome == [None]
    finally:
        _cleanup(factory, notebooks=[], kitchens=[kitchen], users=[owner])


# --- All or nothing (T023) ---------------------------------------------------------------------


def test_a_failed_delete_leaves_the_notebook_complete(engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = _user(factory)
    notebook = _personal_row(factory, owner)
    with factory() as db:
        SqlAlchemyRecipeRepository(db).add(_new_recipe(owner, notebook))
        db.add(IngredientModel(notebook_id=notebook, name="rice"))
        db.commit()

    class FailingCommitter:
        def commit(self) -> None:
            raise RuntimeError("the disk is full")

    try:
        with factory() as session:
            with pytest.raises(RuntimeError):
                DeleteNotebookService(
                    SqlAlchemyNotebookRepository(session), FailingCommitter()
                ).execute(DeleteNotebookCommand(actor_user_id=owner, notebook_id=notebook))
            session.rollback()

        with factory() as db:
            assert db.get(NotebookModel, notebook) is not None
            recipes = db.scalar(
                select(func.count())
                .select_from(RecipeModel)
                .where(RecipeModel.notebook_id == notebook)
            )
            names = db.scalar(
                select(func.count())
                .select_from(IngredientModel)
                .where(IngredientModel.notebook_id == notebook)
            )
            members = db.scalar(
                select(func.count())
                .select_from(NotebookMembershipModel)
                .where(NotebookMembershipModel.notebook_id == notebook)
            )
            assert (recipes, names, members) == (1, 1, 1)
        assert _sources(factory, owner) == 1
    finally:
        with factory() as db:
            db.execute(delete(RecipeModel).where(RecipeModel.notebook_id == notebook))
            db.execute(delete(SourceModel).where(SourceModel.user_id == owner))
            db.commit()
        _cleanup(factory, notebooks=[notebook], kitchens=[], users=[owner])


def test_a_stale_save_answers_404_over_http_when_the_notebook_is_gone(
    client: TestClient, db_session: Session
) -> None:
    people, _kitchen, _notebook = _home(client, db_session)
    ana = people.as_("ana")
    book = _book(ana)
    assert ana.delete(f"/notebooks/{book}").status_code == 204

    response = ana.post(
        "/recipes",
        json={
            "save_key": str(uuid4()),
            "notebook_id": book,
            "title": "Rice",
            "base_servings": 2,
            "ingredient_lines": [{"name": "rice", "quantity": 1, "unit": "cup"}],
            "steps": ["Cook."],
        },
    )

    _refused(response, 404, "notebook_not_found")
