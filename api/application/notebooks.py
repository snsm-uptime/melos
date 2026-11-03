"""Notebook reads and writes for people and kitchens (spec 056).

Creation happens in four places, each under a lock: a person's default notebook
(first use), a kitchen's first notebook (first open or first capture), a capture
notebook in a kitchen or outside one, and a snapshot (spec 035). Every answer is built
with notebook_view.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.errors import (
    AliasRequiredError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
    SnapshotExistsError,
)
from domain.notebook import (
    Notebook,
    NotebookAccess,
    NotebookKind,
    assert_can_manage,
    choose_capture_notebook,
    default_notebook_name,
    kitchen_notebook_name,
    notebook_access,
    validate_notebook_name,
)

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.kitchens import KitchenRecord, KitchenRepository
from application.ports import (
    IngredientCatalog,
    KitchenAccessGrant,
    NotebookFacts,
    NotebookRepository,
    PreferencesRepository,
    RecipeRepository,
    TransactionCommitter,
    UserDefaultNotebook,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NotebookView:
    """The answer for one notebook, as the caller may see it (contract "The notebook object")."""

    id: UUID
    name: str
    kind: NotebookKind
    access: NotebookAccess
    owner_alias: str | None
    kitchen_id: UUID | None
    kitchen_is_archived: bool | None
    is_default: bool
    recipe_count: int
    origin_notebook_name: str | None = None
    is_snapshot: bool = False
    is_own_capture_notebook: bool = False


def notebook_view(facts: NotebookFacts) -> NotebookView:
    access = notebook_access(facts.notebook.kind, facts.role, facts.in_kitchen)
    if access is None:
        raise NotebookNotFoundError()
    return NotebookView(
        id=facts.notebook.id,
        name=facts.notebook.name,
        kind=facts.notebook.kind,
        access=access,
        owner_alias=facts.owner_alias,
        kitchen_id=facts.notebook.kitchen_id,
        kitchen_is_archived=facts.kitchen_is_archived,
        # A kitchen notebook is never anyone's default (data-model.md "Read model").
        is_default=facts.is_default and facts.notebook.kind == "personal",
        recipe_count=facts.recipe_count,
        origin_notebook_name=facts.origin_notebook_name,
        is_snapshot=facts.is_snapshot,
        is_own_capture_notebook=facts.is_own_capture_notebook,
    )


def _naming_profile(prefs: PreferencesRepository, user_id: UUID) -> tuple[str, str | None]:
    """The alias and saved language a new name is written with."""
    record = prefs.get_preferences(user_id)
    if record is None or not record.alias:
        raise AliasRequiredError()
    return record.alias, record.language


def ensure_default_notebook(
    user_id: UUID,
    *,
    notebooks: NotebookRepository,
    defaults: UserDefaultNotebook,
    prefs: PreferencesRepository,
    catalog: IngredientCatalog,
) -> tuple[UUID, bool]:
    """The person's default personal notebook, created under the user-row lock (FR-007).

    Returns (id, created). Simultaneous first calls leave one notebook: the loser waits
    on the lock and finds the default set.
    """
    current = defaults.get_for_update(user_id)
    if current is not None and notebooks.get(current) is not None:
        return current, False

    alias, language = _naming_profile(prefs, user_id)
    notebook = Notebook(id=uuid4(), name=default_notebook_name(alias, language))
    notebooks.create(notebook)
    catalog.seed_from_person(notebook.id, user_id)
    notebooks.add_owner(notebook.id, user_id)
    defaults.set(user_id, notebook.id)
    return notebook.id, True


def ensure_kitchen_notebook(
    kitchen: KitchenRecord,
    actor_user_id: UUID,
    alias: str,
    language: str | None,
    *,
    notebooks: NotebookRepository,
    catalog: IngredientCatalog,
) -> tuple[UUID, bool]:
    """A kitchen's first notebook, owned by the caller, made under the kitchen-row lock (FR-008a).

    Named with the caller's alias, in the caller's language.

    Returns (id, created). Not committed here: the caller decides (research R14).
    """
    notebooks.lock_kitchen(kitchen.id)
    existing = notebooks.kitchen_ids_for(kitchen.id)
    if existing:
        return existing[0], False
    return _create_kitchen_notebook(
        kitchen,
        actor_user_id,
        kitchen_notebook_name(alias, kitchen.name, language),
        notebooks=notebooks,
        catalog=catalog,
    ), True


def ensure_member_kitchen_notebook(
    kitchen: KitchenRecord,
    actor_user_id: UUID,
    alias: str,
    language: str | None,
    *,
    notebooks: NotebookRepository,
    catalog: IngredientCatalog,
) -> tuple[UUID, bool]:
    """The caller's own notebook in the kitchen, made under the kitchen-row lock.

    Returns (id, created). Not committed here: the caller decides (research R14).
    """
    notebooks.lock_kitchen(kitchen.id)
    existing = notebooks.user_kitchen_notebook(actor_user_id, kitchen.id)
    if existing is not None:
        return existing, False
    return _create_kitchen_notebook(
        kitchen,
        actor_user_id,
        kitchen_notebook_name(alias, kitchen.name, language),
        notebooks=notebooks,
        catalog=catalog,
    ), True


def _locked_to_manage(
    notebooks: NotebookRepository, actor_user_id: UUID, notebook_id: UUID
) -> NotebookFacts:
    """The facts of a notebook the caller may rename or delete, with its locks held (research R2).

    An outsider takes no lock. A kitchen notebook locks the kitchen first, the order the snapshot
    path takes, so the archived check below is exact. Access is read again under the locks, since
    it may have ended while the request waited.
    """
    facts = notebooks.facts_for(actor_user_id, notebook_id)
    if facts is None:
        raise NotebookNotFoundError()
    notebook_view(facts)
    if facts.notebook.kitchen_id is not None:
        try:
            notebooks.lock_kitchen(facts.notebook.kitchen_id)
        except KitchenNotFoundError:
            # The notebook went with its kitchen.
            raise NotebookNotFoundError() from None
    notebooks.lock_notebook(notebook_id)
    facts = notebooks.facts_for(actor_user_id, notebook_id)
    if facts is None:
        raise NotebookNotFoundError()
    assert_can_manage(notebook_view(facts).access, facts.kitchen_is_archived)
    return facts


def _create_kitchen_notebook(
    kitchen: KitchenRecord,
    actor_user_id: UUID,
    name: str,
    *,
    notebooks: NotebookRepository,
    catalog: IngredientCatalog,
) -> UUID:
    notebook = Notebook(
        id=uuid4(),
        name=name,
        kitchen_id=kitchen.id,
        owner_user_id=actor_user_id,
    )
    notebooks.create(notebook)
    catalog.seed_from_person(notebook.id, actor_user_id)
    return notebook.id


@dataclass(frozen=True, slots=True)
class ListMyNotebooksCommand:
    actor_user_id: UUID


class ListMyNotebooksService:
    """The personal notebooks the caller owns or is a member of, and the notebooks of the
    kitchens they belong to. Creates nothing (FR-014)."""

    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: ListMyNotebooksCommand) -> list[NotebookView]:
        return [
            notebook_view(facts)
            for facts in self._notebooks.visible_facts_for(command.actor_user_id)
        ]


@dataclass(frozen=True, slots=True)
class GetDefaultNotebookCommand:
    actor_user_id: UUID


class GetDefaultNotebookService:
    """The caller's default notebook, created on first use (FR-007)."""

    def __init__(
        self,
        notebooks: NotebookRepository,
        defaults: UserDefaultNotebook,
        prefs: PreferencesRepository,
        catalog: IngredientCatalog,
    ) -> None:
        self._notebooks = notebooks
        self._defaults = defaults
        self._prefs = prefs
        self._catalog = catalog

    def execute(self, command: GetDefaultNotebookCommand) -> NotebookView:
        notebook_id, _ = ensure_default_notebook(
            command.actor_user_id,
            notebooks=self._notebooks,
            defaults=self._defaults,
            prefs=self._prefs,
            catalog=self._catalog,
        )
        facts = self._notebooks.facts_for(command.actor_user_id, notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        return notebook_view(facts)


@dataclass(frozen=True, slots=True)
class CreateNotebookCommand:
    actor_user_id: UUID
    name: str


class CreateNotebookService:
    """A new personal notebook with no recipes (S-059, creation only).

    The caller owns it and its catalog starts from theirs. Committed here, so the notebook is
    there when the ui opens it.
    """

    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        committer: TransactionCommitter,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._committer = committer

    def execute(self, command: CreateNotebookCommand) -> NotebookView:
        notebook = Notebook(id=uuid4(), name=validate_notebook_name(command.name))
        self._notebooks.create(notebook)
        self._catalog.seed_from_person(notebook.id, command.actor_user_id)
        self._notebooks.add_owner(notebook.id, command.actor_user_id)
        facts = self._notebooks.facts_for(command.actor_user_id, notebook.id)
        if facts is None:
            raise NotebookNotFoundError()
        view = notebook_view(facts)
        self._committer.commit()
        return view


@dataclass(frozen=True, slots=True)
class CreateKitchenNotebookCommand:
    actor_user_id: UUID
    kitchen_id: UUID
    name: str


class CreateKitchenNotebookService:
    """A new, empty kitchen notebook, recorded as the caller's own (spec 059 research R11).

    Access comes first, so a non-member learns nothing from a bad name. The archived check is
    read under the kitchen lock, which conflicts with archiving.
    """

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        committer: TransactionCommitter,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._catalog = catalog
        self._committer = committer

    def execute(self, command: CreateKitchenNotebookCommand) -> NotebookView:
        self._authorize(command)
        self._notebooks.lock_kitchen(command.kitchen_id)
        grant = self._authorize(command)
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        if kitchen.is_archived:
            raise KitchenArchivedError()
        notebook_id = _create_kitchen_notebook(
            kitchen,
            command.actor_user_id,
            validate_notebook_name(command.name),
            notebooks=self._notebooks,
            catalog=self._catalog,
        )
        facts = self._notebooks.facts_for(command.actor_user_id, notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        view = notebook_view(facts)
        self._committer.commit()
        return view

    def _authorize(self, command: CreateKitchenNotebookCommand) -> KitchenAccessGrant:
        return AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )


@dataclass(frozen=True, slots=True)
class RenameNotebookCommand:
    actor_user_id: UUID
    notebook_id: UUID
    name: str


class RenameNotebookService:
    """Give a notebook a new name (spec 059 FR-001 to FR-004).

    Saving the name it already has changes nothing and is not validated: a generated name can
    be over the limit, and the person did not type it (research R6).
    """

    def __init__(self, notebooks: NotebookRepository, committer: TransactionCommitter) -> None:
        self._notebooks = notebooks
        self._committer = committer

    def execute(self, command: RenameNotebookCommand) -> NotebookView:
        facts = _locked_to_manage(self._notebooks, command.actor_user_id, command.notebook_id)
        if command.name.strip() == facts.notebook.name:
            return notebook_view(facts)
        self._notebooks.rename(command.notebook_id, validate_notebook_name(command.name))
        renamed = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if renamed is None:
            raise NotebookNotFoundError()
        view = notebook_view(renamed)
        self._committer.commit()
        return view


@dataclass(frozen=True, slots=True)
class DeleteNotebookCommand:
    actor_user_id: UUID
    notebook_id: UUID


class DeleteNotebookService:
    """Delete a notebook and what it holds, as one step (spec 059 FR-005 to FR-010)."""

    def __init__(self, notebooks: NotebookRepository, committer: TransactionCommitter) -> None:
        self._notebooks = notebooks
        self._committer = committer

    def execute(self, command: DeleteNotebookCommand) -> None:
        _locked_to_manage(self._notebooks, command.actor_user_id, command.notebook_id)
        self._notebooks.delete(command.notebook_id)
        self._committer.commit()
        logger.info("notebook_deleted notebook_id=%s", command.notebook_id)


@dataclass(frozen=True, slots=True)
class GetNotebookCommand:
    actor_user_id: UUID
    notebook_id: UUID


class GetNotebookService:
    """One notebook by id, for a caller who may see it; anyone else gets NotebookNotFoundError."""

    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: GetNotebookCommand) -> NotebookView:
        facts = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        return notebook_view(facts)


@dataclass(frozen=True, slots=True)
class ListKitchenNotebooksCommand:
    actor_user_id: UUID
    kitchen_id: UUID


class ListKitchenNotebooksService:
    """A kitchen's notebooks for a member. The first open creates the first notebook (FR-008a).

    Authorizes with read_kitchen (404 for a missing kitchen and for a non-member). An
    archived kitchen with no notebook lists nothing and creates nothing. No commit: the
    request commits any creation with its response (research R14).
    """

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        prefs: PreferencesRepository,
        catalog: IngredientCatalog,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._prefs = prefs
        self._catalog = catalog

    def execute(self, command: ListKitchenNotebooksCommand) -> list[NotebookView]:
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        if not self._notebooks.kitchen_ids_for(kitchen.id) and not kitchen.is_archived:
            alias, language = _naming_profile(self._prefs, command.actor_user_id)
            ensure_kitchen_notebook(
                kitchen,
                command.actor_user_id,
                alias,
                language,
                notebooks=self._notebooks,
                catalog=self._catalog,
            )
        views = []
        for notebook in self._notebooks.kitchen_notebooks(kitchen.id):
            facts = self._notebooks.facts_for(command.actor_user_id, notebook.id)
            # None: deleted since the list was read (spec 059 FR-019).
            if facts is not None:
                views.append(notebook_view(facts))
        return views


@dataclass(frozen=True, slots=True)
class ResolveCaptureNotebookCommand:
    actor_user_id: UUID
    kitchen_id: UUID | None = None
    picked_notebook_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CaptureNotebook:
    notebook_id: UUID
    created: bool


class ResolveCaptureNotebookService:
    """The notebook a capture goes into (FR-009 to FR-011).

    Also behind POST /notebooks/kitchens/{id}/capture-notebook, which the ui calls for a member
    with no kitchen notebook of their own (spec 035 research R6).

    In a kitchen: the only notebook, the picked one, or a new kitchen notebook.
    Outside a kitchen: the only personal notebook, the picked one, or the default.
    A notebook created here is committed at once, so it stays if the save then fails.
    """

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        defaults: UserDefaultNotebook,
        prefs: PreferencesRepository,
        catalog: IngredientCatalog,
        committer: TransactionCommitter,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._defaults = defaults
        self._prefs = prefs
        self._catalog = catalog
        self._committer = committer

    def execute(self, command: ResolveCaptureNotebookCommand) -> CaptureNotebook:
        if command.kitchen_id is None:
            return self._personal(command)
        return self._kitchen(command)

    def _kitchen(self, command: ResolveCaptureNotebookCommand) -> CaptureNotebook:
        assert command.kitchen_id is not None
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        if kitchen.is_archived:
            raise KitchenArchivedError()

        # If the user explicitly picked one of this kitchen's notebooks, use it
        if command.picked_notebook_id is not None:
            if command.picked_notebook_id not in self._notebooks.kitchen_ids_for(kitchen.id):
                raise NotebookNotFoundError()
            return CaptureNotebook(notebook_id=command.picked_notebook_id, created=False)

        # Look for the user's kitchen notebook in this kitchen
        user_notebook = self._notebooks.user_kitchen_notebook(command.actor_user_id, kitchen.id)
        if user_notebook is not None:
            return CaptureNotebook(notebook_id=user_notebook, created=False)

        # User doesn't have their own notebook yet, create one
        alias, language = _naming_profile(self._prefs, command.actor_user_id)
        notebook_id, created = ensure_member_kitchen_notebook(
            kitchen,
            command.actor_user_id,
            alias,
            language,
            notebooks=self._notebooks,
            catalog=self._catalog,
        )
        if created:
            self._committer.commit()
        return CaptureNotebook(notebook_id=notebook_id, created=created)

    def _personal(self, command: ResolveCaptureNotebookCommand) -> CaptureNotebook:
        chosen = choose_capture_notebook(
            self._notebooks.personal_ids_for(command.actor_user_id),
            command.picked_notebook_id,
        )
        if chosen is not None:
            return CaptureNotebook(notebook_id=chosen, created=False)

        notebook_id, created = ensure_default_notebook(
            command.actor_user_id,
            notebooks=self._notebooks,
            defaults=self._defaults,
            prefs=self._prefs,
            catalog=self._catalog,
        )
        if created:
            self._committer.commit()
        return CaptureNotebook(notebook_id=notebook_id, created=created)


@dataclass(frozen=True, slots=True)
class AddNotebookSnapshotCommand:
    actor_user_id: UUID
    kitchen_id: UUID
    source_notebook_id: UUID
    snapshot_key: UUID
    confirm_repeat: bool = False


@dataclass(frozen=True, slots=True)
class AddedSnapshot:
    notebook: NotebookView
    # False when the key was already used, so the existing snapshot is returned.
    created: bool


class AddNotebookSnapshotService:
    """Add a personal notebook the caller owns to a kitchen as an independent copy (spec 035).

    Runs the checks in the order of contracts/snapshots-api.md. The request's one transaction
    makes it all or nothing, and the kitchen lock turns a concurrent repeat into a replay.
    """

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        recipes: RecipeRepository,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._catalog = catalog
        self._recipes = recipes

    def execute(self, command: AddNotebookSnapshotCommand) -> AddedSnapshot:
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        if kitchen.is_archived:
            raise KitchenArchivedError()

        self._notebooks.lock_kitchen(kitchen.id)
        replayed = self._notebooks.find_snapshot(kitchen.id, command.snapshot_key)
        if replayed is not None:
            logger.info("notebook snapshot outcome=replayed")
            return AddedSnapshot(self._view(command.actor_user_id, replayed), created=False)

        self._owned_source(command)
        # Held to the end, so a deletion of the original waits for the copy or is seen here
        # (spec 059 research R3). The owner may have changed while this waited.
        self._notebooks.lock_notebook(command.source_notebook_id)
        source = self._owned_source(command)
        if not command.confirm_repeat and self._notebooks.has_snapshot_of(
            kitchen.id, source.notebook.id
        ):
            raise SnapshotExistsError()

        notebook = Notebook(
            id=uuid4(),
            name=source.notebook.name,
            kitchen_id=kitchen.id,
            source_notebook_id=source.notebook.id,
            owner_user_id=command.actor_user_id,
            snapshot_key=command.snapshot_key,
        )
        self._notebooks.create(notebook)
        self._catalog.copy_names(source.notebook.id, notebook.id)
        copied = self._recipes.copy_all(source.notebook.id, notebook.id)
        logger.info("notebook snapshot outcome=created recipes=%d", copied)
        return AddedSnapshot(self._view(command.actor_user_id, notebook.id), created=True)

    def _owned_source(self, command: AddNotebookSnapshotCommand) -> NotebookFacts:
        source = self._notebooks.facts_for(command.actor_user_id, command.source_notebook_id)
        if source is None or source.notebook.kind != "personal" or source.role != "owner":
            raise NotebookNotFoundError()
        return source

    def _view(self, user_id: UUID, notebook_id: UUID) -> NotebookView:
        facts = self._notebooks.facts_for(user_id, notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        return notebook_view(facts)
