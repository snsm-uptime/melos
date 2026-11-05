"""Dev/worktree-only seed: pre-verified accounts with optional shared kitchen.

Runs from scripts.entrypoint when SEED_DEV_USER is truthy. Idempotent — existing
accounts are left untouched. With a shared kitchen, each of its two members also gets
one recipe in their own notebook there. Carts, shopping lists and conversations are
seeded once their schema exists.

Environment:
- SEED_DEV_USER_EMAIL / SEED_DEV_USER_PASSWORD (required — owner account)
- SEED_DEV_USER_ALIAS (optional; claimed so kitchen surfaces are usable)
- SEED_DEV_USER_ADMIN (optional; truthy makes the owner an admin, spec 055 /admin).
  Applied on every boot, so it also reaches an owner seeded earlier.
- SEED_DEV_USER_KITCHEN (optional; a shared kitchen with owner + member)
  When set, creates a second user (derived from email) and adds them as member.
- SEED_DEV_MEMBER_EMAIL / SEED_DEV_MEMBER_PASSWORD / SEED_DEV_MEMBER_ALIAS (optional;
  override the derived member account)

With a shared kitchen, real recipes read from a running Melos app over its API
(SEED_RECIPES_SOURCE_*, see scripts/seed_source_recipes.py) are also saved in the
owner's kitchen notebook.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from adapters.persistence.db import get_session_factory
from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import (
    KitchenMembershipModel,
    KitchenModel,
    RecipeModel,
    UserModel,
)
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
from adapters.persistence.units import SqlAlchemyUnitRepository
from api.settings import load_recipe_text_max_chars
from application.kitchens import CreateOwnedKitchenCommand, CreateOwnedKitchenService
from application.notebooks import ResolveCaptureNotebookService, ensure_default_notebook
from application.ports import NewMembershipRecord
from application.preferences import SetAliasCommand, SetAliasService
from application.recipe_save import SaveRecipeCommand, SaveRecipeDraft
from application.signup import SignupCommand, SignUpService
from domain.notebook import Notebook, kitchen_notebook_name
from domain.recipe_draft import IngredientLine
from domain.signup import normalize_email
from sqlalchemy.orm import Session

from scripts.seed_source_recipes import fetch_source_recipes, title_key

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
    keep_units: tuple[str, ...] = (),
) -> None:
    """Save `recipe` as `user_id`'s, in that member's own notebook of the shared kitchen."""
    _save_recipe(
        session,
        _kitchen_notebook(session, user_id, kitchen_id, kitchen_name),
        user_id,
        recipe,
        save_key=uuid5(NAMESPACE_URL, f"melos-dev-seed/{kitchen_id}/{label}"),
        label=label,
        keep_units=keep_units,
    )


def _kitchen_notebook(session: Session, user_id: UUID, kitchen_id: UUID, kitchen_name: str) -> UUID:
    """The member's own notebook of the shared kitchen, made like the app names it.

    The capture flow reuses a kitchen's first notebook for everyone, so it is made here.
    """
    notebooks = SqlAlchemyNotebookRepository(session)
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
        SqlAlchemyIngredientCatalog(session).seed_from_person(notebook_id, user_id)
    return notebook_id


def _personal_notebook(session: Session, user_id: UUID) -> UUID:
    """The user's default personal notebook, created as the app does on first use."""
    notebook_id, _ = ensure_default_notebook(
        user_id,
        notebooks=SqlAlchemyNotebookRepository(session),
        defaults=SqlAlchemyUserDefaultNotebook(session),
        prefs=SqlAlchemyAuthUserRepository(session),
        catalog=SqlAlchemyIngredientCatalog(session),
    )
    return notebook_id


def _save_recipe(
    session: Session,
    notebook_id: UUID,
    user_id: UUID,
    recipe: tuple,
    *,
    save_key: UUID,
    label: str,
    keep_units: tuple[str, ...] = (),
) -> None:
    title, servings, lines, steps = recipe
    notebooks = SqlAlchemyNotebookRepository(session)
    catalog = SqlAlchemyIngredientCatalog(session)
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
        units=SqlAlchemyUnitRepository(session),
        max_text_chars=load_recipe_text_max_chars(),
    )
    saved = save.execute(
        SaveRecipeCommand(
            actor_user_id=user_id,
            save_key=save_key,
            source_text=f"Dev seed recipe: {title}",
            title=title,
            base_servings=servings,
            servings_estimated=False,
            lines=lines,
            steps=steps,
            notebook_id=notebook_id,
            keep_units=keep_units,
        )
    )
    logger.info("Seeded %s recipe recipe_id=%s", label, saved.recipe.id)


def _seed_source_recipes(
    session: Session, user_ids: list[UUID], kitchen_id: UUID, kitchen_name: str
) -> None:
    """Real recipes from the source app (SEED_RECIPES_SOURCE_*), spread over every seeded
    user's personal notebook and own kitchen notebook.

    Each new recipe goes to the target notebook holding the fewest recipes (ties in a fixed
    order), authored by that notebook's user, so the split stays even as recipes are added.
    A title already in any target notebook is skipped, so every boot adds only new ones.
    One failing recipe is logged and skipped; the others are still saved.
    """
    recipes = fetch_source_recipes()
    if not recipes:
        return
    targets: list[tuple[UUID, UUID]] = []  # (user, notebook)
    for user_id in user_ids:
        targets.append((user_id, _personal_notebook(session, user_id)))
        targets.append((user_id, _kitchen_notebook(session, user_id, kitchen_id, kitchen_name)))
    session.commit()

    notebook_ids = [notebook_id for _, notebook_id in targets]
    rows = (
        session.query(RecipeModel.notebook_id, RecipeModel.title)
        .filter(RecipeModel.notebook_id.in_(notebook_ids))
        .all()
    )
    load = dict.fromkeys(notebook_ids, 0)
    for notebook_id, _ in rows:
        load[notebook_id] += 1
    present = {title_key(title) for _, title in rows}

    added = 0
    for recipe, units in sorted(recipes, key=lambda item: title_key(item[0][0])):
        title = recipe[0]
        key = title_key(title)
        if key in present:
            continue
        user_id, notebook_id = min(targets, key=lambda target: load[target[1]])
        try:
            with session.begin_nested():
                _save_recipe(
                    session,
                    notebook_id,
                    user_id,
                    recipe,
                    save_key=uuid5(NAMESPACE_URL, f"melos-dev-seed/source/{notebook_id}/{key}"),
                    label=f"source/{key}",
                    keep_units=units,
                )
        except Exception:
            logger.warning("Seed recipes: could not save %r", title, exc_info=True)
            continue
        present.add(key)
        load[notebook_id] += 1
        added += 1
    session.commit()
    logger.info("Seed recipes: added %d new recipe(s) across %d notebooks", added, len(targets))


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _set_owner_admin(session: Session, email: str, is_admin: bool) -> None:
    """Match the owner's admin flag to SEED_DEV_USER_ADMIN (dev-only seed)."""
    owner = session.query(UserModel).filter(UserModel.email == normalize_email(email)).one_or_none()
    if owner is not None and owner.is_admin != is_admin:
        owner.is_admin = is_admin
        logger.info("Set seeded owner is_admin=%s", is_admin)


def seed() -> None:
    owner_email = (os.environ.get("SEED_DEV_USER_EMAIL") or "").strip()
    owner_password = os.environ.get("SEED_DEV_USER_PASSWORD") or ""
    if not owner_email or not owner_password:
        logger.warning("SEED_DEV_USER set but SEED_DEV_USER_EMAIL/PASSWORD missing — skipping")
        return
    owner_alias = (os.environ.get("SEED_DEV_USER_ALIAS") or "").strip()
    owner_admin = _truthy(os.environ.get("SEED_DEV_USER_ADMIN"))
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
            _set_owner_admin(session, owner_email, owner_admin)
            session.commit()
            logger.info("Owner user already exists — seed skipped")
            # Real recipes still run every boot; ones already saved are not added again.
            owner_id = auth_repo.get_by_email(owner_email).id
            kitchen = (
                session.query(KitchenModel)
                .filter(KitchenModel.owner_id == owner_id, KitchenModel.name == kitchen_name)
                .order_by(KitchenModel.created_at)
                .first()
                if kitchen_name
                else None
            )
            if kitchen is not None:
                # Everyone in the shared kitchen: the owner first, then members by join date.
                user_ids = [
                    row.user_id
                    for row in session.query(KitchenMembershipModel)
                    .filter(KitchenMembershipModel.kitchen_id == kitchen.id)
                    .order_by(
                        KitchenMembershipModel.user_id != owner_id,
                        KitchenMembershipModel.created_at,
                    )
                ]
                _seed_source_recipes(session, user_ids, kitchen.id, kitchen_name)
            return

        owner = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
            SignupCommand(email=owner_email, password=owner_password)
        )
        email_repo.mark_email_verified(owner.user_id, verified_at=datetime.now(UTC))
        if owner_alias:
            SetAliasService(auth_repo).execute(
                SetAliasCommand(user_id=owner.user_id, alias=owner_alias)
            )
        session.flush()
        _set_owner_admin(session, owner_email, owner_admin)
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
        if kitchen_name:
            _seed_source_recipes(
                session, [owner.user_id, member_user_id], shared_kitchen.id, kitchen_name
            )
        logger.info("Seed completed successfully")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
