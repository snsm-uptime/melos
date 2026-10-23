"""Create owned kitchens, rename, archive/hide, membership listing, ACL reads — 2.1 / 2.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from domain.errors import (
    CannotHideOwnedKitchenError,
    NotKitchenMemberError,
    NotKitchenOwnerError,
)
from domain.kitchens import validate_kitchen_name
from domain.notebook import Notebook

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.ports import (
    KitchenAccessGrant,
    NewKitchenRecord,
    NewMembershipRecord,
    NotebookRepository,
    PreferencesRepository,
)


@dataclass(frozen=True, slots=True)
class KitchenRecord:
    id: UUID
    name: str
    owner_id: UUID
    is_archived: bool = False


@dataclass(frozen=True, slots=True)
class MembershipRecord:
    kitchen_id: UUID
    user_id: UUID
    role: str


@dataclass(frozen=True, slots=True)
class KitchenMemberLabel:
    """Roster label on membership summaries — alias only, never email."""

    user_id: UUID
    alias: str | None = None
    photo_base64: str | None = None


@dataclass(frozen=True, slots=True)
class KitchenMembershipSummary:
    id: UUID
    name: str
    owner_id: UUID
    role: str
    members: tuple[KitchenMemberLabel, ...] = ()


@dataclass(frozen=True, slots=True)
class KitchenMemberView:
    user_id: UUID
    # Null only for accounts that have not passed the alias gate yet.
    alias: str | None
    photo_base64: str | None = None


class KitchenRepository(Protocol):
    def create_owned_kitchen(
        self,
        *,
        owned_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None: ...

    def get_kitchen(self, kitchen_id: UUID) -> KitchenRecord | None: ...

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> MembershipRecord | None: ...

    def update_kitchen_name(self, kitchen_id: UUID, name: str) -> KitchenRecord: ...

    def delete_kitchen(self, kitchen_id: UUID) -> None: ...

    def archive_kitchen(self, kitchen_id: UUID) -> None: ...

    def unarchive_kitchen(self, kitchen_id: UUID) -> None: ...

    def hide_kitchen_for_member(self, kitchen_id: UUID, user_id: UUID) -> None: ...

    def unhide_kitchen_for_member(self, kitchen_id: UUID, user_id: UUID) -> None: ...

    def kitchens_for_user(
        self, user_id: UUID, *, archived: bool = False
    ) -> list[KitchenMembershipSummary]: ...

    def get_kitchen_with_grant(
        self, grant: KitchenAccessGrant, kitchen_id: UUID
    ) -> KitchenRecord: ...

    def kitchen_members_with_alias(self, kitchen_id: UUID) -> list[KitchenMemberView]: ...


@dataclass(frozen=True, slots=True)
class CreateOwnedKitchenCommand:
    actor_user_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class RenameKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class DeleteKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class KitchenMembershipsCommand:
    actor_user_id: UUID
    archived: bool = False


@dataclass(frozen=True, slots=True)
class ArchiveKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class UnarchiveKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class HideKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class UnhideKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class GetKitchenDetailCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class KitchenMembersCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class KitchenMembersResult:
    kitchen_id: UUID
    members: tuple[KitchenMemberView, ...]


@dataclass(frozen=True, slots=True)
class SetLastOpenedKitchenCommand:
    actor_user_id: UUID
    kitchen_id: UUID


def _require_owner(repo: KitchenRepository, kitchen_id: UUID, actor_user_id: UUID) -> None:
    """Owner-only mutation guard.

    Missing kitchen and non-membership share the same rejection so the action
    cannot be used as a kitchen-existence oracle (NFR-3). As-built 2.1: ad-hoc
    ACL (not the shared port) with grandfathered HTTP 403.
    """
    existing = repo.get_kitchen(kitchen_id)
    membership = repo.get_membership(kitchen_id, actor_user_id)
    if existing is None or membership is None:
        raise NotKitchenMemberError()
    if existing.owner_id != actor_user_id:
        raise NotKitchenOwnerError()


def _require_non_owner_member(
    repo: KitchenRepository, kitchen_id: UUID, actor_user_id: UUID
) -> None:
    existing = repo.get_kitchen(kitchen_id)
    membership = repo.get_membership(kitchen_id, actor_user_id)
    if existing is None or membership is None:
        raise NotKitchenMemberError()
    if existing.owner_id == actor_user_id:
        raise CannotHideOwnedKitchenError()


class CreateOwnedKitchenService:
    """Create an additional named kitchen owned by the authenticated user.

    Same Kitchen entity as personal kitchens; the creator is the sole owner-member.
    The kitchen's notebook is created in the same transaction (spec 055 FR-001).
    """

    def __init__(self, repo: KitchenRepository, notebooks: NotebookRepository) -> None:
        self._repo = repo
        self._notebooks = notebooks

    def execute(self, command: CreateOwnedKitchenCommand) -> KitchenRecord:
        name = validate_kitchen_name(command.name)
        kitchen_id = uuid4()
        owned = NewKitchenRecord(
            id=kitchen_id,
            name=name,
            owner_id=command.actor_user_id,
        )
        membership = NewMembershipRecord(
            id=uuid4(),
            kitchen_id=kitchen_id,
            user_id=command.actor_user_id,
            role="owner",
        )
        self._repo.create_owned_kitchen(owned_kitchen=owned, membership=membership)
        self._notebooks.create(Notebook(id=uuid4(), kitchen_id=kitchen_id))
        return KitchenRecord(id=kitchen_id, name=name, owner_id=command.actor_user_id)


class RenameKitchenService:
    """Rename a kitchen — owner-only (FR-6); non-members and non-owner members rejected."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: RenameKitchenCommand) -> KitchenRecord:
        name = validate_kitchen_name(command.name)
        _require_owner(self._repo, command.kitchen_id, command.actor_user_id)
        return self._repo.update_kitchen_name(command.kitchen_id, name)


class DeleteKitchenService:
    """Delete a kitchen — owner-only; non-members and non-owner members rejected."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: DeleteKitchenCommand) -> None:
        _require_owner(self._repo, command.kitchen_id, command.actor_user_id)
        self._repo.delete_kitchen(command.kitchen_id)


class ArchiveKitchenService:
    """Archive a kitchen — owner-only; non-members and non-owner members rejected."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: ArchiveKitchenCommand) -> KitchenRecord:
        _require_owner(self._repo, command.kitchen_id, command.actor_user_id)
        self._repo.archive_kitchen(command.kitchen_id)
        return self._repo.get_kitchen(command.kitchen_id)


class UnarchiveKitchenService:
    """Unarchive a kitchen — owner-only; non-members and non-owner members rejected."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: UnarchiveKitchenCommand) -> KitchenRecord:
        _require_owner(self._repo, command.kitchen_id, command.actor_user_id)
        self._repo.unarchive_kitchen(command.kitchen_id)
        return self._repo.get_kitchen(command.kitchen_id)


class HideKitchenService:
    """Hide a kitchen from a non-owner member's own dashboard — personal view filter.

    Unlike ArchiveKitchenService, this is member-only: the owner must use the
    archive action instead, since hiding is scoped to one member's membership
    row and has no meaning for the owner's own kitchen.
    """

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: HideKitchenCommand) -> None:
        _require_non_owner_member(self._repo, command.kitchen_id, command.actor_user_id)
        self._repo.hide_kitchen_for_member(command.kitchen_id, command.actor_user_id)


class UnhideKitchenService:
    """Unhide a kitchen previously hidden by a non-owner member."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: UnhideKitchenCommand) -> None:
        _require_non_owner_member(self._repo, command.kitchen_id, command.actor_user_id)
        self._repo.unhide_kitchen_for_member(command.kitchen_id, command.actor_user_id)


class KitchenMembershipsService:
    """Membership-scoped kitchen summaries for the authenticated user.

    Actor-scoped enumeration — does not call authorize_kitchen_access.
    """

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: KitchenMembershipsCommand) -> list[KitchenMembershipSummary]:
        return self._repo.kitchens_for_user(command.actor_user_id, archived=command.archived)


class GetKitchenDetailService:
    """Kitchen detail shell for members — authorize_kitchen_access(read_kitchen)."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: GetKitchenDetailCommand) -> KitchenRecord:
        grant = AuthorizeKitchenAccessService(self._repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        return self._repo.get_kitchen_with_grant(grant, command.kitchen_id)


class KitchenMembersService:
    """Member roster — authorize_kitchen_access(read_kitchen)."""

    def __init__(self, repo: KitchenRepository) -> None:
        self._repo = repo

    def execute(self, command: KitchenMembersCommand) -> KitchenMembersResult:
        grant = AuthorizeKitchenAccessService(self._repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        self._repo.get_kitchen_with_grant(grant, command.kitchen_id)
        members = self._repo.kitchen_members_with_alias(command.kitchen_id)
        return KitchenMembersResult(kitchen_id=command.kitchen_id, members=tuple(members))


class SetLastOpenedKitchenService:
    """Remember last-opened kitchen — authorize_kitchen_access(set_last_opened_kitchen) → 403."""

    def __init__(self, kitchen_repo: KitchenRepository, prefs_repo: PreferencesRepository) -> None:
        self._kitchen_repo = kitchen_repo
        self._prefs_repo = prefs_repo

    def execute(self, command: SetLastOpenedKitchenCommand) -> UUID:
        AuthorizeKitchenAccessService(self._kitchen_repo).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="set_last_opened_kitchen",
            )
        )
        self._prefs_repo.update_preferences(
            command.actor_user_id,
            last_opened_kitchen_id=command.kitchen_id,
        )
        return command.kitchen_id
