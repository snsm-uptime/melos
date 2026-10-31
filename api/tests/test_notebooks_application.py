"""Notebook use cases against fake ports (spec 056 FR-007 to FR-016, SC-001 to SC-006)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.kitchens import KitchenRecord, MembershipRecord
from application.notebooks import (
    CaptureNotebook,
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    GetNotebookCommand,
    GetNotebookService,
    ListKitchenNotebooksCommand,
    ListKitchenNotebooksService,
    ListMyNotebooksCommand,
    ListMyNotebooksService,
    NotebookView,
    ResolveCaptureNotebookCommand,
    ResolveCaptureNotebookService,
)
from application.ports import KitchenAccessGrant, NotebookFacts, UserPreferencesRecord
from domain.errors import (
    AliasRequiredError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
)
from domain.notebook import Notebook


@dataclass
class FakeKitchenRepo:
    kitchens: dict[UUID, KitchenRecord] = field(default_factory=dict)
    memberships: list[MembershipRecord] = field(default_factory=list)

    def get_kitchen(self, kitchen_id: UUID) -> KitchenRecord | None:
        return self.kitchens.get(kitchen_id)

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> MembershipRecord | None:
        return next(
            (m for m in self.memberships if m.kitchen_id == kitchen_id and m.user_id == user_id),
            None,
        )

    def get_kitchen_with_grant(self, grant: KitchenAccessGrant, kitchen_id: UUID) -> KitchenRecord:
        return self.kitchens[kitchen_id]


@dataclass
class FakeNotebookRepo:
    """Notebooks in creation order, with memberships, defaults and a log of calls."""

    kitchens: FakeKitchenRepo
    aliases: dict[UUID, str]
    notebooks: dict[UUID, Notebook] = field(default_factory=dict)
    # (notebook_id, user_id) -> "owner" | "member"; personal notebooks only.
    roles: dict[tuple[UUID, UUID], str] = field(default_factory=dict)
    defaults: dict[UUID, UUID] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    # The next kitchen_ids_for call returns nothing: another request created one meanwhile.
    hide_next_kitchen_read: bool = False

    def get(self, notebook_id: UUID) -> Notebook | None:
        return self.notebooks.get(notebook_id)

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        notebook = self.notebooks.get(notebook_id)
        if notebook is None:
            return None
        is_default = self.defaults.get(user_id) == notebook_id
        if notebook.kitchen_id is not None:
            kitchen = self.kitchens.kitchens[notebook.kitchen_id]
            owner_id = notebook.owner_user_id or kitchen.owner_id
            return NotebookFacts(
                notebook=notebook,
                role=None,
                in_kitchen=self.kitchens.get_membership(kitchen.id, user_id) is not None,
                owner_alias=self.aliases.get(owner_id),
                kitchen_is_archived=kitchen.is_archived,
                is_default=is_default,
                recipe_count=0,
            )
        owner_id = next(
            (u for (n, u), r in self.roles.items() if n == notebook_id and r == "owner"), None
        )
        return NotebookFacts(
            notebook=notebook,
            role=self.roles.get((notebook_id, user_id)),
            in_kitchen=False,
            owner_alias=self.aliases.get(owner_id) if owner_id is not None else None,
            kitchen_is_archived=None,
            is_default=is_default,
            recipe_count=0,
        )

    def visible_facts_for(self, user_id: UUID) -> list[NotebookFacts]:
        return [
            facts
            for notebook in self.notebooks.values()
            for facts in [self.facts_for(user_id, notebook.id)]
            if facts is not None and (facts.role is not None or facts.in_kitchen)
        ]

    def kitchen_notebooks(self, kitchen_id: UUID) -> list[Notebook]:
        self.calls.append("kitchen_notebooks")
        return [n for n in self.notebooks.values() if n.kitchen_id == kitchen_id]

    def personal_ids_for(self, user_id: UUID) -> list[UUID]:
        self.calls.append("personal_ids_for")
        return [
            n.id
            for n in self.notebooks.values()
            if n.kitchen_id is None and (n.id, user_id) in self.roles
        ]

    def kitchen_ids_for(self, kitchen_id: UUID) -> list[UUID]:
        self.calls.append("kitchen_ids_for")
        if self.hide_next_kitchen_read:
            self.hide_next_kitchen_read = False
            return []
        return [n.id for n in self.notebooks.values() if n.kitchen_id == kitchen_id]

    def user_kitchen_notebook(self, user_id: UUID, kitchen_id: UUID) -> UUID | None:
        self.calls.append("user_kitchen_notebook")
        if self.hide_next_kitchen_read:
            self.hide_next_kitchen_read = False
            return None
        for n in self.notebooks.values():
            if n.kitchen_id == kitchen_id and n.owner_user_id == user_id:
                return n.id
        return None

    def create(self, notebook: Notebook) -> None:
        self.calls.append("create")
        self.notebooks[notebook.id] = notebook

    def add_owner(self, notebook_id: UUID, user_id: UUID) -> None:
        self.calls.append("add_owner")
        self.roles[(notebook_id, user_id)] = "owner"

    def lock_kitchen(self, kitchen_id: UUID) -> None:
        self.calls.append("lock_kitchen")

    def delete(self, notebook_id: UUID) -> None:
        """ON DELETE SET NULL on users.default_notebook_id."""
        del self.notebooks[notebook_id]
        for user_id, default_id in list(self.defaults.items()):
            if default_id == notebook_id:
                del self.defaults[user_id]


@dataclass
class FakeUserDefaultNotebook:
    repo: FakeNotebookRepo
    locks: int = 0

    def get_for_update(self, user_id: UUID) -> UUID | None:
        self.locks += 1
        return self.repo.defaults.get(user_id)

    def set(self, user_id: UUID, notebook_id: UUID) -> None:
        self.repo.defaults[user_id] = notebook_id


@dataclass
class FakeIngredientCatalog:
    repo: FakeNotebookRepo
    names: dict[UUID, set[str]] = field(default_factory=dict)

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return sorted(self.names.get(notebook_id, set()))

    def names_for_person(self, user_id: UUID) -> list[str]:
        personal = [
            n.id
            for n in self.repo.notebooks.values()
            if n.kitchen_id is None and (n.id, user_id) in self.repo.roles
        ]
        return sorted(
            {name for notebook_id in personal for name in self.names.get(notebook_id, set())}
        )

    def seed_from_person(self, notebook_id: UUID, user_id: UUID) -> None:
        self.names[notebook_id] = set(self.names_for_person(user_id))


@dataclass
class FakeCommitter:
    commits: int = 0

    def commit(self) -> None:
        self.commits += 1


@dataclass
class FakePrefs:
    aliases: dict[UUID, str]
    languages: dict[UUID, str] = field(default_factory=dict)

    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None:
        return UserPreferencesRecord(
            id=user_id,
            email="x@example.com",
            language=self.languages.get(user_id),
            theme=None,
            alias=self.aliases.get(user_id),
        )


@dataclass
class World:
    kitchens: FakeKitchenRepo
    notebooks: FakeNotebookRepo
    catalog: FakeIngredientCatalog
    defaults: FakeUserDefaultNotebook
    prefs: FakePrefs
    committer: FakeCommitter


def _world(aliases: dict[UUID, str], languages: dict[UUID, str] | None = None) -> World:
    kitchens = FakeKitchenRepo()
    notebooks = FakeNotebookRepo(kitchens=kitchens, aliases=aliases)
    return World(
        kitchens=kitchens,
        notebooks=notebooks,
        catalog=FakeIngredientCatalog(notebooks),
        defaults=FakeUserDefaultNotebook(notebooks),
        prefs=FakePrefs(aliases, languages or {}),
        committer=FakeCommitter(),
    )


def _kitchen(world: World, owner: UUID, name: str = "Home", *, archived: bool = False) -> UUID:
    kitchen_id = uuid4()
    world.kitchens.kitchens[kitchen_id] = KitchenRecord(
        id=kitchen_id, name=name, owner_id=owner, is_archived=archived
    )
    world.kitchens.memberships.append(
        MembershipRecord(kitchen_id=kitchen_id, user_id=owner, role="owner")
    )
    return kitchen_id


def _join(world: World, kitchen_id: UUID, user_id: UUID) -> None:
    world.kitchens.memberships.append(
        MembershipRecord(kitchen_id=kitchen_id, user_id=user_id, role="member")
    )


def _personal(world: World, owner: UUID, name: str, names: set[str] | None = None) -> UUID:
    notebook = Notebook(id=uuid4(), name=name)
    world.notebooks.create(notebook)
    world.notebooks.add_owner(notebook.id, owner)
    if names:
        world.catalog.names[notebook.id] = set(names)
    return notebook.id


def _kitchen_notebook(world: World, kitchen_id: UUID, name: str, owner: UUID) -> UUID:
    notebook = Notebook(id=uuid4(), name=name, kitchen_id=kitchen_id, owner_user_id=owner)
    world.notebooks.create(notebook)
    return notebook.id


def _default(world: World) -> GetDefaultNotebookService:
    return GetDefaultNotebookService(world.notebooks, world.defaults, world.prefs, world.catalog)


def _list_kitchen(world: World) -> ListKitchenNotebooksService:
    return ListKitchenNotebooksService(world.kitchens, world.notebooks, world.prefs, world.catalog)


def _resolve(world: World) -> ResolveCaptureNotebookService:
    return ResolveCaptureNotebookService(
        world.kitchens,
        world.notebooks,
        world.defaults,
        world.prefs,
        world.catalog,
        world.committer,
    )


# --- The default personal notebook (US1, FR-007) ---


def test_first_default_call_creates_seeded_personal_notebook_and_sets_default() -> None:
    ana = uuid4()
    world = _world({ana: "ana"}, {ana: "en"})

    view = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert view.name == "ana's Notebook"
    assert view.kind == "personal"
    assert view.access == "owner"
    assert view.owner_alias == "ana"
    assert view.kitchen_id is None
    assert view.is_default is True
    assert world.notebooks.roles[(view.id, ana)] == "owner"
    assert world.notebooks.defaults[ana] == view.id


def test_second_default_call_returns_same_notebook_and_creates_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    first = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    second = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert second.id == first.id
    assert len(world.notebooks.notebooks) == 1


def test_default_set_by_another_call_under_the_lock_creates_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    winner = _personal(world, ana, "ana's Notebook")
    world.notebooks.defaults[ana] = winner

    view = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert view.id == winner
    assert len(world.notebooks.notebooks) == 1


def test_deleted_default_is_recreated_on_next_call() -> None:
    ana = uuid4()
    world = _world({ana: "ana"}, {ana: "en"})
    first = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    world.notebooks.delete(first.id)
    second = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert second.id != first.id
    assert second.name == "ana's Notebook"
    assert world.notebooks.defaults[ana] == second.id


def test_new_default_starts_with_the_catalog_of_joined_personal_notebooks() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    family = _personal(world, ben, "ben's Family", {"onion", "garlic"})
    world.notebooks.roles[(family, ana)] = "member"

    view = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert world.catalog.names_for_notebook(view.id) == ["garlic", "onion"]


def test_default_without_alias_raises_and_creates_nothing() -> None:
    ana = uuid4()
    world = _world({})

    with pytest.raises(AliasRequiredError):
        _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))
    assert world.notebooks.notebooks == {}


# --- A kitchen's first notebook (US2, FR-008a) ---


def test_first_open_creates_kitchen_notebook_owned_by_the_opener() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"}, {ben: "en"})
    home = _kitchen(world, ana)
    _join(world, home, ben)
    _personal(world, ben, "ben's Notebook", {"onion"})

    views = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ben, kitchen_id=home)
    )

    assert len(views) == 1
    view = views[0]
    assert view.name == "ben's (Home) Notebook"
    assert view.kind == "kitchen"
    assert view.access == "kitchen_member"
    assert view.owner_alias == "ben"
    assert view.kitchen_id == home
    assert view.is_default is False
    assert world.notebooks.notebooks[view.id].owner_user_id == ben
    assert not any(notebook_id == view.id for notebook_id, _ in world.notebooks.roles)
    assert world.catalog.names_for_notebook(view.id) == ["onion"]


def test_second_open_lists_the_same_notebook_and_creates_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana)
    first = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home)
    )

    world.notebooks.calls.clear()
    second = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert [view.id for view in second] == [view.id for view in first]
    assert "create" not in world.notebooks.calls


def test_first_open_takes_the_kitchen_lock_before_the_second_read() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana)

    _list_kitchen(world).execute(ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home))

    assert world.notebooks.calls[:3] == ["kitchen_ids_for", "lock_kitchen", "kitchen_ids_for"]


def test_archived_kitchen_without_notebook_lists_nothing_and_creates_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana, archived=True)

    views = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert views == []
    assert "create" not in world.notebooks.calls


def test_archived_kitchen_still_lists_its_existing_notebook() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana, archived=True)
    existing = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)

    views = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert [view.id for view in views] == [existing]
    assert views[0].kitchen_is_archived is True


def test_non_member_and_missing_kitchen_get_the_same_not_found() -> None:
    ana, carl = uuid4(), uuid4()
    world = _world({ana: "ana", carl: "carl"})
    home = _kitchen(world, ana)

    with pytest.raises(KitchenNotFoundError):
        _list_kitchen(world).execute(
            ListKitchenNotebooksCommand(actor_user_id=carl, kitchen_id=home)
        )
    with pytest.raises(KitchenNotFoundError):
        _list_kitchen(world).execute(
            ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=uuid4())
        )


# --- Names follow the language of the person who causes them ---


def test_default_notebook_is_named_in_spanish_for_a_spanish_account() -> None:
    ana = uuid4()
    world = _world({ana: "ana"}, {ana: "es"})

    view = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert view.name == "Cuaderno de ana"


def test_default_notebook_is_named_in_spanish_when_the_account_saved_no_language() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})

    view = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))

    assert view.name == "Cuaderno de ana"


def test_kitchen_notebook_takes_the_language_of_the_member_who_opens_it() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"}, {ana: "en", ben: "es"})
    home = _kitchen(world, ana, "Casa")
    _join(world, home, ben)

    views = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ben, kitchen_id=home)
    )

    assert [view.name for view in views] == ["Cuaderno de ben (Casa)"]


# --- The capture notebook step (US3, FR-009 to FR-011) ---


def test_kitchen_capture_with_no_notebook_creates_one_and_commits_once() -> None:
    ana = uuid4()
    world = _world({ana: "ana"}, {ana: "en"})
    my_kitchen = _kitchen(world, ana, "My kitchen")
    _personal(world, ana, "ana's Notebook", {"onion"})
    world.notebooks.calls.clear()

    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=my_kitchen)
    )

    notebook = world.notebooks.notebooks[result.notebook_id]
    assert result.created is True
    assert notebook.name == "ana's (My kitchen) Notebook"
    assert notebook.owner_user_id == ana
    assert notebook.kitchen_id == my_kitchen
    assert world.catalog.names_for_notebook(result.notebook_id) == ["onion"]
    assert world.notebooks.calls[:3] == [
        "user_kitchen_notebook",
        "lock_kitchen",
        "user_kitchen_notebook",
    ]
    assert world.committer.commits == 1


def test_kitchen_capture_uses_a_notebook_created_under_the_lock_without_commit() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    my_kitchen = _kitchen(world, ana, "My kitchen")
    racing = _kitchen_notebook(world, my_kitchen, "ana's (My kitchen) Notebook", ana)
    world.notebooks.hide_next_kitchen_read = True

    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=my_kitchen)
    )

    assert result == CaptureNotebook(notebook_id=racing, created=False)
    assert world.committer.commits == 0


def test_kitchen_capture_with_user_notebook_uses_it_without_creating() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    home = _kitchen(world, ana)
    _join(world, home, ben)
    _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    ben_notebook = _kitchen_notebook(world, home, "ben's (Home) Notebook", ben)

    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ben, kitchen_id=home)
    )

    assert result == CaptureNotebook(notebook_id=ben_notebook, created=False)
    assert "lock_kitchen" not in world.notebooks.calls
    assert world.committer.commits == 0


def test_kitchen_capture_auto_selects_user_notebook_or_creates_one() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    home = _kitchen(world, ana)
    _join(world, home, ben)
    ana_notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    ben_notebook = _kitchen_notebook(world, home, "ben's (Home) Notebook", ben)

    # Ana should use her own notebook automatically
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=home)
    )
    assert result == CaptureNotebook(notebook_id=ana_notebook, created=False)

    # Ben should use his own notebook automatically
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ben, kitchen_id=home)
    )
    assert result == CaptureNotebook(notebook_id=ben_notebook, created=False)

    # When Ana explicitly picks Ben's notebook, use it
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(
            actor_user_id=ana, kitchen_id=home, picked_notebook_id=ben_notebook
        )
    )
    assert result == CaptureNotebook(notebook_id=ben_notebook, created=False)

    # A notebook of another kitchen is not a pick
    stranger = _kitchen_notebook(world, _kitchen(world, ana), "elsewhere", ana)
    with pytest.raises(NotebookNotFoundError):
        _resolve(world).execute(
            ResolveCaptureNotebookCommand(
                actor_user_id=ana, kitchen_id=home, picked_notebook_id=stranger
            )
        )


def test_kitchen_capture_creates_user_notebook_on_first_capture() -> None:
    ana, ben, carl = uuid4(), uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben", carl: "carl"})
    home = _kitchen(world, ana)
    _join(world, home, ben)
    _join(world, home, carl)
    ana_notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)

    # Ben captures without having his own notebook yet
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ben, kitchen_id=home)
    )
    assert result.created is True
    ben_notebook = result.notebook_id
    assert ben_notebook != ana_notebook
    assert world.committer.commits == 1

    # Ben's second capture uses the created notebook
    world.committer.commits = 0
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ben, kitchen_id=home)
    )
    assert result == CaptureNotebook(notebook_id=ben_notebook, created=False)
    assert world.committer.commits == 0

    # Carl captures and gets his own notebook created
    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=carl, kitchen_id=home)
    )
    assert result.created is True
    assert result.notebook_id != ana_notebook
    assert result.notebook_id != ben_notebook


def test_kitchen_capture_by_non_member_or_in_missing_kitchen_creates_nothing() -> None:
    ana, carl = uuid4(), uuid4()
    world = _world({ana: "ana", carl: "carl"})
    home = _kitchen(world, ana)

    with pytest.raises(KitchenNotFoundError):
        _resolve(world).execute(ResolveCaptureNotebookCommand(actor_user_id=carl, kitchen_id=home))
    with pytest.raises(KitchenNotFoundError):
        _resolve(world).execute(
            ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=uuid4())
        )
    assert world.notebooks.notebooks == {}


def test_archived_kitchen_refuses_capture_before_reading_notebooks() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana, archived=True)
    _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    world.notebooks.calls.clear()

    with pytest.raises(KitchenArchivedError):
        _resolve(world).execute(ResolveCaptureNotebookCommand(actor_user_id=ana, kitchen_id=home))
    assert "kitchen_ids_for" not in world.notebooks.calls
    assert len(world.notebooks.notebooks) == 1


def test_personal_capture_with_no_notebook_creates_the_default_and_commits() -> None:
    ana = uuid4()
    world = _world({ana: "ana"}, {ana: "en"})

    result = _resolve(world).execute(ResolveCaptureNotebookCommand(actor_user_id=ana))

    assert result.created is True
    assert world.notebooks.notebooks[result.notebook_id].name == "ana's Notebook"
    assert world.notebooks.defaults[ana] == result.notebook_id
    assert world.committer.commits == 1


def test_personal_capture_with_two_notebooks_needs_a_pick_of_its_own_notebooks() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    own = _personal(world, ana, "ana's Notebook")
    family = _personal(world, ben, "ben's Family")
    world.notebooks.roles[(family, ana)] = "member"
    home = _kitchen(world, ana)
    kitchen_notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)

    with pytest.raises(NotebookChoiceRequiredError) as raised:
        _resolve(world).execute(ResolveCaptureNotebookCommand(actor_user_id=ana))
    assert raised.value.candidate_ids == [own, family]

    with pytest.raises(NotebookNotFoundError):
        _resolve(world).execute(
            ResolveCaptureNotebookCommand(actor_user_id=ana, picked_notebook_id=kitchen_notebook)
        )

    result = _resolve(world).execute(
        ResolveCaptureNotebookCommand(actor_user_id=ana, picked_notebook_id=family)
    )
    assert result == CaptureNotebook(notebook_id=family, created=False)


# --- Reads (US4, FR-014 to FR-017) ---


def test_my_list_has_my_personal_and_kitchen_notebooks_oldest_first_and_creates_nothing() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    default = _default(world).execute(GetDefaultNotebookCommand(actor_user_id=ana))
    family = _personal(world, ben, "ben's Family")
    world.notebooks.roles[(family, ana)] = "member"
    home = _kitchen(world, ana)
    home_notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    bens = _kitchen(world, ben, "Bens")
    _kitchen_notebook(world, bens, "ben's (Bens) Notebook", ben)
    world.notebooks.calls.clear()

    views = ListMyNotebooksService(world.notebooks).execute(
        ListMyNotebooksCommand(actor_user_id=ana)
    )

    assert [view.id for view in views] == [default.id, family, home_notebook]
    assert [view.access for view in views] == ["owner", "member", "kitchen_member"]
    assert [view.kind for view in views] == ["personal", "personal", "kitchen"]
    assert [view.is_default for view in views] == [True, False, False]
    assert "create" not in world.notebooks.calls


def test_get_notebook_by_id_for_personal_and_kitchen_members() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    family = _personal(world, ben, "ben's Family")
    world.notebooks.roles[(family, ana)] = "member"
    home = _kitchen(world, ana)
    _join(world, home, ben)
    kitchen_notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)

    family_view = GetNotebookService(world.notebooks).execute(
        GetNotebookCommand(actor_user_id=ana, notebook_id=family)
    )
    kitchen_view = GetNotebookService(world.notebooks).execute(
        GetNotebookCommand(actor_user_id=ben, notebook_id=kitchen_notebook)
    )

    assert family_view.access == "member"
    assert family_view.owner_alias == "ben"
    assert kitchen_view == NotebookView(
        id=kitchen_notebook,
        name="ana's (Home) Notebook",
        kind="kitchen",
        access="kitchen_member",
        owner_alias="ana",
        kitchen_id=home,
        kitchen_is_archived=False,
        is_default=False,
        recipe_count=0,
    )


def test_personal_notebook_is_not_found_for_a_kitchen_mate_or_stranger() -> None:
    ana, ben, carl = uuid4(), uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben", carl: "carl"})
    ben_notebook = _personal(world, ben, "ben's Notebook")
    home = _kitchen(world, ben)
    _join(world, home, ana)
    _join(world, home, carl)
    service = GetNotebookService(world.notebooks)

    with pytest.raises(NotebookNotFoundError):
        service.execute(GetNotebookCommand(actor_user_id=ana, notebook_id=ben_notebook))
    with pytest.raises(NotebookNotFoundError):
        service.execute(GetNotebookCommand(actor_user_id=carl, notebook_id=ben_notebook))
    with pytest.raises(NotebookNotFoundError):
        service.execute(GetNotebookCommand(actor_user_id=ben, notebook_id=uuid4()))


def test_kitchen_notebook_is_not_found_for_a_person_outside_its_kitchen() -> None:
    ana, carl = uuid4(), uuid4()
    world = _world({ana: "ana", carl: "carl"})
    home = _kitchen(world, ana)
    notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)

    with pytest.raises(NotebookNotFoundError):
        GetNotebookService(world.notebooks).execute(
            GetNotebookCommand(actor_user_id=carl, notebook_id=notebook)
        )


def test_kitchen_list_holds_only_that_kitchens_notebooks() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana)
    other = _kitchen(world, ana, "Other")
    mine = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    _kitchen_notebook(world, other, "ana's (Other) Notebook", ana)
    _personal(world, ana, "ana's Notebook")

    views = _list_kitchen(world).execute(
        ListKitchenNotebooksCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert [view.id for view in views] == [mine]
