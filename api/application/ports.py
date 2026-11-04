"""Ports for application use-cases (implemented by adapters)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from domain.cart import CartAction
from domain.default_kitchen import MemberKitchen
from domain.notebook import Notebook, NotebookRole
from domain.recipe import EditedRecipe, NewRecipe
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
    def names_for_notebook(self, notebook_id: UUID) -> list[str]: ...

    def copy_names(self, source_id: UUID, target_id: UUID) -> None:
        """Copy every name of the source's catalog to the target's, unchanged (spec 035 FR-011)."""
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

    def copy_all(self, source_id: UUID, target_id: UUID) -> int:
        """Copy every recipe of the source notebook to the target as last saved; returns the count.

        Each copy has its own lines, steps and source row, keeps its author and creation time, and
        starts with no save key and a cart count of zero (spec 035 data-model.md).
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


class AdminReportRepository(Protocol):
    """Read-only figures across every account (spec 055 R17). Holds no recipe content."""

    def is_admin(self, user_id: UUID) -> bool: ...

    def units(self) -> Sequence[AdminUnitRow]: ...

    def ingredients(self) -> Sequence[AdminIngredientRow]: ...

    def recipes(self) -> Sequence[AdminRecipeRow]: ...

    def users(self) -> Sequence[AdminUserRow]: ...


class SidePanelRepository(Protocol):
    """Everything the side panel reads about the caller (spec 064)."""

    def stored_default_kitchen(self, user_id: UUID) -> UUID | None: ...

    def member_kitchens(self, user_id: UUID) -> Sequence[MemberKitchen]: ...

    def set_default_kitchen(self, user_id: UUID, kitchen_id: UUID | None) -> None: ...

    def count_recipes_added(self, user_id: UUID) -> int: ...

    def count_notebooks(self, user_id: UUID) -> int: ...

    def is_admin(self, user_id: UUID) -> bool: ...


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
