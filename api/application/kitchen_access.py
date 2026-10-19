"""authorize_kitchen_access application service — Story 2.2 ACL port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from domain.errors import KitchenNotFoundError, NotKitchenMemberError, NotKitchenOwnerError
from domain.kitchen_access import (
    deny_as_not_found_for_action,
    is_owner_action,
    normalize_kitchen_action,
)

from application.ports import KitchenAccessGrant


@dataclass(frozen=True, slots=True)
class _KitchenPeek:
    id: UUID
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class _MembershipPeek:
    user_id: UUID
    role: str


class KitchenAccessLookup(Protocol):
    """Narrow repo surface for ACL — avoids importing full KitchenRepository."""

    def get_kitchen(self, kitchen_id: UUID) -> _KitchenPeek | None: ...

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> _MembershipPeek | None: ...


@dataclass(frozen=True, slots=True)
class AuthorizeKitchenAccessCommand:
    acting_user_id: UUID
    kitchen_id: UUID
    action: str


class AuthorizeKitchenAccessService:
    """Single ACL choke: membership (+ owner when required) → KitchenAccessGrant."""

    def __init__(self, lookup: KitchenAccessLookup) -> None:
        self._lookup = lookup

    def execute(self, command: AuthorizeKitchenAccessCommand) -> KitchenAccessGrant:
        canonical = normalize_kitchen_action(command.action)
        if canonical is None:
            # Fail closed — treat unknown like a mutation deny (403 path).
            raise NotKitchenMemberError()

        existing = self._lookup.get_kitchen(command.kitchen_id)
        membership = self._lookup.get_membership(command.kitchen_id, command.acting_user_id)

        # Structural duck-typing: any object with owner_id / user_id+role works.
        if existing is None or membership is None:
            if deny_as_not_found_for_action(canonical):
                raise KitchenNotFoundError()
            raise NotKitchenMemberError()

        owner_id = existing.owner_id
        if is_owner_action(canonical) and not (
            membership.user_id == owner_id or membership.role == "owner"
        ):
            raise NotKitchenOwnerError()

        return KitchenAccessGrant(
            kitchen_id=command.kitchen_id,
            action=canonical,
            acting_user_id=command.acting_user_id,
        )


def assert_grant_kitchen_id(grant: KitchenAccessGrant, kitchen_id: UUID) -> None:
    """Repositories must reject a grant whose kitchen_id does not match the call."""
    if grant.kitchen_id != kitchen_id:
        raise KitchenNotFoundError()


class KitchenAccessAuthorizerAdapter:
    """Adapter implementing KitchenAccessAuthorizer Protocol via AuthorizeKitchenAccessService."""

    def __init__(self, lookup: KitchenAccessLookup) -> None:
        self._service = AuthorizeKitchenAccessService(lookup)

    def authorize_kitchen_access(
        self,
        acting_user_id: UUID,
        kitchen_id: UUID,
        action: str,
    ) -> KitchenAccessGrant:
        return self._service.execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=acting_user_id,
                kitchen_id=kitchen_id,
                action=action,
            )
        )
