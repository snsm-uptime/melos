"""Domain + application ACL port tests (TDD — fakes, no DB). Story 2.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
    assert_grant_kitchen_id,
)
from application.kitchens import (
    GetKitchenDetailCommand,
    GetKitchenDetailService,
    KitchenMembersCommand,
    KitchenMembershipSummary,
    KitchenMembersService,
    KitchenMemberView,
    KitchenRecord,
    MembershipRecord,
    SetLastOpenedKitchenCommand,
    SetLastOpenedKitchenService,
)
from application.ports import (
    KitchenAccessGrant,
    NewKitchenRecord,
    NewMembershipRecord,
    UserPreferencesRecord,
)
from domain.errors import KitchenNotFoundError, NotKitchenMemberError, NotKitchenOwnerError


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

    def kitchens_for_user(self, user_id: UUID) -> list[KitchenMembershipSummary]:
        out: list[KitchenMembershipSummary] = []
        for m in self.memberships:
            if m.user_id != user_id:
                continue
            kitchen = self.kitchens[m.kitchen_id]
            out.append(
                KitchenMembershipSummary(
                    id=kitchen.id,
                    name=kitchen.name,
                    owner_id=kitchen.owner_id,
                    role=m.role,
                )
            )
        return out

    def get_kitchen_with_grant(self, grant: KitchenAccessGrant, kitchen_id: UUID) -> KitchenRecord:
        assert_grant_kitchen_id(grant, kitchen_id)
        row = self.kitchens.get(kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        return row

    def kitchen_members_with_alias(self, kitchen_id: UUID) -> list[KitchenMemberView]:
        return [
            KitchenMemberView(user_id=m.user_id, alias=None)
            for m in self.memberships
            if m.kitchen_id == kitchen_id
        ]


@dataclass
class FakePrefsRepo:
    prefs: dict[UUID, UserPreferencesRecord] = field(default_factory=dict)

    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None:
        return self.prefs.get(user_id)

    def update_preferences(
        self,
        user_id: UUID,
        *,
        language: str | None = None,
        theme: str | None = None,
        last_opened_kitchen_id: UUID | None = None,
        clear_last_opened_kitchen_id: bool = False,
    ) -> UserPreferencesRecord:
        current = self.prefs[user_id]
        opened = current.last_opened_kitchen_id
        if clear_last_opened_kitchen_id:
            opened = None
        elif last_opened_kitchen_id is not None:
            opened = last_opened_kitchen_id
        updated = UserPreferencesRecord(
            id=current.id,
            email=current.email,
            language=language if language is not None else current.language,
            theme=theme if theme is not None else current.theme,
            last_opened_kitchen_id=opened,
        )
        self.prefs[user_id] = updated
        return updated


def _seed_owned(repo: FakeKitchenRepo, *, owner: UUID, name: str = "Household") -> UUID:
    kitchen_id = uuid4()
    repo.create_owned_kitchen(
        owned_kitchen=NewKitchenRecord(id=kitchen_id, name=name, owner_id=owner),
        membership=NewMembershipRecord(
            id=uuid4(), kitchen_id=kitchen_id, user_id=owner, role="owner"
        ),
    )
    return kitchen_id


def test_member_may_read_kitchen() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    member = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    repo.memberships.append(MembershipRecord(kitchen_id=kitchen_id, user_id=member, role="member"))

    grant = AuthorizeKitchenAccessService(repo).execute(
        AuthorizeKitchenAccessCommand(
            acting_user_id=member, kitchen_id=kitchen_id, action="read_kitchen"
        )
    )
    assert grant.kitchen_id == kitchen_id
    assert grant.action == "read_kitchen"


def test_non_member_read_denied_as_not_found() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    stranger = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)

    with pytest.raises(KitchenNotFoundError):
        AuthorizeKitchenAccessService(repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=stranger, kitchen_id=kitchen_id, action="read_kitchen"
            )
        )


def test_missing_kitchen_read_denied_as_not_found() -> None:
    repo = FakeKitchenRepo()
    with pytest.raises(KitchenNotFoundError):
        AuthorizeKitchenAccessService(repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=uuid4(), kitchen_id=uuid4(), action="read_kitchen"
            )
        )


def test_personal_kitchen_sole_member_allowed() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner, name="My kitchen")
    grant = AuthorizeKitchenAccessService(repo).execute(
        AuthorizeKitchenAccessCommand(
            acting_user_id=owner, kitchen_id=kitchen_id, action="read_kitchen"
        )
    )
    assert grant.acting_user_id == owner


def test_unknown_action_denied() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    with pytest.raises(NotKitchenMemberError):
        AuthorizeKitchenAccessService(repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=owner, kitchen_id=kitchen_id, action="admin_bypass"
            )
        )


def test_grant_kitchen_id_mismatch_rejected_at_repo() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    other = uuid4()
    grant = AuthorizeKitchenAccessService(repo).execute(
        AuthorizeKitchenAccessCommand(
            acting_user_id=owner, kitchen_id=kitchen_id, action="read_kitchen"
        )
    )
    with pytest.raises(KitchenNotFoundError):
        repo.get_kitchen_with_grant(grant, other)


def test_set_last_opened_non_member_is_not_kitchen_member() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    stranger = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    prefs = FakePrefsRepo()
    prefs.prefs[stranger] = UserPreferencesRecord(
        id=stranger, email="stranger@example.com", language=None, theme=None
    )

    with pytest.raises(NotKitchenMemberError):
        SetLastOpenedKitchenService(repo, prefs).execute(
            SetLastOpenedKitchenCommand(actor_user_id=stranger, kitchen_id=kitchen_id)
        )


def test_set_last_opened_member_persists() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    prefs = FakePrefsRepo()
    prefs.prefs[owner] = UserPreferencesRecord(
        id=owner, email="owner@example.com", language=None, theme=None
    )

    SetLastOpenedKitchenService(repo, prefs).execute(
        SetLastOpenedKitchenCommand(actor_user_id=owner, kitchen_id=kitchen_id)
    )
    assert prefs.prefs[owner].last_opened_kitchen_id == kitchen_id


def test_detail_and_members_use_acl() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    stranger = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)

    detail = GetKitchenDetailService(repo).execute(
        GetKitchenDetailCommand(actor_user_id=owner, kitchen_id=kitchen_id)
    )
    assert detail.id == kitchen_id

    roster = KitchenMembersService(repo).execute(
        KitchenMembersCommand(actor_user_id=owner, kitchen_id=kitchen_id)
    )
    assert [m.user_id for m in roster.members] == [owner]

    with pytest.raises(KitchenNotFoundError):
        GetKitchenDetailService(repo).execute(
            GetKitchenDetailCommand(actor_user_id=stranger, kitchen_id=kitchen_id)
        )
    with pytest.raises(KitchenNotFoundError):
        KitchenMembersService(repo).execute(
            KitchenMembersCommand(actor_user_id=stranger, kitchen_id=kitchen_id)
        )


def test_stale_last_opened_read_kitchen_fails_closed() -> None:
    """First-paint revalidation uses the read_kitchen grant, not a membership check alone."""
    repo = FakeKitchenRepo()
    owner = uuid4()
    former = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    # former never had membership — simulates lost membership / stale last-opened
    with pytest.raises(KitchenNotFoundError):
        AuthorizeKitchenAccessService(repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=former, kitchen_id=kitchen_id, action="read_kitchen"
            )
        )


def test_owner_action_member_non_owner_denied() -> None:
    repo = FakeKitchenRepo()
    owner = uuid4()
    member = uuid4()
    kitchen_id = _seed_owned(repo, owner=owner)
    repo.memberships.append(MembershipRecord(kitchen_id=kitchen_id, user_id=member, role="member"))
    with pytest.raises(NotKitchenOwnerError):
        AuthorizeKitchenAccessService(repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=member, kitchen_id=kitchen_id, action="rename_kitchen"
            )
        )
