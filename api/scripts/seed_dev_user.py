"""Dev/worktree-only seed: a pre-verified account with an alias and kitchens.

Runs from scripts.entrypoint when SEED_DEV_USER is truthy. Idempotent — an
existing account with the same email is left untouched. Recipes, carts,
shopping lists and conversations are seeded once their schema exists.

Environment:
- SEED_DEV_USER_EMAIL / SEED_DEV_USER_PASSWORD (required — no silent defaults)
- SEED_DEV_USER_ALIAS (optional; claimed so kitchen surfaces are usable)
- SEED_DEV_USER_KITCHEN (optional; an extra kitchen next to "My kitchen")
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

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
from application.signup import SignupCommand, SignUpService
from domain.signup import normalize_email

logger = logging.getLogger(__name__)


def seed() -> None:
    email = (os.environ.get("SEED_DEV_USER_EMAIL") or "").strip()
    password = os.environ.get("SEED_DEV_USER_PASSWORD") or ""
    if not email or not password:
        logger.warning("SEED_DEV_USER set but SEED_DEV_USER_EMAIL/PASSWORD missing — skipping")
        return
    alias = (os.environ.get("SEED_DEV_USER_ALIAS") or "").strip()
    kitchen_name = (os.environ.get("SEED_DEV_USER_KITCHEN") or "").strip()

    session = get_session_factory()()
    try:
        signup_repo = SqlAlchemySignupRepository(session)
        if signup_repo.email_exists(normalize_email(email)):
            logger.info("Dev user already exists — seed skipped")
            return

        created = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
            SignupCommand(email=email, password=password)
        )
        SqlAlchemyEmailVerificationRepository(session).mark_email_verified(
            created.user_id, verified_at=datetime.now(UTC)
        )
        if alias:
            SetAliasService(SqlAlchemyAuthUserRepository(session)).execute(
                SetAliasCommand(user_id=created.user_id, alias=alias)
            )
        if kitchen_name:
            CreateOwnedKitchenService(SqlAlchemyKitchenRepository(session)).execute(
                CreateOwnedKitchenCommand(actor_user_id=created.user_id, name=kitchen_name)
            )
        session.commit()
        logger.info("Seeded dev user user_id=%s", created.user_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
