"""Dev/worktree-only seed: pre-verified accounts with optional shared kitchen.

Runs from scripts.entrypoint when SEED_DEV_USER is truthy. Idempotent — existing
accounts are left untouched. Recipes, carts, shopping lists and conversations are
seeded once their schema exists.

Environment:
- SEED_DEV_USER_EMAIL / SEED_DEV_USER_PASSWORD (required — owner account)
- SEED_DEV_USER_ALIAS (optional; claimed so kitchen surfaces are usable)
- SEED_DEV_USER_KITCHEN (optional; a shared kitchen with owner + member)
  When set, creates a second user (derived from email) and adds them as member.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from adapters.persistence.db import get_session_factory
from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.password_hasher import Argon2PasswordHasher
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
    SqlAlchemySignupRepository,
)
from application.kitchens import CreateOwnedKitchenCommand, CreateOwnedKitchenService
from application.preferences import SetAliasCommand, SetAliasService
from application.ports import NewMembershipRecord
from application.signup import SignupCommand, SignUpService
from domain.signup import normalize_email

logger = logging.getLogger(__name__)


def _member_email(owner_email: str) -> str:
    """Derive member email from owner (owner@example.com → owner+member@example.com)."""
    parts = owner_email.rsplit("@", 1)
    if len(parts) == 2:
        return f"{parts[0]}+member@{parts[1]}"
    return f"{owner_email}+member"


def seed() -> None:
    owner_email = (os.environ.get("SEED_DEV_USER_EMAIL") or "").strip()
    owner_password = os.environ.get("SEED_DEV_USER_PASSWORD") or ""
    if not owner_email or not owner_password:
        logger.warning("SEED_DEV_USER set but SEED_DEV_USER_EMAIL/PASSWORD missing — skipping")
        return
    owner_alias = (os.environ.get("SEED_DEV_USER_ALIAS") or "").strip()
    kitchen_name = (os.environ.get("SEED_DEV_USER_KITCHEN") or "").strip()

    session = get_session_factory()()
    try:
        signup_repo = SqlAlchemySignupRepository(session)
        kitchen_repo = SqlAlchemyKitchenRepository(session)
        auth_repo = SqlAlchemyAuthUserRepository(session)
        email_repo = SqlAlchemyEmailVerificationRepository(session)

        # Owner user — create if not exists
        owner_exists = signup_repo.email_exists(normalize_email(owner_email))
        if owner_exists:
            logger.info("Owner user already exists — seed skipped")
            return

        owner = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
            SignupCommand(email=owner_email, password=owner_password)
        )
        email_repo.mark_email_verified(owner.user_id, verified_at=datetime.now(UTC))
        if owner_alias:
            SetAliasService(auth_repo).execute(
                SetAliasCommand(user_id=owner.user_id, alias=owner_alias)
            )
        logger.info("Seeded owner user_id=%s", owner.user_id)

        # Shared kitchen with member — create if requested
        if kitchen_name:
            # Create owned kitchen
            shared_kitchen = CreateOwnedKitchenService(kitchen_repo).execute(
                CreateOwnedKitchenCommand(actor_user_id=owner.user_id, name=kitchen_name)
            )
            logger.info("Created shared kitchen kitchen_id=%s", shared_kitchen.id)

            # Create member user — idempotent
            member_email = _member_email(owner_email)
            member_exists = signup_repo.email_exists(normalize_email(member_email))
            if not member_exists:
                member_signup = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
                    SignupCommand(email=member_email, password=owner_password)
                )
                member_user_id = member_signup.user_id
                email_repo.mark_email_verified(member_user_id, verified_at=datetime.now(UTC))
                logger.info("Seeded member user_id=%s", member_user_id)
            else:
                member_user = auth_repo.get_by_email(member_email)
                if member_user is None:
                    raise RuntimeError(f"Member {member_email} exists but not found")
                member_user_id = member_user.id
                logger.info("Member user already exists user_id=%s", member_user_id)

            # Add member to kitchen — idempotent
            membership = kitchen_repo.get_membership(shared_kitchen.id, member_user_id)
            if membership is None:
                kitchen_repo.add_membership(
                    NewMembershipRecord(
                        id=uuid4(),
                        kitchen_id=shared_kitchen.id,
                        user_id=member_user_id,
                        role="member",
                    )
                )
                logger.info(
                    "Added member to shared kitchen kitchen_id=%s user_id=%s",
                    shared_kitchen.id,
                    member_user_id,
                )
            else:
                logger.info("Member already in shared kitchen")

        session.commit()
        logger.info("Seed completed successfully")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
