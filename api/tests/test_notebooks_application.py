"""Notebook use cases against fake ports (spec 055 FR-002, FR-005, FR-010, SC-002, SC-005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.kitchens import KitchenRecord, MembershipRecord
from application.notebooks import (
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    GetKitchenNotebookCommand,
    GetKitchenNotebookService,
    GetMemberNotebookCommand,
    GetMemberNotebookService,
)
from application.ports import KitchenAccessGrant, UserPreferencesRecord
from domain.errors import KitchenNotFoundError, NotebookNotFoundError
from domain.notebook import Notebook


@dataclass
class FakeNotebookRepo:
    rows: dict[UUID, Notebook] = field(default_factory=dict)
    defaults: dict[UUID, UUID | None] = field(default_factory=dict)

    def get(self, notebook_id: UUID) -> Notebook | None:
        return self.rows.get(notebook_id)

    def for_kitchen(self, kitchen_id: UUID) -> Notebook | None:
        return next((n for n in self.rows.values() if n.kitchen_id == kitchen_id), None)

    def for_member(self, user_id: UUID) -> Notebook | None:
        default_id = self.defaults.get(user_id)
        return self.rows.get(default_id) if default_id is not None else None

    def create(self, notebook: Notebook) -> None:
        if notebook.kitchen_id is not None and self.for_kitchen(notebook.kitchen_id):
            return
        self.rows[notebook.id] = notebook

    def delete(self, notebook_id: UUID) -> None:
        """ON DELETE SET NULL on users.default_notebook_id."""
        del self.rows[notebook_id]
        for user_id, default_id in self.defaults.items():
            if default_id == notebook_id:
                self.defaults[user_id] = None


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
class FakePrefs:
    aliases: dict[UUID, str]

    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None:
        alias = self.aliases.get(user_id)
        return UserPreferencesRecord(
            id=user_id, email="x@example.com", language=None, theme=None, alias=alias
        )


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


def _default_service(
    repo: FakeNotebookRepo, user_id: UUID, alias: str = "ana"
) -> tuple[GetDefaultNotebookService, FakeUserDefaultNotebook]:
    defaults = FakeUserDefaultNotebook(repo)
    return GetDefaultNotebookService(repo, defaults, FakePrefs({user_id: alias})), defaults


def test_first_default_call_creates_notebook_and_sets_default() -> None:
    repo = FakeNotebookRepo()
    user = uuid4()
    service, _ = _default_service(repo, user)

    notebook = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))

    assert notebook.kind == "member"
    assert notebook.user_id == user
    assert notebook.name == "ana's Notebook"
    assert repo.defaults[user] == notebook.id
    assert len(repo.rows) == 1


def test_second_default_call_returns_same_notebook() -> None:
    repo = FakeNotebookRepo()
    user = uuid4()
    service, defaults = _default_service(repo, user)

    first = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))
    second = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))

    assert first.id == second.id
    assert len(repo.rows) == 1
    # The second call reads without taking the row lock.
    assert defaults.locks == 1


def test_first_call_that_finds_default_set_under_lock_creates_nothing() -> None:
    """A simultaneous first call set the default between the read and the lock."""
    repo = FakeNotebookRepo()
    user = uuid4()
    winner = Notebook(id=uuid4(), user_id=user, name="ana's Notebook")
    repo.rows[winner.id] = winner

    class RacingRepo(FakeNotebookRepo):
        def for_member(self, user_id: UUID) -> Notebook | None:
            return None

    racing = RacingRepo(rows=repo.rows, defaults={user: winner.id})
    service, _ = _default_service(racing, user)

    notebook = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))

    assert notebook.id == winner.id
    assert len(racing.rows) == 1


def test_deleted_default_is_recreated_on_next_call() -> None:
    repo = FakeNotebookRepo()
    user = uuid4()
    service, _ = _default_service(repo, user)
    first = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))

    repo.delete(first.id)
    assert repo.defaults[user] is None

    second = service.execute(GetDefaultNotebookCommand(actor_user_id=user, user_id=user))
    assert second.id != first.id
    assert second.name == "ana's Notebook"
    assert repo.defaults[user] == second.id


def test_default_notebook_of_another_member_is_not_found() -> None:
    repo = FakeNotebookRepo()
    owner, other = uuid4(), uuid4()
    service, _ = _default_service(repo, owner)

    with pytest.raises(NotebookNotFoundError):
        service.execute(GetDefaultNotebookCommand(actor_user_id=other, user_id=owner))
    assert repo.rows == {}


def test_member_notebook_by_id_owner_only() -> None:
    repo = FakeNotebookRepo()
    owner, other = uuid4(), uuid4()
    notebook = Notebook(id=uuid4(), user_id=owner, name="ana's Notebook")
    repo.rows[notebook.id] = notebook
    service = GetMemberNotebookService(repo)

    found = service.execute(
        GetMemberNotebookCommand(actor_user_id=owner, user_id=owner, notebook_id=notebook.id)
    )
    assert found.id == notebook.id

    with pytest.raises(NotebookNotFoundError):
        service.execute(
            GetMemberNotebookCommand(actor_user_id=other, user_id=owner, notebook_id=notebook.id)
        )
    with pytest.raises(NotebookNotFoundError):
        service.execute(
            GetMemberNotebookCommand(actor_user_id=other, user_id=other, notebook_id=notebook.id)
        )
    with pytest.raises(NotebookNotFoundError):
        service.execute(
            GetMemberNotebookCommand(actor_user_id=owner, user_id=owner, notebook_id=uuid4())
        )


def test_kitchen_notebook_for_member_and_not_found_for_non_member() -> None:
    kitchens = FakeKitchenRepo()
    owner, outsider = uuid4(), uuid4()
    kitchen_id = uuid4()
    kitchens.kitchens[kitchen_id] = KitchenRecord(id=kitchen_id, name="Home", owner_id=owner)
    kitchens.memberships.append(
        MembershipRecord(kitchen_id=kitchen_id, user_id=owner, role="owner")
    )
    notebooks = FakeNotebookRepo()
    existing = Notebook(id=uuid4(), kitchen_id=kitchen_id)
    notebooks.rows[existing.id] = existing
    service = GetKitchenNotebookService(kitchens, notebooks)

    view = service.execute(GetKitchenNotebookCommand(actor_user_id=owner, kitchen_id=kitchen_id))
    assert view.notebook.id == existing.id
    assert view.kitchen_name == "Home"
    assert view.is_archived is False

    with pytest.raises(KitchenNotFoundError):
        service.execute(GetKitchenNotebookCommand(actor_user_id=outsider, kitchen_id=kitchen_id))
    with pytest.raises(KitchenNotFoundError):
        service.execute(GetKitchenNotebookCommand(actor_user_id=owner, kitchen_id=uuid4()))


def test_kitchen_without_notebook_gets_one_on_first_read() -> None:
    """The signup personal kitchen has no notebook until its first read."""
    kitchens = FakeKitchenRepo()
    owner = uuid4()
    kitchen_id = uuid4()
    kitchens.kitchens[kitchen_id] = KitchenRecord(id=kitchen_id, name="My kitchen", owner_id=owner)
    kitchens.memberships.append(
        MembershipRecord(kitchen_id=kitchen_id, user_id=owner, role="owner")
    )
    notebooks = FakeNotebookRepo()
    service = GetKitchenNotebookService(kitchens, notebooks)

    first = service.execute(GetKitchenNotebookCommand(actor_user_id=owner, kitchen_id=kitchen_id))
    second = service.execute(GetKitchenNotebookCommand(actor_user_id=owner, kitchen_id=kitchen_id))

    assert first.notebook.kitchen_id == kitchen_id
    assert first.notebook.id == second.notebook.id
    assert len(notebooks.rows) == 1
