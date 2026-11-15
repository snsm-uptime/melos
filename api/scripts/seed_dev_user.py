"""Dev/worktree-only seed: three fixed, pre-verified accounts and a shared kitchen.

Runs from scripts.entrypoint when SEED_DEV_USER is truthy. Idempotent: an account that
exists is left untouched, and a recipe whose title is already in its notebook is not saved
again. Carts, shopping lists and conversations are seeded once their schema exists.

The accounts are fixed (dev only, never a real person). All share DEV_PASSWORD, none has a
photo. Aliases are stored lowercase, as every alias is.

| Email            | Alias       | Language | Role                                       |
|------------------|-------------|----------|--------------------------------------------|
| owner@dev.com    | DevOwner    | en       | owns the shared kitchen; admin (see below) |
| member@dev.com   | DevMember   | en       | member of the shared kitchen               |
| invitado@dev.com | DevInvitado | es       | outside the kitchen, ready to be invited   |

Environment:
- SEED_DEV_USER_ADMIN (optional; truthy makes the owner an admin, spec 055 /admin).
  Applied on every boot.
- SEED_DEV_USER_KITCHEN (optional; the shared kitchen's name, "Dev's Kitchen" when unset)

Recipes:
- Fixed ones in the owner's and member's kitchen notebooks: one invented recipe each, plus
  an English and a Spanish pair that share "carrot"/"zanahoria" and "olive oil"/"aceite de
  oliva", to try the catalog language setup (merge across languages, spec 043). A pair
  "oil"/"aceite" (English and Spanish, merged into "aceite") and a plural "aceites" merged into
  "aceite" as well, so the singular rule shows.
- A rotation over every seeded notebook (each user's personal notebook, and the kitchen
  notebook of the two members): two built-in recipes and the real ones read from a running
  Melos app over its API (SEED_RECIPES_SOURCE_*, see scripts/seed_source_recipes.py).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from adapters.persistence.db import get_session_factory
from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.models import KitchenModel, RecipeModel, UserModel
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.password_hasher import Argon2PasswordHasher
from adapters.persistence.places import SqlAlchemyPlaceRepository
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
    SqlAlchemySignupRepository,
)
from adapters.persistence.units import SqlAlchemyUnitRepository
from api.settings import load_recipe_text_max_chars
from application.catalog_manage import MergeCommand, MergeService
from application.kitchens import CreateOwnedKitchenCommand, CreateOwnedKitchenService
from application.notebooks import ResolveCaptureNotebookService, ensure_default_notebook
from application.ports import NewMembershipRecord
from application.preferences import (
    SetAliasCommand,
    SetAliasService,
    UpdatePreferencesCommand,
    UpdatePreferencesService,
)
from application.recipe_save import SaveRecipeCommand, SaveRecipeDraft
from application.signup import SignupCommand, SignUpService
from domain.notebook import Notebook, kitchen_notebook_name
from domain.recipe_draft import IngredientLine
from domain.signup import normalize_email
from sqlalchemy.orm import Session

from scripts.seed_source_recipes import fetch_source_recipes, title_key

logger = logging.getLogger(__name__)

DEV_PASSWORD = "pass12word34"
DEFAULT_KITCHEN = "Dev's Kitchen"


@dataclass(frozen=True, slots=True)
class SeedAccount:
    email: str
    alias: str
    language: str


OWNER = SeedAccount("owner@dev.com", "DevOwner", "en")
MEMBER = SeedAccount("member@dev.com", "DevMember", "en")
GUEST = SeedAccount("invitado@dev.com", "DevInvitado", "es")

# A recipe is (title, servings, lines, steps).
_OWNER_RECIPE = (
    "Arepas de queso",
    4,
    (
        IngredientLine("harina de maiz precocida", False, 2.0, "cup"),
        IngredientLine("agua", False, 2.5, "cup"),
        IngredientLine("queso mozzarella", False, 200.0, "g", preparation="rallado"),
        IngredientLine("sal", True, vague_text="una pizca"),
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
        IngredientLine("sal", True, vague_text="al gusto"),
    ),
    (
        "Mezcla el tomate, el aguacate y la cebolla en un bol.",
        "Aliña con el jugo del limon, el aceite y la sal, y sirve de inmediato.",
    ),
)

# The same dish in both languages, so the catalog holds "carrot" and "zanahoria", "olive oil"
# and "aceite de oliva" as separate names until they are merged.
_CARROTS_EN = (
    "Roasted carrots",
    2,
    (
        IngredientLine("carrot", False, 4.0, "unit", "large", preparation="sliced"),
        IngredientLine("olive oil", False, 2.0, "tbsp"),
        IngredientLine("salt", True, vague_text="to taste"),
    ),
    (
        "Heat the oven to 220 C.",
        "Toss the carrots with the olive oil and the salt on a tray.",
        "Roast for 25 minutes, turning once.",
    ),
)
_CARROTS_ES = (
    "Zanahorias asadas",
    2,
    (
        IngredientLine("zanahoria", False, 4.0, "unit", "grande", preparation="en rodajas"),
        IngredientLine("aceite de oliva", False, 2.0, "tbsp"),
        IngredientLine("sal", True, vague_text="al gusto"),
    ),
    (
        "Calienta el horno a 220 C.",
        "Mezcla las zanahorias con el aceite de oliva y la sal en una bandeja.",
        "Hornea 25 minutos, dándoles la vuelta una vez.",
    ),
)

# Oil in both languages and the plural "aceites", merged into "aceite" after the save (see
# _SEED_MERGES). Saving matches names by case and spacing only, so the catalog keeps them apart.
_CHICKEN_ES = (
    "Pollo al horno",
    2,
    (
        IngredientLine("pollo", False, 2.0, "unit"),
        IngredientLine("aceite", False, 2.0, "tbsp"),
        IngredientLine("sal", True, vague_text="al gusto"),
    ),
    (
        "Calienta el horno a 200 C.",
        "Unta el pollo con el aceite y la sal, y hornealo una hora.",
    ),
)
_SALAD_ES = (
    "Ensalada de lechuga",
    2,
    (
        IngredientLine("lechuga", False, 1.0, "unit"),
        IngredientLine("aceites", False, 1.0, "tbsp"),
        IngredientLine("limon", False, 1.0, "unit"),
    ),
    (
        "Lava y corta la lechuga en trozos.",
        "Aliña con los aceites y el limon, y sirve.",
    ),
)
_CHICKEN_EN = (
    "Oven chicken",
    2,
    (
        IngredientLine("chicken", False, 2.0, "unit"),
        IngredientLine("oil", False, 2.0, "tbsp"),
        IngredientLine("salt", True, vague_text="to taste"),
    ),
    (
        "Heat the oven to 200 C.",
        "Rub the chicken with the oil and the salt.",
        "Roast for one hour.",
    ),
)

# Built-in recipes that join the rotation with the real ones: (recipe, units kept, language).
_CAJETAS = (
    "Cajetas de Tita Marielos",
    32,
    (
        IngredientLine(
            "mantequilla sin azúcar", False, 0.25, "unit", preparation="Temperatura ambiente"
        ),
        IngredientLine("azúcar", False, 2.0, "cup"),
        IngredientLine("leche", False, 1.0, "unit"),
    ),
    (
        "Hervir leche",
        "Agregar mantequilla",
        "Mezclar azúcar constantemente",
        "Cuando al pasar una cuchara de madera la mezcla dure en cubrir la base, quitar del fuego",
        "Esparcir mezcla en un contenedor que aguante calor y cortar en las partes que se desee",
    ),
)
_PESTO_PASTA = (
    "JUICY Pesto Pasta!",
    3,
    (
        IngredientLine("homemade pesto", True, vague_text="some", note="To taste"),
        IngredientLine("pasta", False, 300.0, "g"),
        IngredientLine("salt", False, 2.0, "tsp"),
        IngredientLine("pasta cooking water", False, 0.75, "cup"),
        IngredientLine("parmesan", True, vague_text="some", note="for serving"),
    ),
    (
        "Bring a large pot of water to the boil with the salt.",
        "Add pasta and cook for the length of time per the packet.",
        "Just before draining, scoop out 1 cup of the pasta cooking water.",
        "Drain pasta in a colander, leave it for a minute.",
        "Transfer pasta to a bowl (do not use pasta cooking pot, too hot).",
        "Add pesto and 1/4 cup of pasta water. Toss to coat pasta in pesto, adding more water "
        "if required to make pasta silky and saucy, rather than dry and sticky.",
        "Taste, add more salt and pepper if desired.",
        "Serve immediately, garnished with fresh parmesan.",
    ),
)
_ROTATION_RECIPES = (
    (_CAJETAS, (), "es"),
    (_PESTO_PASTA, (), "en"),
)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_account(session: Session, account: SeedAccount) -> UUID:
    """The account's user id: created verified, with its alias and language, when missing."""
    signup_repo = SqlAlchemySignupRepository(session)
    auth_repo = SqlAlchemyAuthUserRepository(session)
    if signup_repo.email_exists(normalize_email(account.email)):
        existing = auth_repo.get_by_email(account.email)
        if existing is None:
            raise RuntimeError(f"{account.email} exists but was not found")
        return existing.id

    created = SignUpService(signup_repo, Argon2PasswordHasher()).execute(
        SignupCommand(email=account.email, password=DEV_PASSWORD, language=account.language)
    )
    SqlAlchemyEmailVerificationRepository(session).mark_email_verified(
        created.user_id, verified_at=datetime.now(UTC)
    )
    SetAliasService(auth_repo).execute(
        SetAliasCommand(user_id=created.user_id, alias=account.alias)
    )
    UpdatePreferencesService(auth_repo).execute(
        UpdatePreferencesCommand(user_id=created.user_id, language=account.language)
    )
    session.flush()
    logger.info("Seeded %s user_id=%s", account.email, created.user_id)
    return created.user_id


def _ensure_kitchen(session: Session, owner_id: UUID, member_id: UUID, name: str) -> UUID:
    """The owner's shared kitchen, created when missing, with the member in it."""
    kitchens = SqlAlchemyKitchenRepository(session)
    kitchen = (
        session.query(KitchenModel)
        .filter(KitchenModel.owner_id == owner_id, KitchenModel.name == name)
        .order_by(KitchenModel.created_at)
        .first()
    )
    if kitchen is None:
        kitchen_id = (
            CreateOwnedKitchenService(kitchens)
            .execute(CreateOwnedKitchenCommand(actor_user_id=owner_id, name=name))
            .id
        )
        logger.info("Created shared kitchen kitchen_id=%s", kitchen_id)
    else:
        kitchen_id = kitchen.id
    if kitchens.get_membership(kitchen_id, member_id) is None:
        kitchens.add_membership(
            NewMembershipRecord(id=uuid4(), kitchen_id=kitchen_id, user_id=member_id, role="member")
        )
        logger.info("Added member to shared kitchen kitchen_id=%s", kitchen_id)
    return kitchen_id


def _set_owner_admin(session: Session, email: str, is_admin: bool) -> None:
    """Match the owner's admin flag to SEED_DEV_USER_ADMIN (dev-only seed)."""
    owner = session.query(UserModel).filter(UserModel.email == normalize_email(email)).one_or_none()
    if owner is not None and owner.is_admin != is_admin:
        owner.is_admin = is_admin
        logger.info("Set seeded owner is_admin=%s", is_admin)


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
    language: str | None = None,
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
            language=language,
        )
    )
    logger.info("Seeded %s recipe recipe_id=%s", label, saved.recipe.id)


def _try_save(session: Session, notebook_id: UUID, user_id: UUID, recipe: tuple, **kwargs) -> bool:
    """Save in a savepoint: one failing recipe is logged and skipped, the others still land."""
    try:
        with session.begin_nested():
            _save_recipe(session, notebook_id, user_id, recipe, **kwargs)
    except Exception:
        logger.warning("Seed recipes: could not save %r", recipe[0], exc_info=True)
        return False
    return True


def _seed_fixed_recipes(
    session: Session,
    owner_id: UUID,
    owner_notebook: UUID,
    member_id: UUID,
    member_notebook: UUID,
) -> None:
    """Each fixed recipe in its own notebook, unless a recipe with that title is already there."""
    fixed = (
        (owner_id, owner_notebook, _OWNER_RECIPE, "es"),
        (member_id, member_notebook, _MEMBER_RECIPE, "es"),
        # Both languages in one notebook, so the catalog can merge their names.
        (owner_id, owner_notebook, _CARROTS_EN, "en"),
        (owner_id, owner_notebook, _CARROTS_ES, "es"),
        (owner_id, owner_notebook, _CHICKEN_ES, "es"),
        (owner_id, owner_notebook, _SALAD_ES, "es"),
        (owner_id, owner_notebook, _CHICKEN_EN, "en"),
    )
    for user_id, notebook_id, recipe, language in fixed:
        key = title_key(recipe[0])
        titles = session.query(RecipeModel.title).filter(RecipeModel.notebook_id == notebook_id)
        if key in {title_key(title) for (title,) in titles}:
            continue
        _try_save(
            session,
            notebook_id,
            user_id,
            recipe,
            save_key=uuid5(NAMESPACE_URL, f"melos-dev-seed/fixed/{notebook_id}/{key}"),
            label=f"fixed/{key}",
            language=language,
        )


# (merged, kept, merged language, kept language): "oil" is the English name of "aceite" (spec 043,
# FR-005), and the plural "aceites" normalizes to "aceite" by the S-018 singular rule.
_SEED_MERGES = (
    ("oil", "aceite", "en", "es"),
    ("aceites", "aceite", "es", "es"),
)


def _merge_seed_names(session: Session, owner_id: UUID, notebook_id: UUID) -> None:
    """Merge the _SEED_MERGES names in the owner's catalog.

    Idempotent: a merged name already resolves to the kept one, so its merge is skipped as
    name_changed.
    """
    service = MergeService(
        SqlAlchemyNotebookRepository(session),
        SqlAlchemyIngredientCatalog(session),
        SqlAlchemyPlaceRepository(session),
    )
    for merged, kept, merged_language, kept_language in _SEED_MERGES:
        result = service.execute(
            MergeCommand(
                actor_user_id=owner_id,
                merged=merged,
                kept=kept,
                merged_language=merged_language,
                kept_language=kept_language,
                notebook_ids=(notebook_id,),
            )
        )
        logger.info(
            "Catalog merge %s -> %s: merged=%s skipped=%s",
            merged,
            kept,
            result.merged,
            result.skipped,
        )


def _seed_rotating_recipes(session: Session, targets: list[tuple[UUID, UUID]]) -> None:
    """The built-in and the real recipes (SEED_RECIPES_SOURCE_*), spread over `targets`.

    `targets` are (user, notebook) pairs. Each new recipe goes to the notebook holding the
    fewest recipes (ties in the order given), authored by that notebook's user, so the split
    stays even as recipes are added. A title already in any target notebook is skipped, so
    every boot adds only new ones. A real recipe with a built-in title yields to the built-in.
    """
    built_in = {title_key(recipe[0]) for recipe, _, _ in _ROTATION_RECIPES}
    fetched = [
        (recipe, units, None)
        for recipe, units in fetch_source_recipes()
        if title_key(recipe[0]) not in built_in
    ]
    recipes = sorted([*_ROTATION_RECIPES, *fetched], key=lambda item: title_key(item[0][0]))

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
    for recipe, units, language in recipes:
        key = title_key(recipe[0])
        if key in present:
            continue
        user_id, notebook_id = min(targets, key=lambda target: load[target[1]])
        saved = _try_save(
            session,
            notebook_id,
            user_id,
            recipe,
            save_key=uuid5(NAMESPACE_URL, f"melos-dev-seed/source/{notebook_id}/{key}"),
            label=f"source/{key}",
            keep_units=units,
            language=language,
        )
        if saved:
            present.add(key)
            load[notebook_id] += 1
            added += 1
    session.commit()
    logger.info("Seed recipes: added %d new recipe(s) across %d notebooks", added, len(targets))


def seed() -> None:
    owner_admin = _truthy(os.environ.get("SEED_DEV_USER_ADMIN"))
    shared_kitchen_name = (os.environ.get("SEED_DEV_USER_KITCHEN") or "").strip() or DEFAULT_KITCHEN

    session = get_session_factory()()
    try:
        owner_id = _ensure_account(session, OWNER)
        member_id = _ensure_account(session, MEMBER)
        guest_id = _ensure_account(session, GUEST)
        _set_owner_admin(session, OWNER.email, owner_admin)
        kitchen_id = _ensure_kitchen(session, owner_id, member_id, shared_kitchen_name)
        session.commit()

        notebooks = {
            "owner": _kitchen_notebook(session, owner_id, kitchen_id, shared_kitchen_name),
            "member": _kitchen_notebook(session, member_id, kitchen_id, shared_kitchen_name),
        }
        personal = {
            user_id: _personal_notebook(session, user_id)
            for user_id in (owner_id, member_id, guest_id)
        }
        session.commit()

        _seed_fixed_recipes(session, owner_id, notebooks["owner"], member_id, notebooks["member"])
        session.commit()
        _merge_seed_names(session, owner_id, notebooks["owner"])
        session.commit()
        _seed_rotating_recipes(
            session,
            [
                (owner_id, personal[owner_id]),
                (owner_id, notebooks["owner"]),
                (member_id, personal[member_id]),
                (member_id, notebooks["member"]),
                (guest_id, personal[guest_id]),
            ],
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
