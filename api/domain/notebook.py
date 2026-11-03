"""Notebook rules (no FastAPI / SQLAlchemy).

A personal notebook belongs to people: one owner and any number of members.
A kitchen notebook belongs to one kitchen: its members read and write it, and
it stores one owner (the member who created it). Recipes and the ingredient
catalog point at the notebook id, never at the owner.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from domain.errors import (
    InvalidNotebookError,
    InvalidNotebookNameError,
    KitchenArchivedError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
    NotebookOwnerOnlyError,
)
from domain.preferences import name_language

NOTEBOOK_NAME_MAX_LENGTH = 200

NotebookKind = Literal["personal", "kitchen"]
NotebookRole = Literal["owner", "member"]
NotebookAccess = Literal["owner", "member", "kitchen_member"]


@dataclass(frozen=True, slots=True)
class JoinedMember:
    """A person's place in a personal notebook, as far as inheriting it goes."""

    user_id: UUID
    role: NotebookRole
    joined_at: datetime


def longest_standing(members: Iterable[JoinedMember]) -> UUID | None:
    """Who inherits a personal notebook: the earliest to join, or None if nobody is a member.

    The owner never counts. Two people can join at the same moment, so the id settles a tie.
    """
    return min(
        ((member.joined_at, member.user_id) for member in members if member.role != "owner"),
        default=(None, None),
    )[1]


@dataclass(frozen=True, slots=True)
class Notebook:
    id: UUID
    name: str
    kitchen_id: UUID | None = None
    # Origin label of a snapshot (spec 035). Only a kitchen notebook may carry one.
    source_notebook_id: UUID | None = None
    # The member who created a kitchen notebook (FR-002). A personal notebook keeps
    # its owner in notebook_membership instead.
    owner_user_id: UUID | None = None
    # Marks a snapshot for good, even after its label is cleared (spec 035 research R1).
    snapshot_key: UUID | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidNotebookError()
        if self.source_notebook_id is not None and self.kitchen_id is None:
            raise InvalidNotebookError()
        if self.source_notebook_id == self.id:
            raise InvalidNotebookError()
        if self.owner_user_id is not None and self.kitchen_id is None:
            raise InvalidNotebookError()
        if self.snapshot_key is not None and self.kitchen_id is None:
            raise InvalidNotebookError()

    @property
    def kind(self) -> NotebookKind:
        return "kitchen" if self.kitchen_id is not None else "personal"


def validate_notebook_name(raw: str) -> str:
    """The trimmed name a person gave a new notebook (S-059)."""
    name = raw.strip()
    if not name or len(name) > NOTEBOOK_NAME_MAX_LENGTH:
        raise InvalidNotebookNameError()
    return name


def default_notebook_name(alias: str, language: str | None) -> str:
    """Name of a person's default personal notebook, fixed at creation time, in their language."""
    if name_language(language) == "es":
        return f"Cuaderno de {alias}"
    return f"{alias}'s Notebook"


def kitchen_notebook_name(alias: str, kitchen_name: str, language: str | None) -> str:
    """Name of a kitchen notebook, fixed at creation time; it names the member who made it.

    Written in that member's language.
    """
    if name_language(language) == "es":
        return f"Cuaderno de {alias} ({kitchen_name})"
    return f"{alias}'s ({kitchen_name}) Notebook"


def notebook_access(
    kind: NotebookKind, role: NotebookRole | None, in_kitchen: bool
) -> NotebookAccess | None:
    """What the caller may do with a notebook, or None when they may not see it (FR-014 to FR-017).

    A personal notebook gives the caller's role; kitchen membership never counts.
    A kitchen notebook gives kitchen_member to members of its kitchen; a role never counts.
    """
    if kind == "personal":
        return role
    return "kitchen_member" if in_kitchen else None


def can_write_recipes(access: NotebookAccess, kitchen_is_archived: bool | None) -> bool:
    """Whether the caller may edit and delete the recipes of a notebook (spec 027 FR-005).

    The owner and members of a personal notebook may. A member of a kitchen may write its
    notebooks unless the kitchen is archived, which is read-only.
    """
    if access == "kitchen_member":
        return not kitchen_is_archived
    return True


def assert_can_manage(access: NotebookAccess, kitchen_is_archived: bool | None) -> None:
    """Refuse a caller who may see a notebook but not rename or delete it (spec 059 research R5).

    The owner of a personal notebook may, its members may not. A member of a kitchen may manage
    its notebooks unless the kitchen is archived.
    """
    if access == "member":
        raise NotebookOwnerOnlyError()
    if access == "kitchen_member" and kitchen_is_archived:
        raise KitchenArchivedError()


def choose_capture_notebook(candidates: list[UUID], picked: UUID | None) -> UUID | None:
    """The notebook a capture goes into, or None when the step must create one (FR-009, FR-011).

    With none or one candidate a pick is ignored. With several, the pick must be one of them.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if picked is None:
        raise NotebookChoiceRequiredError(list(candidates))
    if picked not in candidates:
        raise NotebookNotFoundError()
    return picked
