"""Domain + application signup tests (TDD — fakes, no DB)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest
from application.ports import NewKitchenRecord, NewMembershipRecord, NewUserRecord
from application.signup import SignupCommand, SignUpService
from domain.errors import DuplicateEmailError, InvalidSignupError
from domain.signup import personal_kitchen_name, validate_signup_input


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


@dataclass
class FakeSignupRepo:
    emails: set[str] = field(default_factory=set)
    users: list[NewUserRecord] = field(default_factory=list)
    kitchens: list[NewKitchenRecord] = field(default_factory=list)
    memberships: list[NewMembershipRecord] = field(default_factory=list)

    def email_exists(self, email: str) -> bool:
        return email in self.emails

    def create_user_with_personal_kitchen(
        self,
        *,
        user: NewUserRecord,
        personal_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None:
        self.emails.add(user.email)
        self.users.append(user)
        self.kitchens.append(personal_kitchen)
        self.memberships.append(membership)


def test_validate_signup_normalizes_email() -> None:
    assert validate_signup_input("  User@Example.COM ", "password1") == "user@example.com"


def test_validate_signup_rejects_bad_email() -> None:
    with pytest.raises(InvalidSignupError):
        validate_signup_input("not-an-email", "password1")


def test_validate_signup_rejects_short_password() -> None:
    with pytest.raises(InvalidSignupError):
        validate_signup_input("user@example.com", "short")


def test_validate_signup_rejects_whitespace_only_password() -> None:
    with pytest.raises(InvalidSignupError):
        validate_signup_input("user@example.com", "        ")


def test_signup_creates_user_and_exactly_one_personal_kitchen() -> None:
    repo = FakeSignupRepo()
    service = SignUpService(repo, FakeHasher())

    result = service.execute(SignupCommand(email="member@example.com", password="password1"))

    assert result.email == "member@example.com"
    assert result.kitchen_name == "Mi cocina"
    assert len(repo.users) == 1
    assert len(repo.kitchens) == 1
    assert len(repo.memberships) == 1
    assert repo.users[0].password_hash == "hashed:password1"
    assert "password1" not in repo.users[0].password_hash or repo.users[0].password_hash.startswith(
        "hashed:"
    )
    assert repo.kitchens[0].owner_id == result.user_id
    assert repo.memberships[0].kitchen_id == result.kitchen_id
    assert repo.memberships[0].user_id == result.user_id
    assert repo.memberships[0].role == "owner"
    assert isinstance(result.user_id, UUID)
    assert isinstance(result.kitchen_id, UUID)


def test_signup_rejects_duplicate_email() -> None:
    repo = FakeSignupRepo(emails={"member@example.com"})

    class CountingHasher(FakeHasher):
        def __init__(self) -> None:
            self.calls = 0

        def hash(self, password: str) -> str:
            self.calls += 1
            return super().hash(password)

    hasher = CountingHasher()
    service = SignUpService(repo, hasher)

    with pytest.raises(DuplicateEmailError):
        service.execute(SignupCommand(email="Member@Example.com", password="password1"))

    assert len(repo.users) == 0
    # Argon2-cost work still runs before existence short-circuit.
    assert hasher.calls == 1


def test_signup_fr4_off_does_not_require_verification_step() -> None:
    """When verification is not required, signup succeeds without a verify gate."""
    repo = FakeSignupRepo()
    service = SignUpService(repo, FakeHasher())

    result = service.execute(
        SignupCommand(
            email="member@example.com",
            password="password1",
            email_verification_required=False,
        )
    )

    assert result.user_id is not None
    assert len(repo.kitchens) == 1


@pytest.mark.parametrize(
    ("language", "name"),
    [("en", "My kitchen"), ("es", "Mi cocina"), (None, "Mi cocina"), ("fr", "Mi cocina")],
)
def test_personal_kitchen_name_follows_the_language_and_defaults_to_spanish(
    language: str | None, name: str
) -> None:
    assert personal_kitchen_name(language) == name


def test_signup_names_the_personal_kitchen_in_the_chosen_language() -> None:
    repo = FakeSignupRepo()
    service = SignUpService(repo, FakeHasher())

    result = service.execute(
        SignupCommand(email="member@example.com", password="password1", language="en")
    )

    assert result.kitchen_name == "My kitchen"
    assert repo.kitchens[0].name == "My kitchen"
