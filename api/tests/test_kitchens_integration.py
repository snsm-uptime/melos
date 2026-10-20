"""Postgres integration tests for kitchen create/rename (Story 2.1).

Requires DATABASE_URL (Compose db or CI Postgres 16). Skips when unset.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from adapters.persistence.models import KitchenMembershipModel, KitchenModel
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.integration_db import alias_from_email, claim_alias, database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password1"},
    )
    assert response.status_code == 201, response.text
    claim_alias(client, email)


def test_unauthenticated_create_and_rename_rejected(client: TestClient) -> None:
    create = client.post("/kitchens", json={"name": "Household"})
    assert create.status_code == 401

    rename = client.patch(f"/kitchens/{uuid4()}", json={"name": "Nope"})
    assert rename.status_code == 401


def test_create_owned_kitchen_membership_and_multi_own(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "owner@example.com")

    first = client.get("/kitchens")
    assert first.status_code == 200
    personal = first.json()["kitchens"]
    assert len(personal) == 1
    assert personal[0]["name"] == "My kitchen"
    assert personal[0]["role"] == "owner"

    created = client.post("/kitchens", json={"name": "  Household  "})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Household"
    assert "owner_id" in body

    listed = client.get("/kitchens")
    assert listed.status_code == 200
    names = {item["name"] for item in listed.json()["kitchens"]}
    assert names == {"My kitchen", "Household"}
    for item in listed.json()["kitchens"]:
        assert len(item["members"]) == 1
        assert item["members"][0]["user_id"] == item["owner_id"]
        assert item["members"][0]["alias"] == "owner"

    kitchen_id = body["id"]
    row = db_session.get(KitchenModel, kitchen_id)
    assert row is not None
    assert row.name == "Household"
    memberships = db_session.scalars(
        select(KitchenMembershipModel).where(KitchenMembershipModel.kitchen_id == kitchen_id)
    ).all()
    assert len(memberships) == 1
    assert memberships[0].role == "owner"
    assert str(memberships[0].user_id) == str(row.owner_id)


def test_owner_rename_persists(client: TestClient, db_session: Session) -> None:
    _register(client, "renamer@example.com")
    created = client.post("/kitchens", json={"name": "Trip"})
    kitchen_id = created.json()["id"]

    renamed = client.patch(f"/kitchens/{kitchen_id}", json={"name": "Trip with Alex"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Trip with Alex"

    db_session.expire_all()
    row = db_session.get(KitchenModel, kitchen_id)
    assert row is not None
    assert row.name == "Trip with Alex"

    listed = client.get("/kitchens")
    match = next(item for item in listed.json()["kitchens"] if item["id"] == kitchen_id)
    assert match["name"] == "Trip with Alex"


def test_non_member_and_non_owner_rename_denied(client: TestClient, db_session: Session) -> None:
    _register(client, "owner2@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]
    owner_id = created.json()["owner_id"]

    # Second user: member but not owner
    client.post("/auth/sign-out")
    _register(client, "member@example.com")
    member_me = client.get("/auth/me")
    assert member_me.status_code == 200
    member_id = UUID(member_me.json()["user_id"])
    kitchen_uuid = UUID(kitchen_id)

    db_session.add(
        KitchenMembershipModel(
            id=uuid4(),
            kitchen_id=kitchen_uuid,
            user_id=member_id,
            role="member",
        )
    )
    db_session.flush()

    denied_member = client.patch(f"/kitchens/{kitchen_id}", json={"name": "Stolen"})
    assert denied_member.status_code == 403
    assert denied_member.json()["code"] == "not_kitchen_owner"

    # Stranger (no membership)
    client.post("/auth/sign-out")
    _register(client, "stranger@example.com")
    denied_stranger = client.patch(f"/kitchens/{kitchen_id}", json={"name": "Hacked"})
    assert denied_stranger.status_code == 404
    assert denied_stranger.json()["code"] == "kitchen_not_found"

    db_session.expire_all()
    row = db_session.get(KitchenModel, kitchen_id)
    assert row is not None
    assert row.name == "Household"
    assert str(row.owner_id) == str(owner_id)


def test_owner_archive_and_unarchive_round_trip(client: TestClient, db_session: Session) -> None:
    _register(client, "archiver@example.com")
    created = client.post("/kitchens", json={"name": "Trip"})
    kitchen_id = created.json()["id"]

    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["is_archived"] is True

    default_kitchens = client.get("/kitchens")
    ids_default = {item["id"] for item in default_kitchens.json()["kitchens"]}
    assert kitchen_id not in ids_default

    archived_kitchens = client.get("/kitchens", params={"archived": "true"})
    ids_archived = {item["id"] for item in archived_kitchens.json()["kitchens"]}
    assert kitchen_id in ids_archived

    unarchived = client.post(f"/kitchens/{kitchen_id}/unarchive")
    assert unarchived.status_code == 200, unarchived.text
    assert unarchived.json()["is_archived"] is False

    default_kitchens_again = client.get("/kitchens")
    ids_default_again = {item["id"] for item in default_kitchens_again.json()["kitchens"]}
    assert kitchen_id in ids_default_again


def test_non_owner_and_non_member_archive_denied(client: TestClient, db_session: Session) -> None:
    _register(client, "archiveowner@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]

    client.post("/auth/sign-out")
    _register(client, "archivemember@example.com")
    member_me = client.get("/auth/me")
    member_id = UUID(member_me.json()["user_id"])
    kitchen_uuid = UUID(kitchen_id)

    db_session.add(
        KitchenMembershipModel(
            id=uuid4(),
            kitchen_id=kitchen_uuid,
            user_id=member_id,
            role="member",
        )
    )
    db_session.flush()

    denied_member = client.post(f"/kitchens/{kitchen_id}/archive")
    assert denied_member.status_code == 403
    assert denied_member.json()["code"] == "not_kitchen_owner"

    client.post("/auth/sign-out")
    _register(client, "archivestranger@example.com")
    denied_stranger = client.post(f"/kitchens/{kitchen_id}/archive")
    assert denied_stranger.status_code == 404
    assert denied_stranger.json()["code"] == "kitchen_not_found"


def test_archive_unknown_kitchen_same_as_non_member(client: TestClient) -> None:
    _register(client, "archiveprober@example.com")
    response = client.post(f"/kitchens/{uuid4()}/archive")
    assert response.status_code == 404
    assert response.json()["code"] == "kitchen_not_found"


def test_archiving_preserves_membership(client: TestClient, db_session: Session) -> None:
    _register(client, "archivehistory@example.com")
    created = client.post("/kitchens", json={"name": "Shared"})
    kitchen_id = created.json()["id"]

    before_members = client.get(f"/kitchens/{kitchen_id}/members")
    assert before_members.status_code == 200

    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code == 200, archived.text

    after_members = client.get(f"/kitchens/{kitchen_id}/members")
    assert after_members.status_code == 200
    assert after_members.json() == before_members.json()

    # Detail endpoint stays unfiltered by archive state.
    detail = client.get(f"/kitchens/{kitchen_id}")
    assert detail.status_code == 200
    assert detail.json()["is_archived"] is True


def test_member_hide_and_unhide_round_trip(client: TestClient, db_session: Session) -> None:
    _register(client, "hideowner@example.com")
    created = client.post("/kitchens", json={"name": "Family"})
    kitchen_id = created.json()["id"]
    owner_id = created.json()["owner_id"]
    kitchen_uuid = UUID(kitchen_id)

    client.post("/auth/sign-out")
    _register(client, "hidemember@example.com")
    member_me = client.get("/auth/me")
    member_id = UUID(member_me.json()["user_id"])
    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=kitchen_uuid, user_id=member_id, role="member"
        )
    )
    db_session.flush()

    hidden = client.post(f"/kitchens/{kitchen_id}/hide")
    assert hidden.status_code == 204, hidden.text

    default_kitchens = client.get("/kitchens")
    ids_default = {item["id"] for item in default_kitchens.json()["kitchens"]}
    assert kitchen_id not in ids_default

    archived_kitchens = client.get("/kitchens", params={"archived": "true"})
    ids_archived = {item["id"] for item in archived_kitchens.json()["kitchens"]}
    assert kitchen_id in ids_archived

    unhidden = client.post(f"/kitchens/{kitchen_id}/unhide")
    assert unhidden.status_code == 204, unhidden.text

    default_kitchens_again = client.get("/kitchens")
    ids_default_again = {item["id"] for item in default_kitchens_again.json()["kitchens"]}
    assert kitchen_id in ids_default_again

    # Owner's own view was never affected, at no point in the round trip.
    client.post("/auth/sign-out")
    client.post("/auth/sign-in", json={"email": "hideowner@example.com", "password": "password1"})
    owner_kitchens = client.get("/kitchens")
    owner_ids = {item["id"] for item in owner_kitchens.json()["kitchens"]}
    assert kitchen_id in owner_ids
    assert owner_id == created.json()["owner_id"]


def test_member_hide_preserves_membership_and_is_owner_invisible(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "hidehistoryowner@example.com")
    created = client.post("/kitchens", json={"name": "Shared"})
    kitchen_id = created.json()["id"]
    kitchen_uuid = UUID(kitchen_id)

    client.post("/auth/sign-out")
    _register(client, "hidehistorymember@example.com")
    member_me = client.get("/auth/me")
    member_id = UUID(member_me.json()["user_id"])
    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=kitchen_uuid, user_id=member_id, role="member"
        )
    )
    db_session.flush()

    before_members = client.get(f"/kitchens/{kitchen_id}/members")
    assert before_members.status_code == 200

    hidden = client.post(f"/kitchens/{kitchen_id}/hide")
    assert hidden.status_code == 204, hidden.text

    after_members = client.get(f"/kitchens/{kitchen_id}/members")
    assert after_members.status_code == 200
    assert after_members.json() == before_members.json()

    # Detail endpoint stays unfiltered, same rule as owner archiving.
    detail = client.get(f"/kitchens/{kitchen_id}")
    assert detail.status_code == 200

    # Owner's default listing is unaffected by a member's personal hide.
    client.post("/auth/sign-out")
    client.post(
        "/auth/sign-in",
        json={"email": "hidehistoryowner@example.com", "password": "password1"},
    )
    owner_kitchens = client.get("/kitchens")
    assert kitchen_id in {item["id"] for item in owner_kitchens.json()["kitchens"]}


def test_owner_hide_rejected(client: TestClient) -> None:
    _register(client, "hideself@example.com")
    created = client.post("/kitchens", json={"name": "Trip"})
    kitchen_id = created.json()["id"]

    response = client.post(f"/kitchens/{kitchen_id}/hide")
    assert response.status_code == 403
    assert response.json()["code"] == "cannot_hide_owned_kitchen"


def test_non_member_hide_denied(client: TestClient, db_session: Session) -> None:
    _register(client, "hidestranger_owner@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]

    client.post("/auth/sign-out")
    _register(client, "hidestranger@example.com")
    response = client.post(f"/kitchens/{kitchen_id}/hide")
    assert response.status_code == 404
    assert response.json()["code"] == "kitchen_not_found"


def test_hide_unknown_kitchen_same_as_non_member(client: TestClient) -> None:
    _register(client, "hideprober@example.com")
    response = client.post(f"/kitchens/{uuid4()}/hide")
    assert response.status_code == 404
    assert response.json()["code"] == "kitchen_not_found"


def test_owner_unhide_rejected(client: TestClient) -> None:
    _register(client, "unhideself@example.com")
    created = client.post("/kitchens", json={"name": "Trip"})
    kitchen_id = created.json()["id"]

    response = client.post(f"/kitchens/{kitchen_id}/unhide")
    assert response.status_code == 403
    assert response.json()["code"] == "cannot_hide_owned_kitchen"


def test_owner_archiving_still_hides_kitchen_for_member_who_never_hid_it(
    client: TestClient, db_session: Session
) -> None:
    """Regression guard: a member's personal hide is additive to, never a
    replacement for, the owner's kitchen-wide archive (Story 9.1 behavior)."""
    _register(client, "archregowner@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]
    kitchen_uuid = UUID(kitchen_id)

    client.post("/auth/sign-out")
    _register(client, "archregmember@example.com")
    member_me = client.get("/auth/me")
    member_id = UUID(member_me.json()["user_id"])
    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=kitchen_uuid, user_id=member_id, role="member"
        )
    )
    db_session.flush()

    default_before = client.get("/kitchens")
    assert kitchen_id in {item["id"] for item in default_before.json()["kitchens"]}

    client.post("/auth/sign-out")
    client.post(
        "/auth/sign-in", json={"email": "archregowner@example.com", "password": "password1"}
    )
    archived = client.post(f"/kitchens/{kitchen_id}/archive")
    assert archived.status_code == 200, archived.text

    client.post("/auth/sign-out")
    client.post(
        "/auth/sign-in", json={"email": "archregmember@example.com", "password": "password1"}
    )
    member_default = client.get("/kitchens")
    assert kitchen_id not in {item["id"] for item in member_default.json()["kitchens"]}
    member_archived = client.get("/kitchens", params={"archived": "true"})
    assert kitchen_id in {item["id"] for item in member_archived.json()["kitchens"]}


def test_member_hide_state_is_isolated_per_member(client: TestClient, db_session: Session) -> None:
    _register(client, "isoowner@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]
    kitchen_uuid = UUID(kitchen_id)

    client.post("/auth/sign-out")
    _register(client, "isomembera@example.com")
    member_a_me = client.get("/auth/me")
    member_a_id = UUID(member_a_me.json()["user_id"])
    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=kitchen_uuid, user_id=member_a_id, role="member"
        )
    )
    db_session.flush()

    client.post("/auth/sign-out")
    _register(client, "isomemberb@example.com")
    member_b_me = client.get("/auth/me")
    member_b_id = UUID(member_b_me.json()["user_id"])
    db_session.add(
        KitchenMembershipModel(
            id=uuid4(), kitchen_id=kitchen_uuid, user_id=member_b_id, role="member"
        )
    )
    db_session.flush()

    client.post("/auth/sign-out")
    client.post("/auth/sign-in", json={"email": "isomembera@example.com", "password": "password1"})
    hidden = client.post(f"/kitchens/{kitchen_id}/hide")
    assert hidden.status_code == 204, hidden.text

    a_default = client.get("/kitchens")
    assert kitchen_id not in {item["id"] for item in a_default.json()["kitchens"]}

    client.post("/auth/sign-out")
    client.post("/auth/sign-in", json={"email": "isomemberb@example.com", "password": "password1"})
    b_default = client.get("/kitchens")
    assert kitchen_id in {item["id"] for item in b_default.json()["kitchens"]}


def test_blank_name_rejected(client: TestClient) -> None:
    _register(client, "blank@example.com")
    for name in ("   ", ""):
        response = client.post("/kitchens", json={"name": name})
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "invalid_kitchen_name"


def test_rename_unknown_kitchen_same_as_non_member(client: TestClient) -> None:
    _register(client, "prober@example.com")
    unknown = client.patch(f"/kitchens/{uuid4()}", json={"name": "Nope"})
    assert unknown.status_code == 403
    assert unknown.json()["code"] == "not_kitchen_member"
    assert unknown.json()["detail"] == "You do not have access to this kitchen."


def test_membership_listing_excludes_non_member_kitchens(client: TestClient) -> None:
    _register(client, "alice@example.com")
    created = client.post("/kitchens", json={"name": "Alice House"})
    alice_kitchen = created.json()["id"]
    assert created.status_code == 201

    client.post("/auth/sign-out")
    _register(client, "bob@example.com")
    listed = client.get("/kitchens")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["kitchens"]}
    assert alice_kitchen not in ids


def test_non_member_reads_return_kitchen_not_found(client: TestClient) -> None:
    _register(client, "owner-acl@example.com")
    created = client.post("/kitchens", json={"name": "Secret"})
    kitchen_id = created.json()["id"]

    client.post("/auth/sign-out")
    _register(client, "outsider@example.com")

    for path in (
        f"/kitchens/{kitchen_id}",
        f"/kitchens/{kitchen_id}/members",
    ):
        response = client.get(path)
        assert response.status_code == 404, response.text
        body = response.json()
        assert body["code"] == "kitchen_not_found"
        assert body["detail"] == "Kitchen not found."

    missing = client.get(f"/kitchens/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "kitchen_not_found"


def test_member_detail_and_members_ok(client: TestClient) -> None:
    _register(client, "reader@example.com")
    created = client.post("/kitchens", json={"name": "Household"})
    kitchen_id = created.json()["id"]

    detail = client.get(f"/kitchens/{kitchen_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["name"] == "Household"
    assert "owner_id" in detail.json()

    members = client.get(f"/kitchens/{kitchen_id}/members")
    assert members.status_code == 200
    assert [m["alias"] for m in members.json()["members"]] == [
        alias_from_email("reader@example.com")
    ]


def test_set_last_opened_kitchen_member_and_non_member(client: TestClient) -> None:
    _register(client, "remember@example.com")
    created = client.post("/kitchens", json={"name": "Trip"})
    kitchen_id = created.json()["id"]

    patched = client.patch("/auth/me", json={"last_opened_kitchen_id": kitchen_id})
    assert patched.status_code == 200, patched.text
    assert patched.json()["last_opened_kitchen_id"] == kitchen_id

    me = client.get("/auth/me")
    assert me.json()["last_opened_kitchen_id"] == kitchen_id

    client.post("/auth/sign-out")
    _register(client, "nosy@example.com")
    denied = client.patch("/auth/me", json={"last_opened_kitchen_id": kitchen_id})
    assert denied.status_code == 404
    assert denied.json()["code"] == "kitchen_not_found"

    missing = client.patch("/auth/me", json={"last_opened_kitchen_id": str(uuid4())})
    assert missing.status_code == 404
    assert missing.json()["code"] == "kitchen_not_found"
