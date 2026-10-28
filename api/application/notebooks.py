"""Notebook reads and writes for people and kitchens (spec 056).

Creation happens in three places, each under a lock: a person's default notebook
(first use), a kitchen's first notebook (first open or first capture) and a capture
notebook in a kitchen or outside one. Every answer is built with notebook_view.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.errors import AliasRequiredError, KitchenArchivedError, NotebookNotFoundError
from domain.notebook import (
    Notebook,
    NotebookAccess,
    NotebookKind,
    choose_capture_notebook,
    default_notebook_name,
    kitchen_notebook_name,
    notebook_access,
)

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.kitchens import KitchenRecord, KitchenRepository
from application.ports import (
    IngredientCatalog,
    NotebookFacts,
    NotebookRepository,
    PreferencesRepository,
    TransactionCommitter,
    UserDefaultNotebook,
)


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

    notebook = Notebook(
        id=uuid4(),
        name=kitchen_notebook_name(alias, kitchen.name, language),
        kitchen_id=kitchen.id,
        owner_user_id=actor_user_id,
    )
    notebooks.create(notebook)
    catalog.seed_from_person(notebook.id, actor_user_id)
    return notebook.id, True


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
            if facts is None:
                raise NotebookNotFoundError()
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
    """The notebook a capture goes into (FR-009 to FR-011). Internal: no route (FR-013).

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

        chosen = choose_capture_notebook(
            self._notebooks.kitchen_ids_for(kitchen.id), command.picked_notebook_id
        )
        if chosen is not None:
            return CaptureNotebook(notebook_id=chosen, created=False)

        alias, language = _naming_profile(self._prefs, command.actor_user_id)
        notebook_id, created = ensure_kitchen_notebook(
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
