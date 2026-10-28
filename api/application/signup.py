"""Sign-up use-case: create account + exactly one personal kitchen."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.errors import DuplicateEmailError
from domain.signup import personal_kitchen_name, validate_signup_input

from application.ports import (
    NewKitchenRecord,
    NewMembershipRecord,
    NewUserRecord,
    PasswordHasher,
    SignupRepository,
)


@dataclass(frozen=True, slots=True)
class SignupResult:
    user_id: UUID
    email: str
    kitchen_id: UUID
    kitchen_name: str


@dataclass(frozen=True, slots=True)
class SignupCommand:
    email: str
    password: str
    email_verification_required: bool = False
    # The language the visitor chose before signing up; names the first kitchen. None is Spanish.
    language: str | None = None


class SignUpService:
    def __init__(self, repo: SignupRepository, hasher: PasswordHasher) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(self, command: SignupCommand) -> SignupResult:
        email = validate_signup_input(command.email, command.password)
        # Hash before existence short-circuit so duplicate vs new signup share Argon2 cost.
        password_hash = self._hasher.hash(command.password)
        if self._repo.email_exists(email):
            raise DuplicateEmailError("An account with this email already exists.")

        # FR-4 off: no verification gate — account is immediately usable.
        # When verification is required (Story 1.5), register route auto-sends
        # verification mail; gating remains orthogonal via EnsureEmailVerifiedService.
        _ = command.email_verification_required

        kitchen_name = personal_kitchen_name(command.language)
        user_id = uuid4()
        kitchen_id = uuid4()
        membership_id = uuid4()

        self._repo.create_user_with_personal_kitchen(
            user=NewUserRecord(id=user_id, email=email, password_hash=password_hash),
            personal_kitchen=NewKitchenRecord(
                id=kitchen_id,
                name=kitchen_name,
                owner_id=user_id,
            ),
            membership=NewMembershipRecord(
                id=membership_id,
                kitchen_id=kitchen_id,
                user_id=user_id,
                role="owner",
            ),
        )
        return SignupResult(
            user_id=user_id,
            email=email,
            kitchen_id=kitchen_id,
            kitchen_name=kitchen_name,
        )
