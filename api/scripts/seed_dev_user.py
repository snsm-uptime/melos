"""Dev/worktree-only seed: pre-verified accounts with optional shared kitchen.

Runs from scripts.entrypoint when SEED_DEV_USER is truthy. Idempotent — existing
accounts are left untouched. With a shared kitchen, each of its two members also gets
one recipe in their own notebook there. Carts, shopping lists and conversations are
seeded once their schema exists.

Environment:
- SEED_DEV_USER_EMAIL / SEED_DEV_USER_PASSWORD (required — owner account)
- SEED_DEV_USER_ALIAS (optional; claimed so kitchen surfaces are usable)
- SEED_DEV_USER_KITCHEN (optional; a shared kitchen with owner + member)
  When set, creates a second user (derived from email) and adds them as member.
- SEED_DEV_MEMBER_EMAIL / SEED_DEV_MEMBER_PASSWORD / SEED_DEV_MEMBER_ALIAS (optional;
  override the derived member account)
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from adapters.persistence.db import get_session_factory
from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.password_hasher import Argon2PasswordHasher
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
    SqlAlchemySignupRepository,
)
from api.settings import load_recipe_text_max_chars
from application.kitchens import CreateOwnedKitchenCommand, CreateOwnedKitchenService
from application.notebooks import ResolveCaptureNotebookService
from application.ports import NewMembershipRecord
from application.preferences import SetAliasCommand, SetAliasService
from application.recipe_save import SaveRecipeCommand, SaveRecipeDraft
from application.signup import SignupCommand, SignUpService
from domain.notebook import Notebook, kitchen_notebook_name
from domain.recipe_draft import IngredientLine
from domain.signup import normalize_email
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# One invented recipe per member of the shared kitchen: (title, servings, lines, steps).
_OWNER_RECIPE = (
    "Arepas de queso",
    4,
    (
        IngredientLine("harina de maiz precocida", False, 2.0, "cup"),
        IngredientLine("agua", False, 2.5, "cup"),
        IngredientLine("queso mozzarella", False, 200.0, "g", preparation="rallado"),
        IngredientLine("sal", True, note="una pizca"),
    ),
    (
        "Mezcla el agua con la sal y agrega la harina poco a poco.",
        "Amasa, deja reposar cinco minutos y forma cuatro bolas aplastadas.",
        "Dora las arepas en una sarten por ambos lados hasta que suenen huecas.",
        "Abrelas y rellenalas con el queso rallado.",
    ),
)
_MEMBER_RECIPE = (
    "Ensalada de tomate y aguacate",
    2,
    (
        IngredientLine("tomate", False, 3.0, "unit", "grande", preparation="en cubos"),
        IngredientLine("aguacate", False, 1.0, "unit", preparation="en cubos"),
        IngredientLine("cebolla morada", False, 0.5, "unit", preparation="en rodajas finas"),
        IngredientLine("limon", False, 1.0, "unit"),
        IngredientLine("aceite de oliva", False, 2.0, "tbsp"),
        IngredientLine("sal", True, note="al gusto"),
    ),
    (
        "Mezcla el tomate, el aguacate y la cebolla en un bol.",
        "Aliña con el jugo del limon, el aceite y la sal, y sirve de inmediato.",
    ),
)


def _member_email(owner_email: str) -> str:
    """Derive member email from owner (owner@example.com → owner+member@example.com)."""
    parts = owner_email.rsplit("@", 1)
    if len(parts) == 2:
        return f"{parts[0]}+member@{parts[1]}"
    return f"{owner_email}+member"


def _seed_recipe(
    session: Session,
    kitchen_id: UUID,
    kitchen_name: str,
    user_id: UUID,
    recipe: tuple,
    *,
    label: str,
) -> None:
    """Save `recipe` as `user_id`'s, in that member's own notebook of the shared kitchen.

    The capture flow reuses a kitchen's first notebook for everyone, so the member's
    notebook is made here, named like the app names it.
    """
    title, servings, lines, steps = recipe
    notebooks = SqlAlchemyNotebookRepository(session)
    catalog = SqlAlchemyIngredientCatalog(session)
    notebook_id = notebooks.user_kitchen_notebook(user_id, kitchen_id)
    if notebook_id is None:
        prefs = SqlAlchemyAuthUserRepository(session).get_preferences(user_id)
        alias = (prefs.alias if prefs else None) or "dev"
        notebook_id = uuid4()
        notebooks.create(
            Notebook(
                id=notebook_id,
                name=kitchen_notebook_name(alias, kitchen_name, prefs.language if prefs else None),
                kitchen_id=kitchen_id,
                owner_user_id=user_id,
            )
        )
        catalog.seed_from_person(notebook_id, user_id)
    save = SaveRecipeDraft(
        notebooks,
        catalog,
        SqlAlchemyRecipeRepository(session),
        ResolveCaptureNotebookService(
            SqlAlchemyKitchenRepository(session),
            notebooks,
            SqlAlchemyUserDefaultNotebook(session),
            SqlAlchemyAuthUserRepository(session),
            catalog,
            SqlAlchemyTransactionCommitter(session),
        ),
        max_text_chars=load_recipe_text_max_chars(),
    )
    saved = save.execute(
        SaveRecipeCommand(
            actor_user_id=user_id,
            save_key=uuid5(NAMESPACE_URL, f"melos-dev-seed/{kitchen_id}/{label}"),
            source_text=f"Dev seed recipe: {title}",
            title=title,
            base_servings=servings,
            servings_estimated=False,
            lines=lines,
            steps=steps,
            notebook_id=notebook_id,
        )
    )
    logger.info("Seeded %s recipe recipe_id=%s", label, saved.recipe.id)


def seed() -> None:
    owner_email = (os.environ.get("SEED_DEV_USER_EMAIL") or "").strip()
    owner_password = os.environ.get("SEED_DEV_USER_PASSWORD") or ""
    if not owner_email or not owner_password:
        logger.warning("SEED_DEV_USER set but SEED_DEV_USER_EMAIL/PASSWORD missing — skipping")
        return
    owner_alias = (os.environ.get("SEED_DEV_USER_ALIAS") or "").strip()
    kitchen_name = (os.environ.get("SEED_DEV_USER_KITCHEN") or "").strip()
    member_email = (os.environ.get("SEED_DEV_MEMBER_EMAIL") or "").strip()
    member_password = (os.environ.get("SEED_DEV_MEMBER_PASSWORD") or "").strip()
    member_alias = (os.environ.get("SEED_DEV_MEMBER_ALIAS") or "").strip()

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
            # Use SEED_DEV_MEMBER_EMAIL if set, otherwise derive from owner email
            if not member_email:
                member_email = _member_email(owner_email)
            # Use SEED_DEV_MEMBER_PASSWORD if set, otherwise use owner password
            if not member_password:
                member_password = owner_password

            member_exists = signup_repo.email_exists(normalize_email(member_email))
            if not member_exists:
                member_signup = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
                    SignupCommand(email=member_email, password=member_password)
                )
                member_user_id = member_signup.user_id
                email_repo.mark_email_verified(member_user_id, verified_at=datetime.now(UTC))
                if member_alias:
                    SetAliasService(auth_repo).execute(
                        SetAliasCommand(user_id=member_user_id, alias=member_alias)
                    )
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

            # One recipe per member, each in that member's own notebook
            _seed_recipe(
                session,
                shared_kitchen.id,
                kitchen_name,
                owner.user_id,
                _OWNER_RECIPE,
                label="owner",
            )
            _seed_recipe(
                session,
                shared_kitchen.id,
                kitchen_name,
                member_user_id,
                _MEMBER_RECIPE,
                label="member",
            )

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
