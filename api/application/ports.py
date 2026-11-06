"""Ports for application use-cases (implemented by adapters)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from domain.cart import CartAction
from domain.default_kitchen import MemberKitchen
from domain.ingredient_catalog import CatalogIndex, MergePlan, SplitPlan
from domain.notebook import Notebook, NotebookRole
from domain.places import CustomPlace, PlaceRef
from domain.recipe import EditedRecipe, NewRecipe
from domain.recipe_page import PageRecipe
from domain.recipe_search import SearchFilters
from domain.shopping_list import SavedLine, SavedList

from application.recipe_extraction import (
    AIProviderError,
    InvalidOutput,
    LimitReached,
    Unavailable,
)

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
    recipe_count: int
    # The original's current name, for a snapshot whose original still exists (spec 035 R8).
    origin_notebook_name: str | None = None
    # True on the notebook user_kitchen_notebook returns for the caller.
    is_own_capture_notebook: bool = False

    @property
    def is_snapshot(self) -> bool:
        return self.notebook.snapshot_key is not None


@dataclass(frozen=True, slots=True)
class NotebookMemberRecord:
    user_id: UUID
    alias: str | None
    role: NotebookRole
    joined_at: datetime


class NotebookRepository(Protocol):
    def get(self, notebook_id: UUID) -> Notebook | None: ...

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        """The notebook and the caller's facts, or None when the notebook does not exist."""
        ...

    def visible_facts_for(self, user_id: UUID) -> list[NotebookFacts]:
        """Personal notebooks where the user has a membership, and the notebooks of the
        kitchens they belong to, oldest first."""
        ...

    def kitchen_notebooks(self, kitchen_id: UUID) -> list[Notebook]:
        """A kitchen's notebooks, oldest first."""
        ...

    def user_kitchen_notebook(self, user_id: UUID, kitchen_id: UUID) -> UUID | None:
        """The kitchen notebook created by the user in this kitchen, or None."""
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
        """Serialize first creations in a kitchen (FOR NO KEY UPDATE on the kitchen row).

        Raises KitchenNotFoundError if the kitchen is gone. Reads made after it are current.
        """
        ...

    def find_snapshot(self, kitchen_id: UUID, snapshot_key: UUID) -> UUID | None:
        """The kitchen's snapshot made with this key, or None."""
        ...

    def has_snapshot_of(self, kitchen_id: UUID, source_notebook_id: UUID) -> bool:
        """Whether the kitchen has a snapshot still labelled as coming from this notebook."""
        ...

    def lock_notebook(self, notebook_id: UUID) -> None:
        """Serialize sharing changes on a notebook (FOR NO KEY UPDATE on its row).

        Raises NotebookNotFoundError if the notebook is gone. Reads made after it are current.
        """
        ...

    def rename(self, notebook_id: UUID, name: str) -> None:
        """Store a checked name. Nothing else about the notebook changes."""
        ...

    def owned_personal_ids(self, user_id: UUID) -> list[UUID]:
        """Personal notebooks this person owns, and not those they are only a member of."""
        ...

    def make_owner(self, notebook_id: UUID, user_id: UUID) -> None:
        """Give a member the owner role. The old owner's row must already be gone."""
        ...

    def delete(self, notebook_id: UUID) -> None:
        """Delete a notebook of either kind, what it holds and its captured source text.

        Takes FOR UPDATE on the notebook row first.
        """
        ...

    def members_of(self, notebook_id: UUID) -> list[NotebookMemberRecord]:
        """The owner, then members by join date."""
        ...

    def role_of(self, notebook_id: UUID, user_id: UUID) -> NotebookRole | None:
        """The person's role in a personal notebook, or None when they have no membership."""
        ...

    def add_member(self, notebook_id: UUID, user_id: UUID) -> None:
        """Insert a membership with the role of member."""
        ...

    def delete_membership(self, notebook_id: UUID, user_id: UUID) -> bool:
        """Delete the membership, ending the person's edit locks; True when a row went."""
        ...


@dataclass(frozen=True, slots=True)
class NotebookInviteRecord:
    id: UUID
    notebook_id: UUID
    email: str
    token_hash: str
    invited_by: UUID | None
    expires_at: datetime
    used_at: datetime | None


class NotebookInviteRepository(Protocol):
    def create(
        self,
        *,
        invite_id: UUID,
        notebook_id: UUID,
        email: str,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> None: ...

    def delete_open_for_email(self, notebook_id: UUID, email: str) -> None:
        """End any unused invite for this notebook and email (FR-007)."""
        ...

    def list_unused(self, notebook_id: UUID) -> list[NotebookInviteRecord]:
        """Open and expired invites, most recently sent first."""
        ...

    def get(self, notebook_id: UUID, invite_id: UUID) -> NotebookInviteRecord | None:
        """The invite, only when it belongs to this notebook."""
        ...

    def get_by_token_hash(self, token_hash: str) -> NotebookInviteRecord | None: ...

    def rotate(
        self, invite_id: UUID, *, token_hash: str, invited_by: UUID, expires_at: datetime
    ) -> None:
        """Give the same row a new link and a new period, ending the earlier link."""
        ...

    def delete(self, notebook_id: UUID, invite_id: UUID) -> bool:
        """Delete an unused invite of this notebook; True when a row went."""
        ...

    def claim(self, invite_id: UUID, *, used_at: datetime) -> bool:
        """Mark an unused, unexpired invite as used; False when someone else got there first."""
        ...


class IngredientCatalog(Protocol):
    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        """The catalog's kept names only, sorted (admin and places readers)."""
        ...

    def index_for_notebook(self, notebook_id: UUID) -> CatalogIndex:
        """Every kept and other name of the catalog, for matching and display (spec 043 R4)."""
        ...

    def copy_names(self, source_id: UUID, target_id: UUID) -> None:
        """Copy the source's catalog to the target's, unchanged (spec 035 FR-011).

        Kept names, their languages and their other names all travel (spec 043).
        """
        ...

    def names_for_person(self, user_id: UUID) -> list[str]:
        """Distinct names across the user's personal notebooks (never kitchen notebooks)."""
        ...

    def seed_from_person(self, notebook_id: UUID, user_id: UUID) -> None:
        """Copy the person's personal catalog into a new notebook's catalog."""
        ...

    def add_names(self, notebook_id: UUID, names: Sequence[str]) -> None:
        """Add names the catalog lacks; a name already there is left as it is (spec 020)."""
        ...

    # --- catalog management (spec 043); no commit inside, the request's transaction decides ---

    def savepoint(self) -> AbstractContextManager[object]:
        """A savepoint: an error inside rolls back only its writes.

        A database conflict inside raises CatalogNameChangedError (FR-015).
        """
        ...

    def lock_entries(self, notebook_id: UUID, names: Sequence[str]) -> None:
        """Lock the ingredient rows of these kept names (FOR UPDATE), so two writes serialize."""
        ...

    def recipe_counts(self, notebook_id: UUID) -> dict[str, int]:
        """For each line name used in the notebook, how many of its recipes use it."""
        ...

    def language_counts(self, notebook_id: UUID, name: str) -> dict[str, int]:
        """How many of the notebook's recipes using the name are in each language."""
        ...

    def apply_merge(self, notebook_id: UUID, plan: MergePlan) -> list[UUID]:
        """Write one notebook's merge; the ids of recipes whose lines changed."""
        ...

    def apply_rename(self, notebook_id: UUID, old: str, new: str) -> list[UUID]:
        """Rename a kept name, its lines and its dismissals; the ids of recipes changed."""
        ...

    def set_language(self, notebook_id: UUID, name: str, language: str | None) -> None:
        """Set a kept name's language; no line changes (FR-012)."""
        ...

    def delete_unused(self, notebook_id: UUID, name: str) -> int:
        """Delete the name with its other names when no recipe uses it, and return 0.

        When recipes use it, delete nothing and return how many do (FR-013).
        """
        ...

    def apply_split(self, notebook_id: UUID, kept: str, plan: SplitPlan) -> list[UUID]:
        """Make an other name its own ingredient; the ids of recipes whose lines moved."""
        ...

    def dismissed_pairs(self, notebook_id: UUID) -> list[tuple[str, str]]: ...

    def dismiss_pair(self, notebook_id: UUID, first: str, second: str, user_id: UUID) -> None:
        """Remember a pair as not the same ingredient in this notebook (FR-009d)."""
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
    # The recipe image as a data URI, or None (spec 026).
    preview_image: str | None = None
    # The recipe's language, and the model's differing proposal awaiting a person (spec 043).
    language: str = "es"
    proposed_language: str | None = None


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

    def copy_all(self, source_id: UUID, target_id: UUID) -> int:
        """Copy every recipe of the source notebook to the target as last saved; returns the count.

        Each copy has its own lines, steps and source row, keeps its author and creation time, and
        starts with no save key and a cart count of zero (spec 035 data-model.md).
        """
        ...

    def copy_one(
        self,
        source_recipe_id: UUID,
        target_notebook_id: UUID,
        author_id: UUID,
        *,
        link_source: bool = True,
    ) -> UUID | None:
        """Copy one recipe into the target notebook as last saved; returns the copy's id.

        The copy has its own lines, steps and source row, the given author, a creation time of
        now, and records the source in its hidden copied_from_recipe_id (spec 069). With
        link_source False (spec 071 share) that column stays empty: the copy has no link back.
        The source is read FOR SHARE. Returns None when the source is gone.
        """
        ...

    def rename_line_names(self, recipe_id: UUID, renames: Mapping[str, str]) -> None:
        """Set each line of the recipe whose name is a key to the mapped name (spec 071 R-3)."""
        ...

    def set_language(self, recipe_id: UUID, language: str | None) -> None:
        """Store the language and clear the proposal; with None only clear it (spec 043)."""
        ...

    def overwrite_from(
        self, target_recipe_id: UUID, source_recipe_id: UUID, author_id: UUID
    ) -> bool:
        """Replace the target's title, servings, image, source, lines and steps with the source's.

        Keeps the target's id, notebook, creation time and copied_from_recipe_id; sets its author.
        Returns False when either recipe is gone (spec 069 research R6).
        """
        ...

    def latest_copy_in_kitchen(
        self, source_recipe_id: UUID, kitchen_id: UUID
    ) -> KitchenRecipeCopy | None:
        """The newest recipe in any notebook of the kitchen copied from the source, or None."""
        ...


@dataclass(frozen=True, slots=True)
class KitchenRecipeCopy:
    recipe_id: UUID
    notebook_id: UUID
    notebook_name: str


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
    # The recipe image as a data URI (spec 026), or None.
    preview_image: str | None = None


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


# --- Cart and edit locks (spec 022) ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionRef:
    """The caller and the session their request came with; locks belong to the session."""

    user_id: UUID
    session_id: UUID


@dataclass(frozen=True, slots=True)
class LockHolder:
    session_id: UUID
    user_id: UUID
    # None when the holder has no alias (reads "unknown").
    alias: str | None
    last_active_at: datetime


@dataclass(frozen=True, slots=True)
class LockAccess:
    """The access a recipe lock depends on: exactly one is set (research R11)."""

    kitchen_membership_id: UUID | None
    notebook_id: UUID | None


@dataclass(frozen=True, slots=True)
class CartDraftItem:
    recipe_id: UUID
    servings: int


@dataclass(frozen=True, slots=True)
class CartDraft:
    items: tuple[CartDraftItem, ...]


@dataclass(frozen=True, slots=True)
class CartRecipeFacts:
    recipe_id: UUID
    title: str
    notebook_id: UUID
    notebook_name: str
    base_servings: int
    # None for a personal notebook.
    kitchen_id: UUID | None


@dataclass(frozen=True, slots=True)
class SavedCart:
    kitchen_id: UUID
    # In added order.
    items: tuple[CartDraftItem, ...]


class ShoppingListRepository(Protocol):
    """Saved lists (spec 025). Callers hold the cart row lock, which serializes these writes."""

    def active(self, kitchen_id: UUID) -> SavedList | None: ...

    def get_or_create_active(self, kitchen_id: UUID) -> SavedList:
        """The active list, created empty when there is none."""
        ...

    def replace_cart_lines(self, list_id: UUID, lines: Sequence[SavedLine]) -> None:
        """Replace the rows of origin cart; hand items stay."""
        ...

    def add_item(self, list_id: UUID, item: SavedLine) -> None: ...

    def remove_hand_item(self, list_id: UUID, item_id: UUID) -> bool:
        """False when the list holds no such item added by hand."""
        ...

    def set_bought(self, list_id: UUID, item_id: UUID, bought: bool) -> SavedLine | None:
        """Set the flag on an item of an active list; None when it holds no such item (070)."""
        ...

    def is_closed_item(self, kitchen_id: UUID, item_id: UUID) -> bool:
        """True when the item belongs to one of the kitchen's closed lists (spec 070)."""
        ...

    def close(self, list_id: UUID, closing_date: date) -> bool:
        """Set the closing date if still active; False when it was already closed."""
        ...

    def closed(self, kitchen_id: UUID) -> tuple[SavedList, ...]:
        """Closed lists, newest first."""
        ...

    def closed_by_id(self, kitchen_id: UUID, list_id: UUID) -> SavedList | None: ...


class ShoppingListRefresher(Protocol):
    def refresh(self, kitchen_id: UUID) -> None:
        """Bring the active list in line with the saved cart (spec 025 FR-001)."""
        ...


class CartRepository(Protocol):
    def get_or_create_for_update(self, kitchen_id: UUID) -> SavedCart:
        """Create the row with ON CONFLICT DO NOTHING, then SELECT … FOR UPDATE it."""
        ...

    def read(self, kitchen_id: UUID) -> SavedCart:
        """The saved cart; no row reads as SavedCart(kitchen_id, ())."""
        ...

    def recipe_facts(self, recipe_ids: Sequence[UUID]) -> dict[UUID, CartRecipeFacts]:
        """Facts of the recipes that exist; missing ids are absent."""
        ...

    def save(self, kitchen_id: UUID, draft: CartDraft, user_id: UUID) -> tuple[UUID, ...]:
        """Replace the items, raise cart_add_count by 1 for each recipe not in the
        saved items, and return the newly added ids."""
        ...


class EditLockRepository(Protocol):
    """Cart and recipe edit locks. Every holder read returns live locks only (research R10)."""

    def cart_holder(self, kitchen_id: UUID) -> LockHolder | None: ...

    def cart_draft(self, kitchen_id: UUID, session_id: UUID) -> CartDraft | None: ...

    def take_cart(
        self, kitchen_id: UUID, ref: SessionRef, membership_id: UUID, draft: CartDraft
    ) -> None: ...

    def touch_cart(self, kitchen_id: UUID, session_id: UUID) -> None: ...

    def set_cart_draft(self, kitchen_id: UUID, session_id: UUID, draft: CartDraft) -> None: ...

    def kitchen_membership_id(self, kitchen_id: UUID, user_id: UUID) -> UUID | None: ...

    def release_cart(self, kitchen_id: UUID, session_id: UUID) -> None: ...

    def recipe_holder(self, recipe_id: UUID) -> LockHolder | None: ...

    def take_recipe(self, recipe_id: UUID, ref: SessionRef, access: LockAccess) -> None: ...

    def touch_recipe(self, recipe_id: UUID, session_id: UUID) -> None: ...

    def release_recipe(self, recipe_id: UUID, session_id: UUID) -> None: ...

    def recipe_lock_access(self, recipe_id: UUID, user_id: UUID) -> LockAccess | None:
        """The kitchen membership or notebook membership that lets the user write the recipe."""
        ...

    def lock_recipe_row(self, recipe_id: UUID) -> bool:
        """SELECT … FOR UPDATE on the recipe; False when it is gone (research R5)."""
        ...

    def release_all_for_kitchen(self, kitchen_id: UUID) -> None:
        """Delete the kitchen's cart lock and the locks of every recipe in its notebooks."""
        ...

    def now(self) -> datetime:
        """The clock liveness uses (database time in the adapter)."""
        ...


@dataclass(frozen=True, slots=True)
class CartIngredientLine:
    """One ingredient line of a recipe, as the shopping list reads it (spec 023).

    Either vague (`vague_note` set, `quantity` and `unit` null) or measured (`quantity > 0` and
    `unit` set). Preparation is not part of it (FR-004).
    """

    name: str
    quantity: Decimal | None
    unit: str | None
    size: str | None
    vague_note: str | None


class IngredientLineReader(Protocol):
    """Read only: the ingredient lines of recipes, for the shopping list (spec 023)."""

    def lines_for(self, recipe_ids: Sequence[UUID]) -> dict[UUID, tuple[CartIngredientLine, ...]]:
        """Each recipe's lines in `position` order; a recipe with no lines is absent or empty."""
        ...


class ListNameSource(Protocol):
    """Read only: each ingredient's word per language for a set of recipes (spec 043 R7)."""

    def names_for(self, recipe_ids: Sequence[UUID]) -> dict[str, dict[str, str]]:
        """Kept name -> {language: word}; an ingredient with no variant is absent."""
        ...


class UnitRepository(Protocol):
    """The unit table (spec 055). A person's other units; the ten defaults live in the domain."""

    def extras_for(self, user_id: UUID) -> list[str]:
        """Sorted names that are default or reference the person, without the ten."""
        ...

    def add_user(self, names: Sequence[str], user_id: UUID) -> None:
        """Add the person to each name's row, creating it when missing. Safe to repeat."""
        ...

    def remove_user(self, user_id: UUID) -> None:
        """Take the person off every row, locking in name order. A non-default row left with no
        references goes. Safe to repeat. Never commits and never touches a recipe line."""
        ...


class CartActivityLog(Protocol):
    """Who did what to a cart, for the dashboard only. No cart rule reads it (spec 055 R18)."""

    def record(self, user_id: UUID, action: CartAction) -> None: ...


@dataclass(frozen=True, slots=True)
class AdminUnitRow:
    name: str
    user_references: tuple[UUID, ...]
    user_aliases: tuple[str | None, ...]
    reference_count: int
    is_default: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AdminIngredientRow:
    name: str
    recipes: int
    people: int


@dataclass(frozen=True, slots=True)
class AdminRecipeRow:
    id: UUID
    title: str
    cart_adds: int
    notebook_name: str
    notebook_kind: str
    people_with_access: int
    people_aliases: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class AdminUserRow:
    id: UUID
    alias: str | None
    open_sessions: int
    newest_session_at: datetime | None
    recipes_authored: int
    latest_recipe_at: datetime | None
    carts_created: int
    carts_edited: int
    carts_closed: int
    latest_cart_action_at: datetime | None


@dataclass(frozen=True, slots=True)
class AdminRefusedSiteRow:
    domain: str
    total_refusals: int
    distinct_members: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_status: int
    last_message: str


class AdminReportRepository(Protocol):
    """Figures across every account (spec 055 R17) and the admin's recipe delete.

    Holds no recipe content.
    """

    def is_admin(self, user_id: UUID) -> bool: ...

    def units(self) -> Sequence[AdminUnitRow]: ...

    def ingredients(self) -> Sequence[AdminIngredientRow]: ...

    def recipes(self) -> Sequence[AdminRecipeRow]: ...

    def users(self) -> Sequence[AdminUserRow]: ...

    def refused_sites(self) -> Sequence[AdminRefusedSiteRow]:
        """Sorted by total_refusals DESC, then domain (spec 067)."""
        ...

    def delete_recipe(self, recipe_id: UUID) -> None:
        """Remove a recipe in any notebook. Raises RecipeNotFoundError when it is gone."""
        ...


class SidePanelRepository(Protocol):
    """Everything the side panel reads about the caller (spec 064)."""

    def stored_default_kitchen(self, user_id: UUID) -> UUID | None: ...

    def member_kitchens(self, user_id: UUID) -> Sequence[MemberKitchen]: ...

    def set_default_kitchen(self, user_id: UUID, kitchen_id: UUID | None) -> None: ...

    def count_recipes_added(self, user_id: UUID) -> int: ...

    def count_notebooks(self, user_id: UUID) -> int: ...

    def is_admin(self, user_id: UUID) -> bool: ...


# --- Places to buy things (spec 070) -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlaceSource:
    """Someone who shares a kitchen or a personal notebook with the caller (spec 070 R8)."""

    user_id: UUID
    alias: str


@dataclass(frozen=True, slots=True)
class RecipeUse:
    """One ingredient line of a recipe the person can read: its name, the recipe and its date."""

    name: str
    recipe_id: UUID
    title: str
    used_at: datetime


class PlaceRepository(Protocol):
    """One person's custom places and their place per ingredient name (spec 070 R5)."""

    def list_custom(self, user_id: UUID) -> Sequence[CustomPlace]:
        """The person's places, sorted by name."""
        ...

    def name_keys(self, user_id: UUID, *, except_id: UUID | None = None) -> set[str]:
        """Folded names of the person's places, one place left out when renaming."""
        ...

    def add(self, user_id: UUID, name: str, name_key: str) -> CustomPlace: ...

    def rename(self, user_id: UUID, place_id: UUID, name: str, name_key: str) -> CustomPlace | None:
        """None when the place is not the person's."""
        ...

    def delete(self, user_id: UUID, place_id: UUID) -> bool:
        """False when the place is not the person's; its ingredient choices go with it."""
        ...

    def choices(self, user_id: UUID) -> dict[str, PlaceRef]:
        """Every stored choice of the person, by normalized ingredient name."""
        ...

    def set_choice(self, user_id: UUID, name: str, place: PlaceRef) -> None:
        """Store the person's place for a normalized name, replacing any earlier choice."""
        ...

    def catalog_names(self, user_id: UUID) -> Sequence[str]:
        """Names of the catalogs the person can read plus their chosen names (research R7)."""
        ...

    def recipe_uses(self, user_id: UUID) -> Sequence[RecipeUse]:
        """Every ingredient line of the recipes the person can read (same reach as the catalogs)."""
        ...

    def sources(self, user_id: UUID) -> Sequence[PlaceSource]: ...

    def other_names(self, user_id: UUID) -> Sequence[tuple[str, str]]:
        """(kept name, other name) pairs of the catalogs the person can read (spec 043 R8)."""
        ...

    def move_choices(self, old_name: str, new_name: str) -> None:
        """Move every person's choice for a name to another name (spec 043 R8, FR-009).

        A person with a choice for the new name keeps it, and their old-name row stays.
        """
        ...


class IngredientPairSuggester(Protocol):
    """Port: likely English and Spanish pairs of one catalog's names (spec 043 R9).

    Only names and their languages are sent, never recipe text. Raises AIUnavailableError when
    the model gives no usable answer.
    """

    def suggest(self, names: Sequence[tuple[str, str | None]]) -> list[tuple[str, str]]:
        """(english, spanish) pairs the model thinks are one ingredient; not yet filtered."""
        ...


class LanguageDetector(Protocol):
    """Port: the language most of a recipe is in (spec 043 FR-005a)."""

    def detect(self, text: str) -> str | None:
        """'en' or 'es', or None when unsure or on a model error."""
        ...


# --- Recipe embeddings and search (spec 019) --------------------------------------------------


@dataclass(frozen=True, slots=True)
class Embedded:
    """Vectors of the configured length, L2-normalized, one per text in order."""

    vectors: tuple[tuple[float, ...], ...]
    # None where the service did not say (research R2).
    token_counts: tuple[int | None, ...]
    truncated: tuple[bool, ...]


# The failures are the extractor's result classes: one vocabulary for Gemini (research R11).
EmbedFailure = LimitReached | Unavailable | InvalidOutput | AIProviderError
EmbedResult = Embedded | EmbedFailure


class Embedder(Protocol):
    """Port: one service call per method call, no retries. Never raises for service problems."""

    @property
    def model(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    @property
    def configured(self) -> bool:
        """False with no key or no model: every call would answer AIProviderError (FR-014)."""
        ...

    def embed_documents(
        self, texts: Sequence[str], titles: Sequence[str], timeout_s: float
    ) -> EmbedResult:
        """Recipes, as RETRIEVAL_DOCUMENT with their titles."""
        ...

    def embed_query(self, text: str, timeout_s: float) -> EmbedResult:
        """A question, as RETRIEVAL_QUERY; one vector."""
        ...

    def count_tokens(self, text: str, timeout_s: float) -> int | None:
        """The input size in tokens, or None when it cannot be counted."""
        ...


class EmbedTextStrategy(Protocol):
    @property
    def name(self) -> str: ...

    def render(self, recipe: RecipeDetail) -> str: ...


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    recipe_id: UUID
    attempts: int
    # The wait used after the last failure; None before any (the retry rule starts over).
    last_wait_s: float | None


@dataclass(frozen=True, slots=True)
class Backlog:
    count: int
    oldest_enqueued_at: datetime | None


class EmbeddingJobs(Protocol):
    def enqueue(self, recipe_ids: Sequence[UUID]) -> None:
        """Make each recipe due now, with its retry state reset (an upsert)."""
        ...

    def enqueue_notebook(self, notebook_id: UUID) -> None:
        """Enqueue every recipe of the notebook, in one statement."""
        ...

    def enqueue_missing(self, model: str, *, other_strategy_of: str | None = None) -> int:
        """Queue recipes without a current embedding for the model; returns how many.

        With `other_strategy_of`, an embedding made with another strategy does not count.
        Recipes already queued keep their attempts and last wait but become due now (SC-003);
        they are not counted.
        """
        ...

    def claim(self, batch: int, lease_s: float) -> list[ClaimedJob]:
        """Take up to `batch` due jobs no other process holds, for `lease_s` seconds."""
        ...

    def fail(self, recipe_id: UUID, wait_s: float, failure: str) -> None:
        """Due again after `wait_s`. `failure` is a result class name, never a message."""
        ...

    def release_changed(self, recipe_id: UUID) -> None:
        """The recipe changed while it was embedded: due now, attempts unchanged."""
        ...

    def backlog(self) -> Backlog: ...

    def failure_counts(self) -> dict[str, int]:
        """Waiting jobs by the class of their last failure."""
        ...


class RecipeEmbeddings(Protocol):
    def content_for(self, recipe_ids: Sequence[UUID]) -> list[RecipeDetail]:
        """The recipes that still exist; `updated_at` is the version that was read."""
        ...

    def write_if_current(
        self,
        recipe_id: UUID,
        read_version: datetime,
        model: str,
        vector: Sequence[float],
        strategy: str,
        tokens: int | None,
        truncated: bool = False,
    ) -> bool:
        """Store the embedding only if the recipe still has `read_version`, and end its job.

        False when the recipe changed or is gone; nothing is written then (research R5).
        """
        ...

    def search(
        self,
        notebook_ids: Sequence[UUID],
        filters: SearchFilters,
        model: str,
        query_vector: Sequence[float],
        limit: int,
    ) -> list[RawHit]:
        """Current embeddings of the model only, filters first, then closest first."""
        ...


@dataclass(frozen=True, slots=True)
class RawHit:
    recipe_id: UUID
    notebook_id: UUID
    title: str
    # 1 - cosine distance.
    score: float


@dataclass(frozen=True, slots=True)
class SearchEventRecord:
    feature: str
    scope_kind: str
    model: str
    strategy: str
    min_closeness: float


@dataclass(frozen=True, slots=True)
class RecordedHit:
    recipe_id: UUID
    rank: int
    score: float
    mark: str


@dataclass(frozen=True, slots=True)
class Band:
    low: float
    high: float
    shown: int
    used: int


class SearchRecords(Protocol):
    def record(self, event: SearchEventRecord, hits: Sequence[RecordedHit]) -> UUID: ...

    def mark_used(self, search_id: UUID, recipe_id: UUID) -> bool:
        """Set `used_at` once; False when the pair does not exist."""
        ...

    def delete_older_than(self, cutoff: datetime) -> int: ...

    def score_bands(self, width: float) -> list[Band]: ...


# --- Link capture (spec 026, contracts/ports.md) ---

PageFetchFailureKind = Literal[
    "blocked", "dns", "timeout", "connect", "redirect", "status", "not_html", "too_large", "refused"
]
ImageMediaType = Literal["image/jpeg", "image/png", "image/webp"]


@dataclass(frozen=True, slots=True)
class FetchedPage:
    # The address after redirects; what the draft returns and Save stores.
    final_url: str
    html: str
    byte_count: int


@dataclass(frozen=True, slots=True)
class PageFetchFailed:
    """The page could not be fetched.

    Every kind except `refused` shows the member the same message (spec 026 R10). `refused` means
    the site itself answered 401/402/403/451 (spec 067 R1); only it sets `status` and `message`
    (the refusal page's plain text, at most 1,000 characters).
    """

    kind: PageFetchFailureKind
    status: int | None = None
    message: str = ""


class RefusedSiteLog(Protocol):
    """Port: count one site refusal per registrable domain (spec 067)."""

    def record(self, host: str, actor_user_id: UUID, status: int, message: str) -> None:
        """Count one refusal for host's registrable domain. May raise; callers swallow."""
        ...


@dataclass(frozen=True, slots=True)
class FetchedImage:
    media_type: ImageMediaType
    data: bytes


@dataclass(frozen=True, slots=True)
class PageContent:
    recipes: tuple[PageRecipe, ...]
    main_image_url: str | None
    markdown: str


class PageFetcher(Protocol):
    """Port: the one page the member gave, and its main photo. Never raises."""

    def fetch_page(self, url: str) -> FetchedPage | PageFetchFailed: ...

    def fetch_image(self, url: str) -> FetchedImage | None: ...


class PageReader(Protocol):
    """Port: HTML in, schema.org recipes, main photo address and Markdown out. Never raises."""

    def read(self, html: str, base_url: str) -> PageContent: ...


@dataclass(frozen=True, slots=True)
class CoMemberRecord:
    """A person who shares a kitchen or a notebook with the caller (spec 071).

    `shared_at` is the latest join time over the shared contexts, or None when no join time
    is stored; it is used only for ordering.
    """

    user_id: UUID
    alias: str
    shared_at: datetime | None


class CoMemberDirectory(Protocol):
    def list_co_members(self, user_id: UUID) -> list[CoMemberRecord]:
        """Co-members of the user, most recent shared activity first, then alias (FR-004)."""
        ...

    def is_co_member(self, user_id: UUID, other_id: UUID) -> bool: ...
