"""Domain + application kitchen create/rename tests (TDD — fakes, no DB)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.kitchens import (
    ArchiveKitchenCommand,
    ArchiveKitchenService,
    CreateOwnedKitchenCommand,
    CreateOwnedKitchenService,
    KitchenMembershipsCommand,
    KitchenMembershipsService,
    KitchenMembershipSummary,
    KitchenRecord,
    MembershipRecord,
    RenameKitchenCommand,
    RenameKitchenService,
)
from application.ports import NewKitchenRecord, NewMembershipRecord
from domain.errors import (
    InvalidKitchenNameError,
    KitchenNotFoundError,
    NotKitchenMemberError,
    NotKitchenOwnerError,
)
from domain.kitchens import validate_kitchen_name


@dataclass
class FakeKitchenRepo:
    kitchens: dict[UUID, KitchenRecord] = field(default_factory=dict)
    memberships: list[MembershipRecord] = field(default_factory=list)

    def create_owned_kitchen(
        self,
        *,
        owned_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None:
        self.kitchens[owned_kitchen.id] = KitchenRecord(
            id=owned_kitchen.id,
            name=owned_kitchen.name,
            owner_id=owned_kitchen.owner_id,
        )
        self.memberships.append(
            MembershipRecord(
                kitchen_id=membership.kitchen_id,
                user_id=membership.user_id,
                role=membership.role,
            )
        )

    def get_kitchen(self, kitchen_id: UUID) -> KitchenRecord | None:
        return self.kitchens.get(kitchen_id)

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> MembershipRecord | None:
        for m in self.memberships:
            if m.kitchen_id == kitchen_id and m.user_id == user_id:
                return m
        return None

    def update_kitchen_name(self, kitchen_id: UUID, name: str) -> KitchenRecord:
        current = self.kitchens[kitchen_id]
        updated = KitchenRecord(id=current.id, name=name, owner_id=current.owner_id)
        self.kitchens[kitchen_id] = updated
        return updated

    def archive_kitchen(self, kitchen_id: UUID) -> None:
        current = self.kitchens[kitchen_id]
        self.kitchens[kitchen_id] = KitchenRecord(
            id=current.id, name=current.name, owner_id=current.owner_id, is_archived=True
        )

    def unarchive_kitchen(self, kitchen_id: UUID) -> None:
        current = self.kitchens[kitchen_id]
        self.kitchens[kitchen_id] = KitchenRecord(
            id=current.id, name=current.name, owner_id=current.owner_id, is_archived=False
        )

    def kitchens_for_user(
        self, user_id: UUID, *, archived: bool = False
    ) -> list[KitchenMembershipSummary]:
        out: list[KitchenMembershipSummary] = []
        for m in self.memberships:
            if m.user_id != user_id:
                continue
            kitchen = self.kitchens[m.kitchen_id]
            if kitchen.is_archived != archived:
                continue
            out.append(
                KitchenMembershipSummary(
                    id=kitchen.id,
                    name=kitchen.name,
                    owner_id=kitchen.owner_id,
                    role=m.role,
                )
            )
        return out

    def get_kitchen_with_grant(self, grant, kitchen_id):  # type: ignore[no-untyped-def]
        from application.kitchen_access import assert_grant_kitchen_id

        assert_grant_kitchen_id(grant, kitchen_id)
        row = self.kitchens.get(kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        return row


def _owned_kitchen(repo: FakeKitchenRepo, owner: UUID, name: str = "Household") -> UUID:
    kitchen_id = uuid4()
    repo.create_owned_kitchen(
        owned_kitchen=NewKitchenRecord(id=kitchen_id, name=name, owner_id=owner),
        membership=NewMembershipRecord(
            id=uuid4(), kitchen_id=kitchen_id, user_id=owner, role="owner"
        ),
    )
    return kitchen_id


def test_validate_kitchen_name_trims() -> None:
    assert validate_kitchen_name("  Household  ") == "Household"


def test_validate_kitchen_name_rejects_empty() -> None:
    with pytest.raises(InvalidKitchenNameError):
        validate_kitchen_name("")


def test_validate_kitchen_name_rejects_whitespace_only() -> None:
    with pytest.raises(InvalidKitchenNameError):
        validate_kitchen_name("   \t  ")


def test_create_owned_kitchen_makes_creator_owner_and_member() -> None:
    repo = FakeKitchenRepo()
    actor = uuid4()
    service = CreateOwnedKitchenService(repo)

    result = service.execute(CreateOwnedKitchenCommand(actor_user_id=actor, name="Household"))

    assert result.name == "Household"
    assert result.owner_id == actor
    assert len(repo.kitchens) == 1
    assert len(repo.memberships) == 1
    assert repo.memberships[0].user_id == actor
    assert repo.memberships[0].role == "owner"
    assert repo.memberships[0].kitchen_id == result.id


def test_create_owned_kitchen_makes_no_notebook() -> None:
    """Kitchen creation takes only the kitchen repository (FR-008: no notebook)."""
    repo = FakeKitchenRepo()

    CreateOwnedKitchenService(repo).execute(
        CreateOwnedKitchenCommand(actor_user_id=uuid4(), name="Household")
    )

    assert len(repo.kitchens) == 1


def test_create_allows_multiple_owned_kitchens() -> None:
    repo = FakeKitchenRepo()
    actor = uuid4()
    # Seed personal kitchen (same entity) already owned.
    personal_id = uuid4()
    repo.create_owned_kitchen(
        owned_kitchen=NewKitchenRecord(id=personal_id, name="My kitchen", owner_id=actor),
        membership=NewMembershipRecord(
            id=uuid4(), kitchen_id=personal_id, user_id=actor, role="owner"
        ),
    )
    service = CreateOwnedKitchenService(repo)

    second = service.execute(CreateOwnedKitchenCommand(actor_user_id=actor, name="Trip"))

    owned = [kitchen for kitchen in repo.kitchens.values() if kitchen.owner_id == actor]
    assert len(owned) == 2
    assert {kitchen.name for kitchen in owned} == {"My kitchen", "Trip"}
    assert second.id != personal_id


def test_create_rejects_blank_name() -> None:
    service = CreateOwnedKitchenService(FakeKitchenRepo())
    with pytest.raises(InvalidKitchenNameError):
        service.execute(CreateOwnedKitchenCommand(actor_user_id=uuid4(), name="  "))


def test_owner_rename_updates_name_visible_via_membership_kitchen() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    member = uuid4()
    kitchen_id = _owned_kitchen(repo, owner, "Old")
    repo.memberships.append(MembershipRecord(kitchen_id=kitchen_id, user_id=member, role="member"))

    RenameKitchenService(repo).execute(
        RenameKitchenCommand(actor_user_id=owner, kitchen_id=kitchen_id, name="New Name")
    )

    summaries = KitchenMembershipsService(repo).execute(
        KitchenMembershipsCommand(actor_user_id=member)
    )
    assert len(summaries) == 1
    assert summaries[0].name == "New Name"


def test_non_member_rename_rejected() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    stranger = uuid4()
    kitchen_id = _owned_kitchen(repo, owner)

    with pytest.raises(NotKitchenMemberError):
        RenameKitchenService(repo).execute(
            RenameKitchenCommand(actor_user_id=stranger, kitchen_id=kitchen_id, name="Hacked")
        )
    assert repo.kitchens[kitchen_id].name == "Household"


def test_member_non_owner_rename_rejected() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    member = uuid4()
    kitchen_id = _owned_kitchen(repo, owner)
    repo.memberships.append(MembershipRecord(kitchen_id=kitchen_id, user_id=member, role="member"))

    with pytest.raises(NotKitchenOwnerError):
        RenameKitchenService(repo).execute(
            RenameKitchenCommand(actor_user_id=member, kitchen_id=kitchen_id, name="Renamed")
        )
    assert repo.kitchens[kitchen_id].name == "Household"


def test_rename_missing_kitchen_raises_not_member() -> None:
    with pytest.raises(NotKitchenMemberError):
        RenameKitchenService(FakeKitchenRepo()).execute(
            RenameKitchenCommand(actor_user_id=uuid4(), kitchen_id=uuid4(), name="X")
        )


def test_owner_archive_moves_kitchen_to_the_archived_view_for_members() -> None:
    """Archive is kitchen-wide: every member's archived view follows kitchens.is_archived."""
    repo = FakeKitchenRepo()
    owner = uuid4()
    member = uuid4()
    kitchen_id = _owned_kitchen(repo, owner)
    repo.memberships.append(MembershipRecord(kitchen_id=kitchen_id, user_id=member, role="member"))

    ArchiveKitchenService(repo).execute(
        ArchiveKitchenCommand(actor_user_id=owner, kitchen_id=kitchen_id)
    )

    member_default = KitchenMembershipsService(repo).execute(
        KitchenMembershipsCommand(actor_user_id=member)
    )
    member_archived = KitchenMembershipsService(repo).execute(
        KitchenMembershipsCommand(actor_user_id=member, archived=True)
    )
    assert member_default == []
    assert [s.id for s in member_archived] == [kitchen_id]
