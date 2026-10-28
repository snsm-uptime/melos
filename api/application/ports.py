"""Ports for application use-cases (implemented by adapters)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from domain.notebook import Notebook, NotebookRole
from domain.recipe import EditedRecipe, NewRecipe

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


@dataclass(frozen=True, slots=True)
class NotebookFacts:
    """What the repository knows about one notebook for one caller. The domain decides access."""

    notebook: Notebook
    # The caller's membership role in a personal notebook; None when they have none.
    role: NotebookRole | None
    # Whether the caller belongs to the notebook's kitchen (kitchen notebooks only).
    in_kitchen: bool
    # The stored owner's alias, or the kitchen owner's when none is stored; None if neither.
    owner_alias: str | None
    # Read with the notebook (kitchen notebooks only).
    kitchen_is_archived: bool | None
    is_default: bool


class NotebookRepository(Protocol):
    def get(self, notebook_id: UUID) -> Notebook | None: ...

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        """The notebook and the caller's facts, or None when the notebook does not exist."""
        ...

    def personal_facts_for(self, user_id: UUID) -> list[NotebookFacts]:
        """Personal notebooks where the user has a membership, oldest first."""
        ...

    def kitchen_notebooks(self, kitchen_id: UUID) -> list[Notebook]:
        """A kitchen's notebooks, oldest first."""
        ...

    def personal_ids_for(self, user_id: UUID) -> list[UUID]:
        """Capture candidates outside a kitchen: the user's personal notebooks, oldest first."""
        ...

    def kitchen_ids_for(self, kitchen_id: UUID) -> list[UUID]:
        """Capture candidates in a kitchen: its notebooks, oldest first."""
        ...

    def create(self, notebook: Notebook) -> None: ...

    def add_owner(self, notebook_id: UUID, user_id: UUID) -> None:
        """Insert the owner membership of a personal notebook."""
        ...

    def lock_kitchen(self, kitchen_id: UUID) -> None:
        """Serialize first creations in a kitchen (FOR NO KEY UPDATE on the kitchen row)."""
        ...


class IngredientCatalog(Protocol):
    def names_for_notebook(self, notebook_id: UUID) -> list[str]: ...

    def names_for_person(self, user_id: UUID) -> list[str]:
        """Distinct names across the user's personal notebooks (never kitchen notebooks)."""
        ...

    def seed_from_person(self, notebook_id: UUID, user_id: UUID) -> None:
        """Copy the person's personal catalog into a new notebook's catalog."""
        ...

    def add_names(self, notebook_id: UUID, names: Sequence[str]) -> None:
        """Add names the catalog lacks; a name already there is left as it is (spec 020)."""
        ...


@dataclass(frozen=True, slots=True)
class StoredRecipe:
    id: UUID
    notebook_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class RecipeLineDetail:
    """One ingredient line of a stored recipe (spec 027)."""

    name: str
    vague: bool
    quantity: float | None
    unit: str | None
    size: str | None
    preparation: str | None
    note: str | None


@dataclass(frozen=True, slots=True)
class RecipeDetail:
    """A stored recipe as the detail screen reads it (spec 027)."""

    id: UUID
    notebook_id: UUID
    title: str
    base_servings: int
    servings_estimated: bool
    author_alias: str | None
    lines: tuple[RecipeLineDetail, ...]
    steps: tuple[str, ...]
    source_type: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime


class DuplicateSaveKeyError(Exception):
    """The same author already stored a recipe with this save key (spec 020 research R5)."""


class RecipeRepository(Protocol):
    def find_by_save_key(self, author_id: UUID, save_key: UUID) -> StoredRecipe | None: ...

    def add(self, recipe: NewRecipe) -> StoredRecipe:
        """Store the source, the recipe, its lines and its steps.

        Raises DuplicateSaveKeyError when the author's save key is already stored.
        """
        ...

    def get_detail(self, recipe_id: UUID) -> RecipeDetail | None:
        """One recipe with its lines and steps in position order, or None. Reads only.

        Never returns the source's pasted text.
        """
        ...

    def replace(self, recipe_id: UUID, version: datetime, recipe: EditedRecipe) -> RecipeDetail:
        """Replace title, servings, lines and steps of a recipe (spec 027).

        Locks the recipe row. Raises RecipeNotFoundError when it is gone and
        RecipeChangedError when its `updated_at` differs from `version`. Author, notebook,
        source, save key and creation time are never changed.
        """
        ...

    def delete(self, recipe_id: UUID) -> None:
        """Remove the recipe, its lines, its steps and its source row.

        Raises RecipeNotFoundError when it is gone.
        """
        ...


@dataclass(frozen=True, slots=True)
class RecipeCardRow:
    """One recipe as a list card (spec 021)."""

    id: UUID
    title: str
    # None when the author's account is gone.
    author_alias: str | None
    ingredient_count: int
    notebook_id: UUID
    notebook_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecipePage:
    items: list[RecipeCardRow]
    # Recipes matching the key across all pages.
    total: int


class RecipeListRepository(Protocol):
    def list_page(
        self, notebook_ids: Sequence[UUID], key: str, offset: int, limit: int
    ) -> RecipePage:
        """Recipes of the notebooks, newest first (created_at desc, id desc).

        `key` is a search key (see domain.recipe_search); empty means no filter. Empty
        `notebook_ids` gives an empty page. Reads only.
        """
        ...


class UserDefaultNotebook(Protocol):
    def get_for_update(self, user_id: UUID) -> UUID | None:
        """Lock the user row and return its default_notebook_id.

        The lock serializes simultaneous first calls, so only one creates a notebook.
        """
        ...

    def set(self, user_id: UUID, notebook_id: UUID) -> None: ...


class TransactionCommitter(Protocol):
    def commit(self) -> None:
        """Commit now, so a notebook the capture step created survives a failed save (R8)."""
        ...


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
