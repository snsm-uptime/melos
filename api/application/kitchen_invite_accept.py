"""Accept kitchen invite / signup-with-invite (Story 2.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from domain.errors import EmailNotVerifiedError, InvalidInviteTokenError, KitchenWriteError
from domain.kitchen_invite import (
    INVITE_MEMBER_ROLE,
    assert_invite_email_bind,
    assert_invite_token_redeemable,
    hash_invite_token,
    invite_email_hint,
    resolve_invite_preview_path,
)
from domain.signup import normalize_email

from application.email_verification import (
    EmailVerificationRepository,
    EnsureEmailVerifiedCommand,
    EnsureEmailVerifiedService,
)
from application.kitchen_invite import KitchenInviteTokenRecord, KitchenInviteTokenRepository
from application.kitchens import KitchenRecord, MembershipRecord
from application.ports import NewMembershipRecord
from application.signin import AuthUserRepository
from application.signup import SignupCommand, SignUpService


class KitchenInviteAcceptLookup(Protocol):
    def get_kitchen(self, kitchen_id: UUID) -> KitchenRecord | None: ...

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> MembershipRecord | None: ...

    def add_membership(self, membership: NewMembershipRecord) -> None: ...


class ClaimableKitchenInviteTokenRepository(KitchenInviteTokenRepository, Protocol):
    def claim_token(self, token_id: UUID, *, used_at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class AcceptKitchenInviteCommand:
    actor_user_id: UUID
    raw_token: str
    email_verification_required: bool


@dataclass(frozen=True, slots=True)
class AcceptKitchenInviteResult:
    kitchen_id: UUID
    already_member: bool = False


@dataclass(frozen=True, slots=True)
class SignUpWithInviteCommand:
    email: str
    password: str
    raw_token: str
    email_verification_required: bool


@dataclass(frozen=True, slots=True)
class SignUpWithInviteResult:
    user_id: UUID
    email: str
    personal_kitchen_id: UUID
    personal_kitchen_name: str
    inviting_kitchen_id: UUID | None
    requires_email_verification: bool


@dataclass(frozen=True, slots=True)
class PreviewKitchenInviteCommand:
    raw_token: str


@dataclass(frozen=True, slots=True)
class PreviewKitchenInviteResult:
    kitchen_name: str
    email_hint: str
    path: str  # "signup" | "join"


def _load_redeemable_invite(
    tokens: KitchenInviteTokenRepository,
    raw_token: str,
    *,
    now: datetime,
) -> KitchenInviteTokenRecord:
    token_hash = hash_invite_token(raw_token.strip())
    row = tokens.get_by_token_hash(token_hash)
    if row is None:
        raise InvalidInviteTokenError()
    assert_invite_token_redeemable(
        used_at=row.used_at,
        expires_at=row.expires_at,
        now=now,
    )
    return row


def _claim_or_raise(
    tokens: ClaimableKitchenInviteTokenRepository,
    token_id: UUID,
    *,
    now: datetime,
) -> None:
    if not tokens.claim_token(token_id, used_at=now):
        raise InvalidInviteTokenError()


def _require_inviting_kitchen(
    kitchens: KitchenInviteAcceptLookup,
    kitchen_id: UUID,
) -> None:
    if kitchens.get_kitchen(kitchen_id) is None:
        raise InvalidInviteTokenError()


def _add_invite_membership(
    kitchens: KitchenInviteAcceptLookup,
    *,
    kitchen_id: UUID,
    user_id: UUID,
) -> None:
    try:
        kitchens.add_membership(
            NewMembershipRecord(
                id=uuid4(),
                kitchen_id=kitchen_id,
                user_id=user_id,
                role=INVITE_MEMBER_ROLE,
            )
        )
    except KitchenWriteError as exc:
        # Deleted kitchen / unique race → calm invite error (or idempotent if won the race).
        if kitchens.get_membership(kitchen_id, user_id) is not None:
            return
        raise InvalidInviteTokenError() from exc


class AcceptKitchenInviteService:
    """Registered join + post-verify retry: email-bind → Ensure → claim → membership."""

    def __init__(
        self,
        tokens: ClaimableKitchenInviteTokenRepository,
        users: AuthUserRepository,
        kitchens: KitchenInviteAcceptLookup,
        verification: EmailVerificationRepository,
    ) -> None:
        self._tokens = tokens
        self._users = users
        self._kitchens = kitchens
        self._ensure = EnsureEmailVerifiedService(verification)

    def execute(self, command: AcceptKitchenInviteCommand) -> AcceptKitchenInviteResult:
        now = datetime.now(UTC)
        token_hash = hash_invite_token(command.raw_token.strip())
        invite = self._tokens.get_by_token_hash(token_hash)
        if invite is None:
            raise InvalidInviteTokenError()

        actor = self._users.get_by_id(command.actor_user_id)
        if actor is None:
            raise InvalidInviteTokenError()

        assert_invite_email_bind(invitee_email=invite.email, actor_email=actor.email)

        existing = self._kitchens.get_membership(invite.kitchen_id, command.actor_user_id)
        if existing is not None:
            # Idempotent silent success even if token already used/expired.
            if invite.used_at is None and invite.expires_at > now:
                self._tokens.claim_token(invite.id, used_at=now)
            return AcceptKitchenInviteResult(kitchen_id=invite.kitchen_id, already_member=True)

        assert_invite_token_redeemable(
            used_at=invite.used_at,
            expires_at=invite.expires_at,
            now=now,
        )

        self._ensure.execute(
            EnsureEmailVerifiedCommand(
                user_id=command.actor_user_id,
                email_verification_required=command.email_verification_required,
            )
        )

        _require_inviting_kitchen(self._kitchens, invite.kitchen_id)

        if not self._tokens.claim_token(invite.id, used_at=now):
            # Concurrent accept: winner claimed; if we already have membership, succeed.
            raced = self._kitchens.get_membership(invite.kitchen_id, command.actor_user_id)
            if raced is not None:
                return AcceptKitchenInviteResult(kitchen_id=invite.kitchen_id, already_member=True)
            raise InvalidInviteTokenError()

        _add_invite_membership(
            self._kitchens,
            kitchen_id=invite.kitchen_id,
            user_id=command.actor_user_id,
        )
        return AcceptKitchenInviteResult(kitchen_id=invite.kitchen_id, already_member=False)


class SignUpWithInviteService:
    """Unregistered path: compose SignUpService + invite accept rules.

    When EMAIL_VERIFICATION_REQUIRED is on, keep user/session/personal kitchen and
    return requires_email_verification=True without claiming the token or creating
    inviting membership (retry via AcceptKitchenInvite after verify).
    """

    def __init__(
        self,
        signup: SignUpService,
        tokens: ClaimableKitchenInviteTokenRepository,
        users: AuthUserRepository,
        kitchens: KitchenInviteAcceptLookup,
        verification: EmailVerificationRepository,
    ) -> None:
        self._signup = signup
        self._tokens = tokens
        self._users = users
        self._kitchens = kitchens
        self._ensure = EnsureEmailVerifiedService(verification)

    def execute(self, command: SignUpWithInviteCommand) -> SignUpWithInviteResult:
        now = datetime.now(UTC)
        invite = _load_redeemable_invite(self._tokens, command.raw_token, now=now)
        assert_invite_email_bind(invitee_email=invite.email, actor_email=command.email)
        _require_inviting_kitchen(self._kitchens, invite.kitchen_id)

        created = self._signup.execute(
            SignupCommand(
                email=command.email,
                password=command.password,
                email_verification_required=command.email_verification_required,
            )
        )

        try:
            self._ensure.execute(
                EnsureEmailVerifiedCommand(
                    user_id=created.user_id,
                    email_verification_required=command.email_verification_required,
                )
            )
        except EmailNotVerifiedError:
            return SignUpWithInviteResult(
                user_id=created.user_id,
                email=created.email,
                personal_kitchen_id=created.kitchen_id,
                personal_kitchen_name=created.kitchen_name,
                inviting_kitchen_id=None,
                requires_email_verification=True,
            )

        _claim_or_raise(self._tokens, invite.id, now=now)
        _add_invite_membership(
            self._kitchens,
            kitchen_id=invite.kitchen_id,
            user_id=created.user_id,
        )
        return SignUpWithInviteResult(
            user_id=created.user_id,
            email=created.email,
            personal_kitchen_id=created.kitchen_id,
            personal_kitchen_name=created.kitchen_name,
            inviting_kitchen_id=invite.kitchen_id,
            requires_email_verification=False,
        )


class PreviewKitchenInviteService:
    """Public safe preview for invite deep links (no membership side effects)."""

    def __init__(
        self,
        tokens: KitchenInviteTokenRepository,
        kitchens: KitchenInviteAcceptLookup,
        users: AuthUserRepository,
    ) -> None:
        self._tokens = tokens
        self._kitchens = kitchens
        self._users = users

    def execute(self, command: PreviewKitchenInviteCommand) -> PreviewKitchenInviteResult:
        now = datetime.now(UTC)
        invite = _load_redeemable_invite(self._tokens, command.raw_token, now=now)
        owned = self._kitchens.get_kitchen(invite.kitchen_id)
        if owned is None:
            raise InvalidInviteTokenError()

        invitee = self._users.get_by_email(normalize_email(invite.email))
        path = resolve_invite_preview_path(invitee_registered=invitee is not None)
        return PreviewKitchenInviteResult(
            kitchen_name=owned.name,
            email_hint=invite_email_hint(invite.email),
            path=path,
        )
