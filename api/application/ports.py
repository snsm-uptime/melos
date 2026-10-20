"""Ports for application use-cases (implemented by adapters)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from uuid import UUID

# Canonical session TTL (30d).
# adapters.persistence.sessions re-exports this for SESSION_COOKIE_MAX_AGE.
DEFAULT_SESSION_TTL = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class NewUserRecord:
    id: UUID
    email: str
    password_hash: str


@dataclass(frozen=True, slots=True)
class NewKitchenRecord:
    id: UUID
    name: str
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class NewMembershipRecord:
    id: UUID
    kitchen_id: UUID
    user_id: UUID
    role: str


@dataclass(frozen=True, slots=True)
class UserPreferencesRecord:
    id: UUID
    email: str
    language: str | None
    theme: str | None
    last_opened_kitchen_id: UUID | None = None
    alias: str | None = None
    photo_base64: str | None = None


@dataclass(frozen=True, slots=True)
class KitchenAccessGrant:
    """Opaque per-request grant binding kitchen_id + authorized action."""

    kitchen_id: UUID
    action: str
    acting_user_id: UUID


class KitchenAccessAuthorizer(Protocol):
    """Canonical ACL port — authorize_kitchen_access(acting_user_id, kitchen_id, action)."""

    def authorize_kitchen_access(
        self,
        acting_user_id: UUID,
        kitchen_id: UUID,
        action: str,
    ) -> KitchenAccessGrant: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class SessionStore(Protocol):
    def create(self, user_id: UUID, *, ttl: timedelta = DEFAULT_SESSION_TTL) -> str: ...

    def resolve_user_id(self, token: str | None) -> UUID | None: ...

    def revoke(self, token: str | None) -> bool: ...

    def revoke_all_for_user(self, user_id: UUID) -> int: ...


class PreferencesRepository(Protocol):
    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None: ...

    def update_preferences(
        self,
        user_id: UUID,
        *,
        language: str | None = None,
        theme: str | None = None,
        last_opened_kitchen_id: UUID | None = None,
        clear_last_opened_kitchen_id: bool = False,
        photo_base64: str | None = None,
        clear_photo: bool = False,
    ) -> UserPreferencesRecord: ...

    def claim_alias(self, user_id: UUID, alias: str) -> UserPreferencesRecord:
        """Claim a normalized alias for a user that has none.

        Raises AliasAlreadySetError when one is stored (rename is deferred) and
        AliasTakenError when the case-insensitive unique index rejects the write.
        """
        ...


class SignupRepository(Protocol):
    def email_exists(self, email: str) -> bool: ...

    def create_user_with_personal_kitchen(
        self,
        *,
        user: NewUserRecord,
        personal_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to_address: str
    subject: str
    body_text: str
    body_html: str | None = None


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Send transactional email. Raises SmtpConfigurationError / SmtpSendError on failure."""
        ...
