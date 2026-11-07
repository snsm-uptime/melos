"""Fake ports for notebook sharing use cases (spec 057). `log` records calls in order."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from application.ports import (
    EmailMessage,
    NotebookFacts,
    NotebookInviteRecord,
    NotebookMemberRecord,
    UserPreferencesRecord,
)
from application.signin import AuthUserRecord
from domain.errors import NotebookNotFoundError
from domain.ingredient_catalog import CatalogIndex
from domain.notebook import Notebook

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass
class FakeNotebooks:
    log: list[str] = field(default_factory=list)
    notebooks: dict[UUID, Notebook] = field(default_factory=dict)
    # Insertion order is join order.
    roles: dict[tuple[UUID, UUID], str] = field(default_factory=dict)
    aliases: dict[UUID, str | None] = field(default_factory=dict)
    kitchen_people: set[tuple[UUID, UUID]] = field(default_factory=set)
    locked: list[UUID] = field(default_factory=list)
    # Runs once the lock is held, as another request that got there first would.
    on_lock: Callable[[UUID], None] | None = None

    def personal(self, owner: UUID, name: str = "ana's Notebook") -> UUID:
        notebook = Notebook(id=uuid4(), name=name)
        self.notebooks[notebook.id] = notebook
        self.roles[(notebook.id, owner)] = "owner"
        return notebook.id

    def kitchen(self, person: UUID) -> UUID:
        notebook = Notebook(id=uuid4(), name="Home", kitchen_id=uuid4())
        self.notebooks[notebook.id] = notebook
        self.kitchen_people.add((notebook.id, person))
        return notebook.id

    def get(self, notebook_id: UUID) -> Notebook | None:
        return self.notebooks.get(notebook_id)

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        notebook = self.notebooks.get(notebook_id)
        if notebook is None:
            return None
        return NotebookFacts(
            notebook=notebook,
            role=self.roles.get((notebook_id, user_id)),  # type: ignore[arg-type]
            in_kitchen=(notebook_id, user_id) in self.kitchen_people,
            owner_alias=None,
            kitchen_is_archived=None,
            is_default=False,
            recipe_count=0,
        )

    def lock_notebook(self, notebook_id: UUID) -> None:
        self.log.append("lock")
        self.locked.append(notebook_id)
        if notebook_id not in self.notebooks:
            raise NotebookNotFoundError()
        if self.on_lock is not None:
            self.on_lock(notebook_id)

    def members_of(self, notebook_id: UUID) -> list[NotebookMemberRecord]:
        rows = [(u, r) for (n, u), r in self.roles.items() if n == notebook_id]
        joined = {u: EPOCH + timedelta(seconds=i) for i, (u, _) in enumerate(rows)}
        rows.sort(key=lambda row: row[1] != "owner")
        return [
            NotebookMemberRecord(
                user_id=u,
                alias=self.aliases.get(u),
                role=r,  # type: ignore[arg-type]
                joined_at=joined[u],
            )
            for u, r in rows
        ]

    def owned_personal_ids(self, user_id: UUID) -> list[UUID]:
        # Newest first, so a test sees that the service does the sorting.
        owned = [
            n
            for (n, u), r in self.roles.items()
            if u == user_id and r == "owner" and self.notebooks[n].kitchen_id is None
        ]
        return sorted(owned, reverse=True)

    def make_owner(self, notebook_id: UUID, user_id: UUID) -> None:
        self.log.append("make_owner")
        # The partial unique index allows one owner per notebook.
        assert "owner" not in [r for (n, _), r in self.roles.items() if n == notebook_id]
        self.roles[(notebook_id, user_id)] = "owner"

    def delete(self, notebook_id: UUID) -> None:
        self.log.append("delete")
        del self.notebooks[notebook_id]
        for key in [key for key in self.roles if key[0] == notebook_id]:
            del self.roles[key]

    def role_of(self, notebook_id: UUID, user_id: UUID) -> str | None:
        return self.roles.get((notebook_id, user_id))

    def add_member(self, notebook_id: UUID, user_id: UUID) -> None:
        self.log.append("add_member")
        self.roles[(notebook_id, user_id)] = "member"

    def delete_membership(self, notebook_id: UUID, user_id: UUID) -> bool:
        self.log.append("delete_membership")
        return self.roles.pop((notebook_id, user_id), None) is not None


@dataclass
class FakeInvites:
    log: list[str] = field(default_factory=list)
    rows: dict[UUID, NotebookInviteRecord] = field(default_factory=dict)
    # The next claim finds the row taken, and this runs as the winning request would.
    lose_next_claim_to: object | None = None

    def create(
        self,
        *,
        invite_id: UUID,
        notebook_id: UUID,
        email: str,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> None:
        self.log.append("create")
        self.rows[invite_id] = NotebookInviteRecord(
            id=invite_id,
            notebook_id=notebook_id,
            email=email,
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
            used_at=None,
        )

    def delete_open_for_email(self, notebook_id: UUID, email: str) -> None:
        self.log.append("delete_open")
        for row in list(self.rows.values()):
            if row.notebook_id == notebook_id and row.email == email and row.used_at is None:
                del self.rows[row.id]

    def list_unused(self, notebook_id: UUID) -> list[NotebookInviteRecord]:
        rows = [r for r in self.rows.values() if r.notebook_id == notebook_id and not r.used_at]
        return sorted(rows, key=lambda r: r.expires_at, reverse=True)

    def get(self, notebook_id: UUID, invite_id: UUID) -> NotebookInviteRecord | None:
        row = self.rows.get(invite_id)
        return row if row is not None and row.notebook_id == notebook_id else None

    def get_by_token_hash(self, token_hash: str) -> NotebookInviteRecord | None:
        return next((r for r in self.rows.values() if r.token_hash == token_hash), None)

    def rotate(
        self, invite_id: UUID, *, token_hash: str, invited_by: UUID, expires_at: datetime
    ) -> None:
        self.log.append("rotate")
        self.rows[invite_id] = replace(
            self.rows[invite_id],
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )

    def delete(self, notebook_id: UUID, invite_id: UUID) -> bool:
        row = self.get(notebook_id, invite_id)
        if row is None or row.used_at is not None:
            return False
        del self.rows[invite_id]
        return True

    def claim(self, invite_id: UUID, *, used_at: datetime) -> bool:
        self.log.append("claim")
        if self.lose_next_claim_to is not None:
            winner, self.lose_next_claim_to = self.lose_next_claim_to, None
            winner()  # type: ignore[operator]
            return False
        row = self.rows[invite_id]
        if row.used_at is not None:
            return False
        self.rows[invite_id] = replace(row, used_at=used_at)
        return True


@dataclass
class FakePeople:
    """Accounts: AuthUserRepository, PreferencesRepository and the verification read."""

    users: dict[UUID, AuthUserRecord] = field(default_factory=dict)
    prefs: dict[UUID, UserPreferencesRecord] = field(default_factory=dict)
    verified: dict[UUID, datetime | None] = field(default_factory=dict)

    def add(self, email: str, *, alias: str | None = "ana", language: str | None = None) -> UUID:
        user_id = uuid4()
        self.users[user_id] = AuthUserRecord(id=user_id, email=email, password_hash="x")
        self.prefs[user_id] = UserPreferencesRecord(
            id=user_id, email=email, language=language, theme=None, alias=alias
        )
        return user_id

    def get_by_email(self, email: str) -> AuthUserRecord | None:
        return next((u for u in self.users.values() if u.email == email), None)

    def get_by_id(self, user_id: UUID) -> AuthUserRecord | None:
        return self.users.get(user_id)

    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None:
        return self.prefs.get(user_id)

    def get_user_verified_at(self, user_id: UUID) -> datetime | None:
        return self.verified.get(user_id)


@dataclass
class FakeCatalog:
    log: list[str] = field(default_factory=list)
    person: dict[UUID, list[str]] = field(default_factory=dict)
    notebook: dict[UUID, list[str]] = field(default_factory=dict)

    def names_for_person(self, user_id: UUID) -> list[str]:
        self.log.append("names_for_person")
        return list(self.person.get(user_id, []))

    def index_for_notebook(self, notebook_id: UUID) -> CatalogIndex:
        return CatalogIndex.of_names(self.names_for_notebook(notebook_id))

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return list(self.notebook.get(notebook_id, []))

    def add_names(self, notebook_id: UUID, names: Sequence[str]) -> None:
        self.log.append("add_names")
        self.notebook.setdefault(notebook_id, []).extend(names)


@dataclass
class FakeMailer:
    sent: list[EmailMessage] = field(default_factory=list)
    fail: Exception | None = None

    def send(self, message: EmailMessage) -> None:
        if self.fail is not None:
            raise self.fail
        self.sent.append(message)


@dataclass
class FakeCommitter:
    log: list[str] = field(default_factory=list)
    commits: int = 0

    def commit(self) -> None:
        self.log.append("commit")
        self.commits += 1
